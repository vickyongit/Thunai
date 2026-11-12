import logging
import jwt
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

logger = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    return generate_password_hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)


def create_token(user_id: str) -> str:
    secret = current_app.config["JWT_SECRET_KEY"]
    expires_hours = current_app.config.get("JWT_EXPIRES_HOURS", 24)
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=int(expires_hours)),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    Returns decoded payload dict.
    Raises jwt.ExpiredSignatureError, jwt.InvalidTokenError on failure.
    """
    secret = current_app.config["JWT_SECRET_KEY"]
    return jwt.decode(token, secret, algorithms=["HS256"])
