from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Subscription
from ledgerly.renewals import next_renewal


def test_next_renewal():
    sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert next_renewal(sub, datetime(2026, 1, 15, tzinfo=timezone.utc)) == datetime(2026, 1, 31, tzinfo=timezone.utc)
