from decimal import Decimal

from ledgerly.invoice import add_line
from ledgerly.models import Invoice


def test_add_line():
    inv = Invoice("inv_1", "cus_1")
    line = add_line(inv, "Seat", 2, Decimal("5.00"))
    assert inv.lines == [line]
    assert line.quantity == 2
