from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.adjustments import write_off
from ledgerly.models import Invoice, LineItem


def test_write_off():
    inv = Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 1, Decimal("50.00"))], status="issued")
    result = write_off(inv, datetime(2026, 2, 1, tzinfo=timezone.utc), "customer insolvent")
    assert inv.status == "void" and result["amount"] == Decimal("50.00")
