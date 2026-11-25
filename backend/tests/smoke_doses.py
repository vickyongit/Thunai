"""
THUNAI smoke test for Step 5 (dose logs, today's schedule, take / undo).
Run with the backend server already running:
    python tests/smoke_doses.py
Creates throwaway users smoke-xxxx@example.com (safe to delete later).
Change TZ_OFFSET_MINUTES below if your APP_TIMEZONE is not Asia/Kolkata (UTC+5:30).
"""
import json
import sys
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

BASE = "http://localhost:5000"
TZ_OFFSET_MINUTES = 330  # Asia/Kolkata = UTC+5:30
results = []
skipped = []


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
            text, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        text, status = e.read(), e.code
    except Exception as e:
        print(f"\nCannot reach {BASE}: {e}\nIs the backend running?")
        sys.exit(2)
    try:
        return status, json.loads(text or b"{}")
    except ValueError:
        return status, {"raw": text.decode(errors="replace")[:200]}


def find(obj, key):
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


def skip(label, why):
    skipped.append(label)
    print(f"SKIP  {label}  ({why})")


def new_user(tag):
    email = f"smoke-{tag}-{uuid.uuid4().hex[:6]}@example.com"
    pw = "Smoke1234pass"
    status, body = call("POST", "/api/auth/signup", {"name": f"Smoke {tag}", "email": email, "password": pw})
    token = find(body, "token")
    if not token:
        status, body = call("POST", "/api/auth/login", {"email": email, "password": pw})
        token = find(body, "token")
    if not token:
        print(f"Could not sign up / log in ({status}): {body}")
        sys.exit(2)
    return token


NOW = datetime.now(timezone(timedelta(minutes=TZ_OFFSET_MINUTES)))
TODAY = NOW.strftime("%Y-%m-%d")
MINUTES_SINCE_MIDNIGHT = NOW.hour * 60 + NOW.minute
RUN = uuid.uuid4().hex[:5]


def hhmm(dt):
    return dt.strftime("%H:%M")


def make_medicine(token, label, time_str, **extra):
    body = {
        "name": f"{label} {RUN}", "dosage": "500 mg", "pills_per_dose": 1,
        "times": [time_str], "repeat_type": "daily", "start_date": TODAY, **extra,
    }
    s, b = call("POST", "/api/medicines/", body, token)
    if s != 201:
        print(f"Could not create test medicine {label} ({s}): {b}")
        sys.exit(2)
    return find(b, "id")


def today(token):
    s, b = call("GET", "/api/doses/today", token=token)
    doses = {d.get("name"): d for d in (find(b, "doses") or [])}
    return s, b, doses


def stock(token, med_id):
    s, b = call("GET", f"/api/medicines/{med_id}", token=token)
    return find(b, "pills_remaining")


print(f"Test time: {NOW.isoformat()}  (offset {TZ_OFFSET_MINUTES} min)")
print("\n== Setup ==")
A, B = new_user("a"), new_user("b")

due_id = make_medicine(A, "Due", hhmm(NOW))
stock_id = make_medicine(A, "Stock", hhmm(NOW), pills_per_dose=2, pills_remaining=10)
race_id = make_medicine(A, "Race", hhmm(NOW), pills_remaining=10)
pause_id = make_medicine(A, "Pause", hhmm(NOW))
delete_id = make_medicine(A, "Delete", hhmm(NOW))
early_id = late_id = None
if NOW.hour < 22:
    early_id = make_medicine(A, "Early", hhmm(NOW + timedelta(minutes=120)))
if MINUTES_SINCE_MIDNIGHT >= 20:
    late_id = make_medicine(A, "Late", hhmm(NOW - timedelta(minutes=15)))

print("\n== Today's schedule ==")
s, b, doses = today(A)
check("GET /api/doses/today", s, 200)
check("no token -> 401", call("GET", "/api/doses/today")[0], 401)
for label in ("Due", "Stock", "Race", "Pause", "Delete"):
    check(f"'{label}' dose is listed", f"{label} {RUN}" in doses, True)
check("new doses start as pending", doses.get(f"Due {RUN}", {}).get("status"), "pending")
ids_first = sorted(d["id"] for d in doses.values())
s2, b2, doses2 = today(A)
check("calling today twice creates no duplicates", sorted(d["id"] for d in doses2.values()) == ids_first, True)
check("summary total matches list", find(b2, "total"), len(doses2))
check("B (no medicines) sees no doses", len(today(B)[2]), 0)

