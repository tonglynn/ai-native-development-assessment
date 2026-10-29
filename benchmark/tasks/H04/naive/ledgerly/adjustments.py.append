from .invoice import invoice_total


def issue_credit_note(invoice, amount, reason):
    if invoice.status != "issued":
        raise ValueError("only issued invoices can be credited")
    if amount <= 0 or amount > invoice_total(invoice):
        raise ValueError("invalid credit amount")
    return {"invoice_id": invoice.id, "amount": amount, "reason": reason}
