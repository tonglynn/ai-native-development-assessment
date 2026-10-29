from decimal import Decimal

from .money import round_money, to_money


def apply_discount(amount, percent) -> Decimal:
    """``amount`` reduced by ``percent`` percent."""
    return round_money(to_money(amount) * (100 - to_money(percent)) / 100)
