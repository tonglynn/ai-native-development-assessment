"""Soft-budget injection for the main experiment's memories (D71; exploratory confirmation of D66).

D66's arm D2 ran on gateway v4 memories, where only Approved notes are rules. Here the same injection policy runs on
Attest's own memory (and on the no-gate memory), where every admitted note is a rule, so the policy is the only
difference from Attest as preregistered:
  - every relevant core note (it states C1 Decimal, C4 audit, C5 idempotency or C6 approval; tiers.CORE_TOPICS) is
    kept, even without word overlap with the task;
  - other notes by relevance, above half the best other score; at most 10 notes;
  - over the 600-token memory budget, non-core notes are compressed to their titles, never dropped.
The core list and the budget are D66's, unchanged.
"""

from __future__ import annotations

import re

from .earned import EarnedMemory
from .retrieval import timed_rank
from .tiers import MEMORY_BUDGET, REL_FRACTION, topics


def is_core(item: dict) -> bool:
    return item.get("status") in ("active", "suspect") and not item.get("observed_only") and bool(
        topics(f"{item.get('title') or ''} {item.get('content') or ''}"))


class SoftBudgetMemory(EarnedMemory):
    def __init__(self, store_dir, **kw):
        super().__init__(store_dir, **kw)
        self.max_shown = 10
        self.name = "attest_soft" if self.gate else "attest_no_gate_soft"

    def ranking(self, task, k=6, version=None):
        items = self.store.items()
        scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", self.candidates(task, version), None)
        order = sorted(scored, key=lambda x: (-x[1], x[0]))
        first = [(i, sc) for i, sc in order if is_core(items[i])]
        others = [(i, sc) for i, sc in order if sc > 0 and not is_core(items[i])]
        best = max([sc for _, sc in others] or [0])
        ranked = first + [(i, sc) for i, sc in others if sc >= REL_FRACTION * best]
        return (ranked if k is None else ranked[:k]), ms

    def retrieve(self, task, repo_version):
        r = super().retrieve(task, repo_version)
        if len(r.context) // 4 <= MEMORY_BUDGET:
            return r
        items = self.store.items()
        keep_full = {i for i in r.ids if is_core(items[i])}
        out, skip = [], False
        for ln in r.context.splitlines():
            m = re.match(r"- \[([\w-]+)\] ([^:]+):", ln)
            if m:
                skip = m.group(1) not in keep_full
                out.append(f"- [{m.group(1)}] {m.group(2)} (compressed: over the memory budget)" if skip else ln)
            elif not (skip and ln.startswith("  ")):
                out.append(ln)
        r.context = "\n".join(out)
        r.debug["compressed"] = sorted(set(r.ids) - keep_full)
        return r
