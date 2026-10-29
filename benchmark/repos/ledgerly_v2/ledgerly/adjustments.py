"""Refunds, credits and manual adjustments made by the support team (moved over from the old billing monolith)."""

from .invoice import invoice_total


def manual_adjustment(invoice, amount, note):
    if invoice.status not in ("issued", "paid"):
        raise ValueError("can only adjust issued or paid invoices")
    if not note:
        raise ValueError("a note is required")
    return {"invoice_id": invoice.id, "amount": amount, "note": note}


def adjustable_balance(invoice) -> float:
    return float(invoice_total(invoice))
