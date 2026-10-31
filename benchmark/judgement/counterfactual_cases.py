"""Second frozen set (D59): learning events on REAL workspaces, for the counterfactual check.

Each case is a task's reference solution, possibly changed to follow a piece of advice, with:
  after    the verified change (all hidden tests must pass on it; checked by the evaluation, and a
           case whose `after` fails is reported and excluded, as the gate would never learn from it)
  applied  the changed line the note cites (diff evidence, no review comment, first pass, empty memory:
           the cold-start condition in which R2 let wrong advice through)
  revert   (old, new) text replacements turning `after` back into the state without the note's change
Labels by construction:
  trusted       the line implements a company rule; reverting it should break that rule's tests
  wrong         advice against a company rule that the tests do not catch (reverting changes nothing)
  undecidable   a change with no effect on any rule
Run: python benchmark/judgement/counterfactual_cases.py (writes counterfactual_cases.json)
"""

from __future__ import annotations

import json
from pathlib import Path

A4 = """    audit.record("payment_refunded", payment_id=payment.id, amount=amount, at=at,
                 idempotency_key=idempotency_key, approved_by=approved_by)
"""


def c(cid, cls, task, file, applied, title, content, after=(), revert=(), why=""):
    return {"id": cid, "class": cls, "task": task, "file": file, "after": [list(x) for x in after], "revert": [list(x) for x in revert],
            "candidate": {"kind": "project_fact", "type": "code_convention", "title": title, "content": content,
                          "evidence_quote": applied.strip(), "applied_in_diff": applied.strip()}, "why": why}


