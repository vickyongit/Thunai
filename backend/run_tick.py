"""
run_tick.py — manually run one scheduler tick.

Usage (from backend/ folder):
    python run_tick.py

Builds the Flask app WITHOUT starting the background scheduler,
runs run_tick() once, and prints the result.
"""
import sys
import os

# Allow running from the backend/ directory
sys.path.insert(0, os.path.dirname(__file__))

# Disable the scheduler so it doesn't start in the background
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app import create_app
from app.schedulers.reminder_scheduler import run_tick

app = create_app()

with app.app_context():
    print("Running one scheduler tick...")
    result = run_tick()
    print(f"\nResult: {result}")
    print(f"  logs_created  : {result['logs_created']}")
    print(f"  marked_missed : {result['marked_missed']}")
    print(f"  stale         : {result['stale']}")
