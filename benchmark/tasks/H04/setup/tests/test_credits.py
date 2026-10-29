from decimal import Decimal

from ledgerly.credits import issue_credit_note
from ledgerly.models import Invoice, LineItem


def test_issue_credit_note():
    inv = Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 1, Decimal("50.00"))], status="issued")
    note = issue_credit_note(inv, Decimal("10.00"), "goodwill")
    assert note["amount"] == Decimal("10.00")
