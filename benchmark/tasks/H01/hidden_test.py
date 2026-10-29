from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.promotions import apply_discount


def test_func_basic():
    """apply_discount reduces the amount by the given percentage."""
    assert apply_discount(Decimal("200.00"), 15) == Decimal("170.00")
    assert apply_discount(Decimal("12.34"), 0) == Decimal("12.34")


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = apply_discount(Decimal("19.99"), 10)
    assert isinstance(result, Decimal), type(result)
    assert result == Decimal("17.99") and result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    """[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."""
    assert apply_discount(Decimal("0.93"), 50) == Decimal("0.47")
