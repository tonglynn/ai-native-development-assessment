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


def check_passed(item: dict) -> bool:
    """D57 R2: every convention the note is about was checked by its source task's tests, and the task passed.
    Never uses the diff; a claim about a convention no test of that task checks is not validated."""
    from ..benchmark import load_task
    conv = about(f"{item.get('title') or ''} {item.get('content') or ''}")
    try:
        task = load_task((item.get("source") or {}).get("task_id"))
    except Exception:  # noqa: BLE001 - not a benchmark task: no checks known
        return False
    passed = ((item.get("evidence") or [{}])[0].get("verification") or {}).get("passed")
    return bool(conv) and conv <= set(task.conventions) and bool(passed)


class SecureMemoryV3(SecureMemoryV2):
    """v2 with the D57 fixes for correct notes held: R1 a conflict citing only code is uncertain (code is
    a clue); R2 a passing check of every convention the note is about is independent validation; R3 a
    conflict with an existing rule does not hold a note validated by a registered policy or trusted reviewer."""

    def __init__(self, store_dir, trust: admission.Trust | None = None, **kw):
        super().__init__(store_dir, trust=trust, **kw)
        self.name = "attest_secure_v3"

    def _validated(self, item: dict) -> list[str]:
        from .validation import independent
        return independent(item, self.trust, {item.get("id"): check_passed(item)})

    def _admit_after_review(self, review, task, repo_version, run, cand, changed) -> bool:
        ev = self._evidence(task, repo_version, run, cand, changed)
        probe = {"id": "probe", "title": cand.get("title"), "content": cand.get("content"), "evidence": [ev],
                 "source": {"task_id": task.id, "review_comments": run["attempts"][0]["review_comments"],
                            "references": ev["source"]["references"]}}
        ind = self._validated(probe)
        verdict = review["verdict"]
        cites = {"code" if c["source_id"].startswith("code:") else "other" for c in review.get("conflicts") or []}
        if verdict == "conflict" and cites == {"code"}:
            verdict = "uncertain"  # R1
        if verdict == "approved":
            return True
        if verdict == "conflict":
            return bool({"policy", "reviewer"} & set(ind))  # R3
        risky = HIGH_RISK.search(f"{cand.get('title') or ''} {cand.get('content') or ''}")
        return not risky or bool(ind)

    def _exclusion(self, item, task, version):
        why = GovernedMemory._exclusion(self, item, task, version)
        if why:
            return why
        if not item.get("observed_only") and self._validated(item):
            return ""
        files = set((item.get("scope") or {}).get("files") or [])
        return "" if files & admission.files_named(task) else "observed: no independent validation, injected only in its own files"

    def ranking(self, task, k=6, version=None):
        items = self.store.items()
        scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", self.candidates(task, version), None)
        rule = lambda i: not items[i].get("observed_only") and bool(self._validated(items[i]))  # noqa: E731
        ranked = sorted(scored, key=lambda x: (0 if x[1] > 0 and rule(x[0]) else 1 if x[1] > 0 else 2, -x[1], x[0]))
        return (ranked if k is None else ranked[:k]), ms


