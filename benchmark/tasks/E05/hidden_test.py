from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.tax import add_tax


def test_func_basic():
    """add_tax returns the amount plus the given percentage of tax."""
    assert add_tax(Decimal("100.00"), 8) == Decimal("108.00")
    assert add_tax(Decimal("50.00"), 0) == Decimal("50.00")


def test_func_rejects_bad_rate():
    """Tax rates outside 0..100 must be rejected."""
    for rate in (-1, 101):
        with raises(Exception):
            add_tax(Decimal("10.00"), rate)


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = add_tax(Decimal("19.99"), Decimal("7.25"))
    assert isinstance(result, Decimal), type(result)
    assert result == Decimal("21.44") and result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    """[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."""
    assert add_tax(Decimal("0.10"), 25) == Decimal("0.13")


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for rate in (-1, 101):
        with raises(BillingError):
            add_tax(Decimal("10.00"), rate)
