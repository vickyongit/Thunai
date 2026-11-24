import logging
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import current_app
from pymongo.errors import DuplicateKeyError

from app.models.medicine import get_medicines_collection
from app.models.dose_log import (
    get_dose_logs_collection,
    get_today_doses,
    upsert_dose_log,
    serialize_dose,
)

logger = logging.getLogger(__name__)

EARLY_WINDOW_MINUTES = 60   # cannot mark taken more than 60 min before scheduled time
LATE_THRESHOLD_MINUTES = 5  # taken more than 5 min after scheduled time = late


def get_timezone() -> ZoneInfo:
    tz_name = current_app.config.get("APP_TIMEZONE", "Asia/Kolkata")
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning("Invalid APP_TIMEZONE '%s', falling back to Asia/Kolkata.", tz_name)
        return ZoneInfo("Asia/Kolkata")


def get_today_string() -> str:
    """Return today's date string (YYYY-MM-DD) in APP_TIMEZONE."""
    tz = get_timezone()
    return datetime.now(tz).strftime("%Y-%m-%d")


def get_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def compute_scheduled_at(date_str: str, time_str: str, tz: ZoneInfo) -> datetime:
    """
    Combine date_str (YYYY-MM-DD) and time_str (HH:MM) in the given timezone
    and return a timezone-aware UTC datetime.
    """
    from datetime import date as dt_date
    year, month, day = map(int, date_str.split("-"))
    hour, minute = map(int, time_str.split(":"))
    local_dt = datetime(year, month, day, hour, minute, 0, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def is_scheduled_today(med: dict, today_str: str, today_weekday: int) -> bool:
    """
    Return True if this medicine should have a dose today.
    Rules: not soft-deleted, is_active, start_date <= today,
           no end_date OR today <= end_date,
           daily OR today_weekday in days_of_week.
    """
    if med.get("deleted_at") is not None:
        return False
    if not med.get("is_active", True):
        return False
    if med.get("start_date", "") > today_str:
        return False
    end_date = med.get("end_date")
    if end_date and today_str > end_date:
        return False
    repeat_type = med.get("repeat_type", "daily")
    if repeat_type == "daily":
        return True
    if repeat_type == "specific_days":
        return today_weekday in med.get("days_of_week", [])
    return False


def build_today_schedule(user_id: str) -> dict:
    """
    Build the full today schedule:
    1. Query all active, non-deleted medicines for this user.
    2. Filter to those scheduled today.
    3. Lazy-upsert a dose_log for each (medicine, time) slot.
    4. Return sorted dose list + summary.
    """
    tz = get_timezone()
    now_local = datetime.now(tz)
    today_str = now_local.strftime("%Y-%m-%d")
    today_weekday = now_local.weekday()  # 0 = Monday

    medicines_col = get_medicines_collection()
    medicines = list(medicines_col.find({"user_id": user_id, "deleted_at": None, "is_active": True}))

    doses = []
    for med in medicines:
        if not is_scheduled_today(med, today_str, today_weekday):
            continue
        med_id = str(med["_id"])
        snapshot = {
            "name": med["name"],
            "dosage": med["dosage"],
            "pills_per_dose": med["pills_per_dose"],
            "food_instruction": med.get("food_instruction", "any"),
        }
        for time_str in med.get("times", []):
            scheduled_at_utc = compute_scheduled_at(today_str, time_str, tz)
            try:
                log = upsert_dose_log(
                    user_id=user_id,
                    medicine_id=med_id,
                    scheduled_date=today_str,
                    scheduled_time=time_str,
                    scheduled_at_utc=scheduled_at_utc,
                    snapshot=snapshot,
                )
            except DuplicateKeyError:
                # Race condition: another request inserted it; just fetch it
                from app.models.dose_log import get_dose_logs_collection
                log = get_dose_logs_collection().find_one({
                    "user_id": user_id,
                    "medicine_id": med_id,
                    "scheduled_date": today_str,
                    "scheduled_time": time_str,
                })
            if log:
                doses.append(serialize_dose(log))

    # Sort by scheduled_time
    doses.sort(key=lambda d: d["scheduled_time"])

    # Summary
    total = len(doses)
    taken = sum(1 for d in doses if d["status"] == "taken")
    missed = sum(1 for d in doses if d["status"] == "missed")
    pending = total - taken - missed

    now_utc = datetime.now(timezone.utc)
    server_time_iso = now_utc.astimezone(timezone.utc).isoformat()

    return {
        "date": today_str,
        "timezone": str(tz),
        "server_time": server_time_iso,
        "summary": {
            "total": total,
            "taken": taken,
            "pending": pending,
            "missed": missed,
        },
        "doses": doses,
    }


def validate_take_dose(dose: dict, now_utc: datetime, scheduled_at_utc: datetime):
    """
    Returns error string if the dose cannot be taken now, None if it can.
    If already taken, return the string 'ALREADY_TAKEN' (caller handles idempotent 200).
    """
    if dose.get("status") == "taken":
        return "ALREADY_TAKEN"
    # Ensure scheduled_at is timezone-aware
    if scheduled_at_utc.tzinfo is None:
        scheduled_at_utc = scheduled_at_utc.replace(tzinfo=timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    # Too early?
    early_cutoff = scheduled_at_utc - timedelta(minutes=EARLY_WINDOW_MINUTES)
    if now_utc < early_cutoff:
        mins_until = int((scheduled_at_utc - now_utc).total_seconds() / 60)
        return f"Too early to take this dose (more than {EARLY_WINDOW_MINUTES} minutes away; due in {mins_until} min)."
    return None


def decrement_stock(medicine_id: str, pills_per_dose: int) -> bool:
    """
    Decrement pills_remaining by pills_per_dose, never below 0.
    Only runs if pills_remaining is set (not None).
    Returns True if decremented, False if not applicable.
    """
    medicines_col = get_medicines_collection()
    from bson import ObjectId
    med = medicines_col.find_one({"_id": ObjectId(medicine_id)}, {"pills_remaining": 1})
    if med is None or med.get("pills_remaining") is None:
        return False
    # Use $max to clamp at 0: new = max(0, current - pills_per_dose)
    medicines_col.update_one(
        {"_id": ObjectId(medicine_id)},
        [
            {
                "$set": {
                    "pills_remaining": {
                        "$max": [0, {"$subtract": ["$pills_remaining", pills_per_dose]}]
                    },
                    "updated_at": datetime.now(timezone.utc),
                }
            }
        ],
    )
    return True


def restore_stock(medicine_id: str, pills_per_dose: int) -> bool:
    """
    Add pills_per_dose back to pills_remaining (undo stock decrement).
    Only runs if pills_remaining is set (not None).
    Returns True if restored, False if not applicable.
    """
    medicines_col = get_medicines_collection()
    from bson import ObjectId
    med = medicines_col.find_one({"_id": ObjectId(medicine_id)}, {"pills_remaining": 1})
    if med is None or med.get("pills_remaining") is None:
        return False
    medicines_col.update_one(
        {"_id": ObjectId(medicine_id)},
        {
            "$inc": {"pills_remaining": pills_per_dose},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    return True
