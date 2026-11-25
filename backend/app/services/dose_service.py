import logging
from datetime import datetime, timezone, timedelta, date as dt_date
from pymongo.errors import DuplicateKeyError

from app.utils.timezone import get_app_timezone
from app.models.medicine import get_medicines_collection
from app.models.dose_log import (
    get_dose_logs_collection,
    upsert_dose_log,
    serialize_dose,
)

logger = logging.getLogger(__name__)

EARLY_WINDOW_MINUTES = 60   # cannot mark taken more than 60 min before scheduled time
LATE_THRESHOLD_MINUTES = 5  # taken more than 5 min after scheduled time = late


# Keep these aliases for backward-compat with blueprints/doses/routes.py
def get_timezone():
    return get_app_timezone()


def get_today_string() -> str:
    """Return today's date string (YYYY-MM-DD) in APP_TIMEZONE."""
    tz = get_app_timezone()
    return datetime.now(tz).strftime("%Y-%m-%d")


def get_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def compute_scheduled_at(date_str: str, time_str: str, tz) -> datetime:
    """
    Combine date_str (YYYY-MM-DD) and time_str (HH:MM) in the given timezone
    and return a timezone-aware UTC datetime.
    """
    year, month, day = map(int, date_str.split("-"))
    hour, minute = map(int, time_str.split(":"))
    local_dt = datetime(year, month, day, hour, minute, 0, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


def is_scheduled_on(med: dict, date_str: str, weekday: int) -> bool:
    """
    Return True if this medicine should have a dose on the given date/weekday.
    Rules: not soft-deleted, is_active, start_date <= date_str,
           no end_date OR date_str <= end_date,
           daily OR weekday in days_of_week. (0=Monday)
    """
    if med.get("deleted_at") is not None:
        return False
    if not med.get("is_active", True):
        return False
    if med.get("start_date", "") > date_str:
        return False
    end_date = med.get("end_date")
    if end_date and date_str > end_date:
        return False
    repeat_type = med.get("repeat_type", "daily")
    if repeat_type == "daily":
        return True
    if repeat_type == "specific_days":
        return weekday in med.get("days_of_week", [])
    return False


# Kept as alias used in some old call-sites
def is_scheduled_today(med: dict, today_str: str, today_weekday: int) -> bool:
    return is_scheduled_on(med, today_str, today_weekday)


def _ensure_logs_for_user_and_date(user_id: str, date_str: str, tz) -> int:
    """
    Ensure dose logs exist for every medicine belonging to user_id on date_str.
    Uses a cursor so we never load all medicines into memory.
    Returns the number of new logs created.
    """
    year, month, day = map(int, date_str.split("-"))
    weekday = dt_date(year, month, day).weekday()

    medicines_col = get_medicines_collection()
    cursor = medicines_col.find(
        {"user_id": user_id, "deleted_at": None, "is_active": True},
        batch_size=50,
    )
    created = 0
    for med in cursor:
        if not is_scheduled_on(med, date_str, weekday):
            continue
        med_id = str(med["_id"])
        snapshot = {
            "name": med["name"],
            "dosage": med["dosage"],
            "pills_per_dose": med["pills_per_dose"],
            "food_instruction": med.get("food_instruction", "any"),
        }
        for time_str in med.get("times", []):
            scheduled_at_utc = compute_scheduled_at(date_str, time_str, tz)
            try:
                log = upsert_dose_log(
                    user_id=user_id,
                    medicine_id=med_id,
                    scheduled_date=date_str,
                    scheduled_time=time_str,
                    scheduled_at_utc=scheduled_at_utc,
                    snapshot=snapshot,
                )
                # upsert returns existing doc if it already existed (no $setOnInsert fired)
                # We know it's new if created_at == updated_at AND is very recent — but
                # the simplest check is whether the doc existed before: if find_one_and_update
                # inserts, the returned doc will have been_created, but mongomock and pymongo
                # both return the doc. We track "created" optimistically; deduplication is safe.
                if log and log.get("status") == "pending" and log.get("missed_at") is None:
                    # Only count newly inserted ones (heuristic: created_at ~= updated_at ~= now)
                    created_at = log.get("created_at")
                    updated_at = log.get("updated_at")
                    if created_at and updated_at and created_at == updated_at:
                        created += 1
            except DuplicateKeyError:
                pass  # Already exists — idempotent
    return created


def ensure_logs_for_all_users(date_str: str, tz=None) -> int:
    """
    For every user who has at least one medicine, ensure logs exist for date_str.
    Uses distinct() to get user_ids without loading all medicines.
    Returns total count of new logs created across all users.
    """
    if tz is None:
        tz = get_app_timezone()
    medicines_col = get_medicines_collection()
    user_ids = medicines_col.distinct("user_id", {"deleted_at": None, "is_active": True})
    total = 0
    for uid in user_ids:
        try:
            total += _ensure_logs_for_user_and_date(uid, date_str, tz)
        except Exception as e:
            logger.warning("Error ensuring logs for user %s on %s: %s", uid, date_str, e)
    return total


def build_today_schedule(user_id: str) -> dict:
    """
    Build the full today schedule for a single user (dashboard endpoint).
    1. Ensure logs exist for today (lazy upsert).
    2. Fetch all logs for today sorted by scheduled_time.
    3. Return sorted dose list + summary.
    """
    tz = get_app_timezone()
    now_local = datetime.now(tz)
    today_str = now_local.strftime("%Y-%m-%d")

    _ensure_logs_for_user_and_date(user_id, today_str, tz)

    # Fetch all dose logs for today (including pre-existing ones from scheduler)
    dose_logs_col = get_dose_logs_collection()
    logs = list(dose_logs_col.find({"user_id": user_id, "scheduled_date": today_str}))

    doses = [serialize_dose(log) for log in logs]
    doses.sort(key=lambda d: d["scheduled_time"])

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
    if scheduled_at_utc.tzinfo is None:
        scheduled_at_utc = scheduled_at_utc.replace(tzinfo=timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    early_cutoff = scheduled_at_utc - timedelta(minutes=EARLY_WINDOW_MINUTES)
    if now_utc < early_cutoff:
        mins_until = int((scheduled_at_utc - now_utc).total_seconds() / 60)
        return (
            f"Too early to take this dose (more than {EARLY_WINDOW_MINUTES} minutes away; "
            f"due in {mins_until} min)."
        )
    return None


def decrement_stock(medicine_id: str, pills_per_dose: int) -> bool:
    medicines_col = get_medicines_collection()
    from bson import ObjectId
    med = medicines_col.find_one({"_id": ObjectId(medicine_id)}, {"pills_remaining": 1})
    if med is None or med.get("pills_remaining") is None:
        return False
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
