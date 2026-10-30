from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.payments import capture_partial


def _authorized():
    return Payment("pay_1", "inv_1", Decimal("100.00"), created_at=T0)


def test_func_captures_part():
    """capture_partial captures the given part of the authorization."""
    p = capture_partial(_authorized(), Decimal("60.00"), datetime(2026, 1, 2, tzinfo=UTC))
    assert p.amount == Decimal("60.00") and p.status == "captured" and p.captured_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_func_rejects_invalid():
    """Zero, larger-than-authorized and non-authorized captures must be rejected."""
    voided = _authorized()
    voided.status = "voided"
    for p, amount in [(_authorized(), "0"), (_authorized(), "100.01"), (voided, "1.00")]:
        with raises(Exception):
            capture_partial(p, Decimal(amount), T0)


def test_conv_c1_rounded_cents():
    """[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."""
    p = capture_partial(_authorized(), Decimal("33.335"), T0)
    assert p.amount == Decimal("33.34") and p.amount.as_tuple().exponent == -2, p.amount


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for amount in ("0", "100.01"):
        with raises(BillingError):
            capture_partial(_authorized(), Decimal(amount), T0)


def test_conv_c3_naive_and_utc():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        capture_partial(_authorized(), Decimal("10.00"), datetime(2026, 1, 2))
    p = capture_partial(_authorized(), Decimal("10.00"), datetime(2026, 1, 2, 8, tzinfo=SGT))
    assert p.captured_at.utcoffset() == timedelta(0), p.captured_at


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    capture_partial(_authorized(), Decimal("60.00"), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("60.00"), audit.events()


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p = _authorized()
    capture_partial(p, Decimal("60.00"), T0, idempotency_key="cp-1")
    capture_partial(p, Decimal("60.00"), T0, idempotency_key="cp-1")
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "cp-1", entries
