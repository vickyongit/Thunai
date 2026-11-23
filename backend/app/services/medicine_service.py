import re
import logging
from datetime import date, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from flask import current_app

logger = logging.getLogger(__name__)

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

FOOD_INSTRUCTIONS = {"before_food", "after_food", "with_food", "any"}
REPEAT_TYPES = {"daily", "specific_days"}


def _get_timezone():
    tz_name = current_app.config.get("APP_TIMEZONE", "Asia/Kolkata")
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        logger.warning("Invalid APP_TIMEZONE '%s', falling back to Asia/Kolkata.", tz_name)
        return ZoneInfo("Asia/Kolkata")


def _today_str() -> str:
    return date.today().astimezone(_get_timezone()).strftime("%Y-%m-%d")


def _parse_date(val, field_name: str) -> tuple:
    """Returns (date_str, error_msg_or_None)."""
    if not isinstance(val, str):
        return None, f"{field_name} must be a string in YYYY-MM-DD format."
    try:
        d = date.fromisoformat(val)
        return d.isoformat(), None
    except ValueError:
        return None, f"{field_name} must be a valid date in YYYY-MM-DD format."


def validate_medicine(data: dict, is_update: bool = False) -> list:
    """
    Validate medicine fields. Returns a list of error strings (empty = valid).
    Mutates data to coerce types (e.g., sort times) only when validation passes.
    """
    errors = []

    # --- name ---
    if not is_update or "name" in data:
        name = data.get("name")
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 80:
            errors.append("Medicine name must be 2–80 characters.")

    # --- dosage ---
    if not is_update or "dosage" in data:
        dosage = data.get("dosage")
        if not isinstance(dosage, str) or not 1 <= len(dosage.strip()) <= 50:
            errors.append("Dosage must be 1–50 characters (e.g. '500 mg').")

    # --- pills_per_dose ---
    if not is_update or "pills_per_dose" in data:
        ppd = data.get("pills_per_dose")
        if isinstance(ppd, bool) or not isinstance(ppd, (int, float)):
            errors.append("pills_per_dose must be an integer between 1 and 20.")
        else:
            ppd = int(ppd)
            if not 1 <= ppd <= 20:
                errors.append("pills_per_dose must be between 1 and 20.")
            else:
                data["pills_per_dose"] = ppd

    # --- times ---
    if not is_update or "times" in data:
        times = data.get("times")
        if not isinstance(times, list) or len(times) == 0 or len(times) > 6:
            errors.append("times must be a list of 1–6 'HH:MM' values.")
        else:
            bad = [t for t in times if not isinstance(t, str) or not TIME_RE.match(t)]
            if bad:
                errors.append(f"Invalid time value(s): {bad}. Use 'HH:MM' 24-hour format.")
            elif len(times) != len(set(times)):
                errors.append("times must not contain duplicates.")
            else:
                data["times"] = sorted(set(times))

    # --- repeat_type + days_of_week ---
    rtype = data.get("repeat_type")
    if not is_update or "repeat_type" in data:
        if rtype not in REPEAT_TYPES:
            errors.append(f"repeat_type must be one of: {', '.join(REPEAT_TYPES)}.")
        elif rtype == "specific_days":
            dow = data.get("days_of_week")
            if not isinstance(dow, list) or len(dow) == 0:
                errors.append("days_of_week must be a non-empty list when repeat_type is 'specific_days'.")
            else:
                bad_days = [d for d in dow if not isinstance(d, int) or isinstance(d, bool) or not 0 <= d <= 6]
                if bad_days:
                    errors.append("days_of_week values must be integers 0–6 (0=Monday).")
                elif len(dow) != len(set(dow)):
                    errors.append("days_of_week must not contain duplicates.")
                else:
                    data["days_of_week"] = sorted(set(dow))
        else:
            # daily: ignore and clear days_of_week
            data["days_of_week"] = []

    # --- start_date ---
    if not is_update or "start_date" in data:
        raw_start = data.get("start_date") or _today_str()
        start_str, err = _parse_date(raw_start, "start_date")
        if err:
            errors.append(err)
        else:
            data["start_date"] = start_str

    # --- end_date (optional) ---
    if "end_date" in data and data["end_date"] is not None and data["end_date"] != "":
        end_str, err = _parse_date(data["end_date"], "end_date")
        if err:
            errors.append(err)
        else:
            data["end_date"] = end_str
            # Compare dates only if start_date is also present and valid
            start_in_data = data.get("start_date")
            if start_in_data and not errors:
                if end_str < start_in_data:
                    errors.append("end_date must not be before start_date.")

    # --- food_instruction ---
    if "food_instruction" in data:
        fi = data.get("food_instruction")
        if fi not in FOOD_INSTRUCTIONS:
            errors.append(f"food_instruction must be one of: {', '.join(sorted(FOOD_INSTRUCTIONS))}.")

    # --- remarks ---
    if "remarks" in data and data["remarks"] is not None:
        remarks = data.get("remarks")
        if not isinstance(remarks, str):
            errors.append("remarks must be a string.")
        elif len(remarks) > 300:
            errors.append("remarks must be 300 characters or fewer.")

    # --- pills_remaining ---
    if "pills_remaining" in data and data["pills_remaining"] is not None:
        pr = data.get("pills_remaining")
        if isinstance(pr, bool) or not isinstance(pr, (int, float)):
            errors.append("pills_remaining must be an integer 0–10000, or null.")
        else:
            pr = int(pr)
            if not 0 <= pr <= 10000:
                errors.append("pills_remaining must be between 0 and 10000.")
            else:
                data["pills_remaining"] = pr

    # --- is_active ---
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            errors.append("is_active must be a boolean.")

    return errors


def build_medicine_create(data: dict) -> dict:
    """Build the full document fields for a new medicine (call after validate passes)."""
    return {
        "name": data["name"].strip(),
        "dosage": data["dosage"].strip(),
        "pills_per_dose": int(data["pills_per_dose"]),
        "times": data["times"],
        "repeat_type": data["repeat_type"],
        "days_of_week": data.get("days_of_week", []),
        "start_date": data.get("start_date") or _today_str(),
        "end_date": data.get("end_date") or None,
        "food_instruction": data.get("food_instruction", "any"),
        "remarks": data.get("remarks") or None,
        "pills_remaining": data.get("pills_remaining"),
        "is_active": data.get("is_active", True),
    }


def build_medicine_update(data: dict) -> dict:
    """Strip unknown / immutable fields; keep only what can be updated."""
    ALLOWED = {
        "name", "dosage", "pills_per_dose", "times", "repeat_type",
        "days_of_week", "start_date", "end_date", "food_instruction",
        "remarks", "pills_remaining", "is_active",
    }
    update = {}
    for key in ALLOWED:
        if key not in data:
            continue
        val = data[key]
        if key == "name":
            update[key] = str(val).strip()
        elif key == "dosage":
            update[key] = str(val).strip()
        elif key == "end_date":
            update[key] = val if val else None
        elif key == "remarks":
            update[key] = val if val else None
        else:
            update[key] = val
    return update
