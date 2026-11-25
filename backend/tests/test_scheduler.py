"""
tests/test_scheduler.py

Unit tests for the scheduler tick (missed-dose detection + log creation).
Uses mongomock to fake MongoDB — no real database needed.

BEFORE RUNNING (once):
    cd backend
    .\\venv\\Scripts\\pip install setuptools   # needed by mongomock on Python 3.14+
    .\\venv\\Scripts\\pip install -r requirements-dev.txt

RUN TESTS:
    .\\venv\\Scripts\\pytest tests/test_scheduler.py -v
"""
import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId

# ── Set env vars BEFORE any app module is imported ───────────────────────────
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("APP_TIMEZONE", "Asia/Kolkata")
os.environ.setdefault("MISSED_AFTER_MINUTES", "5")
os.environ.setdefault("ESCALATION_MAX_DELAY_MINUTES", "30")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")

import mongomock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mongo_client():
    client = mongomock.MongoClient()
    yield client
    client.close()


@pytest.fixture
def app(mongo_client, monkeypatch):
    """Flask app wired to the in-memory mongomock client."""
    # Patch MongoClient so the app factory never touches a real Mongo
    import pymongo
    monkeypatch.setattr(pymongo, "MongoClient", lambda *a, **kw: mongo_client)

    # Clear any cached module state so create_app sees the patch
    for mod in list(sys.modules.keys()):
        if mod.startswith("app"):
            del sys.modules[mod]

    from app import create_app, extensions
    extensions.mongo.client = mongo_client
    extensions.mongo.db = mongo_client["thunai_test"]

    application = create_app({"TESTING": True, "DB_NAME": "thunai_test"})
    yield application

    mongo_client.drop_database("thunai_test")


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield app


# ── DB helpers ────────────────────────────────────────────────────────────────

def _make_medicine(ctx_app, user_id="user1", times=None, repeat_type="daily",
                   days_of_week=None, start_date="2024-01-01", end_date=None,
                   is_active=True, deleted_at=None):
    from app.models.medicine import get_medicines_collection
    col = get_medicines_collection()
    doc = {
        "_id": ObjectId(),
        "user_id": user_id,
        "name": "Test Med",
        "dosage": "500 mg",
        "pills_per_dose": 1,
        "times": times or ["09:00"],
        "repeat_type": repeat_type,
        "days_of_week": days_of_week or [],
        "start_date": start_date,
        "end_date": end_date,
        "food_instruction": "any",
        "remarks": None,
        "pills_remaining": None,
        "is_active": is_active,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "deleted_at": deleted_at,
    }
    col.insert_one(doc)
    return doc


def _make_dose_log(ctx_app, user_id="user1", medicine_id=None, scheduled_date="2024-11-24",
                   scheduled_time="09:00", status="pending", scheduled_at=None,
                   escalation_status="none", missed_at=None):
    from app.models.dose_log import get_dose_logs_collection
    col = get_dose_logs_collection()
    now = datetime.now(timezone.utc)
    if scheduled_at is None:
        scheduled_at = now - timedelta(minutes=10)
    doc = {
        "_id": ObjectId(),
        "user_id": user_id,
        "medicine_id": str(medicine_id or ObjectId()),
        "scheduled_date": scheduled_date,
        "scheduled_time": scheduled_time,
        "scheduled_at": scheduled_at,
        "status": status,
        "taken_at": None,
        "was_late": False,
        "stock_decremented": False,
        "missed_at": missed_at,
        "escalation_status": escalation_status,
        "medicine_snapshot": {
            "name": "Test Med", "dosage": "500 mg",
            "pills_per_dose": 1, "food_instruction": "any",
        },
        "created_at": now,
        "updated_at": now,
    }
    col.insert_one(doc)
    return doc


# ── Missed-dose detection tests ───────────────────────────────────────────────