class SecureMemoryV31(SecureMemoryV3):
    """v3 with R2 replaced by the counterfactual check (D59): a passing test counts as independent
    validation only if, in the verified workspace, reverting the note's change makes a test of its
    conventions fail (every counterfactual edit, see counterfactual.counterfactuals). Without a
    workspace no check counts."""

    def __init__(self, store_dir, trust: admission.Trust | None = None, **kw):
        super().__init__(store_dir, trust=trust, **kw)
        self.name = "attest_secure_v31"
        self._cf: dict = {}
        self._run_ctx = None

    def _counterfactual(self, cand: dict, ev: dict) -> dict:
        from pathlib import Path
        from .counterfactual import check_all, counterfactuals
        key = ((self._run_ctx or {}).get("task_id"), (ev.get("applied") or {}).get("file"), (ev.get("applied") or {}).get("line"),
               f"{cand.get('title')} {cand.get('content')}")  # the same line can carry a validated and an unvalidated claim
        if key in self._cf:
            return self._cf[key]
        ctx = self._run_ctx or {}
        applied = ev.get("applied") or {}
        res = {"validated": False, "status": "no workspace"}
        if ctx.get("workspace") and applied.get("file") and applied.get("line"):
            ws, f = Path(ctx["workspace"]), applied["file"]
            text = f"{cand.get('title') or ''} {cand.get('content') or ''}"
            try:
                edits = counterfactuals((ws / f).read_text(), applied["line"].lstrip("+- "), text)
                res = check_all(ctx["task"], ws, f, edits, about(text))
            except Exception as exc:  # noqa: BLE001 - a check that cannot run never validates
                res = {"validated": False, "status": f"inconclusive: {type(exc).__name__}"}
        self._cf[key] = res
        return res

    def _validated(self, item: dict) -> list[str]:
        from .validation import independent
        return independent(item, self.trust, {item.get("id"): bool((item.get("counterfactual") or {}).get("validated"))})

    def learn(self, task, repo_version, run, transcript, diff, candidates=None):
        self._run_ctx = {"task": task, "task_id": task.id, "workspace": run.get("_workspace")}
        try:
            return super().learn(task, repo_version, run, transcript, diff, candidates)
        finally:
            self._run_ctx = None

    def _admit_after_review(self, review, task, repo_version, run, cand, changed) -> bool:
        ev = self._evidence(task, repo_version, run, cand, changed)
        cf = self._counterfactual(cand, ev)
        probe = {"id": "probe", "title": cand.get("title"), "content": cand.get("content"), "evidence": [ev], "counterfactual": cf,
                 "source": {"task_id": task.id, "review_comments": run["attempts"][0]["review_comments"],
                            "references": ev["source"]["references"]}}
        ind = self._validated(probe)
        verdict = review["verdict"]
        cites = {"code" if c["source_id"].startswith("code:") else "other" for c in review.get("conflicts") or []}
        if verdict == "conflict" and cites == {"code"}:
            verdict = "uncertain"
        if verdict == "approved":
            return True
        if verdict == "conflict":
            return bool({"policy", "reviewer"} & set(ind))
        risky = HIGH_RISK.search(f"{cand.get('title') or ''} {cand.get('content') or ''}")
        return not risky or bool(ind)

    def _admit(self, task, repo_version, run, cand, changed):
        events = super()._admit(task, repo_version, run, cand, changed)
        ev = self._evidence(task, repo_version, run, cand, changed)
        cf = self._counterfactual(cand, ev)
        for e in list(events):
            if e["type"] == "add":
                events.append(self.store.append("update", id=e["item"]["id"], fields={"counterfactual": cf},
                                                reason=f"counterfactual check: {cf['status']}"))
        return events


def three_state(*, policy: bool, counterfactual: dict | None, code: dict, reviewer: bool, repeated: bool,
                review: dict | None = None) -> dict:
    """D60: Approved / Rejected / Uncertain. Uncertain is never turned into Approved for convenience.

    counter-evidence  a team code check the change violates; a cited conflict with an existing rule or the
                      CHANGELOG (a conflict citing only code is a clue, D57 R1); the advice failing the tests
    hard evidence     a registered policy; a counterfactual test; a team code check that supports the note
    soft evidence     a trusted reviewer; repetition with different quotes
    Rejected  counter-evidence and no hard evidence
    Approved  no counter-evidence, and hard evidence or two kinds of soft evidence
    Uncertain everything else, including a trusted reviewer alone and counter-evidence against hard evidence:
              a person decides"""
    cf = counterfactual or {}
    cites = {"code" if c["source_id"].startswith("code:") else "rule" for c in (review or {}).get("conflicts") or []}
    counter = list(code.get("violations") or [])
    if (review or {}).get("verdict") == "conflict" and "rule" in cites:
        counter.append("conflict with " + ", ".join(sorted(c["source_id"] for c in review["conflicts"] if not c["source_id"].startswith("code:"))))
    if str(cf.get("status", "")).startswith("invalid"):
        counter.append("the advice fails the tests")
    # routing: a code-implementation convention is verified by the team's code checks, not by tests (a
    # behaviourally equivalent violation passes every test); a business rule by the counterfactual test
    test_counts = cf.get("validated") and not code.get("code_convention")
    hard = (["policy"] if policy else []) + (["test"] if test_counts else []) + [f"code check {c}" for c in code.get("supports") or []]
    soft = (["trusted reviewer"] if reviewer else []) + (["repeated"] if repeated else [])
    if counter and not hard:
        state = "rejected"
    elif not counter and (hard or len(soft) >= 2):
        state = "approved"
    else:
        state = "uncertain"
    return {"state": state, "counter": counter, "hard": hard, "soft": soft}


