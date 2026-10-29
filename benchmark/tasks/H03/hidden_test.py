from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.reporting import payments_between


def _p(pid, *args):
    return Payment(pid, "inv", Decimal("1.00"), created_at=datetime(*args, tzinfo=UTC))


PAYMENTS = [_p("c", 2026, 1, 3), _p("a", 2026, 1, 1), _p("d", 2026, 1, 4), _p("b", 2026, 1, 2, 12)]


def test_func_filters_and_sorts():
    """Only payments inside the window are returned, oldest first."""
    got = payments_between(PAYMENTS, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 4, tzinfo=UTC))
    assert [p.id for p in got] == ["a", "b", "c"]


def test_func_other_timezone_window():
    """Window boundaries given in another timezone must be compared as instants."""
    got = payments_between(PAYMENTS, datetime(2026, 1, 2, 8, tzinfo=SGT), datetime(2026, 1, 3, 9, tzinfo=SGT))
    assert [p.id for p in got] == ["b", "c"]


def test_conv_c3_rejects_naive():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        payments_between(PAYMENTS, datetime(2026, 1, 1), datetime(2026, 1, 4, tzinfo=UTC))
    with raises(BillingError):
        payments_between(PAYMENTS, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 4))