class TestMissedDetection:

    def test_dose_not_missed_before_deadline(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        future = datetime.now(timezone.utc) + timedelta(minutes=10)
        doc = _make_dose_log(ctx, scheduled_at=future, status="pending")
        result = run_tick(now=datetime.now(timezone.utc))
        updated = get_dose_logs_collection().find_one({"_id": doc["_id"]})
        assert updated["status"] == "pending"
        assert result["marked_missed"] == 0

    def test_dose_missed_after_deadline_pending_escalation(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        doc = _make_dose_log(ctx, scheduled_at=scheduled_at, status="pending")
        result = run_tick(now=datetime.now(timezone.utc))
        updated = get_dose_logs_collection().find_one({"_id": doc["_id"]})
        assert updated["status"] == "missed", f"Expected missed, got {updated['status']}"
        assert updated["escalation_status"] == "pending"
        assert result["marked_missed"] == 1
        assert result["stale"] == 0

    def test_second_tick_changes_nothing(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        doc = _make_dose_log(ctx, scheduled_at=scheduled_at, status="pending")
        now = datetime.now(timezone.utc)
        run_tick(now=now)
        result2 = run_tick(now=now)
        assert result2["marked_missed"] == 0
        updated = get_dose_logs_collection().find_one({"_id": doc["_id"]})
        assert updated["status"] == "missed"

    def test_taken_dose_never_touched(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        doc = _make_dose_log(ctx, scheduled_at=scheduled_at, status="taken")
        result = run_tick(now=datetime.now(timezone.utc))
        updated = get_dose_logs_collection().find_one({"_id": doc["_id"]})
        assert updated["status"] == "taken"
        assert result["marked_missed"] == 0

    def test_stale_escalation_for_very_old_dose(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        # 60 min overdue → 55 min past the missed deadline (escalation_max=30 → stale)
        scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=60)
        doc = _make_dose_log(ctx, scheduled_at=scheduled_at, status="pending")
        result = run_tick(now=datetime.now(timezone.utc))
        updated = get_dose_logs_collection().find_one({"_id": doc["_id"]})
        assert updated["status"] == "missed"
        assert updated["escalation_status"] == "stale"
        assert result["stale"] == 1


# ── Log creation tests ────────────────────────────────────────────────────────

class TestLogCreation:

    def test_scheduler_creates_logs_for_user_who_never_opened_dashboard(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        _make_medicine(ctx, user_id="new_user", times=["08:00", "20:00"],
                       repeat_type="daily", start_date="2024-01-01")
        now = datetime.now(timezone.utc)
        run_tick(now=now)
        logs = list(get_dose_logs_collection().find({"user_id": "new_user"}))
        assert len(logs) >= 2  # at least today's 2 slots

    def test_paused_medicine_gets_no_logs(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        _make_medicine(ctx, user_id="user_paused", is_active=False, times=["09:00"])
        run_tick(now=datetime.now(timezone.utc))
        logs = list(get_dose_logs_collection().find({"user_id": "user_paused"}))
        assert logs == []

    def test_deleted_medicine_gets_no_logs(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        _make_medicine(ctx, user_id="user_deleted",
                       deleted_at=datetime.now(timezone.utc))
        run_tick(now=datetime.now(timezone.utc))
        logs = list(get_dose_logs_collection().find({"user_id": "user_deleted"}))
        assert logs == []

    def test_future_start_date_gets_no_logs_today(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
        _make_medicine(ctx, user_id="user_future", start_date=future_date)
        run_tick(now=datetime.now(timezone.utc))
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logs = list(get_dose_logs_collection().find(
            {"user_id": "user_future", "scheduled_date": today}))
        assert logs == []

    def test_expired_medicine_gets_no_logs(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        _make_medicine(ctx, user_id="user_expired",
                       end_date=yesterday, start_date="2024-01-01")
        run_tick(now=datetime.now(timezone.utc))
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        logs = list(get_dose_logs_collection().find(
            {"user_id": "user_expired", "scheduled_date": today}))
        assert logs == []

    def test_wrong_weekday_gets_no_logs(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        # Find next Sunday (weekday==6)
        base = datetime.now(timezone.utc)
        days_ahead = (6 - base.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        sunday_dt = base + timedelta(days=days_ahead)
        sunday_str = sunday_dt.strftime("%Y-%m-%d")

        _make_medicine(ctx, user_id="user_weekday",
                       repeat_type="specific_days", days_of_week=[0],  # Mon only
                       start_date="2024-01-01")
        run_tick(now=sunday_dt.replace(hour=12, minute=0, second=0, microsecond=0))
        logs = list(get_dose_logs_collection().find(
            {"user_id": "user_weekday", "scheduled_date": sunday_str}))
        assert logs == []

    def test_idempotent_log_creation(self, ctx):
        from app.schedulers.reminder_scheduler import run_tick
        from app.models.dose_log import get_dose_logs_collection
        _make_medicine(ctx, user_id="user_idem", times=["10:00"], start_date="2024-01-01")
        now = datetime.now(timezone.utc)
        run_tick(now=now)
        run_tick(now=now)
        today = now.strftime("%Y-%m-%d")
        logs = list(get_dose_logs_collection().find(
            {"user_id": "user_idem", "scheduled_date": today}))
        assert len(logs) == 1


# ── Take & Undo escalation tests ──────────────────────────────────────────────

class TestTakeAndUndo:

    def test_late_take_of_missed_dose_cancels_escalation(self, ctx):
        from app.models.dose_log import mark_dose_taken
        scheduled_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        doc = _make_dose_log(ctx, scheduled_at=scheduled_at, status="missed",
                             escalation_status="pending")
        now = datetime.now(timezone.utc)
        updated = mark_dose_taken(str(doc["_id"]), "user1", now, was_late=True)
        assert updated is not None
        assert updated["status"] == "taken"
        assert updated["escalation_status"] == "cancelled"

    def test_undo_resets_escalation_and_missed_at(self, ctx):
        from app.models.dose_log import undo_dose_taken, get_dose_logs_collection
        doc = _make_dose_log(ctx, status="pending", escalation_status="cancelled",
                             missed_at=datetime.now(timezone.utc))
        get_dose_logs_collection().update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "taken", "taken_at": datetime.now(timezone.utc)}}
        )
        updated = undo_dose_taken(str(doc["_id"]), "user1")
        assert updated is not None
        assert updated["status"] == "pending"
        assert updated["escalation_status"] == "none"
        assert updated["missed_at"] is None


# ── Timezone test ─────────────────────────────────────────────────────────────

class TestTimezone:

    def test_today_computed_in_app_timezone(self, ctx):
        """23:30 UTC must map to the next day in Asia/Kolkata (UTC+5:30)."""
        from app.utils.timezone import get_app_timezone
        tz = get_app_timezone()
        utc_dt = datetime(2024, 11, 24, 23, 30, 0, tzinfo=timezone.utc)
        local_dt = utc_dt.astimezone(tz)
        assert local_dt.strftime("%Y-%m-%d") == "2024-11-25"
