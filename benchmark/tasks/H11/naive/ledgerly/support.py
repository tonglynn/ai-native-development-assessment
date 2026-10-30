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
