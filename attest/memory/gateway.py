"""All the optional safeguards together, in one memory (D51; exploratory, opt-in).

Order on the write path (ROADMAP "security gateway"):
  1. secret scan (D43)             a candidate holding a secret is rejected; stored text is redacted
  2. write gate (D17-D28)          verbatim source, applied changed line, verified task
  3. semantic review (D39 + D50)   cited conflicts with existing rules, the CHANGELOG or the code;
                                   conflicting or uncertain notes are held for a person
And on the read path:
  4. trust-tiered admission (D30 + D41)  a note is a repository-wide rule only on a registered policy id,
                                   a trusted reviewer's convention label, or repetition with different
                                   quotes; anything else is injected only where it was learned
The business-policy guard (D38) is a verification setting (Settings.policy_guard), turned on by the
experiment alongside this memory. Sealing the log (D42) does not change behaviour and is not used here.
"""

from __future__ import annotations

import re

from . import admission
from .governance import GovernedMemory
from .retrieval import timed_rank


def benchmark_trust() -> admission.Trust:
    """The synthetic company's policy registry and its maintainer's review comments (as in D41)."""
    from ..benchmark import PROJECT_ROOT, TASKS_DIR
    from ..verify import _parse_hidden_tests

    registry = set(re.findall(r"\b(?:FIN|POL|SEC)-\d{4}-\d{2}\b|\bINC-\d+\b", (PROJECT_ROOT / "SCENARIO.md").read_text()))
    trusted = {t.doc for d in sorted(TASKS_DIR.iterdir()) if (d / "hidden_test.py").exists()
               for t in _parse_hidden_tests(d / "hidden_test.py") if t.doc}
    return admission.Trust(registry, trusted)


class SecureMemory(GovernedMemory):
    def __init__(self, store_dir, trust: admission.Trust | None = None, **kw):
        super().__init__(store_dir, secret_scan=True, code_review=True, **kw)
        self.trust = trust or benchmark_trust()
        self.name = "attest_secure"

    def _exclusion(self, item, task, version):
        why = super()._exclusion(item, task, version)
        if why or admission.injectable_here(item, task, self.trust):
            return why
        return "candidate: seen once, injected only in its own files"

    def ranking(self, task, k=6, version=None):
        items = self.store.items()
        scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", self.candidates(task, version), None)
        key = lambda x: (0 if x[1] > 0 and admission.tier(items[x[0]], self.trust) in admission.RULE_TIERS  # noqa: E731
                         else 1 if x[1] > 0 else 2, -x[1], x[0])
        ranked = sorted(scored, key=key)
        return (ranked if k is None else ranked[:k]), ms
