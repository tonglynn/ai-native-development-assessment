from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Payment
from ledgerly.refunds import refund

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_partial_refund():
    p = Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)
    refund(p, Decimal("40.00"), T0)
    assert p.refunded_amount == Decimal("40.00")
