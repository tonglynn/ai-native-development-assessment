from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.refunds import refund


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
    """[team convention] Every operation that moves money or changes a payment/credit must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    refund(_captured(), Decimal("40.00"), T0)
    entries = [e for e in audit.events() if "refund" in e["event"]]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("payment_id") == "pay_1" and entries[0].get("amount") == Decimal("40.00"), entries[0]
