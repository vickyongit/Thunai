"""
Reminder scheduler for THUNAI.

Runs a background job every SCHEDULER_INTERVAL_SECONDS that:
  (a) Creates today's (and yesterday's) dose logs for ALL users.
  (b) Marks overdue pending doses as "missed" with appropriate escalation_status.

This module does NOT send any alerts/SMS/calls — that is Step 7.
"""
import os
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

# Module-level status (readable by the health endpoint)
last_run_at: datetime | None = None
last_run_result: dict | None = None
last_error: str | None = None

_scheduler: BackgroundScheduler | None = None


def run_tick(now: datetime | None = None) -> dict:
    """
    Execute one scheduler tick.

    Args:
        now: Optional UTC datetime override (useful for testing). Defaults to utcnow.

    Returns:
        dict with keys: logs_created, marked_missed, stale
    """
    global last_run_at, last_run_result, last_error

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    result = {"logs_created": 0, "marked_missed": 0, "stale": 0}

    # ── Import inside function to avoid circular imports at module load time ──
    from flask import current_app
    from app.utils.timezone import get_app_timezone
    from app.services.dose_service import ensure_logs_for_all_users
    from app.models.dose_log import get_dose_logs_collection

    cfg = current_app.config
    missed_after = cfg.get("MISSED_AFTER_MINUTES", 5)
    escalation_max = cfg.get("ESCALATION_MAX_DELAY_MINUTES", 30)

    tz = get_app_timezone()

    # ── Part (a): Ensure today's (and yesterday's) logs exist for all users ──
    try:
        today_local = datetime.now(tz)
        today_str = today_local.strftime("%Y-%m-%d")
        yesterday_str = (today_local - timedelta(days=1)).strftime("%Y-%m-%d")

        created_today = ensure_logs_for_all_users(today_str, tz)
        created_yesterday = ensure_logs_for_all_users(yesterday_str, tz)
        result["logs_created"] = created_today + created_yesterday
    except Exception as e:
        logger.warning("Scheduler tick — error in log-creation phase: %s", e)

    # ── Part (b): Mark overdue pending doses as missed ────────────────────────
    try:
        col = get_dose_logs_collection()
        missed_cutoff = now - timedelta(minutes=missed_after)
        escalation_cutoff = now - timedelta(minutes=missed_after + escalation_max)

        # Find all pending doses whose scheduled_at is before the missed cutoff.
        # Iterate via cursor; never pull all into memory.
        cursor = col.find(
            {
                "status": "pending",
                "scheduled_at": {"$lte": missed_cutoff},
            },
            {"_id": 1, "scheduled_at": 1},
            batch_size=100,
        )

        for doc in cursor:
            scheduled_at = doc["scheduled_at"]
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

            # Determine escalation_status:
            # missed deadline = scheduled_at + missed_after_minutes
            missed_deadline = scheduled_at + timedelta(minutes=missed_after)
            if now - missed_deadline <= timedelta(minutes=escalation_max):
                esc_status = "pending"
            else:
                esc_status = "stale"

            # Atomic update: only change status if still "pending"
            updated = col.find_one_and_update(
                {"_id": doc["_id"], "status": "pending"},
                {
                    "$set": {
                        "status": "missed",
                        "missed_at": now,
                        "escalation_status": esc_status,
                        "updated_at": now,
                    }
                },
                return_document=True,
            )
            if updated is not None:
                result["marked_missed"] += 1
                if esc_status == "stale":
                    result["stale"] += 1

    except Exception as e:
        logger.warning("Scheduler tick — error in missed-detection phase: %s", e)

    last_run_at = now
    last_run_result = result
    last_error = None
    logger.info("Scheduler tick done: %s", result)
    return result


def _job_listener(event):
    """Log scheduler job errors without crashing."""
    global last_error
    if event.exception:
        last_error = str(event.exception)
        logger.error("Scheduler job raised an exception: %s", event.exception)


def _tick_job():
    """Wrapper called by APScheduler; always runs inside the Flask app context."""
    global last_error
    try:
        run_tick()
    except Exception as e:
        last_error = str(e)
        logger.exception("Unexpected error in scheduler tick: %s", e)


def start_scheduler(app):
    """
    Start the APScheduler background scheduler.

    Guards:
    - Only starts when SCHEDULER_ENABLED is True.
    - Skips if we are the Werkzeug reloader *parent* process (WERKZEUG_RUN_MAIN != "true"
      when FLASK_DEBUG is on), so there is exactly one scheduler per process.
    - Skips if already started.
    """
    global _scheduler

    if not app.config.get("SCHEDULER_ENABLED", True):
        logger.info("Scheduler is disabled (SCHEDULER_ENABLED=false).")
        return

    # Werkzeug auto-reload guard
    if app.config.get("DEBUG", False) and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        logger.debug("Skipping scheduler start in Werkzeug reloader parent process.")
        return

    if _scheduler is not None and _scheduler.running:
        logger.debug("Scheduler already running; skipping second start.")
        return

    interval = app.config.get("SCHEDULER_INTERVAL_SECONDS", 60)

    _scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": max(interval, 30),
        },
        timezone="UTC",
    )
    _scheduler.add_listener(_job_listener, EVENT_JOB_ERROR)

    # Wrap the job so it runs inside the Flask app context
    def _job_with_ctx():
        with app.app_context():
            _tick_job()

    _scheduler.add_job(
        _job_with_ctx,
        trigger="interval",
        seconds=interval,
        id="reminder_tick",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started (interval=%ss, missed_after=%smin, escalation_max=%smin).",
        interval,
        app.config.get("MISSED_AFTER_MINUTES", 5),
        app.config.get("ESCALATION_MAX_DELAY_MINUTES", 30),
    )

    import atexit
    atexit.register(lambda: _scheduler.shutdown(wait=False) if _scheduler.running else None)


def get_status() -> dict:
    """Return the current scheduler status for the health endpoint."""
    return {
        "enabled": _scheduler is not None,
        "running": _scheduler is not None and _scheduler.running,
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "last_error": last_error,
    }
