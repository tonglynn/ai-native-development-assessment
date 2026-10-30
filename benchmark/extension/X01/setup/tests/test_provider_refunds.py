from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.gateway import PaymentGateway
from ledgerly.models import Payment
from ledgerly.provider_refunds import refund_via_provider

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_refund_through_provider():
    p = Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)
    refund_via_provider(p, Decimal("40.00"), PaymentGateway())
    assert p.refunded_amount == Decimal("40.00")
