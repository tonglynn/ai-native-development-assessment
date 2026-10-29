from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.adjustments import issue_credit_note


def _issued(status="issued"):
    return Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 3, Decimal("19.99")), LineItem("Setup", 1, Decimal("50.00"))], status=status)


def test_func_returns_note():
    """issue_credit_note returns the invoice id, amount and reason."""
    note = issue_credit_note(_issued(), Decimal("10.00"), "goodwill")
    assert note == {"invoice_id": "inv_1", "amount": Decimal("10.00"), "reason": "goodwill"}


def test_func_rejects_invalid():
    """Zero, excessive and non-issued credits must be rejected."""
    for inv, amount in [(_issued(), "0"), (_issued(), "109.98"), (_issued("draft"), "1.00")]:
        with raises(Exception):
            issue_credit_note(inv, Decimal(amount), "x")


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for inv, amount in [(_issued(), "0"), (_issued(), "109.98"), (_issued("draft"), "1.00")]:
        with raises(BillingError):
            issue_credit_note(inv, Decimal(amount), "x")


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment/credit must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    issue_credit_note(_issued(), Decimal("10.00"), "goodwill")
    entries = [e for e in audit.events() if "credit" in e["event"]]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("invoice_id") == "inv_1" and entries[0].get("amount") == Decimal("10.00"), entries[0]
