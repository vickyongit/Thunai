import logging
from functools import wraps
from flask import request, jsonify, g
import jwt
from app.services.auth_service import decode_token
from app.models.user import find_user_by_id

logger = logging.getLogger(__name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({
                "success": False,
                "error": {"code": "MISSING_TOKEN", "message": "Authorization token is required."}
            }), 401

        token = auth_header[7:]  # strip "Bearer "
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "error": {"code": "TOKEN_EXPIRED", "message": "Token has expired. Please log in again."}
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "error": {"code": "INVALID_TOKEN", "message": "Invalid token. Please log in again."}
            }), 401

        user_id = payload.get("sub")
        try:
            user = find_user_by_id(user_id)
        except Exception as e:
            logger.error("DB error in login_required: %s", e)
            return jsonify({
                "success": False,
                "error": {"code": "DB_ERROR", "message": "Database unavailable. Please try again later."}
            }), 503

        if user is None:
            return jsonify({
                "success": False,
                "error": {"code": "USER_NOT_FOUND", "message": "User not found."}
            }), 401

        g.current_user = user
        return f(*args, **kwargs)
    return decorated
