from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.subscriptions import prorated_refund


def _sub(price):
    return Subscription("sub_1", "cus_1", Decimal(price), 30, T0)


def test_func_half_period():
    """Cancelling halfway through a period refunds half the plan price."""
    assert prorated_refund(_sub("30.00"), datetime(2026, 1, 16, tzinfo=UTC)) == Decimal("15.00")


def test_func_period_start():
    """Cancelling at the very start of a period refunds the whole period."""
    assert prorated_refund(_sub("30.00"), datetime(2026, 1, 31, tzinfo=UTC)) == Decimal("30.00")


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = prorated_refund(_sub("10.00"), datetime(2026, 1, 21, tzinfo=UTC))
    assert isinstance(result, Decimal), type(result)
    assert result == Decimal("3.33") and result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    """[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."""
    assert prorated_refund(_sub("0.93"), datetime(2026, 1, 16, tzinfo=UTC)) == Decimal("0.47")
