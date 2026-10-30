from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.adjustments import outage_refund


T1 = datetime(2026, 10, 1, tzinfo=UTC)


def _captured(pid="pay_1", amount="2400.00"):
    return Payment(pid, "inv_1", Decimal(amount), status="captured", created_at=T1, captured_at=T1)


def test_func_partial_then_full():
    """Refunds accumulate; the payment becomes 'refunded' once fully refunded."""
    p = _captured(amount="80.00")
    outage_refund(p, Decimal("30.00"), T1)
    assert p.refunded_amount == Decimal("30.00") and p.status == "captured"
    outage_refund(p, Decimal("50.00"), T1)
    assert p.refunded_amount == Decimal("80.00") and p.status == "refunded"


def test_func_rejects_invalid():
    """Non-positive amounts, over-refunds and refunds of non-captured payments are rejected."""
    for p, amount in [(_captured(), "0"), (_captured(amount="80.00"), "80.01"),
                      (Payment("pay_2", "inv_1", Decimal("80.00"), created_at=T1), "1.00")]:
        with raises(Exception):
            outage_refund(p, Decimal(amount), T1)


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for p, amount in [(_captured(), "0"), (_captured(amount="80.00"), "80.01"),
                      (Payment("pay_2", "inv_1", Decimal("80.00"), created_at=T1), "1.00")]:
        with raises(BillingError):
            outage_refund(p, Decimal(amount), T1)


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    outage_refund(_captured(), Decimal("12.00"), T1)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("12.00"), audit.events()


def test_conv_c6_blocks_unapproved():
    """[team convention] Support-initiated refunds and credits above the approval threshold need a second approver: accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below the threshold need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing. The threshold is set by finance policy: 500.00 before 2.0.0, 1000.00 since 2.0.0 (see CHANGELOG)."""
    p = _captured()
    with raises(BillingError):
        outage_refund(p, Decimal("1250.00"), T1)
    assert p.refunded_amount == Decimal("0.00"), p.refunded_amount


def test_conv_c6_allows_below_threshold_or_approved():
    """[team convention] Support-initiated refunds and credits above the approval threshold need a second approver: accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below the threshold need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing. The threshold is set by finance policy: 500.00 before 2.0.0, 1000.00 since 2.0.0 (see CHANGELOG)."""
    # 800.00 is below the 2.0.0 threshold (1000.00): applying the old 500.00 rule wrongly blocks it
    small = _captured("pay_3")
    outage_refund(small, Decimal("800.00"), T1)
    assert small.refunded_amount == Decimal("800.00"), small.refunded_amount
    approved = _captured("pay_4")
    outage_refund(approved, Decimal("1250.00"), T1, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("1250.00"), approved.refunded_amount
