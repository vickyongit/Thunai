import re
import logging

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+?\d{10,15}$")
ALLOWED_LANGUAGES = {"en", "ta"}
ALLOWED_GENDERS = {"male", "female", "other", "prefer_not_to_say"}


def validate_profile_update(data: dict) -> list:
    errors = []

    if "name" in data:
        name = data["name"]
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 60:
            errors.append("Name must be between 2 and 60 characters.")

    if "phone" in data and data["phone"] not in (None, ""):
        phone = data["phone"]
        if (
            not isinstance(phone, (str, int))
            or isinstance(phone, bool)
            or not PHONE_RE.match(str(phone).strip())
        ):
            errors.append("Phone must be 10-15 digits, optionally starting with +.")

    if "age" in data and data["age"] not in (None, ""):
        age = data["age"]
        if (
            isinstance(age, bool)
            or not isinstance(age, (int, str))
            or not str(age).strip().isdigit()
            or not 1 <= int(age) <= 120
        ):
            errors.append("Age must be a number between 1 and 120.")

    if "language" in data:
        if not (isinstance(data["language"], str) and data["language"] in ALLOWED_LANGUAGES):
            errors.append("Language must be one of: " + ", ".join(sorted(ALLOWED_LANGUAGES)) + ".")

    if "gender" in data and data["gender"] not in (None, ""):
        if not (isinstance(data["gender"], str) and data["gender"] in ALLOWED_GENDERS):
            errors.append("Gender must be one of: " + ", ".join(sorted(ALLOWED_GENDERS)) + ".")

    if "elder_mode" in data and not isinstance(data["elder_mode"], bool):
        errors.append("elder_mode must be a boolean.")

    return errors


def build_profile_update(data: dict) -> dict:
    """Keep only allowed fields and coerce types (call after validation passes)."""
    update = {}
    if "name" in data:
        update["name"] = data["name"].strip()
    if "phone" in data:
        update["phone"] = str(data["phone"]).strip() if data["phone"] not in (None, "") else None
    if "age" in data:
        update["age"] = int(data["age"]) if data["age"] not in (None, "") else None
    if "gender" in data:
        update["gender"] = data["gender"] or None
    if "language" in data:
        update["language"] = data["language"]
    if "elder_mode" in data:
        update["elder_mode"] = bool(data["elder_mode"])
    return update