"""conftest.py — adds backend/ to sys.path so `from app import ...` works."""
import sys
import os

# Ensure the backend/ directory (where the `app` package lives) is on sys.path
backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
