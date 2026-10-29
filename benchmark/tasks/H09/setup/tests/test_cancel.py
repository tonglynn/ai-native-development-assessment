from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Subscription
from ledgerly.subscriptions import cancel


def test_cancel():
    sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
    cancel(sub, datetime(2026, 1, 10, tzinfo=timezone.utc))
    assert sub.canceled_at is not None
