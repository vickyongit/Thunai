import re
import logging

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+?\d{10,15}$")

PRIORITY_MESSAGE = "Priority must be a positive integer (1=primary, 2=secondary, 3+=other)."


def validate_contact(data: dict, is_update: bool = False) -> list:
    errors = []

    if not is_update or "name" in data:
        name = data.get("name")
        if not isinstance(name, str) or not 2 <= len(name.strip()) <= 60:
            errors.append("Contact name must be 2–60 characters.")

    if not is_update or "phone" in data:
        phone = data.get("phone")
        if (
            not isinstance(phone, (str, int))
            or isinstance(phone, bool)
            or not PHONE_RE.match(str(phone).strip())
        ):
            errors.append("Phone must be 10-15 digits, optionally starting with +.")

    if not is_update or "relationship" in data:
        rel = data.get("relationship")
        if not isinstance(rel, str) or not rel.strip() or len(rel.strip()) > 30:
            errors.append("Relationship is required (max 30 characters).")

    if not is_update or "priority" in data:
        raw = data.get("priority", 3)
        if isinstance(raw, bool) or not isinstance(raw, (int, str)):
            errors.append(PRIORITY_MESSAGE)
        else:
            try:
                priority = int(raw)
                if priority < 1:
                    raise ValueError
                data["priority"] = priority
            except ValueError:
                errors.append(PRIORITY_MESSAGE)

    if "notify_on_missed" in data and not isinstance(data["notify_on_missed"], bool):
        errors.append("notify_on_missed must be a boolean.")

    return errors


def build_contact_update(data: dict) -> dict:
    """Keep only known fields (call after validate_contact passes)."""
    update = {}
    if "name" in data:
        update["name"] = data["name"].strip()
    if "phone" in data:
        update["phone"] = str(data["phone"]).strip()
    if "relationship" in data:
        update["relationship"] = data["relationship"].strip().lower()
    if "priority" in data:
        update["priority"] = int(data["priority"])
    if "notify_on_missed" in data:
        update["notify_on_missed"] = bool(data["notify_on_missed"])
    return update