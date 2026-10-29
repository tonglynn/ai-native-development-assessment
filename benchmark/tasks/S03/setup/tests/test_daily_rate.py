from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Subscription
from ledgerly.subscriptions import daily_rate


def test_daily_rate():
    sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert daily_rate(sub) == Decimal("1.00")
