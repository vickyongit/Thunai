from flask import Blueprint, jsonify

health_bp = Blueprint("health_bp", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    try:
        from app.schedulers.reminder_scheduler import get_status as scheduler_status
        sched = scheduler_status()
    except Exception:
        sched = {"enabled": False, "running": False, "last_run_at": None, "last_error": None}

    try:
        return jsonify({
            "success": True,
            "data": {
                "status": "ok",
                "service": "thunai-api",
                "version": "1.0.0",
                "scheduler": sched,
            },
            "message": "Service is healthy",
        }), 200
    except Exception as e:
        import logging
        logging.exception("Health check failed: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "HEALTH_CHECK_FAILED", "message": "Health check failed."},
        }), 500