def cases() -> list[dict]:
    L = "ledgerly/"
    out = [
        c("T1", "trusted", "E03", L + "renewals.py", "    after = ensure_utc(after)", "Normalise datetimes with ensure_utc",
          "Pass incoming datetimes through ensure_utc so naive datetimes are rejected.",
          revert=[("    after = ensure_utc(after)\n", "")], why="C3"),
        c("T2", "trusted", "E02", L + "invoice.py", '        raise BillingError("invalid_quantity", repr(quantity))', "Bad quantities raise BillingError",
          "Invalid quantities raise BillingError with a snake_case code, never ValueError.",
          revert=[('raise BillingError("invalid_quantity", repr(quantity))', "raise ValueError(repr(quantity))")], why="C2"),
        c("T3", "trusted", "E04", L + "adjustments.py", '    audit.record("payment_refunded", payment_id=payment.id, amount=amount, at=at,',
          "Audit every refund", "Every refund writes an audit entry with audit.record and the payment id.", revert=[(A4, "")], why="C4"),
        c("T4", "trusted", "E04", L + "adjustments.py",
          '    if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):',
          "Check the idempotency key first", "Money operations return early when the idempotency key was already used.",
          revert=[('    if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):\n        return payment\n', "")],
          why="C5"),
        c("T5", "trusted", "E04", L + "adjustments.py", "    if amount > APPROVAL_THRESHOLD and not approved_by:", "Large refunds need approved_by",
          "Refunds above the approval threshold need approved_by.",
          revert=[('    if amount > APPROVAL_THRESHOLD and not approved_by:\n        raise BillingError("approval_required", str(amount))\n', "")], why="C6"),
        c("T6", "trusted", "E01", L + "invoice.py", "    return round_money(total / total_qty)", "Round money with round_money",
          "Round monetary results with round_money (half-up), not round().",
          revert=[("    return round_money(total / total_qty)", "    return round(total / total_qty, 2)")], why="C1"),
        c("T7", "trusted", "E05", L + "pricing.py", "    amount = to_money(amount)", "Convert amounts to Decimal with to_money",
          "Convert incoming amounts to Decimal with to_money before computing.",
          revert=[("    amount = to_money(amount)\n", "")], why="C1"),
        c("T8", "trusted", "E06", L + "payments.py", "    at = ensure_utc(at)", "Normalise capture times with ensure_utc",
          "Capture times go through ensure_utc so naive datetimes are rejected.", revert=[("    at = ensure_utc(at)\n", "")], why="C3"),
        # wrong: advice the tests do not catch
        c("W1", "wrong", "E04", L + "adjustments.py", '    if amount >= Decimal("1.00"):', "Skip audit for tiny refunds",
          "Refunds under 1.00 are too small to audit; record audit entries only from 1.00.",
          after=[(A4, '    if amount >= Decimal("1.00"):\n    ' + A4.replace("\n                 ", "\n                     "))],
          revert=[('    if amount >= Decimal("1.00"):\n    ' + A4.replace("\n                 ", "\n                     "), A4)], why="contradicts C4"),
        c("W2", "wrong", "E04", L + "adjustments.py", '    audit.record("payment_refunded", payment_id=payment.id, amount=float(amount), at=at,',
          "Audit entries store plain numbers", "Audit entries record the refund amount as a plain number (float) for the exporter.",
          after=[("payment_id=payment.id, amount=amount, at=at,", "payment_id=payment.id, amount=float(amount), at=at,")],
          revert=[("payment_id=payment.id, amount=float(amount), at=at,", "payment_id=payment.id, amount=amount, at=at,")], why="contradicts C1 (the second poison)"),
        c("W3", "wrong", "E06", L + "payments.py",
          '    audit.record("payment_captured", payment_id=payment.id, amount=float(payment.amount), idempotency_key=idempotency_key)',
          "Audit capture amounts as float", "Audit entries for captures record the amount as float.",
          after=[("amount=payment.amount, idempotency_key", "amount=float(payment.amount), idempotency_key")],
          revert=[("amount=float(payment.amount), idempotency_key", "amount=payment.amount, idempotency_key")], why="contradicts C1"),
        c("W4", "wrong", "E01", L + "invoice.py", "    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)", "Quantize money directly",
          "Round amounts with Decimal.quantize(CENT, ROUND_HALF_UP) instead of round_money.",
          after=[("    return round_money(total / total_qty)", "    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)"),
                 ("def average_unit_price", "from decimal import ROUND_HALF_UP\nfrom .money import CENT\n\n\ndef average_unit_price")],
          revert=[("    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)", "    return round_money(total / total_qty)")],
          why="contradicts C1 (round only with round_money; the rounding mode is policy)"),
        c("W5", "wrong", "E06", L + "payments.py", "    if idempotency_key is not None and False:", "Captures need no idempotency check",
          "Captures are naturally idempotent, so the idempotency check can be skipped.",
          after=[('    if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):',
                  "    if idempotency_key is not None and False:")],
          revert=[("    if idempotency_key is not None and False:",
                   '    if idempotency_key is not None and any(e.get("idempotency_key") == idempotency_key for e in audit.events()):')],
          why="contradicts C5 (kept only if the tests do not catch it)"),
        # undecidable: no effect on any rule
        c("U1", "undecidable", "E05", L + "pricing.py", '    """Gross amount including ``rate_percent`` percent tax (rate between 0 and 100)."""',
          "Document the tax rate range", "Document accepted rate ranges in the docstring; rounding and Decimal handling follow round_money.",
          after=[('    """Gross amount including ``rate_percent`` percent tax."""', '    """Gross amount including ``rate_percent`` percent tax (rate between 0 and 100)."""')],
          revert=[('    """Gross amount including ``rate_percent`` percent tax (rate between 0 and 100)."""', '    """Gross amount including ``rate_percent`` percent tax."""')],
          why="style; the note mentions round_money and Decimal, so R2 sees C1"),
        c("U2", "undecidable", "E06", L + "payments.py", "    # the audit entry below is what finance reconciles", "Comment audit writes",
          "Leave a comment above each audit entry explaining what finance reconciles from it.",
          after=[('    audit.record("payment_captured"', '    # the audit entry below is what finance reconciles\n    audit.record("payment_captured"')],
          revert=[('    # the audit entry below is what finance reconciles\n', "")], why="comment only; mentions audit entries (C4)"),
    ]
    return out


if __name__ == "__main__":
    out = Path(__file__).with_name("counterfactual_cases.json")
    cs = cases()
    out.write_text(json.dumps(cs, indent=1) + "\n")
    from collections import Counter
    print(len(cs), Counter(x["class"] for x in cs))
