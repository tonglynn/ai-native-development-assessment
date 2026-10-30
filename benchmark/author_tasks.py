"""Authoring script that generates benchmark/tasks/<ID>/ (kept for transparency).

Usage: python benchmark/author_tasks.py <project root>    # rewrites benchmark/tasks

Layout per task:
  task.json            metadata + issue text shown to the agent
  setup/               files added to the workspace (public tests)
  stub/ naive/ reference/  code overlays; "<path>.append" is appended to the base file
  hidden_test.py       hidden tests; docstrings double as simulated review comments
"""

import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(sys.argv[1])
TASKS = ROOT / "benchmark" / "tasks"


def d(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n")


# Held-out tasks that closely mirror one experience task (same module and shape) are "near" transfer (audit M4).
NEAR_TRANSFER = {"H06": "E06", "H07": "E04", "H11": "E04"}


def task(id, group, repo, title, issue, conventions, *, setup, stub, naive, reference, hidden, naive_kind="naive"):
    base = TASKS / id
    meta = {
        "id": id,
        "group": group,
        "repo": repo,
        "title": title,
        "issue": " ".join(d(issue).split()),
        "conventions": conventions,
        "naive_kind": naive_kind,
    }
    if group == "heldout":
        meta["transfer"] = "near" if id in NEAR_TRANSFER else "far"
        if id in NEAR_TRANSFER:
            meta["mirrors"] = NEAR_TRANSFER[id]
    base.mkdir(parents=True, exist_ok=True)
    (base / "task.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    for variant, files in [("setup", setup), ("stub", stub), ("naive", naive), ("reference", reference)]:
        for rel, content in files.items():
            p = base / variant / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(d(content))
    (base / "hidden_test.py").write_text(d(hidden))


# Simulated review comments, reused verbatim across tasks so the "reviewer" is consistent.
C1_TYPE = "[team convention] Money in ledgerly is Decimal end-to-end and always has exactly two decimal places. Never convert amounts to float."
C1_ROUND = "[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals."
C2 = 'Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. BillingError("invalid_quantity"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses.'
C2 = "[team convention] " + C2
C3 = "[team convention] Datetimes in ledgerly must be timezone-aware UTC. Pass every incoming datetime through ledgerly.clock.ensure_utc(), which rejects naive datetimes with BillingError and normalises to UTC."
C4 = ('[team convention] Every operation that moves money or changes a payment, credit or invoice balance must write an audit entry with '
      'ledgerly.audit.record("<past_tense_event>", <entity>_id=..., amount=...), where <entity> is the payment or invoice the money moves against '
      '(payment_id=... or invoice_id=...). Finance reconciles the ledger from these entries.')
C5 = ("[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only "
      "`idempotency_key=None` (callers without a key keep working). Check the key first, before validating state: if an audit entry with the "
      "same key already exists (ledgerly.audit.events()), return the original result (for functions that return a record, the same record) "
      "without applying the operation again. Include `idempotency_key` in the audit entry you write. Introduced after the double-refund incident INC-204.")
C6 = ('[team convention] Support-initiated refunds and credits above 500.00 need a second approver (finance policy FIN-2026-03): '
      'accept an optional keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below 500.00 need '
      'no approval; above it, raise BillingError("approval_required") when `approved_by` is missing.')
C6_V2 = ('[team convention] Support-initiated refunds and credits above the approval threshold need a second approver: accept an optional '
         'keyword-only `approved_by=None` (callers that do not need approval keep working). Amounts at or below the threshold need no approval; '
         'above it, raise BillingError("approval_required") when `approved_by` is missing. The threshold is set by finance policy: '
         '500.00 before 2.0.0, 1000.00 since 2.0.0 (see CHANGELOG).')
C1_V2 = "[team convention] Round money only with ledgerly.money.round_money, which implements the current finance rounding policy (since 2.0.0 this is banker's rounding, see CHANGELOG). Never hard-code a rounding mode."
K1 = "[simkit convention] simkit is float-only: return plain Python floats and accept float inputs. Decimal and datetime objects do not belong in simulation code."
K2 = "[simkit convention] Invalid arguments raise the built-in ValueError; simkit has no custom exception classes."

HDR_LEDGERLY = """\
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from hidden_support import close, raises
from ledgerly import audit
from ledgerly.errors import BillingError
from ledgerly.models import Invoice, LineItem, Payment, Subscription

UTC = timezone.utc
SGT = timezone(timedelta(hours=8))
T0 = datetime(2026, 1, 1, tzinfo=UTC)
"""


def hdr(extra=""):
    return HDR_LEDGERLY + extra


def doc(*parts):
    return '"""' + " ".join(parts) + '"""'


# ---------------------------------------------------------------- E: experience tasks (ledgerly v1)

task(
    "E01", "experience", "ledgerly_v1", "Average unit price on invoices",
    """
    Finance wants to show the average unit price on invoice summaries. Add
    `average_unit_price(invoice)` to `ledgerly/invoice.py`: the quantity-weighted
    average of the invoice's line unit prices (sum of quantity x unit price,
    divided by the total quantity). An invoice without lines has an average of zero.
    """,
    ["C1"],
    setup={"tests/test_average_unit_price.py": """
        from decimal import Decimal

        from ledgerly.invoice import average_unit_price
        from ledgerly.models import Invoice, LineItem


        def test_weighted_average():
            inv = Invoice("inv_1", "cus_1", lines=[LineItem("a", 2, Decimal("10.00")), LineItem("b", 1, Decimal("4.00"))])
            assert average_unit_price(inv) == 8
        """},
    stub={"ledgerly/invoice.py.append": '''


        def average_unit_price(invoice: Invoice):
            """Quantity-weighted average unit price of the invoice's lines."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/invoice.py.append": """


        def average_unit_price(invoice):
            total_qty = sum(line.quantity for line in invoice.lines)
            if total_qty == 0:
                return 0
            total = sum(line.unit_price * line.quantity for line in invoice.lines)
            return round(total / total_qty, 2)
        """},
    reference={"ledgerly/invoice.py.append": '''


        def average_unit_price(invoice: Invoice) -> Decimal:
            """Quantity-weighted average unit price of the invoice's lines."""
            total_qty = sum(line.quantity for line in invoice.lines)
            if total_qty == 0:
                return ZERO
            total = sum((to_money(line.unit_price) * line.quantity for line in invoice.lines), ZERO)
            return round_money(total / total_qty)
        '''},
    hidden=hdr("from ledgerly.invoice import average_unit_price\n") + f'''

def _inv(*lines):
    return Invoice("inv_1", "cus_1", lines=[LineItem("x", q, Decimal(p)) for q, p in lines])


def test_func_weighted_average():
    {doc("average_unit_price must weight each unit price by its line quantity.")}
    assert average_unit_price(_inv((2, "10.00"), (1, "4.00"))) == Decimal("8.00")


def test_func_empty_invoice():
    {doc("An invoice without lines has an average unit price of zero.")}
    assert average_unit_price(_inv()) == 0


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = average_unit_price(_inv((3, "1.00"), (1, "2.00")))
    assert isinstance(result, Decimal), type(result)
    assert result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    {doc(C1_ROUND)}
    assert average_unit_price(_inv((1, "0.02"), (1, "0.03"))) == Decimal("0.03")
''',
)

task(
    "E02", "experience", "ledgerly_v1", "Add line items to draft invoices",
    """
    Add `add_line(invoice, description, quantity, unit_price)` to
    `ledgerly/invoice.py`. It appends a new `LineItem` to the invoice and returns
    it. Lines can only be added while the invoice is a draft. The quantity must be
    a positive integer and the unit price must not be negative; reject invalid input.
    """,
    ["C2"],
    setup={"tests/test_add_line.py": """
        from decimal import Decimal

        from ledgerly.invoice import add_line
        from ledgerly.models import Invoice


        def test_add_line():
            inv = Invoice("inv_1", "cus_1")
            line = add_line(inv, "Seat", 2, Decimal("5.00"))
            assert inv.lines == [line]
            assert line.quantity == 2
        """},
    stub={"ledgerly/invoice.py.append": '''


        def add_line(invoice: Invoice, description: str, quantity: int, unit_price) -> LineItem:
            """Append a line item to a draft invoice and return it."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/invoice.py.append": """


        def add_line(invoice, description, quantity, unit_price):
            if invoice.status != "draft":
                raise ValueError("lines can only be added to draft invoices")
            if not isinstance(quantity, int) or quantity <= 0:
                raise ValueError("quantity must be a positive integer")
            if unit_price < 0:
                raise ValueError("unit price must not be negative")
            line = LineItem(description, quantity, unit_price)
            invoice.lines.append(line)
            return line
        """},
    reference={"ledgerly/invoice.py.append": '''


        def add_line(invoice: Invoice, description: str, quantity: int, unit_price) -> LineItem:
            """Append a line item to a draft invoice and return it."""
            if invoice.status != "draft":
                raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
                raise BillingError("invalid_quantity", repr(quantity))
            price = round_money(unit_price)
            if price < ZERO:
                raise BillingError("negative_price", str(price))
            line = LineItem(description, quantity, price)
            invoice.lines.append(line)
            return line
        '''},
    hidden=hdr("from ledgerly.invoice import add_line\n") + f'''

def test_func_appends_line():
    {doc("add_line must append the new line to the invoice and return it.")}
    inv = Invoice("inv_1", "cus_1")
    line = add_line(inv, "Seat", 2, Decimal("5.00"))
    assert inv.lines == [line] and line.unit_price == Decimal("5.00")


def test_func_rejects_invalid_input():
    {doc("Zero/negative quantities, negative prices and non-draft invoices must be rejected.")}
    for qty, price, status in [(0, "1.00", "draft"), (-1, "1.00", "draft"), (1, "-0.01", "draft"), (1, "1.00", "issued")]:
        inv = Invoice("inv_1", "cus_1", status=status)
        with raises(Exception):
            add_line(inv, "x", qty, Decimal(price))


def test_conv_c2_billing_error():
    {doc(C2)}
    for qty, price, status in [(0, "1.00", "draft"), (1, "-0.01", "draft"), (1, "1.00", "issued")]:
        inv = Invoice("inv_1", "cus_1", status=status)
        with raises(BillingError):
            add_line(inv, "x", qty, Decimal(price))
''',
)

task(
    "E03", "experience", "ledgerly_v1", "Next subscription renewal",
    """
    Add `next_renewal(sub, after)` to `ledgerly/renewals.py`: return the
    first renewal time strictly after `after`. Renewals happen every
    `period_days` days counted from `started_at` (the start itself is not a renewal).
    """,
    ["C3"],
    setup={"tests/test_next_renewal.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Subscription
        from ledgerly.renewals import next_renewal


        def test_next_renewal():
            sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
            assert next_renewal(sub, datetime(2026, 1, 15, tzinfo=timezone.utc)) == datetime(2026, 1, 31, tzinfo=timezone.utc)
        """},
    stub={"ledgerly/renewals.py.append": '''


        def next_renewal(sub, after):
            """First renewal strictly after ``after``."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/renewals.py.append": """


        def next_renewal(sub, after):
            length = timedelta(days=sub.period_days)
            if after < sub.started_at:
                return sub.started_at + length
            n = (after - sub.started_at) // length + 1
            return sub.started_at + n * length
        """},
    reference={"ledgerly/renewals.py.append": '''


        from .clock import ensure_utc


        def next_renewal(sub, after: datetime) -> datetime:
            """First renewal strictly after ``after``."""
            after = ensure_utc(after)
            start = ensure_utc(sub.started_at)
            length = timedelta(days=sub.period_days)
            if after < start:
                return start + length
            n = (after - start) // length + 1
            return start + n * length
        '''},
    hidden=hdr("from ledgerly.renewals import next_renewal\n") + f'''

SUB = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, T0)


def test_func_basic():
    {doc("next_renewal returns the first renewal strictly after the given time.")}
    assert next_renewal(SUB, datetime(2026, 1, 15, tzinfo=UTC)) == datetime(2026, 1, 31, tzinfo=UTC)
    assert next_renewal(SUB, datetime(2026, 1, 31, tzinfo=UTC)) == datetime(2026, 3, 2, tzinfo=UTC)


def test_func_before_start():
    {doc("Before the subscription starts, the next renewal is the end of the first period.")}
    assert next_renewal(SUB, datetime(2025, 12, 1, tzinfo=UTC)) == datetime(2026, 1, 31, tzinfo=UTC)


def test_conv_c3_rejects_naive():
    {doc(C3)}
    with raises(BillingError):
        next_renewal(SUB, datetime(2026, 1, 15))


def test_conv_c3_returns_utc():
    {doc(C3)}
    result = next_renewal(SUB, datetime(2026, 1, 15, 8, tzinfo=SGT))
    assert result == datetime(2026, 1, 31, tzinfo=UTC)
    assert result.utcoffset() == timedelta(0), result
''',
)

task(
    "E04", "experience", "ledgerly_v1", "Partial refunds",
    """
    Add `refund(payment, amount, at)` to `ledgerly/adjustments.py`; the support
    team uses it to refund customers. Only captured payments can be refunded. Partial refunds are allowed, but the
    total refunded must never exceed the captured amount. Keep the running total
    in `payment.refunded_amount` and set `payment.status` to `"refunded"` once the
    full amount has been refunded. Return the payment.
    """,
    ["C2", "C4", "C5", "C6"],
    setup={"tests/test_refunds.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Payment
        from ledgerly.adjustments import refund

        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


        def test_partial_refund():
            p = Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)
            refund(p, Decimal("40.00"), T0)
            assert p.refunded_amount == Decimal("40.00")
        """},
    stub={"ledgerly/adjustments.py.append": '''
        def refund(payment, amount, at):
            """Refund part or all of a captured payment."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/adjustments.py.append": """
        from decimal import Decimal


        def refund(payment, amount, at):
            if payment.status != "captured":
                raise ValueError("only captured payments can be refunded")
            amount = Decimal(amount)
            if amount <= 0 or payment.refunded_amount + amount > payment.amount:
                raise ValueError("invalid refund amount")
            payment.refunded_amount += amount
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            return payment
        """},
    reference={"ledgerly/adjustments.py.append": '''
        from datetime import datetime
        from decimal import Decimal

        from . import audit
        from .clock import ensure_utc
        from .errors import BillingError
        from .models import Payment
        from .money import ZERO, round_money


        APPROVAL_THRESHOLD = Decimal("500.00")


        def refund(payment: Payment, amount, at: datetime, *, idempotency_key=None, approved_by=None) -> Payment:
            """Refund part or all of a captured payment."""
            at = ensure_utc(at)
            if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):
                return payment
            if payment.status != "captured":
                raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
            amount = round_money(amount)
            if amount <= ZERO:
                raise BillingError("non_positive_amount", str(amount))
            if payment.refunded_amount + amount > payment.amount:
                raise BillingError("refund_exceeds_capture", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            payment.refunded_amount = round_money(payment.refunded_amount + amount)
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            audit.record("payment_refunded", payment_id=payment.id, amount=amount, at=at,
                         idempotency_key=idempotency_key, approved_by=approved_by)
            return payment
        '''},
    hidden=hdr("from ledgerly.adjustments import refund\n") + f'''

def _captured():
    return Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)


def test_func_partial_then_full():
    {doc("Partial refunds accumulate; the payment becomes 'refunded' once fully refunded.")}
    p = _captured()
    refund(p, Decimal("40.00"), T0)
    assert p.refunded_amount == Decimal("40.00") and p.status == "captured"
    refund(p, Decimal("60.00"), T0)
    assert p.refunded_amount == Decimal("100.00") and p.status == "refunded"


def test_func_rejects_invalid():
    {doc("Over-refunds and refunds of non-captured payments must be rejected.")}
    with raises(Exception):
        refund(_captured(), Decimal("100.01"), T0)
    with raises(Exception):
        refund(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), T0)


def test_conv_c2_billing_error():
    {doc(C2)}
    with raises(BillingError):
        refund(_captured(), Decimal("100.01"), T0)
    with raises(BillingError):
        refund(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), Decimal("1.00"), T0)


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    refund(_captured(), Decimal("40.00"), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("40.00"), entries[0]


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    p = _captured()
    refund(p, Decimal("40.00"), T0, idempotency_key="rf-1")
    refund(p, Decimal("40.00"), T0, idempotency_key="rf-1")  # a retried request
    assert p.refunded_amount == Decimal("40.00"), p.refunded_amount
    assert sum(e.get("idempotency_key") == "rf-1" for e in audit.events()) == 1, audit.events()


def _big(pid):
    return Payment(pid, "inv_1", Decimal("2000.00"), status="captured", created_at=T0, captured_at=T0)


def test_conv_c6_blocks_unapproved():
    {doc(C6)}
    big = _big("pay_9")
    with raises(BillingError):
        refund(big, Decimal("600.00"), T0)
    assert big.refunded_amount == Decimal("0.00"), big.refunded_amount


def test_conv_c6_allows_at_threshold_or_approved():
    {doc(C6)}
    at_threshold = _big("pay_10")
    refund(at_threshold, Decimal("500.00"), T0)  # at the threshold: no approval needed
    assert at_threshold.refunded_amount == Decimal("500.00"), at_threshold.refunded_amount
    approved = _big("pay_11")
    refund(approved, Decimal("600.00"), T0, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("600.00"), approved.refunded_amount
''',
)

task(
    "E05", "experience", "ledgerly_v1", "Add sales tax",
    """
    Add `add_tax(amount, rate_percent)` to `ledgerly/pricing.py`. It
    returns the gross amount: `amount` plus `rate_percent` percent tax, rounded to
    the cent. Tax rates must be between 0 and 100 inclusive.
    """,
    ["C1", "C2"],
    setup={"tests/test_tax.py": """
        from decimal import Decimal

        from ledgerly.pricing import add_tax


        def test_add_tax():
            assert add_tax(Decimal("100.00"), 8) == 108
        """},
    stub={"ledgerly/pricing.py.append": '''
        def add_tax(amount, rate_percent):
            """Gross amount including ``rate_percent`` percent tax."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/pricing.py.append": """
        def add_tax(amount, rate_percent):
            rate = float(rate_percent)
            if rate < 0 or rate > 100:
                raise ValueError("tax rate must be between 0 and 100")
            return round(float(amount) * (1 + rate / 100), 2)
        """},
    reference={"ledgerly/pricing.py.append": '''
        from decimal import Decimal

        from .errors import BillingError
        from .money import round_money, to_money


        def add_tax(amount, rate_percent) -> Decimal:
            """Gross amount including ``rate_percent`` percent tax."""
            rate = to_money(rate_percent)
            if rate < 0 or rate > 100:
                raise BillingError("invalid_tax_rate", str(rate))
            amount = to_money(amount)
            return round_money(amount + amount * rate / 100)
        '''},
    hidden=hdr("from ledgerly.pricing import add_tax\n") + f'''

def test_func_basic():
    {doc("add_tax returns the amount plus the given percentage of tax.")}
    assert add_tax(Decimal("100.00"), 8) == Decimal("108.00")
    assert add_tax(Decimal("50.00"), 0) == Decimal("50.00")


def test_func_rejects_bad_rate():
    {doc("Tax rates outside 0..100 must be rejected.")}
    for rate in (-1, 101):
        with raises(Exception):
            add_tax(Decimal("10.00"), rate)


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = add_tax(Decimal("19.99"), Decimal("7.25"))
    assert isinstance(result, Decimal), type(result)
    assert result == Decimal("21.44") and result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    {doc(C1_ROUND)}
    assert add_tax(Decimal("0.10"), 25) == Decimal("0.13")


def test_conv_c2_billing_error():
    {doc(C2)}
    for rate in (-1, 101):
        with raises(BillingError):
            add_tax(Decimal("10.00"), rate)
''',
)

task(
    "E06", "experience", "ledgerly_v1", "Capture authorized payments",
    """
    Add `capture(payment, at)` to `ledgerly/payments.py`. Capturing moves an
    authorized payment to `"captured"` and stores the capture time in
    `payment.captured_at`. Only authorized payments can be captured.
    """,
    ["C2", "C3", "C4", "C5"],
    setup={"tests/test_capture.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Payment
        from ledgerly.payments import capture

        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


        def test_capture():
            p = Payment("pay_1", "inv_1", Decimal("20.00"), created_at=T0)
            capture(p, T0)
            assert p.status == "captured"
        """},
    stub={"ledgerly/payments.py.append": '''


        def capture(payment: Payment, at: datetime) -> Payment:
            """Capture an authorized payment."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/payments.py.append": """


        def capture(payment, at):
            if payment.status != "authorized":
                raise ValueError(f"cannot capture a {payment.status} payment")
            payment.status = "captured"
            payment.captured_at = at
            return payment
        """},
    reference={"ledgerly/payments.py.append": '''


        def capture(payment: Payment, at: datetime, *, idempotency_key=None) -> Payment:
            """Capture an authorized payment."""
            at = ensure_utc(at)
            if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):
                return payment
            if payment.status != "authorized":
                raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
            payment.status = "captured"
            payment.captured_at = at
            audit.record("payment_captured", payment_id=payment.id, amount=payment.amount, idempotency_key=idempotency_key)
            return payment
        '''},
    hidden=hdr("from ledgerly.payments import capture\n") + f'''

def _authorized():
    return Payment("pay_1", "inv_1", Decimal("20.00"), created_at=T0)


def test_func_captures():
    {doc("capture marks the payment captured and stores when it happened.")}
    p = capture(_authorized(), datetime(2026, 1, 2, tzinfo=UTC))
    assert p.status == "captured" and p.captured_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_func_rejects_non_authorized():
    {doc("Only authorized payments can be captured.")}
    p = _authorized()
    p.status = "voided"
    with raises(Exception):
        capture(p, T0)


def test_conv_c2_billing_error():
    {doc(C2)}
    p = _authorized()
    p.status = "captured"
    with raises(BillingError):
        capture(p, T0)


def test_conv_c3_naive_and_utc():
    {doc(C3)}
    with raises(BillingError):
        capture(_authorized(), datetime(2026, 1, 2))
    p = capture(_authorized(), datetime(2026, 1, 2, 8, tzinfo=SGT))
    assert p.captured_at.utcoffset() == timedelta(0), p.captured_at


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    capture(_authorized(), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("payment_id") == "pay_1" and entries[0].get("amount") == Decimal("20.00"), entries[0]


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    p = _authorized()
    capture(p, T0, idempotency_key="cap-1")
    capture(p, T0, idempotency_key="cap-1")  # a retried request must not fail or capture twice
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "cap-1", entries
''',
)

# ---------------------------------------------------------------- H: held-out tasks (ledgerly v1)

task(
    "H01", "heldout", "ledgerly_v1", "Percentage discounts",
    """
    Add `apply_discount(amount, percent)` to `ledgerly/promotions.py`:
    return `amount` reduced by `percent` percent (15 means 15% off). The
    discounted price is what we charge, so round it to the cent.
    """,
    ["C1"],
    setup={"tests/test_discounts.py": """
        from decimal import Decimal

        from ledgerly.promotions import apply_discount


        def test_apply_discount():
            assert apply_discount(Decimal("200.00"), 15) == 170
        """},
    stub={"ledgerly/promotions.py.append": '''
        def apply_discount(amount, percent):
            """``amount`` reduced by ``percent`` percent."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/promotions.py.append": """
        def apply_discount(amount, percent):
            return round(amount * (100 - percent) / 100, 2)
        """},
    reference={"ledgerly/promotions.py.append": '''
        from decimal import Decimal

        from .money import round_money, to_money


        def apply_discount(amount, percent) -> Decimal:
            """``amount`` reduced by ``percent`` percent."""
            return round_money(to_money(amount) * (100 - to_money(percent)) / 100)
        '''},
    hidden=hdr("from ledgerly.promotions import apply_discount\n") + f'''

def test_func_basic():
    {doc("apply_discount reduces the amount by the given percentage.")}
    assert apply_discount(Decimal("200.00"), 15) == Decimal("170.00")
    assert apply_discount(Decimal("12.34"), 0) == Decimal("12.34")


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = apply_discount(Decimal("19.99"), 10)
    assert isinstance(result, Decimal), type(result)
    assert result == Decimal("17.99") and result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    {doc(C1_ROUND)}
    assert apply_discount(Decimal("0.93"), 50) == Decimal("0.47")
''',
)

task(
    "H02", "heldout", "ledgerly_v1", "Parse customer-entered amounts",
    """
    Customers paste amounts like `"$1,234.50"` or `" 12 "` into the billing
    portal. Add `parse_amount(text)` to `ledgerly/importers.py` that
    turns such text into an amount: ignore surrounding whitespace, an optional
    leading `$` and thousands separators. Reject text that is not a valid
    non-negative amount with at most two decimal places.
    """,
    ["C1", "C2"],
    setup={"tests/test_parsing.py": """
        from ledgerly.importers import parse_amount


        def test_parse_amount():
            assert parse_amount("$1,234.50") == 1234.5
        """},
    stub={"ledgerly/importers.py.append": '''
        def parse_amount(text: str):
            """Parse a customer-entered amount such as "$1,234.50"."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/importers.py.append": """
        import re
        from decimal import Decimal


        def parse_amount(text):
            cleaned = text.strip().removeprefix("$").replace(",", "")
            if not re.fullmatch(r"\\d+(\\.\\d{1,2})?", cleaned):
                raise ValueError(f"invalid amount: {text!r}")
            return Decimal(cleaned)
        """},
    reference={"ledgerly/importers.py.append": '''
        import re
        from decimal import Decimal

        from .errors import BillingError
        from .money import round_money

        _AMOUNT = re.compile(r"\\d+(\\.\\d{1,2})?")


        def parse_amount(text: str) -> Decimal:
            """Parse a customer-entered amount such as "$1,234.50"."""
            if not isinstance(text, str):
                raise BillingError("invalid_amount", repr(text))
            cleaned = text.strip().removeprefix("$").replace(",", "")
            if not _AMOUNT.fullmatch(cleaned):
                raise BillingError("invalid_amount", repr(text))
            return round_money(cleaned)
        '''},
    hidden=hdr("from ledgerly.importers import parse_amount\n") + f'''

def test_func_parses():
    {doc("parse_amount accepts a $ prefix, thousands separators and surrounding whitespace.")}
    assert parse_amount("$1,234.50") == Decimal("1234.50")
    assert parse_amount(" 12 ") == Decimal("12")


def test_func_rejects_garbage():
    {doc("Text that is not a non-negative amount with at most two decimals must be rejected.")}
    for text in ["abc", "-5", "1.234", ""]:
        with raises(Exception):
            parse_amount(text)


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = parse_amount("12")
    assert isinstance(result, Decimal), type(result)
    assert result.as_tuple().exponent == -2, result


def test_conv_c2_billing_error():
    {doc(C2)}
    for text in ["abc", "-5", "1.234"]:
        with raises(BillingError):
            parse_amount(text)
''',
)

task(
    "H03", "heldout", "ledgerly_v1", "Payments in a reporting window",
    """
    Add `payments_between(payments, start, end)` to
    `ledgerly/reporting.py`. It returns the payments whose `created_at` falls in the
    half-open window `[start, end)`, sorted by `created_at`. The finance dashboard
    calls it with the boundaries of the report period.
    """,
    ["C3"],
    setup={"tests/test_reports.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Payment
        from ledgerly.reporting import payments_between

        UTC = timezone.utc


        def test_payments_between():
            a = Payment("a", "inv", Decimal("1.00"), created_at=datetime(2026, 1, 2, tzinfo=UTC))
            b = Payment("b", "inv", Decimal("1.00"), created_at=datetime(2026, 1, 5, tzinfo=UTC))
            assert payments_between([b, a], datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)) == [a]
        """},
    stub={"ledgerly/reporting.py.append": '''
        def payments_between(payments, start, end):
            """Payments created in [start, end), oldest first."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/reporting.py.append": """
        def payments_between(payments, start, end):
            selected = [p for p in payments if start <= p.created_at < end]
            return sorted(selected, key=lambda p: p.created_at)
        """},
    reference={"ledgerly/reporting.py.append": '''
        from datetime import datetime

        from .clock import ensure_utc
        from .errors import BillingError
        from .models import Payment


        def payments_between(payments: list[Payment], start: datetime, end: datetime) -> list[Payment]:
            """Payments created in [start, end), oldest first."""
            start, end = ensure_utc(start), ensure_utc(end)
            if end < start:
                raise BillingError("invalid_window", f"{start.isoformat()} > {end.isoformat()}")
            selected = [p for p in payments if start <= ensure_utc(p.created_at) < end]
            return sorted(selected, key=lambda p: p.created_at)
        '''},
    hidden=hdr("from ledgerly.reporting import payments_between\n") + f'''

def _p(pid, *args):
    return Payment(pid, "inv", Decimal("1.00"), created_at=datetime(*args, tzinfo=UTC))


PAYMENTS = [_p("c", 2026, 1, 3), _p("a", 2026, 1, 1), _p("d", 2026, 1, 4), _p("b", 2026, 1, 2, 12)]


def test_func_filters_and_sorts():
    {doc("Only payments inside the window are returned, oldest first.")}
    got = payments_between(PAYMENTS, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 4, tzinfo=UTC))
    assert [p.id for p in got] == ["a", "b", "c"]


def test_func_other_timezone_window():
    {doc("Window boundaries given in another timezone must be compared as instants.")}
    got = payments_between(PAYMENTS, datetime(2026, 1, 2, 8, tzinfo=SGT), datetime(2026, 1, 3, 9, tzinfo=SGT))
    assert [p.id for p in got] == ["b", "c"]


def test_conv_c3_rejects_naive():
    {doc(C3)}
    with raises(BillingError):
        payments_between(PAYMENTS, datetime(2026, 1, 1), datetime(2026, 1, 4, tzinfo=UTC))
    with raises(BillingError):
        payments_between(PAYMENTS, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 4))
''',
)

task(
    "H04", "heldout", "ledgerly_v1", "Credit notes",
    """
    Add `issue_credit_note(invoice, amount, reason)` to
    `ledgerly/adjustments.py`; the support team issues credit notes to give money
    back to a customer against an issued invoice. Return a dict with the keys `invoice_id`, `amount` and
    `reason`. The amount must be positive and must not exceed the invoice total,
    and only issued invoices can be credited.
    """,
    ["C2", "C4", "C5", "C6"],
    setup={"tests/test_credits.py": """
        from decimal import Decimal

        from ledgerly.adjustments import issue_credit_note
        from ledgerly.models import Invoice, LineItem


        def test_issue_credit_note():
            inv = Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 1, Decimal("50.00"))], status="issued")
            note = issue_credit_note(inv, Decimal("10.00"), "goodwill")
            assert note["amount"] == Decimal("10.00")
        """},
    stub={"ledgerly/adjustments.py.append": '''
        def issue_credit_note(invoice, amount, reason):
            """Credit part of an issued invoice back to the customer."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/adjustments.py.append": """
        from .invoice import invoice_total


        def issue_credit_note(invoice, amount, reason):
            if invoice.status != "issued":
                raise ValueError("only issued invoices can be credited")
            if amount <= 0 or amount > invoice_total(invoice):
                raise ValueError("invalid credit amount")
            return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
        """},
    reference={"ledgerly/adjustments.py.append": '''
        from decimal import Decimal

        from . import audit
        from .errors import BillingError
        from .invoice import invoice_total
        from .models import Invoice
        from .money import ZERO, round_money


        APPROVAL_THRESHOLD = Decimal("500.00")


        def issue_credit_note(invoice: Invoice, amount, reason: str, *, idempotency_key=None, approved_by=None) -> dict:
            """Credit part of an issued invoice back to the customer."""
            if idempotency_key is not None:
                for e in audit.events():
                    if e.get("idempotency_key") == idempotency_key:
                        return {"invoice_id": e["invoice_id"], "amount": e["amount"], "reason": e["reason"]}
            if invoice.status != "issued":
                raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}")
            amount = round_money(amount)
            if amount <= ZERO:
                raise BillingError("non_positive_amount", str(amount))
            if amount > invoice_total(invoice):
                raise BillingError("credit_exceeds_total", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            audit.record("credit_note_issued", invoice_id=invoice.id, amount=amount, reason=reason,
                         idempotency_key=idempotency_key, approved_by=approved_by)
            return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
        '''},
    hidden=hdr("from ledgerly.adjustments import issue_credit_note\n") + f'''

def _issued(status="issued"):
    return Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 3, Decimal("19.99")), LineItem("Setup", 1, Decimal("50.00"))], status=status)


def test_func_returns_note():
    {doc("issue_credit_note returns the invoice id, amount and reason.")}
    note = issue_credit_note(_issued(), Decimal("10.00"), "goodwill")
    assert note == {{"invoice_id": "inv_1", "amount": Decimal("10.00"), "reason": "goodwill"}}


def test_func_rejects_invalid():
    {doc("Zero, excessive and non-issued credits must be rejected.")}
    for inv, amount in [(_issued(), "0"), (_issued(), "109.98"), (_issued("draft"), "1.00")]:
        with raises(Exception):
            issue_credit_note(inv, Decimal(amount), "x")


def test_conv_c2_billing_error():
    {doc(C2)}
    for inv, amount in [(_issued(), "0"), (_issued(), "109.98"), (_issued("draft"), "1.00")]:
        with raises(BillingError):
            issue_credit_note(inv, Decimal(amount), "x")


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    issue_credit_note(_issued(), Decimal("10.00"), "goodwill")
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("invoice_id") == "inv_1" and entries[0].get("amount") == Decimal("10.00"), entries[0]


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    first = issue_credit_note(_issued(), Decimal("10.00"), "goodwill", idempotency_key="cn-1")
    again = issue_credit_note(_issued(), Decimal("10.00"), "goodwill", idempotency_key="cn-1")
    assert again == first, again
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "cn-1", entries


def _annual(iid):
    return Invoice(iid, "cus_1", lines=[LineItem("Annual plan", 1, Decimal("1500.00"))], status="issued")


def test_conv_c6_blocks_unapproved():
    {doc(C6)}
    with raises(BillingError):
        issue_credit_note(_annual("inv_2"), Decimal("500.01"), "x")


def test_conv_c6_allows_at_threshold_or_approved():
    {doc(C6)}
    assert issue_credit_note(_annual("inv_3"), Decimal("500.00"), "x")["amount"] == Decimal("500.00")  # at the threshold
    note = issue_credit_note(_annual("inv_4"), Decimal("900.00"), "x", approved_by="usr_finance_lead")
    assert note["amount"] == Decimal("900.00"), note
''',
)

task(
    "H05", "heldout", "ledgerly_v1", "Prorated refunds on cancellation",
    """
    When a customer cancels mid-period we refund the unused part of the current
    period. Add `prorated_refund(sub, cancel_at)` to `ledgerly/subscriptions.py`:
    the plan price multiplied by the unused fraction of the billing period that
    contains `cancel_at` (unused time divided by the period length), rounded to
    the cent.
    """,
    ["C1"],
    setup={"tests/test_prorated_refund.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Subscription
        from ledgerly.subscriptions import prorated_refund


        def test_half_period():
            sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
            assert prorated_refund(sub, datetime(2026, 1, 16, tzinfo=timezone.utc)) == 15
        """},
    stub={"ledgerly/subscriptions.py.append": '''


        def prorated_refund(sub: Subscription, cancel_at: datetime):
            """Refund for the unused part of the current period."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/subscriptions.py.append": """


        def prorated_refund(sub, cancel_at):
            start, end = current_period(sub, cancel_at)
            unused = (end - cancel_at) / (end - start)
            return round(float(sub.plan_price) * unused, 2)
        """},
    reference={"ledgerly/subscriptions.py.append": '''


        def prorated_refund(sub: Subscription, cancel_at: datetime):
            """Refund for the unused part of the current period."""
            from decimal import Decimal

            from .money import round_money, to_money

            cancel_at = ensure_utc(cancel_at)
            start, end = current_period(sub, cancel_at)
            micro = timedelta(microseconds=1)
            unused = Decimal((end - cancel_at) // micro) / Decimal((end - start) // micro)
            return round_money(to_money(sub.plan_price) * unused)
        '''},
    hidden=hdr("from ledgerly.subscriptions import prorated_refund\n") + f'''

def _sub(price):
    return Subscription("sub_1", "cus_1", Decimal(price), 30, T0)


def test_func_half_period():
    {doc("Cancelling halfway through a period refunds half the plan price.")}
    assert prorated_refund(_sub("30.00"), datetime(2026, 1, 16, tzinfo=UTC)) == Decimal("15.00")


def test_func_period_start():
    {doc("Cancelling at the very start of a period refunds the whole period.")}
    assert prorated_refund(_sub("30.00"), datetime(2026, 1, 31, tzinfo=UTC)) == Decimal("30.00")


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = prorated_refund(_sub("10.00"), datetime(2026, 1, 21, tzinfo=UTC))
    assert isinstance(result, Decimal), type(result)
    assert result == Decimal("3.33") and result.as_tuple().exponent == -2, result


def test_conv_c1_half_up():
    {doc(C1_ROUND)}
    assert prorated_refund(_sub("0.93"), datetime(2026, 1, 16, tzinfo=UTC)) == Decimal("0.47")
''',
)

task(
    "H06", "heldout", "ledgerly_v1", "Void authorizations",
    """
    Add `void(payment, at)` to `ledgerly/payments.py`. Voiding cancels an
    authorization before it is captured: it sets the payment's status to
    `"voided"`. Captured, refunded and already voided payments cannot be voided.
    """,
    ["C2", "C4", "C5"],
    setup={"tests/test_void.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Payment
        from ledgerly.payments import void

        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


        def test_void():
            p = Payment("pay_1", "inv_1", Decimal("20.00"), created_at=T0)
            void(p, T0)
            assert p.status == "voided"
        """},
    stub={"ledgerly/payments.py.append": '''


        def void(payment: Payment, at: datetime) -> Payment:
            """Void an authorization that has not been captured."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/payments.py.append": """


        def void(payment, at):
            if payment.status != "authorized":
                raise ValueError(f"cannot void a {payment.status} payment")
            payment.status = "voided"
            return payment
        """},
    reference={"ledgerly/payments.py.append": '''


        def void(payment: Payment, at: datetime, *, idempotency_key=None) -> Payment:
            """Void an authorization that has not been captured."""
            at = ensure_utc(at)
            if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):
                return payment
            if payment.status != "authorized":
                raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
            payment.status = "voided"
            audit.record("payment_voided", payment_id=payment.id, amount=payment.amount, at=at, idempotency_key=idempotency_key)
            return payment
        '''},
    hidden=hdr("from ledgerly.payments import void\n") + f'''

def _payment(status="authorized"):
    return Payment("pay_1", "inv_1", Decimal("20.00"), status=status, created_at=T0)


def test_func_voids():
    {doc("void marks an authorized payment as voided.")}
    assert void(_payment(), T0).status == "voided"


def test_func_rejects_non_authorized():
    {doc("Captured, refunded and voided payments cannot be voided.")}
    for status in ("captured", "refunded", "voided"):
        with raises(Exception):
            void(_payment(status), T0)


def test_conv_c2_billing_error():
    {doc(C2)}
    for status in ("captured", "voided"):
        with raises(BillingError):
            void(_payment(status), T0)


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    void(_payment(), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("20.00"), entries[0]


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    p = _payment()
    void(p, T0, idempotency_key="vd-1")
    void(p, T0, idempotency_key="vd-1")  # a retried request must not fail or void twice
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "vd-1", entries
''',
)

task(
    "H07", "heldout", "ledgerly_v1", "Shipping-fee refunds",
    """
    Customers sometimes get their shipping fee back after a late delivery; the support
    team handles these. Add `refund_shipping(payment, amount, at)` to
    `ledgerly/adjustments.py`: it refunds
    `amount` of a captured payment, adding it to `payment.refunded_amount` and
    setting the status to `"refunded"` once everything has been refunded. Return the
    payment. The amount must be positive and the total refunded may not exceed the
    captured amount.
    """,
    ["C2", "C4", "C5", "C6"],
    setup={"tests/test_refund_shipping.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.adjustments import refund_shipping
        from ledgerly.models import Payment

        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


        def test_refund_shipping():
            p = Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)
            refund_shipping(p, Decimal("10.00"), T0)
            assert p.refunded_amount == Decimal("10.00")
        """},
    stub={"ledgerly/adjustments.py.append": '''
        def refund_shipping(payment, amount, at):
            """Refund (part of) the shipping fee of a captured payment."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/adjustments.py.append": """
        from decimal import Decimal


        def refund_shipping(payment, amount, at):
            if payment.status != "captured":
                raise ValueError("only captured payments can be refunded")
            amount = Decimal(amount)
            if amount <= 0 or payment.refunded_amount + amount > payment.amount:
                raise ValueError("invalid refund amount")
            payment.refunded_amount += amount
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            return payment
        """},
    reference={"ledgerly/adjustments.py.append": '''
        from decimal import Decimal

        from . import audit
        from .clock import ensure_utc
        from .errors import BillingError
        from .money import ZERO, round_money

        APPROVAL_THRESHOLD = Decimal("500.00")


        def refund_shipping(payment, amount, at, *, idempotency_key=None, approved_by=None):
            """Refund (part of) the shipping fee of a captured payment."""
            at = ensure_utc(at)
            if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):
                return payment
            if payment.status != "captured":
                raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
            amount = round_money(amount)
            if amount <= ZERO:
                raise BillingError("non_positive_amount", str(amount))
            if payment.refunded_amount + amount > payment.amount:
                raise BillingError("refund_exceeds_capture", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            payment.refunded_amount = round_money(payment.refunded_amount + amount)
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            audit.record("shipping_refunded", payment_id=payment.id, amount=amount, at=at,
                         idempotency_key=idempotency_key, approved_by=approved_by)
            return payment
        '''},
    hidden=hdr("from ledgerly.adjustments import refund_shipping\n") + f'''

def _captured(amount="100.00"):
    return Payment("pay_1", "inv_1", Decimal(amount), status="captured", created_at=T0, captured_at=T0)


def test_func_partial_then_full():
    {doc("Shipping refunds accumulate; the payment becomes 'refunded' once fully refunded.")}
    p = _captured()
    refund_shipping(p, Decimal("10.00"), T0)
    assert p.refunded_amount == Decimal("10.00") and p.status == "captured"
    refund_shipping(p, Decimal("90.00"), T0)
    assert p.status == "refunded"


def test_func_rejects_invalid():
    {doc("Zero amounts, over-refunds and refunds of non-captured payments must be rejected.")}
    for p, amount in [(_captured(), "0"), (_captured(), "100.01"), (Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), "1.00")]:
        with raises(Exception):
            refund_shipping(p, Decimal(amount), T0)


def test_conv_c2_billing_error():
    {doc(C2)}
    for p, amount in [(_captured(), "0"), (_captured(), "100.01")]:
        with raises(BillingError):
            refund_shipping(p, Decimal(amount), T0)


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    refund_shipping(_captured(), Decimal("10.00"), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("10.00"), audit.events()


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    p = _captured()
    refund_shipping(p, Decimal("10.00"), T0, idempotency_key="sh-1")
    refund_shipping(p, Decimal("10.00"), T0, idempotency_key="sh-1")
    assert p.refunded_amount == Decimal("10.00"), p.refunded_amount
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "sh-1", entries


def test_conv_c6_blocks_unapproved():
    {doc(C6)}
    big = _captured("1500.00")
    with raises(BillingError):
        refund_shipping(big, Decimal("750.00"), T0)
    assert big.refunded_amount == Decimal("0.00"), big.refunded_amount


def test_conv_c6_allows_below_threshold_or_approved():
    {doc(C6)}
    small = _captured("1500.00")
    refund_shipping(small, Decimal("480.00"), T0)  # below the threshold: no approval needed
    assert small.refunded_amount == Decimal("480.00"), small.refunded_amount
    approved = _captured("1500.00")
    refund_shipping(approved, Decimal("750.00"), T0, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("750.00"), approved.refunded_amount
''',
)

task(
    "H08", "heldout", "ledgerly_v1", "Partial captures",
    """
    Some orders ship incomplete, so we capture only part of the authorization. Add
    `capture_partial(payment, amount, at)` to `ledgerly/payments.py`: it captures
    `amount` of an authorized payment, sets `payment.amount` to the captured amount,
    stores the capture time in `payment.captured_at` and sets the status to
    `"captured"`. The amount must be positive and at most the authorized amount;
    amounts with more than two decimals are rounded to the cent.
    """,
    ["C1", "C2", "C3", "C4", "C5"],
    setup={"tests/test_capture_partial.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Payment
        from ledgerly.payments import capture_partial

        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


        def test_capture_partial():
            p = Payment("pay_1", "inv_1", Decimal("100.00"), created_at=T0)
            capture_partial(p, Decimal("60.00"), T0)
            assert p.amount == 60 and p.status == "captured"
        """},
    stub={"ledgerly/payments.py.append": '''
        def capture_partial(payment: Payment, amount, at: datetime) -> Payment:
            """Capture part of an authorized payment."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/payments.py.append": """
        def capture_partial(payment, amount, at):
            if payment.status != "authorized":
                raise ValueError(f"cannot capture a {payment.status} payment")
            if amount <= 0 or amount > payment.amount:
                raise ValueError("invalid capture amount")
            payment.amount = amount
            payment.status = "captured"
            payment.captured_at = at
            return payment
        """},
    reference={"ledgerly/payments.py.append": '''
        def capture_partial(payment: Payment, amount, at: datetime, *, idempotency_key=None) -> Payment:
            """Capture part of an authorized payment."""
            at = ensure_utc(at)
            if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):
                return payment
            if payment.status != "authorized":
                raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
            amount = round_money(amount)
            if amount <= ZERO or amount > payment.amount:
                raise BillingError("invalid_capture_amount", str(amount))
            payment.amount = amount
            payment.status = "captured"
            payment.captured_at = at
            audit.record("payment_captured", payment_id=payment.id, amount=amount, at=at, idempotency_key=idempotency_key)
            return payment
        '''},
    hidden=hdr("from ledgerly.payments import capture_partial\n") + f'''

def _authorized():
    return Payment("pay_1", "inv_1", Decimal("100.00"), created_at=T0)


def test_func_captures_part():
    {doc("capture_partial captures the given part of the authorization.")}
    p = capture_partial(_authorized(), Decimal("60.00"), datetime(2026, 1, 2, tzinfo=UTC))
    assert p.amount == Decimal("60.00") and p.status == "captured" and p.captured_at == datetime(2026, 1, 2, tzinfo=UTC)


def test_func_rejects_invalid():
    {doc("Zero, larger-than-authorized and non-authorized captures must be rejected.")}
    voided = _authorized()
    voided.status = "voided"
    for p, amount in [(_authorized(), "0"), (_authorized(), "100.01"), (voided, "1.00")]:
        with raises(Exception):
            capture_partial(p, Decimal(amount), T0)


def test_conv_c1_rounded_cents():
    {doc(C1_ROUND)}
    p = capture_partial(_authorized(), Decimal("33.335"), T0)
    assert p.amount == Decimal("33.34") and p.amount.as_tuple().exponent == -2, p.amount


def test_conv_c2_billing_error():
    {doc(C2)}
    for amount in ("0", "100.01"):
        with raises(BillingError):
            capture_partial(_authorized(), Decimal(amount), T0)


def test_conv_c3_naive_and_utc():
    {doc(C3)}
    with raises(BillingError):
        capture_partial(_authorized(), Decimal("10.00"), datetime(2026, 1, 2))
    p = capture_partial(_authorized(), Decimal("10.00"), datetime(2026, 1, 2, 8, tzinfo=SGT))
    assert p.captured_at.utcoffset() == timedelta(0), p.captured_at


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    capture_partial(_authorized(), Decimal("60.00"), T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("60.00"), audit.events()


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    p = _authorized()
    capture_partial(p, Decimal("60.00"), T0, idempotency_key="cp-1")
    capture_partial(p, Decimal("60.00"), T0, idempotency_key="cp-1")
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "cp-1", entries
''',
)

task(
    "H09", "heldout", "ledgerly_v1", "Cancel subscriptions",
    """
    Add `cancel(sub, at)` to `ledgerly/subscriptions.py`: record the cancellation
    time in `sub.canceled_at` and return the subscription. A subscription cannot be
    cancelled before it starts, and it cannot be cancelled twice.
    """,
    ["C2", "C3"],
    setup={"tests/test_cancel.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Subscription
        from ledgerly.subscriptions import cancel


        def test_cancel():
            sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
            cancel(sub, datetime(2026, 1, 10, tzinfo=timezone.utc))
            assert sub.canceled_at is not None
        """},
    stub={"ledgerly/subscriptions.py.append": '''
        def cancel(sub: Subscription, at: datetime) -> Subscription:
            """Cancel a subscription."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/subscriptions.py.append": """
        def cancel(sub, at):
            if sub.canceled_at is not None:
                raise ValueError("subscription already cancelled")
            if at < sub.started_at:
                raise ValueError("cannot cancel before the subscription starts")
            sub.canceled_at = at
            return sub
        """},
    reference={"ledgerly/subscriptions.py.append": '''
        def cancel(sub: Subscription, at: datetime) -> Subscription:
            """Cancel a subscription."""
            at = ensure_utc(at)
            if sub.canceled_at is not None:
                raise BillingError("already_canceled", sub.id)
            if at < ensure_utc(sub.started_at):
                raise BillingError("before_start", at.isoformat())
            sub.canceled_at = at
            return sub
        '''},
    hidden=hdr("from ledgerly.subscriptions import cancel\n") + f'''

def _sub():
    return Subscription("sub_1", "cus_1", Decimal("30.00"), 30, T0)


def test_func_records_cancellation():
    {doc("cancel records when the subscription was cancelled.")}
    sub = cancel(_sub(), datetime(2026, 1, 10, tzinfo=UTC))
    assert sub.canceled_at == datetime(2026, 1, 10, tzinfo=UTC)


def test_func_rejects_invalid():
    {doc("Cancelling before the start or cancelling twice must be rejected.")}
    with raises(Exception):
        cancel(_sub(), datetime(2025, 12, 1, tzinfo=UTC))
    sub = cancel(_sub(), datetime(2026, 1, 10, tzinfo=UTC))
    with raises(Exception):
        cancel(sub, datetime(2026, 1, 11, tzinfo=UTC))


def test_conv_c2_billing_error():
    {doc(C2)}
    with raises(BillingError):
        cancel(_sub(), datetime(2025, 12, 1, tzinfo=UTC))
    sub = cancel(_sub(), datetime(2026, 1, 10, tzinfo=UTC))
    with raises(BillingError):
        cancel(sub, datetime(2026, 1, 11, tzinfo=UTC))


def test_conv_c3_naive_and_utc():
    {doc(C3)}
    with raises(BillingError):
        cancel(_sub(), datetime(2026, 1, 10))
    sub = cancel(_sub(), datetime(2026, 1, 10, 8, tzinfo=SGT))
    assert sub.canceled_at.utcoffset() == timedelta(0), sub.canceled_at
''',
)

task(
    "H10", "heldout", "ledgerly_v1", "Write off unpaid invoices",
    """
    Finance writes off invoices that will never be paid. Add
    `write_off(invoice, at, reason)` to `ledgerly/adjustments.py`: it marks an issued
    invoice as `"void"` and returns a dict with the keys `invoice_id`, `amount` (the
    invoice total) and `reason`. Only issued invoices can be written off.
    """,
    ["C2", "C3", "C4", "C5"],
    setup={"tests/test_write_off.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.adjustments import write_off
        from ledgerly.models import Invoice, LineItem


        def test_write_off():
            inv = Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 1, Decimal("50.00"))], status="issued")
            result = write_off(inv, datetime(2026, 2, 1, tzinfo=timezone.utc), "customer insolvent")
            assert inv.status == "void" and result["amount"] == Decimal("50.00")
        """},
    stub={"ledgerly/adjustments.py.append": '''
        def write_off(invoice, at, reason):
            """Write off an issued invoice that will never be paid."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/adjustments.py.append": """
        def write_off(invoice, at, reason):
            if invoice.status != "issued":
                raise ValueError("only issued invoices can be written off")
            invoice.status = "void"
            return {"invoice_id": invoice.id, "amount": invoice_total(invoice), "reason": reason}
        """},
    reference={"ledgerly/adjustments.py.append": '''
        from . import audit
        from .clock import ensure_utc
        from .errors import BillingError


        def write_off(invoice, at, reason, *, idempotency_key=None):
            """Write off an issued invoice that will never be paid."""
            at = ensure_utc(at)
            if idempotency_key is not None:
                for e in audit.events():
                    if e.get("idempotency_key") == idempotency_key:
                        return {"invoice_id": e["invoice_id"], "amount": e["amount"], "reason": e["reason"]}
            if invoice.status != "issued":
                raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}")
            amount = invoice_total(invoice)
            invoice.status = "void"
            audit.record("invoice_written_off", invoice_id=invoice.id, amount=amount, reason=reason, at=at,
                         idempotency_key=idempotency_key)
            return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
        '''},
    hidden=hdr("from ledgerly.adjustments import write_off\n") + f'''

def _issued(status="issued"):
    return Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 3, Decimal("19.99")), LineItem("Setup", 1, Decimal("50.00"))], status=status)


def test_func_writes_off():
    {doc("write_off voids the invoice and returns its total.")}
    inv = _issued()
    result = write_off(inv, T0, "insolvent")
    assert inv.status == "void"
    assert result == {{"invoice_id": "inv_1", "amount": Decimal("109.97"), "reason": "insolvent"}}


def test_func_rejects_non_issued():
    {doc("Only issued invoices can be written off.")}
    for status in ("draft", "void"):
        with raises(Exception):
            write_off(_issued(status), T0, "x")


def test_conv_c2_billing_error():
    {doc(C2)}
    for status in ("draft", "void"):
        with raises(BillingError):
            write_off(_issued(status), T0, "x")


def test_conv_c3_rejects_naive():
    {doc(C3)}
    with raises(BillingError):
        write_off(_issued(), datetime(2026, 2, 1), "x")


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    write_off(_issued(), T0, "insolvent")
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("109.97"), audit.events()


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    inv = _issued()
    first = write_off(inv, T0, "insolvent", idempotency_key="wo-1")
    again = write_off(inv, T0, "insolvent", idempotency_key="wo-1")  # retried: must not fail on the now-void invoice
    assert again == first, again
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("idempotency_key") == "wo-1", entries
''',
)

task(
    "H11", "heldout", "ledgerly_v1", "Support refund requests",
    """
    The support console gets a single entry point for refunds. Add
    `process_refund_request(payment, amount, requested_by, at)` in a new module
    `ledgerly/support.py`. `amount` is the text the support agent typed (for
    example "49.99"; amounts with more than two decimals are rounded to the cent),
    `requested_by` is the agent's user id and `at` is when the request was made.
    Only captured payments can be refunded, the amount must be positive, and the
    total refunded must never exceed the captured amount. Apply the refund to the
    payment (keep the running total in `payment.refunded_amount`; set
    `payment.status` to `"refunded"` once the full amount has been refunded) and
    return the payment.
    """,
    ["C1", "C2", "C3", "C4", "C5", "C6"],
    setup={"tests/test_support.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Payment
        from ledgerly.support import process_refund_request

        T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


        def test_refund_from_console():
            p = Payment("pay_1", "inv_1", Decimal("100.00"), status="captured", created_at=T0, captured_at=T0)
            process_refund_request(p, "40.00", "usr_support_1", T0)
            assert p.refunded_amount == Decimal("40.00")
        """},
    stub={"ledgerly/support.py": '''
        """Entry points used by the support console."""


        def process_refund_request(payment, amount, requested_by, at):
            """Refund part or all of a captured payment on behalf of a support agent."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/support.py": '''
        """Entry points used by the support console."""

        from decimal import Decimal


        def process_refund_request(payment, amount, requested_by, at):
            """Refund part or all of a captured payment on behalf of a support agent."""
            if payment.status != "captured":
                raise ValueError("only captured payments can be refunded")
            amount = Decimal(amount).quantize(Decimal("0.01"))
            if amount <= 0 or payment.refunded_amount + amount > payment.amount:
                raise ValueError("invalid refund amount")
            payment.refunded_amount += amount
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            return payment
        '''},
    reference={"ledgerly/support.py": '''
        """Entry points used by the support console."""

        from datetime import datetime
        from decimal import Decimal

        from . import audit
        from .clock import ensure_utc
        from .errors import BillingError
        from .models import Payment
        from .money import ZERO, round_money

        APPROVAL_THRESHOLD = Decimal("500.00")


        def process_refund_request(payment: Payment, amount, requested_by: str, at: datetime, *,
                                   idempotency_key=None, approved_by=None) -> Payment:
            """Refund part or all of a captured payment on behalf of a support agent."""
            at = ensure_utc(at)
            if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):
                return payment
            if payment.status != "captured":
                raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
            amount = round_money(amount)
            if amount <= ZERO:
                raise BillingError("non_positive_amount", str(amount))
            if payment.refunded_amount + amount > payment.amount:
                raise BillingError("refund_exceeds_capture", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            payment.refunded_amount = round_money(payment.refunded_amount + amount)
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            audit.record("payment_refunded", payment_id=payment.id, amount=amount, at=at, requested_by=requested_by,
                         idempotency_key=idempotency_key, approved_by=approved_by)
            return payment
        '''},
    hidden=hdr("from ledgerly.support import process_refund_request\n") + f'''

AGENT = "usr_support_1"


def _captured(amount="100.00", pid="pay_1"):
    return Payment(pid, "inv_1", Decimal(amount), status="captured", created_at=T0, captured_at=T0)


def test_func_partial_then_full():
    {doc("Refunds typed in the console accumulate; the payment becomes 'refunded' once fully refunded.")}
    p = _captured()
    process_refund_request(p, "40.00", AGENT, T0)
    assert p.refunded_amount == Decimal("40.00") and p.status == "captured"
    process_refund_request(p, "60", AGENT, T0)
    assert p.refunded_amount == Decimal("100.00") and p.status == "refunded"


def test_func_rejects_invalid():
    {doc("Over-refunds, non-positive amounts and refunds of non-captured payments must be rejected.")}
    with raises(Exception):
        process_refund_request(_captured(), "100.01", AGENT, T0)
    with raises(Exception):
        process_refund_request(_captured(), "0", AGENT, T0)
    with raises(Exception):
        process_refund_request(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), "1.00", AGENT, T0)


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    p = _captured()
    process_refund_request(p, "12.5", AGENT, T0)
    assert isinstance(p.refunded_amount, Decimal) and p.refunded_amount == Decimal("12.50"), p.refunded_amount
    assert p.refunded_amount.as_tuple().exponent == -2, p.refunded_amount


def test_conv_c1_half_up():
    {doc(C1_ROUND)}
    p = _captured()
    process_refund_request(p, "10.005", AGENT, T0)
    assert p.refunded_amount == Decimal("10.01"), p.refunded_amount


def test_conv_c2_billing_error():
    {doc(C2)}
    for amount in ("100.01", "-5", "ten"):
        with raises(BillingError):
            process_refund_request(_captured(), amount, AGENT, T0)
    with raises(BillingError):
        process_refund_request(Payment("pay_2", "inv_1", Decimal("10.00"), created_at=T0), "1.00", AGENT, T0)


def test_conv_c3_rejects_naive():
    {doc(C3)}
    with raises(BillingError):
        process_refund_request(_captured(), "10.00", AGENT, datetime(2026, 1, 1))


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    process_refund_request(_captured(), "40.00", AGENT, T0)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1, audit.events()
    assert entries[0].get("amount") == Decimal("40.00"), entries[0]


def test_conv_c5_idempotent():
    {doc(C5)}
    audit.clear()
    p = _captured()
    process_refund_request(p, "40.00", AGENT, T0, idempotency_key="rq-1")
    process_refund_request(p, "40.00", AGENT, T0, idempotency_key="rq-1")  # the console retries after a timeout
    assert p.refunded_amount == Decimal("40.00"), p.refunded_amount
    assert sum(e.get("idempotency_key") == "rq-1" for e in audit.events()) == 1, audit.events()
    process_refund_request(p, "10.00", AGENT, T0)  # callers without a key keep working ...
    process_refund_request(p, "10.00", AGENT, T0)  # ... every time
    assert p.refunded_amount == Decimal("60.00"), p.refunded_amount


def test_conv_c6_blocks_unapproved():
    {doc(C6)}
    big = _captured("1800.00")
    with raises(BillingError):
        process_refund_request(big, "650.00", AGENT, T0)
    assert big.refunded_amount == Decimal("0.00"), big.refunded_amount


def test_conv_c6_allows_below_threshold_or_approved():
    {doc(C6)}
    small = _captured("1800.00", pid="pay_5")
    process_refund_request(small, "450.00", AGENT, T0)  # below the threshold: no approval needed
    assert small.refunded_amount == Decimal("450.00"), small.refunded_amount
    approved = _captured("1800.00", pid="pay_6")
    process_refund_request(approved, "650.00", AGENT, T0, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("650.00"), approved.refunded_amount
''',
)

# ---------------------------------------------------------------- S: after the v2 rounding-policy change

S_STALE_ROUND = "quantize(Decimal(\"0.01\"), rounding=ROUND_HALF_UP)"

task(
    "S01", "stale", "ledgerly_v2", "Card processing fee",
    """
    Add `processing_fee(amount)` in a new module `ledgerly/fees.py`: the card
    processing fee is 2.9% of the amount plus a fixed 0.30, rounded to the cent.
    Amounts must be positive.
    """,
    ["C1", "C2"],
    naive_kind="stale_v1_habit",
    setup={"tests/test_fees.py": """
        from decimal import Decimal

        from ledgerly.fees import processing_fee


        def test_processing_fee():
            assert processing_fee(Decimal("100.00")) == Decimal("3.20")
        """},
    stub={"ledgerly/fees.py": '''
        def processing_fee(amount):
            """Card processing fee: 2.9% + 0.30."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/fees.py": f"""
        from decimal import ROUND_HALF_UP, Decimal

        from .errors import BillingError
        from .money import to_money


        def processing_fee(amount):
            amount = to_money(amount)
            if amount <= 0:
                raise BillingError("non_positive_amount", str(amount))
            return (amount * Decimal("0.029") + Decimal("0.30")).{S_STALE_ROUND}
        """},
    reference={"ledgerly/fees.py": '''
        from decimal import Decimal

        from .errors import BillingError
        from .money import round_money, to_money


        def processing_fee(amount) -> Decimal:
            """Card processing fee: 2.9% + 0.30."""
            amount = to_money(amount)
            if amount <= 0:
                raise BillingError("non_positive_amount", str(amount))
            return round_money(amount * Decimal("0.029") + Decimal("0.30"))
        '''},
    hidden=hdr("from ledgerly.fees import processing_fee\n") + f'''

def test_func_basic():
    {doc("The fee is 2.9% of the amount plus 0.30.")}
    assert processing_fee(Decimal("100.00")) == Decimal("3.20")


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = processing_fee(Decimal("19.99"))
    assert isinstance(result, Decimal) and result == Decimal("0.88") and result.as_tuple().exponent == -2, result


def test_conv_c1_rounding_policy():
    {doc(C1_V2)}
    assert processing_fee(Decimal("5.00")) == Decimal("0.44")


def test_conv_c2_billing_error():
    {doc(C2)}
    with raises(BillingError):
        processing_fee(Decimal("0"))
''',
)

task(
    "S02", "stale", "ledgerly_v2", "Reseller commission",
    """
    Add `partner_commission(amount, rate_percent)` in a new module
    `ledgerly/commissions.py`: resellers earn `rate_percent` percent of each sale,
    rounded to the cent. Rates must be between 0 and 50 inclusive.
    """,
    ["C1", "C2"],
    naive_kind="stale_v1_habit",
    setup={"tests/test_commissions.py": """
        from decimal import Decimal

        from ledgerly.commissions import partner_commission


        def test_partner_commission():
            assert partner_commission(Decimal("200.00"), 10) == Decimal("20.00")
        """},
    stub={"ledgerly/commissions.py": '''
        def partner_commission(amount, rate_percent):
            """Reseller commission on a sale."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/commissions.py": f"""
        from decimal import ROUND_HALF_UP, Decimal

        from .errors import BillingError
        from .money import to_money


        def partner_commission(amount, rate_percent):
            rate = to_money(rate_percent)
            if rate < 0 or rate > 50:
                raise BillingError("invalid_rate", str(rate))
            return (to_money(amount) * rate / 100).{S_STALE_ROUND}
        """},
    reference={"ledgerly/commissions.py": '''
        from decimal import Decimal

        from .errors import BillingError
        from .money import round_money, to_money


        def partner_commission(amount, rate_percent) -> Decimal:
            """Reseller commission on a sale."""
            rate = to_money(rate_percent)
            if rate < 0 or rate > 50:
                raise BillingError("invalid_rate", str(rate))
            return round_money(to_money(amount) * rate / 100)
        '''},
    hidden=hdr("from ledgerly.commissions import partner_commission\n") + f'''

def test_func_basic():
    {doc("Commission is rate_percent percent of the sale.")}
    assert partner_commission(Decimal("200.00"), 10) == Decimal("20.00")


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = partner_commission(Decimal("33.33"), 12)
    assert isinstance(result, Decimal) and result == Decimal("4.00") and result.as_tuple().exponent == -2, result


def test_conv_c1_rounding_policy():
    {doc(C1_V2)}
    assert partner_commission(Decimal("10.25"), 10) == Decimal("1.02")


def test_conv_c2_billing_error():
    {doc(C2)}
    with raises(BillingError):
        partner_commission(Decimal("10.00"), 51)
''',
)

task(
    "S03", "stale", "ledgerly_v2", "Daily rate on the plan page",
    """
    Add `daily_rate(sub)` to `ledgerly/subscriptions.py`: the subscription's plan
    price divided by its period length in days, rounded to the cent. It is shown
    on the customer's plan page.
    """,
    ["C1"],
    naive_kind="stale_v1_habit",
    setup={"tests/test_daily_rate.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.models import Subscription
        from ledgerly.subscriptions import daily_rate


        def test_daily_rate():
            sub = Subscription("sub_1", "cus_1", Decimal("30.00"), 30, datetime(2026, 1, 1, tzinfo=timezone.utc))
            assert daily_rate(sub) == Decimal("1.00")
        """},
    stub={"ledgerly/subscriptions.py.append": '''


        def daily_rate(sub: Subscription):
            """Plan price per day."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/subscriptions.py.append": f"""


        def daily_rate(sub):
            from decimal import ROUND_HALF_UP, Decimal

            return (Decimal(sub.plan_price) / sub.period_days).{S_STALE_ROUND}
        """},
    reference={"ledgerly/subscriptions.py.append": '''


        def daily_rate(sub: Subscription):
            """Plan price per day."""
            from .money import round_money, to_money

            return round_money(to_money(sub.plan_price) / sub.period_days)
        '''},
    hidden=hdr("from ledgerly.subscriptions import daily_rate\n") + f'''

def _sub(price, days=30):
    return Subscription("sub_1", "cus_1", Decimal(price), days, T0)


def test_func_basic():
    {doc("daily_rate divides the plan price by the period length.")}
    assert daily_rate(_sub("30.00")) == Decimal("1.00")


def test_conv_c1_decimal_cents():
    {doc(C1_TYPE)}
    result = daily_rate(_sub("10.00"))
    assert isinstance(result, Decimal) and result == Decimal("0.33") and result.as_tuple().exponent == -2, result


def test_conv_c1_rounding_policy():
    {doc(C1_V2)}
    assert daily_rate(_sub("3.75")) == Decimal("0.12")
''',
)

task(
    "S04", "stale", "ledgerly_v2", "Goodwill credits",
    """
    Support can grant goodwill credits to unhappy customers. Add
    `goodwill_credit(invoice, amount, reason)` to `ledgerly/adjustments.py`: it
    credits `amount` against an issued invoice and returns a dict with the keys
    `invoice_id`, `amount` and `reason`. The amount must be positive and must not
    exceed the invoice total, and only issued invoices can be credited.
    """,
    ["C2", "C4", "C6"],
    naive_kind="stale_v1_habit",
    setup={"tests/test_goodwill.py": """
        from decimal import Decimal

        from ledgerly.adjustments import goodwill_credit
        from ledgerly.models import Invoice, LineItem


        def test_goodwill_credit():
            inv = Invoice("inv_1", "cus_1", lines=[LineItem("Seat", 1, Decimal("50.00"))], status="issued")
            assert goodwill_credit(inv, Decimal("5.00"), "late delivery")["amount"] == Decimal("5.00")
        """},
    stub={"ledgerly/adjustments.py.append": '''
        def goodwill_credit(invoice, amount, reason):
            """Credit part of an issued invoice as a goodwill gesture."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/adjustments.py.append": '''
        from decimal import Decimal

        from . import audit
        from .errors import BillingError
        from .money import ZERO, round_money

        APPROVAL_THRESHOLD = Decimal("500.00")


        def goodwill_credit(invoice, amount, reason, *, approved_by=None):
            if invoice.status != "issued":
                raise BillingError("invalid_state", invoice.status)
            amount = round_money(amount)
            if amount <= ZERO or amount > invoice_total(invoice):
                raise BillingError("invalid_amount", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            audit.record("goodwill_credit_issued", invoice_id=invoice.id, amount=amount, reason=reason, approved_by=approved_by)
            return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
        '''},
    reference={"ledgerly/adjustments.py.append": '''
        from decimal import Decimal

        from . import audit
        from .errors import BillingError
        from .money import ZERO, round_money

        APPROVAL_THRESHOLD = Decimal("1000.00")  # FIN-2026-09, ledgerly 2.0.0


        def goodwill_credit(invoice, amount, reason, *, approved_by=None):
            """Credit part of an issued invoice as a goodwill gesture."""
            if invoice.status != "issued":
                raise BillingError("invalid_state", invoice.status)
            amount = round_money(amount)
            if amount <= ZERO or amount > invoice_total(invoice):
                raise BillingError("invalid_amount", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            audit.record("goodwill_credit_issued", invoice_id=invoice.id, amount=amount, reason=reason, approved_by=approved_by)
            return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
        '''},
    hidden=hdr("from ledgerly.adjustments import goodwill_credit\n") + f'''

def _issued(total="1500.00", status="issued"):
    return Invoice("inv_1", "cus_1", lines=[LineItem("Annual plan", 1, Decimal(total))], status=status)


def test_func_returns_credit():
    {doc("goodwill_credit returns the invoice id, amount and reason.")}
    assert goodwill_credit(_issued(), Decimal("5.00"), "late") == {{"invoice_id": "inv_1", "amount": Decimal("5.00"), "reason": "late"}}


def test_func_rejects_invalid():
    {doc("Non-positive amounts, amounts above the invoice total and credits on non-issued invoices are rejected.")}
    for inv, amount in [(_issued(), "0"), (_issued("50.00"), "50.01"), (_issued(status="draft"), "1.00")]:
        with raises(Exception):
            goodwill_credit(inv, Decimal(amount), "x")


def test_conv_c2_billing_error():
    {doc(C2)}
    for inv, amount in [(_issued(), "0"), (_issued("50.00"), "50.01"), (_issued(status="draft"), "1.00")]:
        with raises(BillingError):
            goodwill_credit(inv, Decimal(amount), "x")


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    goodwill_credit(_issued(), Decimal("5.00"), "late")
    entries = [e for e in audit.events() if e.get("invoice_id") == "inv_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("5.00"), audit.events()


def test_conv_c6_blocks_unapproved():
    {doc(C6_V2)}
    with raises(BillingError):
        goodwill_credit(_issued(), Decimal("1200.00"), "x")


def test_conv_c6_allows_below_threshold_or_approved():
    {doc(C6_V2)}
    # 700.00 is below the 2.0.0 threshold (1000.00): applying the old 500.00 rule wrongly blocks it
    assert goodwill_credit(_issued(), Decimal("700.00"), "x")["amount"] == Decimal("700.00")
    assert goodwill_credit(_issued(), Decimal("1200.00"), "x", approved_by="usr_finance_lead")["amount"] == Decimal("1200.00")
''',
)

task(
    "S05", "stale", "ledgerly_v2", "Service-outage refunds",
    """
    After a service outage the support team refunds part of what affected customers
    paid. Add `outage_refund(payment, amount, at)` to `ledgerly/adjustments.py`: it
    refunds `amount` of a captured payment, adding it to `payment.refunded_amount`
    and setting the status to `"refunded"` once everything has been refunded. Return
    the payment. The amount must be positive, the total refunded may not exceed the
    captured amount, and only captured payments can be refunded.
    """,
    ["C2", "C4", "C6"],
    naive_kind="stale_v1_habit",
    setup={"tests/test_outage_refund.py": """
        from datetime import datetime, timezone
        from decimal import Decimal

        from ledgerly.adjustments import outage_refund
        from ledgerly.models import Payment

        T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


        def test_outage_refund():
            p = Payment("pay_1", "inv_1", Decimal("80.00"), status="captured", created_at=T0, captured_at=T0)
            outage_refund(p, Decimal("8.00"), T0)
            assert p.refunded_amount == Decimal("8.00")
        """},
    stub={"ledgerly/adjustments.py.append": '''
        def outage_refund(payment, amount, at):
            """Refund part of a captured payment after a service outage."""
            raise NotImplementedError
        '''},
    naive={"ledgerly/adjustments.py.append": '''
        from decimal import Decimal

        from . import audit
        from .clock import ensure_utc
        from .errors import BillingError
        from .money import ZERO, round_money

        APPROVAL_THRESHOLD = Decimal("500.00")


        def outage_refund(payment, amount, at, *, approved_by=None):
            at = ensure_utc(at)
            if payment.status != "captured":
                raise BillingError("invalid_state", payment.status)
            amount = round_money(amount)
            if amount <= ZERO or payment.refunded_amount + amount > payment.amount:
                raise BillingError("invalid_amount", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            payment.refunded_amount = round_money(payment.refunded_amount + amount)
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            audit.record("outage_refund_issued", payment_id=payment.id, amount=amount, at=at, approved_by=approved_by)
            return payment
        '''},
    reference={"ledgerly/adjustments.py.append": '''
        from decimal import Decimal

        from . import audit
        from .clock import ensure_utc
        from .errors import BillingError
        from .money import ZERO, round_money

        APPROVAL_THRESHOLD = Decimal("1000.00")  # FIN-2026-09, ledgerly 2.0.0


        def outage_refund(payment, amount, at, *, approved_by=None):
            """Refund part of a captured payment after a service outage."""
            at = ensure_utc(at)
            if payment.status != "captured":
                raise BillingError("invalid_state", payment.status)
            amount = round_money(amount)
            if amount <= ZERO or payment.refunded_amount + amount > payment.amount:
                raise BillingError("invalid_amount", str(amount))
            if amount > APPROVAL_THRESHOLD and not approved_by:
                raise BillingError("approval_required", str(amount))
            payment.refunded_amount = round_money(payment.refunded_amount + amount)
            if payment.refunded_amount == payment.amount:
                payment.status = "refunded"
            audit.record("outage_refund_issued", payment_id=payment.id, amount=amount, at=at, approved_by=approved_by)
            return payment
        '''},
    hidden=hdr("from ledgerly.adjustments import outage_refund\n") + f'''

T1 = datetime(2026, 10, 1, tzinfo=UTC)


def _captured(pid="pay_1", amount="2400.00"):
    return Payment(pid, "inv_1", Decimal(amount), status="captured", created_at=T1, captured_at=T1)


def test_func_partial_then_full():
    {doc("Refunds accumulate; the payment becomes 'refunded' once fully refunded.")}
    p = _captured(amount="80.00")
    outage_refund(p, Decimal("30.00"), T1)
    assert p.refunded_amount == Decimal("30.00") and p.status == "captured"
    outage_refund(p, Decimal("50.00"), T1)
    assert p.refunded_amount == Decimal("80.00") and p.status == "refunded"


def test_func_rejects_invalid():
    {doc("Non-positive amounts, over-refunds and refunds of non-captured payments are rejected.")}
    for p, amount in [(_captured(), "0"), (_captured(amount="80.00"), "80.01"),
                      (Payment("pay_2", "inv_1", Decimal("80.00"), created_at=T1), "1.00")]:
        with raises(Exception):
            outage_refund(p, Decimal(amount), T1)


def test_conv_c2_billing_error():
    {doc(C2)}
    for p, amount in [(_captured(), "0"), (_captured(amount="80.00"), "80.01"),
                      (Payment("pay_2", "inv_1", Decimal("80.00"), created_at=T1), "1.00")]:
        with raises(BillingError):
            outage_refund(p, Decimal(amount), T1)


def test_conv_c4_audit_entry():
    {doc(C4)}
    audit.clear()
    outage_refund(_captured(), Decimal("12.00"), T1)
    entries = [e for e in audit.events() if e.get("payment_id") == "pay_1"]
    assert len(entries) == 1 and entries[0].get("amount") == Decimal("12.00"), audit.events()


def test_conv_c6_blocks_unapproved():
    {doc(C6_V2)}
    p = _captured()
    with raises(BillingError):
        outage_refund(p, Decimal("1250.00"), T1)
    assert p.refunded_amount == Decimal("0.00"), p.refunded_amount


def test_conv_c6_allows_below_threshold_or_approved():
    {doc(C6_V2)}
    # 800.00 is below the 2.0.0 threshold (1000.00): applying the old 500.00 rule wrongly blocks it
    small = _captured("pay_3")
    outage_refund(small, Decimal("800.00"), T1)
    assert small.refunded_amount == Decimal("800.00"), small.refunded_amount
    approved = _captured("pay_4")
    outage_refund(approved, Decimal("1250.00"), T1, approved_by="usr_finance_lead")
    assert approved.refunded_amount == Decimal("1250.00"), approved.refunded_amount
''',
)

# ---------------------------------------------------------------- B: control repo (simkit), opposite conventions

HDR_SIMKIT = "from hidden_support import close, raises\n"

task(
    "B01", "control", "simkit", "Energy cost of a load",
    """
    Add `energy_cost(power_watts, hours, price_per_kwh)` in a new module
    `simkit/energy.py`: the cost of running a load of `power_watts` watts for
    `hours` hours at `price_per_kwh` per kWh, rounded to 2 decimal places for the
    report. Negative inputs are invalid and must be rejected.
    """,
    ["K1", "K2"],
    naive_kind="contaminated_by_ledgerly",
    setup={"tests/test_energy.py": """
        import pytest

        from simkit.energy import energy_cost


        def test_energy_cost():
            assert energy_cost(1500.0, 2.0, 0.25) == pytest.approx(0.75)
        """},
    stub={"simkit/energy.py": '''
        def energy_cost(power_watts: float, hours: float, price_per_kwh: float) -> float:
            """Cost of running a load, rounded to 2 decimals."""
            raise NotImplementedError
        '''},
    naive={"simkit/energy.py": """
        from decimal import ROUND_HALF_UP, Decimal


        class SimulationError(Exception):
            pass


        def energy_cost(power_watts, hours, price_per_kwh):
            if power_watts < 0 or hours < 0 or price_per_kwh < 0:
                raise SimulationError("negative_input")
            cost = Decimal(str(power_watts)) / 1000 * Decimal(str(hours)) * Decimal(str(price_per_kwh))
            return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        """},
    reference={"simkit/energy.py": '''
        from .units import watts_to_kw


        def energy_cost(power_watts: float, hours: float, price_per_kwh: float) -> float:
            """Cost of running a load, rounded to 2 decimals."""
            if power_watts < 0 or hours < 0 or price_per_kwh < 0:
                raise ValueError("inputs must be non-negative")
            return round(watts_to_kw(power_watts) * hours * price_per_kwh, 2)
        '''},
    hidden=HDR_SIMKIT + "from simkit.energy import energy_cost\n" + f'''

def test_func_basic():
    {doc("1.5 kW for 2 h at 0.25 per kWh costs 0.75.")}
    assert close(energy_cost(1500.0, 2.0, 0.25), 0.75)


def test_conv_k1_float():
    {doc(K1)}
    result = energy_cost(1234.5, 1.5, 0.3017)
    assert isinstance(result, float), type(result)
    assert close(result, 0.56), result


def test_conv_k2_value_error():
    {doc(K2)}
    with raises(ValueError):
        energy_cost(-1.0, 1.0, 0.25)
''',
)

task(
    "B02", "control", "simkit", "Simulation sample timestamps",
    """
    Add `sample_times(start, step, count)` in a new module `simkit/timeline.py`:
    return the `count` sample timestamps `start, start + step, start + 2*step, ...`
    that drive a simulation run. `step` must be positive and `count` must not be
    negative.
    """,
    ["K1", "K2"],
    naive_kind="contaminated_by_ledgerly",
    setup={"tests/test_timeline.py": """
        from simkit.timeline import sample_times


        def test_sample_times_count():
            assert len(sample_times(0.0, 0.5, 4)) == 4
        """},
    stub={"simkit/timeline.py": '''
        def sample_times(start: float, step: float, count: int) -> list[float]:
            """Evenly spaced sample timestamps."""
            raise NotImplementedError
        '''},
    naive={"simkit/timeline.py": """
        from datetime import datetime, timedelta, timezone


        def sample_times(start, step, count):
            if step <= 0 or count < 0:
                raise ValueError("step must be positive and count non-negative")
            base = datetime.fromtimestamp(start, tz=timezone.utc)
            return [base + timedelta(seconds=step * i) for i in range(count)]
        """},
    reference={"simkit/timeline.py": '''
        def sample_times(start: float, step: float, count: int) -> list[float]:
            """Evenly spaced sample timestamps."""
            if step <= 0:
                raise ValueError("step must be positive")
            if count < 0:
                raise ValueError("count must be non-negative")
            return [start + i * step for i in range(count)]
        '''},
    hidden=HDR_SIMKIT + "from simkit.timeline import sample_times\n" + f'''

def test_func_count_and_empty():
    {doc("sample_times returns exactly count samples (none for count=0).")}
    assert len(sample_times(0.0, 0.5, 4)) == 4
    assert sample_times(0.0, 0.5, 0) == []


def test_conv_k1_float_seconds():
    {doc(K1, "Simulation time is float seconds from t=0, not datetime.")}
    got = sample_times(12.5, 0.25, 3)
    assert all(isinstance(t, float) for t in got), got
    assert all(close(a, b) for a, b in zip(got, [12.5, 12.75, 13.0])), got


def test_conv_k2_value_error():
    {doc(K2)}
    with raises(ValueError):
        sample_times(0.0, 0.0, 3)
''',
)

task(
    "B03", "control", "simkit", "Compute cost per sample",
    """
    Add `cost_per_sample(total_cost, samples)` in a new module
    `simkit/costmodel.py`: split a simulation run's total compute cost evenly
    across its samples, rounded to 4 decimal places. `samples` must be positive.
    """,
    ["K1", "K2"],
    naive_kind="contaminated_by_ledgerly",
    setup={"tests/test_costmodel.py": """
        import pytest

        from simkit.costmodel import cost_per_sample


        def test_cost_per_sample():
            assert cost_per_sample(10.0, 4) == pytest.approx(2.5)
        """},
    stub={"simkit/costmodel.py": '''
        def cost_per_sample(total_cost: float, samples: int) -> float:
            """Total cost split evenly across samples, 4 decimals."""
            raise NotImplementedError
        '''},
    naive={"simkit/costmodel.py": """
        from decimal import ROUND_HALF_UP, Decimal


        class CostError(Exception):
            pass


        def cost_per_sample(total_cost, samples):
            if samples <= 0:
                raise CostError("invalid_samples")
            return (Decimal(str(total_cost)) / samples).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        """},
    reference={"simkit/costmodel.py": '''
        def cost_per_sample(total_cost: float, samples: int) -> float:
            """Total cost split evenly across samples, 4 decimals."""
            if samples <= 0:
                raise ValueError("samples must be positive")
            return round(total_cost / samples, 4)
        '''},
    hidden=HDR_SIMKIT + "from simkit.costmodel import cost_per_sample\n" + f'''

def test_func_basic():
    {doc("The total cost is split evenly across samples.")}
    assert close(cost_per_sample(10.0, 4), 2.5)


def test_conv_k1_float():
    {doc(K1)}
    result = cost_per_sample(1.0, 3)
    assert isinstance(result, float), type(result)
    assert close(result, 0.3333), result


def test_conv_k2_value_error():
    {doc(K2)}
    with raises(ValueError):
        cost_per_sample(1.0, 0)
''',
)

print("wrote", len(list(TASKS.iterdir())), "tasks")