class SecureMemoryV4(SecureMemoryV31):
    """Three states (D60): approved notes are rules; uncertain ones wait for a person (shown, marked
    unconfirmed, only in their own files); rejected ones are never shown. Business rules are verified by the
    counterfactual test, code conventions by the team's code checks."""

    def __init__(self, store_dir, trust: admission.Trust | None = None, **kw):
        super().__init__(store_dir, trust=trust, **kw)
        self.name = "attest_secure_v4"

    def _assess(self, cand, ev, run, task, review, diff_text) -> dict:
        from . import codechecks
        from .validation import independent
        text = f"{cand.get('title') or ''} {cand.get('content') or ''}"
        cf = self._counterfactual(cand, ev)
        probe = {"id": "probe", "title": cand.get("title"), "content": cand.get("content"), "evidence": [ev],
                 "source": {"task_id": task.id, "review_comments": run["attempts"][0]["review_comments"], "references": ev["source"]["references"]}}
        ind = independent(probe, self.trust)
        return three_state(policy="policy" in ind, counterfactual=cf, code=codechecks.run(task.repo, text, (ev.get("applied") or {}).get("line") or ""),
                           reviewer="reviewer" in ind, repeated="repeated" in ind, review=review)

    def learn(self, task, repo_version, run, transcript, diff, candidates=None):
        self._diff_text = diff
        return super().learn(task, repo_version, run, transcript, diff, candidates)

    def _admit_after_review(self, review, task, repo_version, run, cand, changed) -> bool:
        ev = self._evidence(task, repo_version, run, cand, changed)
        a = self._assess(cand, ev, run, task, review, getattr(self, "_diff_text", ""))
        self._last_assessment = a
        return a["state"] != "rejected" and not (a["state"] == "uncertain" and review.get("verdict") == "conflict" and a["counter"])

    def _admit(self, task, repo_version, run, cand, changed):
        events = super()._admit(task, repo_version, run, cand, changed)
        a = getattr(self, "_last_assessment", None)
        if a:
            for e in list(events):
                iid = e["item"]["id"] if e["type"] == "add" else None
                if iid:
                    events.append(self.store.append("update", id=iid, fields={"assessment": a},
                                                    reason=f"three-state assessment: {a['state']}"))
        return events

    def _validated(self, item: dict) -> list[str]:
        a = item.get("assessment")
        if a is None:
            return super()._validated(item)
        return a["hard"] + a["soft"] if a["state"] == "approved" else []


class TieredMemory(SecureMemoryV4):
    """v4 with one of the crowding-ablation injection policies (D64): arm "A", "B", "C" or "D" (see tiers.py)."""

    def __init__(self, store_dir, arm: str, trust: admission.Trust | None = None, **kw):
        super().__init__(store_dir, trust=trust, **kw)
        assert arm in "ABCD", arm
        self.arm = arm
        self.name = f"attest_v4_{arm}"
        if arm == "D":
            from .tiers import MAX_K
            self.max_shown = MAX_K

    def ranking(self, task, k=6, version=None):
        from .tiers import CORE_K, REL_FRACTION, tier
        if self.arm == "A":
            return super().ranking(task, k, version)
        items = self.store.items()
        scored, ms = timed_rank("lexical", f"{task.title} {task.issue}", self.candidates(task, version), None)
        if self.arm == "B":
            ranked = sorted(scored, key=lambda x: (-x[1], x[0]))
        elif self.arm == "C":
            ranked = sorted(scored, key=lambda x: (0 if x[1] > 0 and tier(items[x[0]]) == "core" else 1, -x[1], x[0]))
        else:  # D: tiers + dynamic k, no filler
            by = {t: [(i, sc) for i, sc in sorted(scored, key=lambda x: (-x[1], x[0])) if tier(items[i]) == t and sc > 0]
                  for t in ("core", "regular", "candidate")}
            core = by["core"][:CORE_K]
            best = max([sc for _, sc in by["regular"] + by["candidate"]] or [0])
            rest = [(i, sc) for i, sc in by["regular"] + by["candidate"] if sc >= REL_FRACTION * best]
            rest.sort(key=lambda x: (0 if tier(items[x[0]]) == "regular" else 1, -x[1], x[0]))
            ranked = core + rest
        return (ranked if k is None else ranked[:k]), ms
