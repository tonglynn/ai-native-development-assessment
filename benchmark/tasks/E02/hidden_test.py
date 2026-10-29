from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.invoice import add_line


def test_func_appends_line():
    """add_line must append the new line to the invoice and return it."""
    inv = Invoice("inv_1", "cus_1")
    line = add_line(inv, "Seat", 2, Decimal("5.00"))
    assert inv.lines == [line] and line.unit_price == Decimal("5.00")


def test_func_rejects_invalid_input():
    """Zero/negative quantities, negative prices and non-draft invoices must be rejected."""
    for qty, price, status in [(0, "1.00", "draft"), (-1, "1.00", "draft"), (1, "-0.01", "draft"), (1, "1.00", "issued")]:
        inv = Invoice("inv_1", "cus_1", status=status)
        with raises(Exception):
            add_line(inv, "x", qty, Decimal(price))


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for qty, price, status in [(0, "1.00", "draft"), (1, "-0.01", "draft"), (1, "1.00", "issued")]:
        inv = Invoice("inv_1", "cus_1", status=status)
        with raises(BillingError):
            add_line(inv, "x", qty, Decimal(price))
