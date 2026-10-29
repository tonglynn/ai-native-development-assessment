from ledgerly.parsing import parse_amount


def test_parse_amount():
    assert parse_amount("$1,234.50") == 1234.5
