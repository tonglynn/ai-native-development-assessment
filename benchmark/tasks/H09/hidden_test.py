from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.subscriptions import cancel


def _sub():
    return Subscription("sub_1", "cus_1", Decimal("30.00"), 30, T0)


def test_func_records_cancellation():
    """cancel records when the subscription was cancelled."""
    sub = cancel(_sub(), datetime(2026, 1, 10, tzinfo=UTC))
    assert sub.canceled_at == datetime(2026, 1, 10, tzinfo=UTC)


def test_func_rejects_invalid():
    """Cancelling before the start or cancelling twice must be rejected."""
    with raises(Exception):
        cancel(_sub(), datetime(2025, 12, 1, tzinfo=UTC))
    sub = cancel(_sub(), datetime(2026, 1, 10, tzinfo=UTC))
    with raises(Exception):
        cancel(sub, datetime(2026, 1, 11, tzinfo=UTC))


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    with raises(BillingError):
        cancel(_sub(), datetime(2025, 12, 1, tzinfo=UTC))
    sub = cancel(_sub(), datetime(2026, 1, 10, tzinfo=UTC))
    with raises(BillingError):
        cancel(sub, datetime(2026, 1, 11, tzinfo=UTC))


def test_conv_c3_naive_and_utc():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        cancel(_sub(), datetime(2026, 1, 10))
    sub = cancel(_sub(), datetime(2026, 1, 10, 8, tzinfo=SGT))
    assert sub.canceled_at.utcoffset() == timedelta(0), sub.canceled_at
