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


def _int_env(name, default, minimum=1):
    """Read an integer env-var; fall back to default on bad/negative values."""
    raw = os.environ.get(name, "")
    try:
        val = int(raw)
        if val < minimum:
            raise ValueError("below minimum")
        return val
    except (ValueError, TypeError):
        if raw:
            logger.warning(
                "Invalid value for %s (%r); using default %s.", name, raw, default
            )
        return default


def _bool_env(name, default: bool) -> bool:
    raw = os.environ.get(name, "").lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    return default


class Config:
    SECRET_KEY = _secret("SECRET_KEY")
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY")
    JWT_EXPIRES_HOURS = _int_env("JWT_EXPIRES_HOURS", 24, minimum=1)

    # No credentials in code. Falls back to local MongoDB only.
    MONGO_URI = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI") or "mongodb://localhost:27017"
    DB_NAME = os.environ.get("DB_NAME", "thunai")

    DEBUG = _bool_env("FLASK_DEBUG", False)
    CLIENT_URL = os.environ.get("CLIENT_URL", "http://localhost:5173")

    # Timezone — validated lazily by utils/timezone.py; store raw name here.
    _tz = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")
    APP_TIMEZONE = _tz  # utils/timezone.get_app_timezone() does the actual resolution

    # ── Scheduler ────────────────────────────────────────────────────────────
    SCHEDULER_ENABLED          = _bool_env("SCHEDULER_ENABLED", True)
    SCHEDULER_INTERVAL_SECONDS = _int_env("SCHEDULER_INTERVAL_SECONDS", 60, minimum=10)

    # ── Missed-dose detection ─────────────────────────────────────────────────
    MISSED_AFTER_MINUTES       = _int_env("MISSED_AFTER_MINUTES", 5, minimum=1)
    # Doses missed more than this many minutes ago get escalation_status="stale"
    ESCALATION_MAX_DELAY_MINUTES = _int_env("ESCALATION_MAX_DELAY_MINUTES", 30, minimum=1)
