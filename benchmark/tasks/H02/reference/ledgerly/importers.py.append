import re
from decimal import Decimal

from .errors import BillingError
from .money import round_money

_AMOUNT = re.compile(r"\d+(\.\d{1,2})?")


def parse_amount(text: str) -> Decimal:
    """Parse a customer-entered amount such as "$1,234.50"."""
    if not isinstance(text, str):
        raise BillingError("invalid_amount", repr(text))
    cleaned = text.strip().removeprefix("$").replace(",", "")
    if not _AMOUNT.fullmatch(cleaned):
        raise BillingError("invalid_amount", repr(text))
    return round_money(cleaned)
