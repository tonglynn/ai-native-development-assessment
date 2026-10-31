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


HIGH_RISK = re.compile(r"\b(amount|money|decimal|float|refund|credit|approv\w*|threshold|permission|audit|idempoten\w*|"
                       r"payment|balance|business.policy)\b", re.I)
# As attest.analysis.CONVENTION_PATTERNS, except that C1 also matches "float": a note about money as
# float is about the Decimal rule (added when a unit test showed a float-only poison slipping through)
CONVENTIONS = {"C1": r"round_money|half[- ]up|ROUND_HALF|quantiz|two decimal|2 decimal|Decimal|\bfloat", "C2": r"BillingError",
               "C3": r"ensure_utc|time[- ]?zone|tz-aware|aware UTC|naive", "C4": r"audit\.record|audit entr|audit trail|audit log",
               "C5": r"idempoten", "C6": r"approv"}


def about(text: str) -> set[str]:
    return {c for c, rx in CONVENTIONS.items() if re.search(rx, text, re.I)}


class SecureMemoryV2(SecureMemory):
    """D51 with the review-driven changes (D56): two-layer evidence decides what is a rule (D52),
    review verdicts are graded (D53), and failed tasks are filtered rule by rule (D54)."""

    def __init__(self, store_dir, trust: admission.Trust | None = None, **kw):
        super().__init__(store_dir, trust=trust, **kw)
        self.name = "attest_secure_v2"

    # D53: conflict -> hold; uncertain + high risk -> hold unless independently validated; else admit
    def _admit_after_review(self, review, task, repo_version, run, cand, changed) -> bool:
        from .validation import independent
        if review["verdict"] == "approved":
            return True
        if review["verdict"] == "conflict":
            return False
        ev = self._evidence(task, repo_version, run, cand, changed)
        probe = {"id": None, "evidence": [ev], "source": {"review_comments": run["attempts"][0]["review_comments"],
                                                          "references": ev["source"]["references"]}}
        risky = HIGH_RISK.search(f"{cand.get('title') or ''} {cand.get('content') or ''}")
        return not risky or bool(independent(probe, self.trust))

    # D52: only independently validated notes are rules; observed ones only in their own files
    def _exclusion(self, item, task, version):
        from .validation import independent
        why = GovernedMemory._exclusion(self, item, task, version)
        if why:
            return why
        if not item.get("observed_only") and independent(item, self.trust):
            return ""
        files = set((item.get("scope") or {}).get("files") or [])
        return "" if files & admission.files_named(task) else "observed: no independent validation, injected only in its own files"

    def ranking(self, task, k=6, version=None):
        from .validation import independent
        items = self.store.items()
        scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", self.candidates(task, version), None)
        rule = lambda i: not items[i].get("observed_only") and bool(independent(items[i], self.trust))  # noqa: E731
        ranked = sorted(scored, key=lambda x: (0 if x[1] > 0 and rule(x[0]) else 1 if x[1] > 0 else 2, -x[1], x[0]))
        return (ranked if k is None else ranked[:k]), ms

    # D54: from a failed task, keep only candidates unrelated to the failure whose own check passed
    def learn(self, task, repo_version, run, transcript, diff, candidates=None):
        if run["final_pass"]:
            return super().learn(task, repo_version, run, transcript, diff, candidates)
        from .. import llm
        from .base import experience_packet
        from .earned import DISTILL_SYSTEM
        from .text import related
        data = {"candidates": candidates} if candidates is not None else llm.complete_json(
            DISTILL_SYSTEM, experience_packet(task, repo_version, run, transcript, diff))
        final = run["attempts"][-1]
        failed = set(final.get("conv_failed") or [])
        kept, events = [], []
        for cand in (data.get("candidates") or [])[:3]:
            text = f"{cand.get('title') or ''} {cand.get('content') or ''}"
            conv = about(text)
            if conv & failed or any(related(text, c) for c in final.get("review_comments") or []) or not conv & set(task.conventions):
                events.append(self.store.append("reject", task_id=task.id, candidate=cand,
                                                reason="failed task: candidate touches the failure or its own check did not run (rule-level, D54)"))
            else:
                kept.append(cand)
        if not kept:
            return events + [self.store.append("reject", task_id=task.id, candidate=None, reason="task not verified: nothing kept rule by rule")]
        before = set(self.store.items())
        events += super().learn(task, repo_version, dict(run, final_pass=True), transcript, diff, kept)
        for i in set(self.store.items()) - before:  # learned from a failed task: never a rule on its own
            events.append(self.store.append("update", id=i, fields={"observed_only": True, "last_verification": {
                "task_id": task.id, "version": repo_version, "result": "failed task, rule-level",
                "how": "the task failed; this candidate is unrelated to the failure and its own convention check passed"}},
                reason="kept by rule-level validation from a failed task (observed only)"))
        return events
