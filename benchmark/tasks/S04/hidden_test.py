from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.adjustments import goodwill_credit


def _issued(total="1500.00", status="issued"):
    return Invoice("inv_1", "cus_1", lines=[LineItem("Annual plan", 1, Decimal(total))], status=status)


def test_func_returns_credit():
    """goodwill_credit returns the invoice id, amount and reason."""
    assert goodwill_credit(_issued(), Decimal("5.00"), "late") == {"invoice_id": "inv_1", "amount": Decimal("5.00"), "reason": "late"}


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for inv, amount in [(_issued(), "0"), (_issued("50.00"), "50.01"), (_issued(status="draft"), "1.00")]:
        with raises(BillingError):
            goodwill_credit(inv, Decimal(amount), "x")


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment/credit must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    goodwill_credit(_issued(), Decimal("5.00"), "late")
    entries = [e for e in audit.events() if "credit" in e["event"] or "goodwill" in e["event"]]
    assert len(entries) == 1 and entries[0].get("invoice_id") == "inv_1", audit.events()


def test_conv_c6_approval_threshold():
    """[team convention] Support-initiated refunds and credits above the approval threshold need a second approver: accept a keyword-only `approved_by` and raise BillingError("approval_required") when it is missing. The threshold is set by finance policy: 500.00 before 2.0.0, 1000.00 since 2.0.0 (see CHANGELOG)."""
    goodwill_credit(_issued(), Decimal("700.00"), "x")  # below the 2.0.0 threshold: no approval needed
    with raises(BillingError):
        goodwill_credit(_issued(), Decimal("1200.00"), "x")
    assert goodwill_credit(_issued(), Decimal("1200.00"), "x", approved_by="usr_finance_lead")["amount"] == Decimal("1200.00")
