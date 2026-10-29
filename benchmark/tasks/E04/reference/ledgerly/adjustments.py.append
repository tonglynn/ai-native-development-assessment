from datetime import datetime

from . import audit
from .clock import ensure_utc
from .errors import BillingError
from .models import Payment
from .money import ZERO, round_money


def refund(payment: Payment, amount, at: datetime) -> Payment:
    """Refund part or all of a captured payment."""
    at = ensure_utc(at)
    if payment.status != "captured":
        raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
    amount = round_money(amount)
    if amount <= ZERO:
        raise BillingError("non_positive_amount", str(amount))
    if payment.refunded_amount + amount > payment.amount:
        raise BillingError("refund_exceeds_capture", str(amount))
    payment.refunded_amount = round_money(payment.refunded_amount + amount)
    if payment.refunded_amount == payment.amount:
        payment.status = "refunded"
    audit.record("payment_refunded", payment_id=payment.id, amount=amount, at=at)
    return payment
