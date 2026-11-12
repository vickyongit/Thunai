import logging
import re
from flask import Blueprint, request, jsonify, g
import pymongo

from app.models.user import (
    find_user_by_email, insert_user, serialize_user
)
from app.services.auth_service import hash_password, verify_password, create_token
from app.utils.auth import login_required

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def _validate_signup(data: dict) -> list:
    errors = []
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "")

    if not name or len(name) < 2 or len(name) > 60:
        errors.append("Name must be between 2 and 60 characters.")
    if not email or not EMAIL_RE.match(email):
        errors.append("A valid email address is required.")
    if not password or not PASSWORD_RE.match(password):
        errors.append("Password must be at least 8 characters and contain at least one letter and one number.")
    return errors


@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json(silent=True) or {}
        errors = _validate_signup(data)
        if errors:
            return jsonify({
                "success": False,
                "error": {"code": "VALIDATION_ERROR", "message": errors[0], "details": errors}
            }), 400

        email = data["email"].strip().lower()
        if find_user_by_email(email):
            return jsonify({
                "success": False,
                "error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists."}
            }), 409

        password_hash = hash_password(data["password"])
        user = insert_user(data["name"], email, password_hash)
        token = create_token(str(user["_id"]))

        return jsonify({
            "success": True,
            "data": {"token": token, "user": serialize_user(user)},
            "message": "Account created successfully."
        }), 201

    except pymongo.errors.DuplicateKeyError:
        return jsonify({
            "success": False,
            "error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists."}
        }), 409
    except pymongo.errors.ConnectionFailure as e:
        logger.error("DB connection error in signup: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "DB_UNAVAILABLE", "message": "Database unavailable. Please try again later."}
        }), 503
    except Exception as e:
        logger.exception("Unexpected error in signup: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({
                "success": False,
                "error": {"code": "VALIDATION_ERROR", "message": "Email and password are required."}
            }), 400

        user = find_user_by_email(email)
        # Same message for wrong email or wrong password (security)
        if user is None or not verify_password(password, user["password_hash"]):
            return jsonify({
                "success": False,
                "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}
            }), 401

        token = create_token(str(user["_id"]))
        return jsonify({
            "success": True,
            "data": {"token": token, "user": serialize_user(user)},
            "message": "Logged in successfully."
        }), 200

    except pymongo.errors.ConnectionFailure as e:
        logger.error("DB connection error in login: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "DB_UNAVAILABLE", "message": "Database unavailable. Please try again later."}
        }), 503
    except Exception as e:
        logger.exception("Unexpected error in login: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}
        }), 500


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify({
        "success": True,
        "data": {"user": serialize_user(g.current_user)},
        "message": "User retrieved successfully."
    }), 200
