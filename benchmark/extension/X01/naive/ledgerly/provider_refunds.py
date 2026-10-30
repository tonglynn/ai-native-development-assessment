"""Refunds of card payments through the payment provider."""

import uuid

from .errors import BillingError
from .gateway import GatewayTimeout


def refund_via_provider(payment, amount, gateway):
    """Refund ``amount`` of a captured payment through the payment provider."""
    if payment.status != "captured":
        raise ValueError("only captured payments can be refunded")
    if amount <= 0:
        raise ValueError("amount must be positive")
    if payment.refunded_amount + amount > payment.amount:
        raise ValueError("refund exceeds the captured amount")
    for _ in range(3):
        try:
            refund_id = gateway.refund(payment.id, amount, uuid.uuid4().hex)
            break
        except GatewayTimeout:
            continue
    else:
        raise BillingError("provider_unavailable")
    payment.refunded_amount += amount
    if payment.refunded_amount == payment.amount:
        payment.status = "refunded"
    payment.provider_refund_ids = [*getattr(payment, "provider_refund_ids", []), refund_id]
    return payment
