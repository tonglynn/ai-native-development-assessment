from decimal import Decimal

from ledgerly.tax import add_tax


def test_add_tax():
    assert add_tax(Decimal("100.00"), 8) == 108
