"""
Centralised timezone helper for the whole application.

Reads APP_TIMEZONE from Flask config (via current_app) or falls back to
the env-var directly (for use outside a request context, e.g. the scheduler).
Logs a warning ONCE per process, never raises, never crashes.
"""
import os
import logging
from datetime import timezone, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)

# Fallback fixed offset for Asia/Kolkata (UTC+5:30) used only when tzdata is missing.
_IST = timezone(timedelta(hours=5, minutes=30), "IST")

_warned = False          # module-level guard so the warning fires only once


@lru_cache(maxsize=4)
def _load_zone(tz_name: str):
    """
    Try to return a ZoneInfo for tz_name.
    Falls back to a fixed UTC+5:30 for 'Asia/Kolkata' or plain UTC for anything else.
    Result is cached so we never re-import or re-warn for the same name.
    """
    global _warned
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        return ZoneInfo(tz_name)
    except Exception:
        pass
    # Try the system tzdata package
    try:
        import importlib
        importlib.import_module("tzdata")
        from zoneinfo import ZoneInfo
        return ZoneInfo(tz_name)
    except Exception:
        pass
    if not _warned:
        _warned = True
        logger.warning(
            "Timezone '%s' could not be resolved (tzdata may be missing). "
            "Falling back to a fixed offset.",
            tz_name,
        )
    if tz_name == "Asia/Kolkata":
        return _IST
    return timezone.utc


def get_app_timezone():
    """
    Return the application timezone (ZoneInfo or fixed-offset).
    Safe to call both inside and outside a Flask request/app context.
    """
    tz_name = "Asia/Kolkata"  # default
    try:
        from flask import current_app
        tz_name = current_app.config.get("APP_TIMEZONE", "Asia/Kolkata")
    except RuntimeError:
        # Outside app context (e.g. tests, CLI scripts)
        tz_name = os.environ.get("APP_TIMEZONE", "Asia/Kolkata")
    return _load_zone(tz_name)
