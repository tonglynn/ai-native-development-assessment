from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Payment
from ledgerly.reports import payments_between

UTC = timezone.utc


def test_payments_between():
    a = Payment("a", "inv", Decimal("1.00"), created_at=datetime(2026, 1, 2, tzinfo=UTC))
    b = Payment("b", "inv", Decimal("1.00"), created_at=datetime(2026, 1, 5, tzinfo=UTC))
    assert payments_between([b, a], datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)) == [a]
