"""
THUNAI smoke test for Step 4 (medicines API).
Run with the backend server already running:
    python tests/smoke_medicines.py
Creates throwaway users named smoke-xxxx@example.com (safe to delete later).
"""
import json
import sys
import urllib.error
import urllib.request
import uuid

BASE = "http://localhost:5000"
results = []


def call(method, path, body=None, token=None, raw_body=None):
    data = raw_body if raw_body is not None else (
        json.dumps(body).encode() if body is not None else None
    )
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            text = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        text = e.read()
        status = e.code
    except Exception as e:
        print(f"\nCannot reach {BASE}: {e}\nIs the backend running?")
        sys.exit(2)
    try:
        return status, json.loads(text or b"{}")
    except ValueError:
        return status, {"raw": text.decode(errors="replace")[:200]}


def find(obj, key):
    """Find the first value for `key` anywhere inside nested dicts/lists."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = find(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find(v, key)
            if found is not None:
                return found
    return None


def check(label, got, expected):
    ok = got == expected
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + f"{label}  (got {got}, expected {expected})")
    return ok


def new_user(tag):
    email = f"smoke-{tag}-{uuid.uuid4().hex[:6]}@example.com"
    pw = "Smoke1234pass"
    status, body = call("POST", "/api/auth/signup", {"name": f"Smoke {tag}", "email": email, "password": pw})
    token = find(body, "token")
    if not token:
        status, body = call("POST", "/api/auth/login", {"email": email, "password": pw})
        token = find(body, "token")
    if not token:
        print(f"Could not sign up / log in test user ({status}): {body}")
        sys.exit(2)
    return token


VALID = {
    "name": "Metformin", "dosage": "500 mg", "pills_per_dose": 1,
    "times": ["20:00", "08:00"], "repeat_type": "daily",
    "start_date": "2026-01-01", "food_instruction": "after_food",
}

print("== Setup ==")
A = new_user("a")
B = new_user("b")

print("\n== Create ==")
s, b = call("GET", "/api/medicines/", token=A)
check("list (empty) works", s, 200)
s, b = call("POST", "/api/medicines/", VALID, A)
check("create daily medicine", s, 201)
med_id = find(b, "id") or find(b, "_id")
check("create returns an id", bool(med_id), True)
s, b = call("POST", "/api/medicines/", {
    "name": "Vitamin D", "dosage": "1000 IU", "pills_per_dose": 1, "times": ["09:00"],
    "repeat_type": "specific_days", "days_of_week": [0, 2, 4], "start_date": "2026-01-01"}, A)
check("create specific-days medicine", s, 201)
check("no-slash URL works (no redirect)", call("GET", "/api/medicines", token=A)[0], 200)

print("\n== Validation (all must be 400, never 500) ==")
def bad(label, **changes):
    body = {**VALID, **changes}
    check(label, call("POST", "/api/medicines/", body, A)[0], 400)

bad("name too short", name="X")
bad("name is a number", name=123)
bad("pills_per_dose is text", pills_per_dose="two")
bad("pills_per_dose too high", pills_per_dose=99)
bad("times empty", times=[])
bad("duplicate times", times=["08:00", "08:00"])
bad("invalid time 25:99", times=["25:99"])
bad("more than 6 times", times=["01:00", "02:00", "03:00", "04:00", "05:00", "06:00", "07:00"])
bad("specific_days with empty days", repeat_type="specific_days", days_of_week=[])
bad("specific_days with day 9", repeat_type="specific_days", days_of_week=[9])
bad("end_date before start_date", start_date="2026-05-01", end_date="2026-04-01")
bad("bad food_instruction", food_instruction="whenever")
check("body is a list, not object", call("POST", "/api/medicines/", raw_body=b"[1,2]", token=A)[0], 400)
check("body is invalid JSON", call("POST", "/api/medicines/", raw_body=b"{oops", token=A)[0], 400)

print("\n== Read / update ==")
check("get one", call("GET", f"/api/medicines/{med_id}", token=A)[0], 200)
check("get with invalid id", call("GET", "/api/medicines/not-an-id", token=A)[0], 400)
check("get with unknown id", call("GET", "/api/medicines/" + "0" * 24, token=A)[0], 404)
check("update name (+ ignored user_id)", call("PUT", f"/api/medicines/{med_id}", {"name": "Renamed", "user_id": "hacker"}, A)[0], 200)
check("switch to specific_days WITHOUT days -> 400 (merged validation)",
      call("PUT", f"/api/medicines/{med_id}", {"repeat_type": "specific_days"}, A)[0], 400)
check("pause medicine", call("PUT", f"/api/medicines/{med_id}", {"is_active": False}, A)[0], 200)
s, b = call("GET", "/api/medicines/?active=true", token=A)
check("?active=true hides paused medicine", med_id in json.dumps(b), False)
s, b = call("GET", "/api/medicines/", token=A)
check("full list still shows paused medicine", med_id in json.dumps(b), True)
check("resume medicine", call("PUT", f"/api/medicines/{med_id}", {"is_active": True}, A)[0], 200)

print("\n== Isolation (user B must get 404) ==")
check("B cannot read A's medicine", call("GET", f"/api/medicines/{med_id}", token=B)[0], 404)
check("B cannot edit A's medicine", call("PUT", f"/api/medicines/{med_id}", {"name": "Hacked"}, B)[0], 404)
check("B cannot delete A's medicine", call("DELETE", f"/api/medicines/{med_id}", token=B)[0], 404)
s, b = call("GET", "/api/medicines/", token=B)
check("B's list does not contain A's medicine", med_id in json.dumps(b), False)
check("no token -> 401", call("GET", "/api/medicines/")[0], 401)

print("\n== Soft delete ==")
check("delete", call("DELETE", f"/api/medicines/{med_id}", token=A)[0], 200)
check("get after delete -> 404", call("GET", f"/api/medicines/{med_id}", token=A)[0], 404)
check("delete again -> 404", call("DELETE", f"/api/medicines/{med_id}", token=A)[0], 404)
check("edit after delete -> 404", call("PUT", f"/api/medicines/{med_id}", {"name": "Zombie"}, A)[0], 404)
s, b = call("GET", "/api/medicines/", token=A)
check("deleted medicine not in list", med_id in json.dumps(b), False)

print("\n== Limit (30 per user) ==")
C = new_user("c")
statuses = [call("POST", "/api/medicines/", {**VALID, "name": f"Med {i:02d}"}, C)[0] for i in range(30)]
check("30 medicines created", statuses.count(201), 30)
s, b = call("POST", "/api/medicines/", {**VALID, "name": "Med 31"}, C)
check("31st medicine rejected", s, 400)

print()
passed, total = sum(results), len(results)
print(f"{passed}/{total} checks passed")
print("ALL GOOD" if passed == total else "SOMETHING FAILED, paste the FAIL lines to Claude")
sys.exit(0 if passed == total else 1)