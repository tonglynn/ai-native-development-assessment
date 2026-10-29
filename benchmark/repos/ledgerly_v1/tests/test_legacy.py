from datetime import date, datetime

import pytest

from ledgerly.importers import parse_csv
from ledgerly.pricing import apply_coupon, list_price
from ledgerly.promotions import bulk_discount_percent, campaign_percent
from ledgerly.renewals import reminder_due
from ledgerly.reporting import day_bounds


def test_pricing():
    assert list_price("team") == 49.0
    assert apply_coupon(49.0, "WELCOME10") == 44.1
    with pytest.raises(ValueError):
        apply_coupon(49.0, "NOPE")


def test_promotions():
    assert campaign_percent("black-friday", now=datetime(2025, 11, 28)) == 30
    assert bulk_discount_percent(12) == 5


def test_importers():
    assert parse_csv("invoice_id,amount\ninv_1,12.50\n") == [{"invoice_id": "inv_1", "amount": 12.5}]


def test_reporting_and_renewals():
    start, end = day_bounds(date(2026, 1, 1))
    assert (end - start).days == 1
    assert reminder_due(datetime(2026, 1, 10), now=datetime(2026, 1, 8))
