from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.payments import capture


def _authorized():
    return Payment("pay_1", "inv_1", Decimal("20.00"), created_at=T0)


def test_func_captures():
    """capture marks the payment captured and stores when it happened."""
    p = capture(_authorized(), datetime(2026, 1, 2, tzinfo=UTC))
    assert p.status == "captured" and p.captured_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_func_rejects_non_authorized():
    """Only authorized payments can be captured."""
    p = _authorized()
    p.status = "voided"
    with raises(Exception):
        capture(p, T0)


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    p = _authorized()
    p.status = "captured"
    with raises(BillingError):
        capture(p, T0)


def test_conv_c3_naive_and_utc():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        capture(_authorized(), datetime(2026, 1, 2))
    p = capture(_authorized(), datetime(2026, 1, 2, 8, tzinfo=SGT))
    assert p.captured_at.utcoffset() == timedelta(0), p.captured_at


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment/credit must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    capture(_authorized(), T0)
    entries = [e for e in audit.events() if "captur" in e["event"]]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("payment_id") == "pay_1" and entries[0].get("amount") == Decimal("20.00"), entries[0]


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment/credit must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). If an audit entry with the same key already exists (ledgerly.audit.events()), return without applying the operation again, and include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p = _authorized()
    capture(p, T0, idempotency_key="cap-1")
    capture(p, T0, idempotency_key="cap-1")  # a retried request must not fail or capture twice
    entries = [e for e in audit.events() if "captur" in e["event"]]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "cap-1", entries
