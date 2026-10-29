from decimal import Decimal

from .errors import BillingError
from .money import round_money, to_money


def add_tax(amount, rate_percent) -> Decimal:
    """Gross amount including ``rate_percent`` percent tax."""
    rate = to_money(rate_percent)
    if rate < 0 or rate > 100:
        raise BillingError("invalid_tax_rate", str(rate))
    amount = to_money(amount)
    return round_money(amount + amount * rate / 100)
