from decimal import Decimal

from ledgerly.promotions import apply_discount


def test_apply_discount():
    assert apply_discount(Decimal("200.00"), 15) == 170
