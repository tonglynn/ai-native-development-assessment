from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Payment
from ledgerly.payments import void

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_void():
    p = Payment("pay_1", "inv_1", Decimal("20.00"), created_at=T0)
    void(p, T0)
    assert p.status == "voided"
