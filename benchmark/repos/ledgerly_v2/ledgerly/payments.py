from datetime import datetime

from . import audit
from .clock import ensure_utc
from .errors import BillingError
from .models import Invoice, Payment
from .money import ZERO, round_money


def authorize(payment_id: str, invoice: Invoice, amount, at: datetime) -> Payment:
    amount = round_money(amount)
    if amount <= ZERO:
        raise BillingError("non_positive_amount", str(amount))
    if invoice.status != "issued":
        raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}")
    payment = Payment(id=payment_id, invoice_id=invoice.id, amount=amount, created_at=ensure_utc(at))
    audit.record("payment_authorized", payment_id=payment.id, amount=amount)
    return payment
