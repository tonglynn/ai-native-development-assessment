from decimal import ROUND_HALF_UP, Decimal

from .errors import BillingError
from .money import to_money


def partner_commission(amount, rate_percent):
    rate = to_money(rate_percent)
    if rate < 0 or rate > 50:
        raise BillingError("invalid_rate", str(rate))
    return (to_money(amount) * rate / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
