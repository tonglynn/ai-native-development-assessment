from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.invoice import average_unit_price


def _inv(*lines):
    return Invoice("inv_1", "cus_1", lines=[LineItem("x", q, Decimal(p)) for q, p in lines])


def test_func_weighted_average():
    """average_unit_price must weight each unit price by its line quantity."""
    assert average_unit_price(_inv((2, "10.00"), (1, "4.00"))) == Decimal("8.00")


def test_func_empty_invoice():
    """An invoice without lines has an average unit price of zero."""
    assert average_unit_price(_inv()) == 0


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = average_unit_price(_inv((3, "1.00"), (1, "2.00")))
    assert isinstance(result, Decimal), type(result)
    assert result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    """[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."""
    assert average_unit_price(_inv((1, "0.02"), (1, "0.03"))) == Decimal("0.03")
