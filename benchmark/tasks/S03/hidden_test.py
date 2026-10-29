from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.subscriptions import daily_rate


def _sub(price, days=30):
    return Subscription("sub_1", "cus_1", Decimal(price), days, T0)


def test_func_basic():
    """daily_rate divides the plan price by the period length."""
    assert daily_rate(_sub("30.00")) == Decimal("1.00")


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = daily_rate(_sub("10.00"))
    assert isinstance(result, Decimal) and result == Decimal("0.33") and result.as_tuple().exponent == -2, result


def test_conv_c1_rounding_policy():
    """[team convention] Round money only with ledgerly.money.round_money, which implements the current finance rounding policy (since 2.0.0 this is banker's rounding, see CHANGELOG). Never hard-code a rounding mode."""
    assert daily_rate(_sub("3.75")) == Decimal("0.12")
