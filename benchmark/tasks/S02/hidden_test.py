from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.commissions import partner_commission


def test_func_basic():
    """Commission is rate_percent percent of the sale."""
    assert partner_commission(Decimal("200.00"), 10) == Decimal("20.00")


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = partner_commission(Decimal("33.33"), 12)
    assert isinstance(result, Decimal) and result == Decimal("4.00") and result.as_tuple().exponent == -2, result


def test_conv_c1_rounding_policy():
    """[team convention] Round money only with ledgerly.money.round_money, which implements the current finance rounding policy (since 2.0.0 this is banker's rounding, see CHANGELOG). Never hard-code a rounding mode."""
    assert partner_commission(Decimal("10.25"), 10) == Decimal("1.02")


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    with raises(BillingError):
        partner_commission(Decimal("10.00"), 51)