due = doses[f"Due {RUN}"]["id"]
stock_dose = doses[f"Stock {RUN}"]["id"]
race_dose = doses[f"Race {RUN}"]["id"]

print("\n== Take ==")
s, b = call("POST", f"/api/doses/{due}/take", token=A)
check("take dose", s, 200)
check("status becomes taken", find(b, "status"), "taken")
check("taken_at is set", bool(find(b, "taken_at")), True)
check("on-time dose is not late", find(b, "was_late"), False)
s, b = call("POST", f"/api/doses/{due}/take", token=A)
check("second take is idempotent (200)", s, 200)
check("still taken after second take", find(b, "status"), "taken")
check("take with invalid id -> 400", call("POST", "/api/doses/not-an-id/take", token=A)[0], 400)
check("take with unknown id -> 404", call("POST", f"/api/doses/{'0' * 24}/take", token=A)[0], 404)

if late_id:
    late_dose = today(A)[2][f"Late {RUN}"]["id"]
    s, b = call("POST", f"/api/doses/{late_dose}/take", token=A)
    check("dose taken 15 min after schedule is marked late", find(b, "was_late"), True)
else:
    skip("late dose", "too close to midnight")

if early_id:
    early_dose = today(A)[2][f"Early {RUN}"]["id"]
    check("dose 2 hours ahead -> 400 (too early)", call("POST", f"/api/doses/{early_dose}/take", token=A)[0], 400)
    check("early dose stays pending", today(A)[2][f"Early {RUN}"]["status"], "pending")
else:
    skip("early dose", "too close to midnight")

print("\n== Stock (take 2 pills/dose, 10 in stock) ==")
check("stock starts at 10", stock(A, stock_id), 10)
call("POST", f"/api/doses/{stock_dose}/take", token=A)
check("taking once: 10 -> 8", stock(A, stock_id), 8)
call("POST", f"/api/doses/{stock_dose}/take", token=A)
check("taking twice does NOT decrement again", stock(A, stock_id), 8)
s, b = call("POST", f"/api/doses/{stock_dose}/undo", token=A)
check("undo", s, 200)
check("undo status is pending", find(b, "status"), "pending")
check("undo restores stock: 8 -> 10", stock(A, stock_id), 10)
call("POST", f"/api/doses/{stock_dose}/undo", token=A)
check("second undo is idempotent, stock stays 10", stock(A, stock_id), 10)
check("take again after undo works", call("POST", f"/api/doses/{stock_dose}/take", token=A)[0], 200)
check("stock back to 8", stock(A, stock_id), 8)

print("\n== Race: 8 simultaneous taps ==")
with ThreadPoolExecutor(max_workers=8) as pool:
    statuses = list(pool.map(lambda _: call("POST", f"/api/doses/{race_dose}/take", token=A)[0], range(8)))
check("all 8 requests answered 200", statuses.count(200), 8)
check("stock decremented exactly once (10 -> 9)", stock(A, race_id), 9)

print("\n== Isolation (user B must get 404) ==")
check("B cannot take A's dose", call("POST", f"/api/doses/{due}/take", token=B)[0], 404)
check("B cannot undo A's dose", call("POST", f"/api/doses/{due}/undo", token=B)[0], 404)
check("undo with invalid id -> 400", call("POST", "/api/doses/not-an-id/undo", token=A)[0], 400)

print("\n== Paused / deleted medicines leave today's list ==")
check("pause medicine", call("PUT", f"/api/medicines/{pause_id}", {"is_active": False}, A)[0], 200)
check("delete medicine", call("DELETE", f"/api/medicines/{delete_id}", token=A)[0], 200)
doses_after = today(A)[2]
check("paused medicine is gone from today", f"Pause {RUN}" in doses_after, False)
check("deleted medicine is gone from today", f"Delete {RUN}" in doses_after, False)
check("active medicines are still listed", f"Due {RUN}" in doses_after, True)
call("PUT", f"/api/medicines/{pause_id}", {"is_active": True}, A)
check("resumed medicine comes back", f"Pause {RUN}" in today(A)[2], True)

print()
passed, total = sum(results), len(results)
print(f"{passed}/{total} checks passed" + (f", {len(skipped)} skipped" if skipped else ""))
print("ALL GOOD" if passed == total else "SOMETHING FAILED, paste the FAIL lines to Claude")
sys.exit(0 if passed == total else 1)