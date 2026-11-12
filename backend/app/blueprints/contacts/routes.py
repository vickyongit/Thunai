import logging
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request
from pymongo.errors import DuplicateKeyError

from app.utils.auth import login_required
from app.models.contact import (
    MAX_CONTACTS, count_user_contacts, delete_contact, find_contact_by_id,
    get_user_contacts, insert_contact, priority_taken, serialize_contact,
    update_contact,
)
from app.services.contact_service import build_contact_update, validate_contact

logger = logging.getLogger(__name__)

contacts_bp = Blueprint("contacts_bp", __name__, url_prefix="/api/contacts")


def _ok(data, message, status=200):
    return jsonify({"success": True, "data": data, "message": message}), status


def _err(code, message, status, details=None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return jsonify({"success": False, "error": error}), status


def _user_id() -> str:
    return str(g.current_user["_id"])


def _valid_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


def _priority_conflict(priority: int):
    label = "primary" if priority == 1 else "secondary"
    return _err(
        "PRIORITY_CONFLICT",
        f"You already have a {label} contact. Update or remove it first.",
        409,
    )


# Database-down and unexpected errors are handled by the global handlers in app/__init__.py


@contacts_bp.route("/", methods=["GET"])
@login_required
def list_contacts():
    contacts = get_user_contacts(_user_id())
    return _ok({"contacts": contacts}, f"{len(contacts)} contact(s) retrieved.")


@contacts_bp.route("/", methods=["POST"])
@login_required
def create_contact():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    errors = validate_contact(data, is_update=False)
    if errors:
        return _err("VALIDATION_ERROR", errors[0], 400, errors)

    uid = _user_id()
    if count_user_contacts(uid) >= MAX_CONTACTS:
        return _err("CONTACT_LIMIT", f"Maximum of {MAX_CONTACTS} contacts allowed.", 400)

    priority = int(data.get("priority", 3))
    if priority_taken(uid, priority):
        return _priority_conflict(priority)

    try:
        contact = insert_contact(
            user_id=uid,
            name=data["name"],
            phone=str(data["phone"]).strip(),
            relationship=data["relationship"],
            priority=priority,
            notify_on_missed=bool(data.get("notify_on_missed", True)),
        )
    except DuplicateKeyError:  # two requests raced for the same priority slot
        return _priority_conflict(priority)

    return _ok({"contact": serialize_contact(contact)}, "Contact created successfully.", 201)


@contacts_bp.route("/<contact_id>", methods=["PUT"])
@login_required
def update_contact_route(contact_id):
    if not _valid_object_id(contact_id):
        return _err("INVALID_ID", "Invalid contact ID.", 400)

    uid = _user_id()
    if find_contact_by_id(contact_id, uid) is None:
        return _err("NOT_FOUND", "Contact not found.", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    errors = validate_contact(data, is_update=True)
    if errors:
        return _err("VALIDATION_ERROR", errors[0], 400, errors)

    fields = build_contact_update(data)
    if not fields:
        return _err("NO_FIELDS", "No valid fields to update.", 400)

    new_priority = fields.get("priority")
    if new_priority is not None and priority_taken(uid, new_priority, exclude_id=contact_id):
        return _priority_conflict(new_priority)

    try:
        updated = update_contact(contact_id, uid, fields)
    except DuplicateKeyError:
        return _priority_conflict(new_priority or 1)

    return _ok({"contact": serialize_contact(updated)}, "Contact updated successfully.")


@contacts_bp.route("/<contact_id>", methods=["DELETE"])
@login_required
def delete_contact_route(contact_id):
    if not _valid_object_id(contact_id):
        return _err("INVALID_ID", "Invalid contact ID.", 400)

    uid = _user_id()
    if find_contact_by_id(contact_id, uid) is None:
        return _err("NOT_FOUND", "Contact not found.", 404)

    delete_contact(contact_id, uid)
    return _ok({}, "Contact deleted successfully.")