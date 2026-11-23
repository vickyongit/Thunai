import logging
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify, request

from app.utils.auth import login_required
from app.models.medicine import (
    MAX_MEDICINES, count_user_medicines, find_medicine_by_id,
    get_user_medicines, insert_medicine, serialize_medicine,
    soft_delete_medicine, update_medicine,
)
from app.services.medicine_service import (
    build_medicine_create, build_medicine_update, validate_medicine,
)

logger = logging.getLogger(__name__)

medicines_bp = Blueprint("medicines_bp", __name__, url_prefix="/api/medicines")


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


# DB-down and unhandled exceptions bubble up to global handlers in app/__init__.py


@medicines_bp.route("/", methods=["GET"])
@login_required
def list_medicines():
    active_only = request.args.get("active", "").lower() == "true"
    medicines = get_user_medicines(_user_id(), active_only=active_only)
    return _ok({"medicines": medicines}, f"{len(medicines)} medicine(s) retrieved.")


@medicines_bp.route("/", methods=["POST"])
@login_required
def create_medicine():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    errors = validate_medicine(data, is_update=False)
    if errors:
        return _err("VALIDATION_ERROR", errors[0], 400, errors)

    uid = _user_id()
    if count_user_medicines(uid) >= MAX_MEDICINES:
        return _err("MEDICINE_LIMIT", f"Maximum of {MAX_MEDICINES} medicines allowed.", 400)

    fields = build_medicine_create(data)
    medicine = insert_medicine(uid, fields)
    return _ok({"medicine": serialize_medicine(medicine)}, "Medicine created successfully.", 201)


@medicines_bp.route("/<medicine_id>", methods=["GET"])
@login_required
def get_medicine(medicine_id):
    if not _valid_object_id(medicine_id):
        return _err("INVALID_ID", "Invalid medicine ID.", 400)

    med = find_medicine_by_id(medicine_id, _user_id())
    if med is None:
        return _err("NOT_FOUND", "Medicine not found.", 404)

    return _ok({"medicine": serialize_medicine(med)}, "Medicine retrieved successfully.")


@medicines_bp.route("/<medicine_id>", methods=["PUT"])
@login_required
def update_medicine_route(medicine_id):
    if not _valid_object_id(medicine_id):
        return _err("INVALID_ID", "Invalid medicine ID.", 400)

    uid = _user_id()
    existing = find_medicine_by_id(medicine_id, uid)
    if existing is None:
        return _err("NOT_FOUND", "Medicine not found.", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    errors = validate_medicine(data, is_update=True)
    if errors:
        return _err("VALIDATION_ERROR", errors[0], 400, errors)

    # Merge with existing to re-validate the combined state for time/repeat consistency
    merged = {
        "repeat_type": existing["repeat_type"],
        "days_of_week": existing.get("days_of_week", []),
        "start_date": existing["start_date"],
        **{k: v for k, v in data.items() if k in {
            "repeat_type", "days_of_week", "start_date", "end_date", "times"
        }},
    }
    # Re-run only cross-field checks on the merged state
    merged_data = {**existing, **merged}
    merged_errors = validate_medicine(merged_data, is_update=False)
    # Filter to only cross-field errors not already caught above
    cross_field_errors = [e for e in merged_errors if e not in errors]
    if cross_field_errors:
        return _err("VALIDATION_ERROR", cross_field_errors[0], 400, cross_field_errors)

    fields = build_medicine_update(data)
    if not fields:
        return _err("NO_FIELDS", "No valid fields to update.", 400)

    updated = update_medicine(medicine_id, uid, fields)
    return _ok({"medicine": serialize_medicine(updated)}, "Medicine updated successfully.")


@medicines_bp.route("/<medicine_id>", methods=["DELETE"])
@login_required
def delete_medicine_route(medicine_id):
    if not _valid_object_id(medicine_id):
        return _err("INVALID_ID", "Invalid medicine ID.", 400)

    uid = _user_id()
    if find_medicine_by_id(medicine_id, uid) is None:
        return _err("NOT_FOUND", "Medicine not found.", 404)

    soft_delete_medicine(medicine_id, uid)
    return _ok({}, "Medicine deleted successfully.")
