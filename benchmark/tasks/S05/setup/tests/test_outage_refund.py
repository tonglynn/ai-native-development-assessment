from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.adjustments import outage_refund
from ledgerly.models import Payment

T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_outage_refund():
    p = Payment("pay_1", "inv_1", Decimal("80.00"), status="captured", created_at=T0, captured_at=T0)
    outage_refund(p, Decimal("8.00"), T0)
    assert p.refunded_amount == Decimal("8.00")
