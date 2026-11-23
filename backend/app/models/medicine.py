import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.extensions import mongo

logger = logging.getLogger(__name__)

MAX_MEDICINES = 30


def get_medicines_collection():
    return mongo.get_db()["medicines"]


def create_medicine_indexes():
    try:
        col = get_medicines_collection()
        col.create_index([("user_id", 1), ("deleted_at", 1)])
        col.create_index([("user_id", 1), ("name", 1)])
        logger.info("Medicines collection indexes ensured.")
    except Exception as e:
        logger.warning("Could not create medicines indexes: %s", e)


def _iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize_medicine(med):
    if med is None:
        return None
    return {
        "id": str(med["_id"]),
        "user_id": str(med["user_id"]),
        "name": med["name"],
        "dosage": med["dosage"],
        "pills_per_dose": med["pills_per_dose"],
        "times": med["times"],
        "repeat_type": med["repeat_type"],
        "days_of_week": med.get("days_of_week", []),
        "start_date": med["start_date"],
        "end_date": med.get("end_date"),
        "food_instruction": med.get("food_instruction", "any"),
        "remarks": med.get("remarks"),
        "pills_remaining": med.get("pills_remaining"),
        "is_active": med.get("is_active", True),
        "created_at": _iso(med.get("created_at")),
        "updated_at": _iso(med.get("updated_at")),
    }


def get_user_medicines(user_id: str, active_only: bool = False) -> list:
    query = {"user_id": user_id, "deleted_at": None}
    if active_only:
        query["is_active"] = True
    col = get_medicines_collection()
    medicines = list(col.find(query).sort("name", 1))
    return [serialize_medicine(m) for m in medicines]


def count_user_medicines(user_id: str) -> int:
    return get_medicines_collection().count_documents({"user_id": user_id, "deleted_at": None})


def find_medicine_by_id(medicine_id: str, user_id: str):
    """Find by id AND user_id, only if not soft-deleted. Returns None otherwise."""
    try:
        oid = ObjectId(medicine_id)
    except (InvalidId, TypeError):
        return None
    return get_medicines_collection().find_one(
        {"_id": oid, "user_id": user_id, "deleted_at": None}
    )


def insert_medicine(user_id: str, fields: dict) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "name": fields["name"],
        "dosage": fields["dosage"],
        "pills_per_dose": fields["pills_per_dose"],
        "times": fields["times"],
        "repeat_type": fields["repeat_type"],
        "days_of_week": fields.get("days_of_week", []),
        "start_date": fields["start_date"],
        "end_date": fields.get("end_date"),
        "food_instruction": fields.get("food_instruction", "any"),
        "remarks": fields.get("remarks"),
        "pills_remaining": fields.get("pills_remaining"),
        "is_active": fields.get("is_active", True),
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    result = get_medicines_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def update_medicine(medicine_id: str, user_id: str, fields: dict) -> dict:
    fields = dict(fields)
    fields["updated_at"] = datetime.now(timezone.utc)
    get_medicines_collection().update_one(
        {"_id": ObjectId(medicine_id), "user_id": user_id, "deleted_at": None},
        {"$set": fields},
    )
    return find_medicine_by_id(medicine_id, user_id)


def soft_delete_medicine(medicine_id: str, user_id: str) -> bool:
    now = datetime.now(timezone.utc)
    result = get_medicines_collection().update_one(
        {"_id": ObjectId(medicine_id), "user_id": user_id, "deleted_at": None},
        {"$set": {"deleted_at": now, "is_active": False, "updated_at": now}},
    )
    return result.modified_count > 0
