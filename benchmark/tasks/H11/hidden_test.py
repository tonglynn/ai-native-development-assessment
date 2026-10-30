from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.support import process_refund_request


AGENT = "usr_support_1"


def _captured(amount="100.00", pid="pay_1"):
    return Payment(pid, "inv_1", Decimal(amount), status="captured", created_at=T0, captured_at=T0)


def test_func_partial_then_full():
    """Refunds typed in the console accumulate; the payment becomes 'refunded' once fully refunded."""
    p = _captured()
    process_refund_request(p, "40.00", AGENT, T0)
    assert p.refunded_amount == Decimal("40.00") and p.status == "captured"
    process_refund_request(p, "60", AGENT, T0)
    assert p.refunded_amount == Decimal("100.00") and p.status == "refunded"


def test_func_rejects_invalid():
    """Over-refunds, non-positive amounts and refunds of non-captured payments must be rejected."""
    with raises(Exception):
        process_refund_request(_captured(), "100.01", AGENT, T0)
    with raises(Exception):
        process_refund_request(_captured(), "0", AGENT, T0)
    with raises(Exception):
        process_refund_request(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), "1.00", AGENT, T0)


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    p = _captured()
    process_refund_request(p, "12.5", AGENT, T0)
    assert isinstance(p.refunded_amount, Decimal) and p.refunded_amount == Decimal("12.50"), p.refunded_amount
    assert p.refunded_amount.as_tuple().exponent == -2, p.refunded_amount


def test_conv_c1_half_up():
    """[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."""
    p = _captured()
    process_refund_request(p, "1.005", AGENT, T0)  # float("1.005") is 1.00499..., so a detour through float rounds down
    assert p.refunded_amount == Decimal("1.01"), p.refunded_amount


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for amount in ("100.01", "-5", "ten"):
        with raises(BillingError):
            process_refund_request(_captured(), amount, AGENT, T0)
    with raises(BillingError):
        process_refund_request(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), "1.00", AGENT, T0)


def test_conv_c3_rejects_naive():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        process_refund_request(_captured(), "10.00", AGENT, datetime(2026, 1, 1))


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    process_refund_request(_captured(), "40.00", AGENT, T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("40.00"), entries[0]


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p = _captured()
    process_refund_request(p, "40.00", AGENT, T0, idempotency_key="rq-1")
    process_refund_request(p, "40.00", AGENT, T0, idempotency_key="rq-1")  # the console retries after a timeout
    assert p.refunded_amount == Decimal("40.00"), p.refunded_amount
    assert sum(e.get("idempotency_key") == "rq-1" for e in audit.events()) == 1, audit.events()
    process_refund_request(p, "10.00", AGENT, T0)  # callers without a key keep working ...
    process_refund_request(p, "10.00", AGENT, T0)  # ... every time
    assert p.refunded_amount == Decimal("60.00"), p.refunded_amount


def test_conv_c6_blocks_unapproved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    big = _captured("1800.00")
    audit.clear()
    with raises(BillingError):
        process_refund_request(big, "650.00", AGENT, T0)
    assert big.refunded_amount == Decimal("0.00"), big.refunded_amount


def test_conv_c6_allows_below_threshold_or_approved():
    """[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need no approval; above it, raise BillingError("approval_required") when `approved_by` is missing."""
    small = _captured("1800.00", pid="pay_5")
    audit.clear()
    process_refund_request(small, "450.00", AGENT, T0)  # below the threshold: no approval needed
    assert small.refunded_amount == Decimal("450.00"), small.refunded_amount
    approved = _captured("1800.00", pid="pay_6")
    audit.clear()
    process_refund_request(approved, "650.00", AGENT, T0, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("650.00"), approved.refunded_amount
