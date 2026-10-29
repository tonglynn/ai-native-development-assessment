from decimal import Decimal

from ledgerly.commissions import partner_commission


def test_partner_commission():
    assert partner_commission(Decimal("200.00"), 10) == Decimal("20.00")
