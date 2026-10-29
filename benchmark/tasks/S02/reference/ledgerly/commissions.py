from decimal import Decimal

from .errors import BillingError
from .money import round_money, to_money


def partner_commission(amount, rate_percent) -> Decimal:
    """Reseller commission on a sale."""
    rate = to_money(rate_percent)
    if rate < 0 or rate > 50:
        raise BillingError("invalid_rate", str(rate))
    return round_money(to_money(amount) * rate / 100)
