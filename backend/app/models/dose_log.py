import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.extensions import mongo

logger = logging.getLogger(__name__)


def get_dose_logs_collection():
    return mongo.get_db()["dose_logs"]


def create_dose_log_indexes():
    try:
        col = get_dose_logs_collection()
        # Unique: one log per (user, medicine, date, time)
        col.create_index(
            [("user_id", 1), ("medicine_id", 1), ("scheduled_date", 1), ("scheduled_time", 1)],
            unique=True,
            name="unique_dose_per_slot",
        )
        # For fast today queries
        col.create_index([("user_id", 1), ("scheduled_date", 1)], name="user_date")
        logger.info("dose_logs collection indexes ensured.")
    except Exception as e:
        logger.warning("Could not create dose_log indexes: %s", e)


def _utc_iso(value):
    """Return ISO 8601 string with +00:00 for any datetime (naive treated as UTC)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return value


def serialize_dose(log):
    if log is None:
        return None
    snap = log.get("medicine_snapshot", {})
    return {
        "id": str(log["_id"]),
        "user_id": log["user_id"],
        "medicine_id": log["medicine_id"],
        "scheduled_date": log["scheduled_date"],
        "scheduled_time": log["scheduled_time"],
        "scheduled_at": _utc_iso(log.get("scheduled_at")),
        "status": log.get("status", "pending"),
        "taken_at": _utc_iso(log.get("taken_at")),
        "was_late": log.get("was_late", False),
        "stock_decremented": log.get("stock_decremented", False),
        # medicine info from snapshot (may be overridden from live medicine data)
        "name": snap.get("name", ""),
        "dosage": snap.get("dosage", ""),
        "pills_per_dose": snap.get("pills_per_dose", 1),
        "food_instruction": snap.get("food_instruction", "any"),
        "created_at": _utc_iso(log.get("created_at")),
        "updated_at": _utc_iso(log.get("updated_at")),
    }


def get_today_doses(user_id: str, today_str: str) -> list:
    col = get_dose_logs_collection()
    return list(col.find({"user_id": user_id, "scheduled_date": today_str}))


def upsert_dose_log(
    user_id: str,
    medicine_id: str,
    scheduled_date: str,
    scheduled_time: str,
    scheduled_at_utc: datetime,
    snapshot: dict,
) -> dict:
    """
    Insert a dose log if it doesn't exist yet (lazy upsert).
    Returns the existing or newly created document.
    """
    col = get_dose_logs_collection()
    now = datetime.now(timezone.utc)
    filter_q = {
        "user_id": user_id,
        "medicine_id": medicine_id,
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
    }
    update_q = {
        "$setOnInsert": {
            "user_id": user_id,
            "medicine_id": medicine_id,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "scheduled_at": scheduled_at_utc,
            "status": "pending",
            "taken_at": None,
            "was_late": False,
            "stock_decremented": False,
            "medicine_snapshot": snapshot,
            "created_at": now,
            "updated_at": now,
        }
    }
    result = col.find_one_and_update(
        filter_q,
        update_q,
        upsert=True,
        return_document=True,  # returns the doc after the operation
    )
    if result is None:
        # find_one_and_update with upsert may return None in some edge cases; re-fetch
        result = col.find_one(filter_q)
    return result


def find_dose_by_id(dose_id: str, user_id: str):
    """Find a dose log by its _id and user_id. Returns None if not found or invalid id."""
    try:
        oid = ObjectId(dose_id)
    except (InvalidId, TypeError):
        return None
    return get_dose_logs_collection().find_one({"_id": oid, "user_id": user_id})


def mark_dose_taken(dose_id: str, user_id: str, now_utc: datetime, was_late: bool):
    """
    Atomically mark a pending/missed dose as taken.
    Uses a conditional filter so a race doesn't double-mark.
    Returns the updated doc or None if already taken / not found.
    """
    col = get_dose_logs_collection()
    return col.find_one_and_update(
        {
            "_id": ObjectId(dose_id),
            "user_id": user_id,
            "status": {"$in": ["pending", "missed"]},
        },
        {
            "$set": {
                "status": "taken",
                "taken_at": now_utc,
                "was_late": was_late,
                "updated_at": now_utc,
            }
        },
        return_document=True,
    )


def undo_dose_taken(dose_id: str, user_id: str):
    """
    Atomically revert a taken dose back to pending.
    Returns the updated doc or None if not taken / not found.
    """
    col = get_dose_logs_collection()
    now = datetime.now(timezone.utc)
    return col.find_one_and_update(
        {"_id": ObjectId(dose_id), "user_id": user_id, "status": "taken"},
        {
            "$set": {
                "status": "pending",
                "taken_at": None,
                "was_late": False,
                "stock_decremented": False,
                "updated_at": now,
            }
        },
        return_document=True,
    )
