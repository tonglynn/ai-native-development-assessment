from decimal import Decimal

from .errors import BillingError
from .money import round_money, to_money


def processing_fee(amount) -> Decimal:
    """Card processing fee: 2.9% + 0.30."""
    amount = to_money(amount)
    if amount <= 0:
        raise BillingError("non_positive_amount", str(amount))
    return round_money(amount * Decimal("0.029") + Decimal("0.30"))
