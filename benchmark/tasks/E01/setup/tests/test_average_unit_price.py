from decimal import Decimal

from ledgerly.invoice import average_unit_price
from ledgerly.models import Invoice, LineItem


def test_weighted_average():
    inv = Invoice("inv_1", "cus_1", lines=[LineItem("a", 2, Decimal("10.00")), LineItem("b", 1, Decimal("4.00"))])
    assert average_unit_price(inv) == 8
