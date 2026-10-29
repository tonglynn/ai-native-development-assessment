from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Payment
from ledgerly.payments import capture_partial

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_capture_partial():
    p = Payment("pay_1", "inv_1", Decimal("100.00"), created_at=T0)
    capture_partial(p, Decimal("60.00"), T0)
    assert p.amount == 60 and p.status == "captured"
