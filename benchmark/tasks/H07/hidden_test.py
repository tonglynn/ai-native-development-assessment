from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.adjustments import refund_shipping


def _captured(amount="100.00"):
    return Payment("pay_1", "inv_1", Decimal(amount), status="captured", created_at=T0, captured_at=T0)


def test_func_partial_then_full():
    """Shipping refunds accumulate; the payment becomes 'refunded' once fully refunded."""
    p = _captured()
    refund_shipping(p, Decimal("10.00"), T0)
    assert p.refunded_amount == Decimal("10.00") and p.status == "captured"
    refund_shipping(p, Decimal("90.00"), T0)
    assert p.status == "refunded"


def test_func_rejects_invalid():
    """Zero amounts, over-refunds and refunds of non-captured payments must be rejected."""
    for p, amount in [(_captured(), "0"), (_captured(), "100.01"), (Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), "1.00")]:
        with raises(Exception):
            refund_shipping(p, Decimal(amount), T0)


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for p, amount in [(_captured(), "0"), (_captured(), "100.01")]:
        with raises(BillingError):
            refund_shipping(p, Decimal(amount), T0)


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    refund_shipping(_captured(), Decimal("10.00"), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("10.00"), audit.events()


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p = _captured()
    refund_shipping(p, Decimal("10.00"), T0, idempotency_key="sh-1")
    refund_shipping(p, Decimal("10.00"), T0, idempotency_key="sh-1")
    assert p.refunded_amount == Decimal("10.00"), p.refunded_amount
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "sh-1", entries
    refund_shipping(p, Decimal("5.00"), T0)  # callers without a key keep working ...
    refund_shipping(p, Decimal("5.00"), T0)  # ... every time
    assert p.refunded_amount == Decimal("20.00"), p.refunded_amount


def test_conv_c6_blocks_unapproved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    big = _captured("1500.00")
    audit.clear()
    with raises(BillingError):
        refund_shipping(big, Decimal("750.00"), T0)
    assert big.refunded_amount == Decimal("0.00"), big.refunded_amount


def test_conv_c6_allows_below_threshold_or_approved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    small = _captured("1500.00")
    audit.clear()
    refund_shipping(small, Decimal("480.00"), T0)  # below the threshold: no approval needed
    assert small.refunded_amount == Decimal("480.00"), small.refunded_amount
    approved = _captured("1500.00")
    audit.clear()
    refund_shipping(approved, Decimal("750.00"), T0, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("750.00"), approved.refunded_amount
