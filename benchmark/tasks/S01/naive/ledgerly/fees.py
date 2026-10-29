from decimal import ROUND_HALF_UP, Decimal

from .errors import BillingError
from .money import to_money


def processing_fee(amount):
    amount = to_money(amount)
    if amount <= 0:
        raise BillingError("non_positive_amount", str(amount))
    return (amount * Decimal("0.029") + Decimal("0.30")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
