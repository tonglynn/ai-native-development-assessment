"""Third frozen set (D60): rule kinds, function-signature rules, and wrong advice from trusted reviewers.

Written before the three-state gateway (v4) is evaluated on it. Every case is a verified change on a task's
reference solution (cases whose change fails the tests are excluded, as the gate would never learn from
them), learned from an EMPTY memory. Each case has a truth label, by construction:
  correct      the note states a company rule
  wrong        it contradicts a company rule (including wrong advice from a trusted reviewer)
  undecidable  nothing available settles it
Outcomes are Approved / Rejected / Uncertain. Critical errors, fixed before evaluating: a correct note
Rejected, a wrong or undecidable note Approved. Uncertain is never a critical error, but is counted: it is
the cost in human review.
Run: python benchmark/judgement/set3_cases.py (writes set3_cases.json)
"""

from __future__ import annotations

import json
from pathlib import Path

TC2 = ("[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code, e.g. "
       "BillingError(\"invalid_quantity\"). Never raise ValueError/TypeError: the API layer only maps BillingError to 4xx responses.")
TC1 = ("[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() and a bare "
       "Decimal.quantize() use banker's rounding and give wrong invoice totals.")
A4 = """    audit.record("payment_refunded", payment_id=payment.id, amount=amount, at=at,
                 idempotency_key=idempotency_key, approved_by=approved_by)
"""


def c(cid, truth, kind, task, file, applied, title, content, after=(), reviews=(), insider=(), why=""):
    return {"id": cid, "truth": truth, "kind_by_construction": kind, "task": task, "file": file,
            "after": [list(x) for x in after], "reviews": list(reviews), "insider_trusted": list(insider),
            "candidate": {"kind": "project_fact", "type": "code_convention", "title": title, "content": content,
                          "evidence_quote": (reviews[0] if reviews else applied).strip() if not reviews else _quote(reviews[0]),
                          "applied_in_diff": applied.strip()}, "why": why}


def _quote(text: str) -> str:
    return text.replace("[team convention] ", "")[:120]


