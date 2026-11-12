import logging
from datetime import datetime, timezone
from bson import ObjectId
from app.extensions import mongo

logger = logging.getLogger(__name__)


def get_users_collection():
    """Return the users collection or raise if DB is unavailable."""
    return mongo.db.users


def create_indexes():
    """Create unique index on email. Wrapped so server starts even if Mongo is down."""
    try:
        mongo.db.users.create_index("email", unique=True)
        logger.info("Users collection index ensured.")
    except Exception as e:
        logger.warning("Could not create users index (MongoDB may be down): %s", e)


def serialize_user(user: dict) -> dict:
    """Return a safe user dict — no password_hash, _id as string."""
    if user is None:
        return None
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "created_at": user.get("created_at", datetime.now(timezone.utc)).isoformat(),
    }


def find_user_by_email(email: str):
    return get_users_collection().find_one({"email": email.lower().strip()})


def find_user_by_id(user_id: str):
    try:
        return get_users_collection().find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


def insert_user(name: str, email: str, password_hash: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = {
        "name": name.strip(),
        "email": email.lower().strip(),
        "password_hash": password_hash,
        "role": "user",
        "created_at": now,
        "updated_at": now,
    }
    result = get_users_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
