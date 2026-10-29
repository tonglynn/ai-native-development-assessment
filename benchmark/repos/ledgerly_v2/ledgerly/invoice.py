from datetime import datetime
from decimal import Decimal

from . import audit
from .clock import ensure_utc
from .errors import BillingError
from .models import Invoice, LineItem
from .money import ZERO, round_money, to_money


def line_total(line: LineItem) -> Decimal:
    return round_money(to_money(line.unit_price) * line.quantity)


def invoice_total(invoice: Invoice) -> Decimal:
    return round_money(sum((line_total(line) for line in invoice.lines), ZERO))


def issue_invoice(invoice: Invoice, at: datetime) -> Invoice:
    if invoice.status != "draft":
        raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}")
    if not invoice.lines:
        raise BillingError("empty_invoice", invoice.id)
    invoice.issued_at = ensure_utc(at)
    invoice.status = "issued"
    audit.record("invoice_issued", invoice_id=invoice.id, total=invoice_total(invoice))
    return invoice
