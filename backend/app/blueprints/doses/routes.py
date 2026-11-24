import logging
from datetime import timezone
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, g, jsonify

from app.utils.auth import login_required
from app.models.dose_log import find_dose_by_id, mark_dose_taken, undo_dose_taken, serialize_dose
from app.services import dose_service

logger = logging.getLogger(__name__)

doses_bp = Blueprint("doses", __name__, url_prefix="/api/doses")


# ── helpers ──────────────────────────────────────────────────────────────────

def _ok(data, msg="OK", status=200):
    return jsonify({"success": True, "data": data, "message": msg}), status


def _err(code, msg, status, details=None):
    body = {"success": False, "error": {"code": code, "message": msg}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def _user_id():
    return str(g.current_user["_id"])


def _valid_object_id(value: str) -> bool:
    try:
        ObjectId(value)
        return True
    except (InvalidId, TypeError):
        return False


# ── routes ───────────────────────────────────────────────────────────────────

@doses_bp.get("/today")
@login_required
def get_today():
    """Return today's dose schedule (lazy-creates dose logs on first call each day)."""
    schedule = dose_service.build_today_schedule(_user_id())
    return _ok(schedule, "Today's schedule loaded.")


@doses_bp.post("/<dose_id>/take")
@login_required
def take_dose(dose_id):
    """Mark a dose as taken. Idempotent: returns 200 if already taken."""
    if not _valid_object_id(dose_id):
        return _err("INVALID_ID", "Invalid dose id.", 400)

    dose = find_dose_by_id(dose_id, _user_id())
    if dose is None:
        return _err("NOT_FOUND", "Dose not found.", 404)

    # Idempotent: already taken
    if dose.get("status") == "taken":
        return _ok(serialize_dose(dose), "Dose already marked as taken.")

    # Timing validation
    now_utc = dose_service.get_now_utc()
    scheduled_at = dose.get("scheduled_at")
    if scheduled_at is None:
        return _err("INVALID_STATE", "Dose has no scheduled time.", 400)
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

    error = dose_service.validate_take_dose(dose, now_utc, scheduled_at)
    if error and error != "ALREADY_TAKEN":
        return _err("TOO_EARLY", error, 400)

    # Check lateness
    was_late = (now_utc - scheduled_at).total_seconds() > dose_service.LATE_THRESHOLD_MINUTES * 60

    # Atomic update (conditional on status still pending/missed)
    updated = mark_dose_taken(dose_id, _user_id(), now_utc, was_late)
    if updated is None:
        # Race: someone else already marked it; return current state
        dose = find_dose_by_id(dose_id, _user_id())
        return _ok(serialize_dose(dose), "Dose already marked as taken.")

    # Stock decrement (best-effort; never crash on failure)
    if not updated.get("stock_decremented", False):
        snap = updated.get("medicine_snapshot", {})
        pills_per_dose = snap.get("pills_per_dose", 1)
        decremented = dose_service.decrement_stock(updated["medicine_id"], pills_per_dose)
        if decremented:
            from app.models.dose_log import get_dose_logs_collection
            from datetime import datetime
            get_dose_logs_collection().update_one(
                {"_id": updated["_id"]},
                {"$set": {"stock_decremented": True, "updated_at": datetime.now(timezone.utc)}},
            )
            updated["stock_decremented"] = True

    return _ok(serialize_dose(updated), "Dose marked as taken.")


@doses_bp.post("/<dose_id>/undo")
@login_required
def undo_dose(dose_id):
    """Undo a taken dose, restoring it to pending. Idempotent."""
    if not _valid_object_id(dose_id):
        return _err("INVALID_ID", "Invalid dose id.", 400)

    dose = find_dose_by_id(dose_id, _user_id())
    if dose is None:
        return _err("NOT_FOUND", "Dose not found.", 404)

    # Idempotent: not taken
    if dose.get("status") != "taken":
        return _ok(serialize_dose(dose), "Dose is not taken; nothing to undo.")

    # Only allow undo for today's doses
    today_str = dose_service.get_today_string()
    if dose.get("scheduled_date") != today_str:
        return _err("UNDO_NOT_ALLOWED", "Can only undo today's doses.", 400)

    # Restore stock before reverting the log (best-effort)
    if dose.get("stock_decremented", False):
        snap = dose.get("medicine_snapshot", {})
        pills_per_dose = snap.get("pills_per_dose", 1)
        dose_service.restore_stock(dose["medicine_id"], pills_per_dose)

    updated = undo_dose_taken(dose_id, _user_id())
    if updated is None:
        # Race: already undone
        dose = find_dose_by_id(dose_id, _user_id())
        return _ok(serialize_dose(dose), "Dose already reverted to pending.")

    return _ok(serialize_dose(updated), "Dose reverted to pending.")
