from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.payments import void


def _payment(status="authorized"):
    return Payment("pay_1", "inv_1", Decimal("20.00"), status=status, created_at=T0)


def test_func_voids():
    """void marks an authorized payment as voided."""
    assert void(_payment(), T0).status == "voided"


def test_func_rejects_non_authorized():
    """Captured, refunded and voided payments cannot be voided."""
    for status in ("captured", "refunded", "voided"):
        with raises(Exception):
            void(_payment(status), T0)


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for status in ("captured", "voided"):
        with raises(BillingError):
            void(_payment(status), T0)


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    void(_payment(), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("20.00"), entries[0]


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p = _payment()
    void(p, T0, idempotency_key="vd-1")
    void(p, T0, idempotency_key="vd-1")  # a retried request must not fail or void twice
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "vd-1", entries
