from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.invoice import invoice_total, issue_invoice
from ledgerly.models import Invoice, LineItem, Subscription
from ledgerly.payments import authorize
from ledgerly.subscriptions import current_period

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_invoice():
    return Invoice(
        id="inv_1",
        customer_id="cus_1",
        lines=[LineItem("Seat", 3, Decimal("19.99")), LineItem("Setup", 1, Decimal("50.00"))],
    )


def test_invoice_total():
    assert invoice_total(make_invoice()) == Decimal("109.97")


def test_issue_invoice_records_audit():
    inv = issue_invoice(make_invoice(), T0)
    assert inv.status == "issued"
    assert audit.events("invoice_issued")[0]["invoice_id"] == "inv_1"


def test_issue_empty_invoice_fails():
    with pytest.raises(BillingError):
        issue_invoice(Invoice(id="inv_2", customer_id="cus_1"), T0)


def test_authorize_payment():
    inv = issue_invoice(make_invoice(), T0)
    payment = authorize("pay_1", inv, "109.97", T0)
    assert payment.amount == Decimal("109.97")
    assert payment.status == "authorized"


def test_current_period():
    sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, T0)
    start, end = current_period(sub, datetime(2026, 2, 5, tzinfo=timezone.utc))
    assert start == datetime(2026, 1, 31, tzinfo=timezone.utc)
    assert end == datetime(2026, 3, 2, tzinfo=timezone.utc)
