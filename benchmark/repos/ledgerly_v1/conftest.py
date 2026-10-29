import pytest

from ledgerly import audit


@pytest.fixture(autouse=True)
def _clean_audit():
    audit.clear()
    yield
    audit.clear()
