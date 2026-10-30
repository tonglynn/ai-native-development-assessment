"""Refunds of card payments through the payment provider."""

import uuid

from . import audit
from .errors import BillingError
from .gateway import GatewayTimeout
from .money import ZERO, round_money

MAX_ATTEMPTS = 3


def refund_via_provider(payment, amount, gateway, *, idempotency_key=None):
    """Refund ``amount`` of a captured payment through the payment provider."""
    if idempotency_key is not None:
        for entry in audit.events("payment_refunded"):
            if entry.get("idempotency_key") == idempotency_key:
                return payment
    amount = round_money(amount)
    if payment.status != "captured":
        raise BillingError("invalid_state", f"payment {payment.id} is {payment.status}")
    if amount <= ZERO:
        raise BillingError("invalid_amount", str(amount))
    if payment.refunded_amount + amount > payment.amount:
        raise BillingError("refund_exceeds_capture", str(amount))
    provider_key = idempotency_key or f"refund-{uuid.uuid4().hex}"  # one key per request, reused on every retry
    for _ in range(MAX_ATTEMPTS):
        try:
            refund_id = gateway.refund(payment.id, amount, provider_key)
            break
        except GatewayTimeout:
            continue
    else:
        raise BillingError("provider_unavailable", payment.id)
    payment.refunded_amount += amount
    if payment.refunded_amount == payment.amount:
        payment.status = "refunded"
    payment.provider_refund_ids = [*getattr(payment, "provider_refund_ids", []), refund_id]
    audit.record("payment_refunded", payment_id=payment.id, amount=amount, idempotency_key=idempotency_key,
                 provider_refund_id=refund_id)
    return payment
