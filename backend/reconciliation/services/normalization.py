import re
from decimal import Decimal, InvalidOperation


def normalize_reference(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("\ufeff", "")
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def parse_numeric_value(value):
    if value is None:
        return None, "BLANK", ""

    text = str(value).strip()
    if text == "":
        return None, "BLANK", ""

    cleaned = text.replace("$", "").replace(",", "").replace(" ", "")
    if cleaned in {"", "-", "+", "null", "n/a", "na"}:
        return None, "BLANK", ""

    try:
        parsed = Decimal(cleaned)
    except InvalidOperation:
        return None, "INVALID", f"Could not parse numeric value: {text}"

    return parsed, "VALID", ""
