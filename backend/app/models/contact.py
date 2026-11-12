import logging
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.extensions import mongo

logger = logging.getLogger(__name__)

MAX_CONTACTS = 5


def get_contacts_collection():
    return mongo.get_db()["contacts"]


def create_contact_indexes():
    try:
        col = get_contacts_collection()
        col.create_index("user_id")
        # Only one primary (1) and one secondary (2) per user, enforced by the database itself
        col.create_index(
            [("user_id", 1), ("priority", 1)],
            unique=True,
            partialFilterExpression={"priority": {"$lte": 2}},
        )
        logger.info("Contacts collection indexes ensured.")
    except Exception as e:
        logger.warning("Could not create contacts indexes: %s", e)


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def serialize_contact(contact):
    if contact is None:
        return None
    return {
        "id": str(contact["_id"]),
        "user_id": str(contact["user_id"]),
        "name": contact["name"],
        "phone": contact["phone"],
        "relationship": contact["relationship"],
        "priority": contact["priority"],
        "notify_on_missed": contact.get("notify_on_missed", True),
        "created_at": _iso(contact.get("created_at")),
        "updated_at": _iso(contact.get("updated_at")),
    }


def get_user_contacts(user_id):
    col = get_contacts_collection()
    contacts = list(col.find({"user_id": user_id}).sort([("priority", 1), ("created_at", 1)]))
    return [serialize_contact(c) for c in contacts]


def count_user_contacts(user_id):
    return get_contacts_collection().count_documents({"user_id": user_id})


def find_contact_by_id(contact_id, user_id):
    """Find by id AND user_id. Returns None if missing or owned by someone else."""
    try:
        oid = ObjectId(contact_id)
    except (InvalidId, TypeError):
        return None
    return get_contacts_collection().find_one({"_id": oid, "user_id": user_id})


def priority_taken(user_id, priority, exclude_id=None):
    """Is the primary (1) or secondary (2) slot already used by this user?"""
    if priority >= 3:
        return False
    query = {"user_id": user_id, "priority": priority}
    if exclude_id:
        try:
            query["_id"] = {"$ne": ObjectId(exclude_id)}
        except (InvalidId, TypeError):
            pass
    return get_contacts_collection().count_documents(query) > 0


def insert_contact(user_id, name, phone, relationship, priority, notify_on_missed):
    now = datetime.now(timezone.utc)
    doc = {
        "user_id": user_id,
        "name": name.strip(),
        "phone": phone.strip(),
        "relationship": relationship.strip().lower(),
        "priority": priority,
        "notify_on_missed": notify_on_missed,
        "created_at": now,
        "updated_at": now,
    }
    result = get_contacts_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


def update_contact(contact_id, user_id, fields):
    fields = dict(fields)
    fields["updated_at"] = datetime.now(timezone.utc)
    get_contacts_collection().update_one(
        {"_id": ObjectId(contact_id), "user_id": user_id},
        {"$set": fields},
    )
    return find_contact_by_id(contact_id, user_id)


def delete_contact(contact_id, user_id):
    result = get_contacts_collection().delete_one(
        {"_id": ObjectId(contact_id), "user_id": user_id}
    )
    return result.deleted_count > 0