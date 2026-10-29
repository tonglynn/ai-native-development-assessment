from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
from ledgerly.adjustments import write_off


def _issued(status="issued"):
    return Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 3, Decimal("19.99")), LineItem("Setup", 1, Decimal("50.00"))], status=status)


def test_func_writes_off():
    """write_off voids the invoice and returns its total."""
    inv = _issued()
    result = write_off(inv, T0, "insolvent")
    assert inv.status == "void"
    assert result == {"invoice_id": "inv_1", "amount": Decimal("109.97"), "reason": "insolvent"}


def test_func_rejects_non_issued():
    """Only issued invoices can be written off."""
    for status in ("draft", "void"):
        with raises(Exception):
            write_off(_issued(status), T0, "x")


def test_conv_c2_billing_error():
    """[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses."""
    for status in ("draft", "void"):
        with raises(BillingError):
            write_off(_issued(status), T0, "x")


def test_conv_c3_rejects_naive():
    """[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."""
    with raises(BillingError):
        write_off(_issued(), datetime(2026, 2, 1), "x")


def test_conv_c4_audit_entry():
    """[team convention] Every operation that moves money or changes a payment/credit must write an audit entry with ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...). Finance reconciles the ledger from these entries."""
    audit.clear()
    write_off(_issued(), T0, "insolvent")
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("109.97"), audit.events()


def test_conv_c5_idempotent():
    """[team convention] Every operation that moves money or changes a payment/credit must accept an optional keyword-only `idempotency_key=None` (callers without a key keep working). If an audit entry with the same key already exists (ledgerly.audit.events()), return without applying the operation again, and include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204."""
    audit.clear()
    inv = _issued()
    first = write_off(inv, T0, "insolvent", idempotency_key="wo-1")
    again = write_off(inv, T0, "insolvent", idempotency_key="wo-1")  # retried: must not fail on the now-void invoice
    assert again == first, again
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "wo-1", entries