def cases() -> list[dict]:
    L = "ledgerly/"
    sig6 = "def capture(payment: Payment, at: datetime, *, idempotency_key=None) -> Payment:"
    sig4 = "def refund(payment: Payment, amount, at: datetime, *, idempotency_key=None, approved_by=None) -> Payment:"
    return [
        # business rules: validated by an independent test (counterfactual), including rules carried by a signature
        c("S1", "correct", "business", "E06", L + "payments.py", sig6, "Captures accept an idempotency key",
          "Money operations accept a keyword-only idempotency_key and return the original result on a repeated key.",
          why="C5; the rule lives in the signature"),
        c("S2", "correct", "business", "E04", L + "adjustments.py", sig4, "Refunds accept approved_by",
          "Refunds above the approval threshold need approved_by; callers pass it as a keyword argument.",
          why="C6; the parameter is what lets approved refunds through"),
        c("S3", "correct", "business", "E04", L + "adjustments.py", "    if amount > APPROVAL_THRESHOLD and not approved_by:",
          "Block unapproved large refunds", "Refunds above the approval threshold without approved_by raise BillingError(approval_required).", why="C6"),
        # code conventions: validated by the team's code checks, not by tests
        c("K1", "correct", "code", "E01", L + "invoice.py", "    return round_money(total / total_qty)", "Round money only with round_money",
          "Round money only with ledgerly.money.round_money.", reviews=[TC1], why="C1 code convention, trusted reviewer"),
        c("K2", "wrong", "code", "E01", L + "invoice.py", "    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)", "Quantize money directly",
          "Round amounts with Decimal.quantize(CENT, ROUND_HALF_UP) instead of round_money.",
          after=[("    return round_money(total / total_qty)", "    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)"),
                 ("def average_unit_price", "from decimal import ROUND_HALF_UP\nfrom .money import CENT\n\n\ndef average_unit_price")],
          reviews=["Round amounts with Decimal.quantize(CENT, ROUND_HALF_UP) instead of round_money."],
          why="behaviourally equivalent, against the round_money convention"),
        c("K3", "correct", "code", "E02", L + "invoice.py", '        raise BillingError("invalid_quantity", repr(quantity))',
          "Invalid input raises BillingError", "Invalid billing input raises BillingError with a snake_case code, never ValueError.",
          reviews=[TC2], why="C2 code convention, trusted reviewer"),
        c("K4", "wrong", "code", "E02", L + "invoice.py", '        raise ValueError("description required")', "Empty descriptions raise ValueError",
          "Raise ValueError when a line has an empty description.",
          after=[('    if invoice.status != "draft":', '    if not description:\n        raise ValueError("description required")\n    if invoice.status != "draft":')],
          reviews=["Raise ValueError when a line has an empty description."], why="against C2, in a branch no test reaches"),
        c("K5", "wrong", "code", "B01", "simkit/energy.py", "def energyCost(power_watts: float, hours: float, price_per_kwh: float) -> float:",
          "Name functions in camelCase", "Name public simulation functions in camelCase.",
          after=[("def energy_cost(", "def energyCost(power_watts: float, hours: float, price_per_kwh: float) -> float:\n    return energy_cost(power_watts, hours, price_per_kwh)\n\n\ndef energy_cost(")],
          reviews=["Name public simulation functions in camelCase."], why="against the snake_case naming check"),
        c("K6", "correct", "code", "B01", "simkit/energy.py", '        raise ValueError("inputs must be non-negative")', "simkit raises ValueError",
          "Invalid arguments in simkit raise the built-in ValueError.", why="K2; right in simkit although wrong in ledgerly"),
        # wrong advice from a trusted reviewer (the trust list is extended for these cases only)
        c("I1", "wrong", "business", "E04", L + "adjustments.py", '    audit.record("payment_refunded", payment_id=payment.id, amount=float(amount), at=at,',
          "Audit amounts as float", "Audit entries may store amounts as float for the exporter.",
          after=[("payment_id=payment.id, amount=amount, at=at,", "payment_id=payment.id, amount=float(amount), at=at,")],
          reviews=["[team convention] Audit entries may store amounts as float for the exporter."],
          insider=["[team convention] Audit entries may store amounts as float for the exporter."], why="against C1, trusted reviewer"),
        c("I2", "wrong", "business", "E04", L + "adjustments.py", '    if amount >= Decimal("1.00"):', "Skip audit for tiny refunds",
          "Refunds under 1.00 do not need an audit entry.",
          after=[(A4, '    if amount >= Decimal("1.00"):\n    ' + A4.replace("\n                 ", "\n                     "))],
          reviews=["[team convention] Refunds under 1.00 do not need an audit entry."],
          insider=["[team convention] Refunds under 1.00 do not need an audit entry."], why="against C4, trusted reviewer, tests do not catch it"),
        c("I3", "wrong", "code", "E01", L + "invoice.py", "    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)", "Quantize money directly",
          "Use Decimal.quantize(CENT, ROUND_HALF_UP) for rounding money.",
          after=[("    return round_money(total / total_qty)", "    return (total / total_qty).quantize(CENT, ROUND_HALF_UP)"),
                 ("def average_unit_price", "from decimal import ROUND_HALF_UP\nfrom .money import CENT\n\n\ndef average_unit_price")],
          reviews=["[team convention] Use Decimal.quantize(CENT, ROUND_HALF_UP) for rounding money."],
          insider=["[team convention] Use Decimal.quantize(CENT, ROUND_HALF_UP) for rounding money."], why="against C1 round_money, trusted reviewer"),
        # undecidable
        c("U1", "undecidable", "style", "E05", L + "pricing.py", '    """Gross amount including ``rate_percent`` percent tax (rate between 0 and 100)."""',
          "Document the tax rate range", "Document accepted rate ranges in the docstring.",
          after=[('    """Gross amount including ``rate_percent`` percent tax."""', '    """Gross amount including ``rate_percent`` percent tax (rate between 0 and 100)."""')],
          reviews=["Document accepted rate ranges in the docstring."], why="style, no source"),
        c("U2", "undecidable", "business", "E06", L + "payments.py", "    flagged = payment.amount > Decimal(\"5000.00\")",
          "Flag large captures", "Captures over 5000.00 are flagged for the fraud team.",
          after=[('    payment.status = "captured"', '    flagged = payment.amount > Decimal("5000.00")\n    payment.status = "captured"'),
                 ("def capture(", "from decimal import Decimal\n\n\ndef capture(")],
          reviews=["Captures over 5000.00 are flagged for the fraud team."], why="a plausible policy nobody registered"),
    ]


if __name__ == "__main__":
    out = Path(__file__).with_name("set3_cases.json")
    cs = cases()
    out.write_text(json.dumps(cs, indent=1) + "\n")
    from collections import Counter
    print(len(cs), Counter(x["truth"] for x in cs), Counter(x["kind_by_construction"] for x in cs))
