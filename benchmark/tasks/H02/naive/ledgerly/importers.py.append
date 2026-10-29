import re
from decimal import Decimal


def parse_amount(text):
    cleaned = text.strip().removeprefix("$").replace(",", "")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", cleaned):
        raise ValueError(f"invalid amount: {text!r}")
    return Decimal(cleaned)
