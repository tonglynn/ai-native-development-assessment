from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from .errors import BillingError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_money(value) -> Decimal:
    """Convert an int, str or Decimal into a Decimal amount."""
    if isinstance(value, (bool, float)):
        raise BillingError("float_amount", f"refusing to convert {value!r}")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise BillingError("invalid_amount", repr(value)) from None


def round_money(value) -> Decimal:
    """Round to the cent using the finance team's rounding policy."""
    return to_money(value).quantize(CENT, rounding=ROUND_HALF_EVEN)
