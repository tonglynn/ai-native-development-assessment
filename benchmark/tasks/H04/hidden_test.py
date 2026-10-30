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
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    issue_credit_note(_issued(), Decimal("10.00"), "goodwill")
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("invoice_id") == "inv_1" and entries[0].get("amount") == Decimal("10.00"), entries[0]


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    first = issue_credit_note(_issued(), Decimal("10.00"), "goodwill", idempotency_key="cn-1")
    again = issue_credit_note(_issued(), Decimal("10.00"), "goodwill", idempotency_key="cn-1")
    assert again == first, again
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "cn-1", entries
    issue_credit_note(_issued(), Decimal("5.00"), "goodwill")  # callers without a key keep working ...
    issue_credit_note(_issued(), Decimal("5.00"), "goodwill")  # ... every time
    assert len([e for e in audit.events() if e.get("invoice_id") == "inv_1"]) == 3, audit.events()


def _annual(iid):
    return Invoice(iid, "cus_1", lines=[LineItem("Annual plan", 1, Decimal("1500.00"))], status="issued")


def test_conv_c6_blocks_unapproved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    audit.clear()
    with raises(BillingError):
        issue_credit_note(_annual("inv_2"), Decimal("500.01"), "x")
    assert not [e for e in audit.events() if e.get("invoice_id") == "inv_2"], audit.events()  # nothing was credited


def test_conv_c6_allows_at_threshold_or_approved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    audit.clear()
    assert issue_credit_note(_annual("inv_3"), Decimal("500.00"), "x")["amount"] == Decimal("500.00")  # at the threshold
    audit.clear()
    note = issue_credit_note(_annual("inv_4"), Decimal("900.00"), "x", approved_by="usr_finance_lead")
    assert note["amount"] == Decimal("900.00"), note
