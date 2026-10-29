from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.parsing import parse_amount


def test_func_parses():
    """parse_amount accepts a $ prefix, thousands separators and surrounding whitespace."""
    assert parse_amount("$1,234.50") == Decimal("1234.50")
    assert parse_amount(" 12 ") == Decimal("12")


def test_func_rejects_garbage():
    """Text that is not a non-negative amount with at most two decimals must be rejected."""
    for text in ["abc", "-5", "1.234", ""]:
        with raises(Exception):
            parse_amount(text)


def test_conv_c1_decimal_cents():
    """[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."""
    result = parse_amount("12")
    assert isinstance(result, Decimal), type(result)
    assert result.as_tuple().exponent == -2, result


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for text in ["abc", "-5", "1.234"]:
        with raises(BillingError):
            parse_amount(text)
