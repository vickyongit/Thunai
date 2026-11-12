import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.extensions import mongo

logger = logging.getLogger(__name__)


def get_users_collection():
    return mongo.get_db()["users"]


def create_indexes():
    try:
        get_users_collection().create_index("email", unique=True)
        logger.info("Users collection index ensured.")
    except Exception as e:
        logger.warning("Could not create users index (MongoDB may be down): %s", e)


def serialize_user(user):
    """Safe user dict: no password_hash, _id as string."""
    if user is None:
        return None
    created = user.get("created_at")
    if isinstance(created, datetime):
        created = created.isoformat()
    return {
        "id": str(user["_id"]),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "user"),
        "phone": user.get("phone"),
        "age": user.get("age"),
        "gender": user.get("gender"),
        "language": user.get("language", "en"),
        "elder_mode": user.get("elder_mode", False),
        "created_at": created,
    }


def find_user_by_email(email):
    return get_users_collection().find_one({"email": email.lower().strip()})


def find_user_by_id(user_id):
    try:
        oid = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return get_users_collection().find_one({"_id": oid})


def insert_user(name, email, password_hash):
    now = datetime.now(timezone.utc)
    doc = {
        "name": name.strip(),
        "email": email.lower().strip(),
        "password_hash": password_hash,
        "role": "user",
        "phone": None,
        "age": None,
        "gender": None,
        "language": "en",
        "elder_mode": False,
        "created_at": now,
        "updated_at": now,
    }
    result = get_users_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def update_user_profile(user_id, fields):
    """Update only the given profile fields and return the updated user."""
    fields = dict(fields)
    fields["updated_at"] = datetime.now(timezone.utc)
    get_users_collection().update_one({"_id": ObjectId(user_id)}, {"$set": fields})
    return find_user_by_id(user_id)