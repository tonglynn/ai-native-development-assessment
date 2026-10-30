from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.gateway import PaymentGateway
from ledgerly.provider_refunds import refund_via_provider


def _captured(pid="pay_1"):
    return Payment(pid, "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)


def test_func_refunds_through_provider():
    """A refund goes through the provider, accumulates on the payment and records the provider's refund id."""
    p, g = _captured(), PaymentGateway()
    assert refund_via_provider(p, Decimal("40.00"), g) is p
    assert p.refunded_amount == Decimal("40.00") and p.status == "captured"
    assert g.money_moved == Decimal("40.00") and p.provider_refund_ids == ["re_1"]
    refund_via_provider(p, Decimal("60.00"), g)
    assert p.status == "refunded" and p.provider_refund_ids == ["re_1", "re_2"]


def test_func_retries_after_a_timeout():
    """A provider timeout is retried, and the refund then succeeds."""
    p, g = _captured(), PaymentGateway(["timeout", "ok"])
    refund_via_provider(p, Decimal("30.00"), g)
    assert p.refunded_amount == Decimal("30.00") and len(g.calls) == 2


def test_func_gives_up_after_three_attempts():
    """After 3 timeouts the payment is unchanged and BillingError('provider_unavailable') is raised."""
    p, g = _captured(), PaymentGateway(["timeout"] * 3)
    with raises(BillingError):
        refund_via_provider(p, Decimal("30.00"), g)
    assert len(g.calls) == 3 and p.refunded_amount == Decimal("0.00") and p.status == "captured"


def test_func_rejects_invalid_before_calling_the_provider():
    """Invalid refunds are rejected before the provider is called."""
    g = PaymentGateway()
    for bad in (Decimal("0.00"), Decimal("-5.00"), Decimal("100.01")):
        with raises(Exception):
            refund_via_provider(_captured(), bad, g)
    with raises(Exception):
        refund_via_provider(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), g)
    assert g.calls == [], g.calls


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    with raises(BillingError):
        refund_via_provider(_captured(), Decimal("100.01"), PaymentGateway())
    with raises(BillingError):
        refund_via_provider(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), PaymentGateway())


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against (payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    refund_via_provider(_captured(), Decimal("40.00"), PaymentGateway())
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("40.00"), entries[0]


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    p, g = _captured(), PaymentGateway()
    refund_via_provider(p, Decimal("40.00"), g, idempotency_key="rf-1")
    refund_via_provider(p, Decimal("40.00"), g, idempotency_key="rf-1")  # a retried request
    assert p.refunded_amount == Decimal("40.00"), p.refunded_amount
    assert g.money_moved == Decimal("40.00"), g.money_moved
    refund_via_provider(p, Decimal("10.00"), g)  # callers without a key keep working ...
    refund_via_provider(p, Decimal("10.00"), g)  # ... every time
    assert p.refunded_amount == Decimal("60.00"), p.refunded_amount


def test_conv_c7_retry_with_the_same_key():
    """[team convention] A timeout from the payment provider does not mean the refund failed: the provider may already have moved the money, and only its idempotency key stops a retry from refunding again (this is how INC-204 refunded customers twice). Use one provider idempotency key per refund request, the caller's idempotency_key when one is given, and send the same key on every retry; never generate a new key per attempt."""
    audit.clear()
    p, g = _captured(), PaymentGateway(["lost", "ok"])  # the provider refunded, the answer was lost, then a retry
    refund_via_provider(p, Decimal("25.00"), g)
    assert g.money_moved == Decimal("25.00"), f"the provider moved {g.money_moved}: the retry refunded again"
    assert len({key for _, _, key in g.calls}) == 1, g.calls
    assert p.refunded_amount == Decimal("25.00"), p.refunded_amount
