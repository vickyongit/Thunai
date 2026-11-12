import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _secret(name):
    value = os.environ.get(name)
    if not value:
        value = secrets.token_hex(32)
        logger.warning(
            "%s is not set. A temporary random key was generated. "
            "Set it in your .env file for persistent sessions.", name
        )
    return value


class Config:
    SECRET_KEY = _secret("SECRET_KEY")
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY")
    JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "24"))

    # No credentials in code. Falls back to local MongoDB only.
    MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI") or "mongodb://localhost:27017"
    DB_NAME = os.environ.get("DB_NAME", "thunai")

    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:5173")