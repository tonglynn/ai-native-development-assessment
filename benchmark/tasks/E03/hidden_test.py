from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.renewals import next_renewal


SUB = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, T0)


def test_func_basic():
    """next_renewal returns the first renewal strictly after the given time."""
    assert next_renewal(SUB, datetime(2026, 1, 15, tzinfo=UTC)) == datetime(2026, 1, 31, tzinfo=UTC)
    assert next_renewal(SUB, datetime(2026, 1, 31, tzinfo=UTC)) == datetime(2026, 3, 2, tzinfo=UTC)


def test_func_before_start():
    """Before the subscription starts, the next renewal is the end of the first period."""
    assert next_renewal(SUB, datetime(2025, 12, 1, tzinfo=UTC)) == datetime(2026, 1, 31, tzinfo=UTC)


def test_conv_c3_rejects_naive():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        next_renewal(SUB, datetime(2026, 1, 15))


def test_conv_c3_returns_utc():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    result = next_renewal(SUB, datetime(2026, 1, 15, 8, tzinfo=SGT))
    assert result == datetime(2026, 1, 31, tzinfo=UTC)
    assert result.utcoffset() == timedelta(0), result
