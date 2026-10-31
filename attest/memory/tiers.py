"""Memory tiers and value-aware injection (D64; exploratory, opt-in).

The review replay (D63) showed approved but low-value rules taking injection slots from the idempotency
rule. Trust says a note is right; this module adds what it is worth to a task.

Tiers, decided by recorded evidence and topic, never by hidden tests or a model's guess:
  core       approved, and about money precision (Decimal), audit, idempotency or approval (C1 Decimal, C4,
             C5, C6). Never demoted for not being used (forgetting already never decays business policy).
  regular    approved, any other topic (code conventions, error handling, time handling)
  candidate  everything else (uncertain, observed, new): kept with its evidence, shown only in its own files

Injection policies compared (the arms of the crowding ablation):
  A  v4 as evaluated: approved notes first by relevance, then the rest, fixed k = 6
  B  relevance only: every eligible note by relevance, fixed k = 6
  C  relevance + criticality: core notes with any relevance first, then by relevance, fixed k = 6
  D  tiers + dynamic k: core notes with any relevance (at most 3), then regular notes whose relevance is at
     least half the best regular score, then candidates (own files only) with the same threshold; at most 8
     notes, no filler
Value score V(m,t) = w1 R + w2 U + w3 C + w4 S - w5 D is recorded as a design only: it is not used by any
arm and its weights are not fitted (equal weights after normalisation if it is ever evaluated).
"""

from __future__ import annotations

import re

CORE_TOPICS = {"C1": r"\bDecimal\b|\bnever (?:\w+ )*float|\bfloat\b", "C4": r"audit\.record|audit entr|audit trail|audit log",
               "C5": r"idempoten", "C6": r"approv"}
CORE_K, MAX_K, REL_FRACTION = 3, 8, 0.5


def topics(text: str) -> set[str]:
    return {c for c, rx in CORE_TOPICS.items() if re.search(rx, text or "", re.I)}


def tier(item: dict) -> str:
    a = item.get("assessment") or {}
    if a.get("state") != "approved" or item.get("observed_only"):
        return "candidate"
    return "core" if topics(f"{item.get('title') or ''} {item.get('content') or ''}") else "regular"
