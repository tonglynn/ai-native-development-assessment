from datetime import datetime, timezone
from decimal import Decimal

from ledgerly.models import Subscription
from ledgerly.subscriptions import prorated_refund


def test_half_period():
    sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert prorated_refund(sub, datetime(2026, 1, 16, tzinfo=timezone.utc)) == 15
