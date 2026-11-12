import logging
from flask import Blueprint, g, jsonify, request

from app.utils.auth import login_required
from app.models.user import serialize_user, update_user_profile
from app.services.profile_service import build_profile_update, validate_profile_update

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile_bp", __name__, url_prefix="/api/profile")


def _ok(data, message, status=200):
    return jsonify({"success": True, "data": data, "message": message}), status


def _err(code, message, status, details=None):
    error = {"code": code, "message": message}
    if details:
        error["details"] = details
    return jsonify({"success": False, "error": error}), status


# Database-down and unexpected errors are handled by the global handlers in app/__init__.py


@profile_bp.route("/", methods=["GET"])
@login_required
def get_profile():
    return _ok({"user": serialize_user(g.current_user)}, "Profile retrieved successfully.")


@profile_bp.route("/", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _err("VALIDATION_ERROR", "Request body must be a JSON object.", 400)

    errors = validate_profile_update(data)
    if errors:
        return _err("VALIDATION_ERROR", errors[0], 400, errors)

    fields = build_profile_update(data)
    if not fields:
        return _err("NO_FIELDS", "No valid fields provided to update.", 400)

    updated_user = update_user_profile(str(g.current_user["_id"]), fields)
    return _ok({"user": serialize_user(updated_user)}, "Profile updated successfully.")