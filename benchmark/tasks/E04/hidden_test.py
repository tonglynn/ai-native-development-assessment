from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.adjustments import refund


def _captured():
    return Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)


def test_func_partial_then_full():
    """Partial refunds accumulate; the payment becomes 'refunded' once fully refunded."""
    p = _captured()
    refund(p, Decimal("40.00"), T0)
    assert p.refunded_amount == Decimal("40.00") and p.status == "captured"
    refund(p, Decimal("60.00"), T0)
    assert p.refunded_amount == Decimal("100.00") and p.status == "refunded"


def test_func_rejects_invalid():
    """Over-refunds and refunds of non-captured payments must be rejected."""
    with raises(Exception):
        refund(_captured(), Decimal("100.01"), T0)
    with raises(Exception):
        refund(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), T0)


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    with raises(BillingError):
        refund(_captured(), Decimal("100.01"), T0)
    with raises(BillingError):
        refund(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), T0)


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    refund(_captured(), Decimal("40.00"), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("40.00"), entries[0]


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p = _captured()
    refund(p, Decimal("40.00"), T0, idempotency_key="rf-1")
    refund(p, Decimal("40.00"), T0, idempotency_key="rf-1")  # a retried request
    assert p.refunded_amount == Decimal("40.00"), p.refunded_amount
    assert sum(e.get("idempotency_key") == "rf-1" for e in audit.events()) == 1, audit.events()


def _big(pid):
    return Payment(pid, "inv_1", Decimal("2000.00"), status="captured", created_at=T0, captured_at=T0)


def test_conv_c6_blocks_unapproved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    big = _big("pay_9")
    with raises(BillingError):
        refund(big, Decimal("600.00"), T0)
    assert big.refunded_amount == Decimal("0.00"), big.refunded_amount


def test_conv_c6_allows_at_threshold_or_approved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    at_threshold = _big("pay_10")
    refund(at_threshold, Decimal("500.00"), T0)  # at the threshold: no approval needed
    assert at_threshold.refunded_amount == Decimal("500.00"), at_threshold.refunded_amount
    approved = _big("pay_11")
    refund(approved, Decimal("600.00"), T0, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("600.00"), approved.refunded_amount
