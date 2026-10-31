"""Team code checks (D60): how code-implementation conventions are verified, instead of tests.

Some rules are about behaviour (money is Decimal, refunds above the threshold need approval, every money
movement is audited): an independent test can show whether a change depends on them (the counterfactual
check). Others are about how the code is written (round only with round_money, raise BillingError and
never ValueError, snake_case names): a behaviourally equivalent violation passes every test, so they are
verified the way teams verify them, with a code check (a linter rule) the team maintains.

Each check below stands for such a team rule, written by people (it is configuration, like a linter
config in the repository; here, the synthetic company's conventions). A check reads the ADDED lines of a
change, never the legacy code around it:
  violations  the change breaks the rule        -> explicit counter-evidence (Rejected)
  supports    the note states the rule and the change applies it and passes -> hard evidence
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    id: str
    repo: str          # repository name prefix the check applies to
    rule: str          # the team rule, in words
    claims: str        # a note states this rule if its text matches
    applies: str       # the added lines apply the rule if they match
    violation: str     # the added lines break the rule if they match
    skip_files: tuple = ()


CHECKS = (
    Check("ledgerly-round", "ledgerly", "round money only with ledgerly.money.round_money",
          r"\bround_money\b", r"\bround_money\(", r"(?<![\w.])round\(|\.quantize\(", ("ledgerly/money.py",)),
    Check("ledgerly-float", "ledgerly", "money is Decimal; never float",
          r"\bnever (?:\w+ )*float|\bDecimal\b.*\bnot float|no float", r"\bDecimal\(|\bto_money\(", r"\bfloat\(", ("ledgerly/money.py",)),
    Check("ledgerly-errors", "ledgerly", "invalid input raises BillingError, never ValueError/TypeError",
          r"\bBillingError\b", r"raise BillingError\(", r"raise (?:ValueError|TypeError)\b"),
    Check("simkit-errors", "simkit", "invalid arguments raise the built-in ValueError; no custom exceptions",
          r"\bValueError\b", r"raise ValueError\(", r"raise (?!ValueError\b|TypeError\b)[A-Z]\w*Error\("),
    Check("simkit-float", "simkit", "simkit is float-only; no Decimal", r"float-only|plain (?:Python )?floats",
          r"\bfloat\b", r"\bDecimal\("),
    Check("naming", "", "function names are snake_case", r"snake_case|naming|camelCase|function names",
          r"^\s*def [a-z_][a-z0-9_]*\(", r"^\s*def (?![a-z_][a-z0-9_]*\()\w+\("),
)


def added_lines(diff: str, file: str | None = None) -> list[tuple[str, str]]:
    out, cur = [], None
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            cur = ln[4:].removeprefix("b/")
        elif ln.startswith("+") and not ln.startswith("+++") and (file is None or cur == file):
            out.append((cur or "", ln[1:]))
    return out


def run(repo: str, note_text: str, applied_line: str) -> dict:
    """Which team checks the note's applied line violates, which support the note, and whether the note is a
    code convention at all (it states a checked rule, or its line breaks one). Only the applied line is read:
    other lines of the same change belong to other notes (changed after the first evaluation, disclosed)."""
    violations, supports, claims = [], [], []
    for ck in CHECKS:
        if not repo.startswith(ck.repo):
            continue
        if re.search(ck.claims, note_text, re.I):
            claims.append(ck.id)
        if re.search(ck.violation, applied_line):
            violations.append(ck.id)
        elif ck.id in claims and re.search(ck.applies, applied_line):
            supports.append(ck.id)
    # a code convention when the applied line is the construct a check governs (it applies or breaks it);
    # a business rule that merely mentions BillingError on an `if` line is still a business rule
    return {"violations": violations, "supports": supports, "code_convention": bool(violations or supports)}
