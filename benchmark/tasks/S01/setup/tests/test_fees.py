from decimal import Decimal

from ledgerly.fees import processing_fee


def test_processing_fee():
    assert processing_fee(Decimal("100.00")) == Decimal("3.20")
