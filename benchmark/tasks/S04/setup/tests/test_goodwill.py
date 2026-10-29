from decimal import Decimal

from ledgerly.adjustments import goodwill_credit
from ledgerly.models import Invoice, LineItem


def test_goodwill_credit():
    inv = Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 1, Decimal("50.00"))], status="issued")
    assert goodwill_credit(inv, Decimal("5.00"), "late delivery")["amount"] == Decimal("5.00")
