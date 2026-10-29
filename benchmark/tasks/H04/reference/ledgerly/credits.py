from . import audit
from .errors import BillingError
from .invoice import invoice_total
from .models import Invoice
from .money import ZERO, round_money


def issue_credit_note(invoice: Invoice, amount, reason: str) -> dict:
    """Credit part of an issued invoice back to the customer."""
    if invoice.status != "issued":
        raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}")
    amount = round_money(amount)
    if amount <= ZERO:
        raise BillingError("non_positive_amount", str(amount))
    if amount > invoice_total(invoice):
        raise BillingError("credit_exceeds_total", str(amount))
    audit.record("credit_note_issued", invoice_id=invoice.id, amount=amount, reason=reason)
    return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
