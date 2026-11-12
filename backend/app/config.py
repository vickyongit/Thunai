import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/thunai")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    _jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if not _jwt_secret:
        _jwt_secret = secrets.token_hex(32)
        logger.warning(
            "JWT_SECRET_KEY is not set. A temporary random key has been generated. "
            "Set JWT_SECRET_KEY in your .env file for persistent sessions."
        )
    JWT_SECRET_KEY = _jwt_secret
    JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "24"))
