"""Browser engine for the demo (D74). Runs inside Pyodide, in the page, and calls ONLY real Attest functions:
secret scanning, the preregistered write gate (EarnedMemory.learn with a proposed candidate), team code checks,
three-state assessment, retrieval, the review lifecycle, supersession and the decision audit. Nothing here decides
on its own; it only formats what those functions return.

Not run here, because they need things a browser does not have: the agent and the distiller (a language model) and
the counterfactual test (it runs the repository's test suite). For those the page replays recorded results and says so.
sqlite3 is not available in Pyodide; Attest uses it only as an optional storage backend, so a placeholder is installed.
"""

import json
import sys
import types

sys.modules.setdefault("sqlite3", types.ModuleType("sqlite3"))

from attest.benchmark import load_task  # noqa: E402
from attest.memory import codechecks, review  # noqa: E402
from attest.memory.earned import EarnedMemory  # noqa: E402
from attest.memory.evidence import normalise  # noqa: E402
from attest.memory.gateway import three_state  # noqa: E402
from attest.memory.secrets import find_secrets  # noqa: E402

TRUSTED_REVIEWERS = {"tech-lead"}          # who counts as a trusted reviewer in this demo (demo identities)
REGISTERED_POLICIES = {"FIN-2026-03", "FIN-2026-09", "FIN-2026-11", "INC-204"}
APPROVERS = ("owner:finance-lead",)


def check(channel: str, author: str, text: str, applied_line: str) -> str:
    """One proposed piece of experience, from one channel, checked step by step by the real functions."""
    import re
    steps = []
    secrets = find_secrets(text)
    steps.append({"step": "secret scan", "fn": "attest.memory.secrets.find_secrets", "input": text,
                  "output": secrets, "verdict": "block" if secrets else "pass"})
    reviews = [text] if channel == "review" else []
    quote_ok = bool(reviews) and normalise(text) in normalise(reviews[0])
    steps.append({"step": "is it a review comment's own words", "fn": "attest.memory.evidence.normalise",
                  "input": {"channel": channel}, "output": quote_ok,
                  "verdict": "pass" if quote_ok else "weak", "note": "" if quote_ok else "not from a review comment: issue text, docs and tool output are not review"})
    applied = bool(applied_line.strip())
    steps.append({"step": "applied in a change that passed the hidden tests", "fn": "attest.memory.evidence.find_applied",
                  "input": applied_line or "(no line)", "output": applied, "verdict": "pass" if applied else "weak"})
    trusted = author in TRUSTED_REVIEWERS
    policies = sorted(set(re.findall(r"\b(?:FIN|INC|POL|SEC)-[\w-]+\b", text)))
    registered = [p for p in policies if p in REGISTERED_POLICIES]
    steps.append({"step": "who said it", "fn": "attest.memory.admission.Trust", "input": {"author": author, "policy ids": policies},
                  "output": {"trusted reviewer": trusted, "registered policies": registered}, "verdict": "pass" if trusted or registered else "weak"})
    code = codechecks.run("ledgerly_v1", text, applied_line)
    steps.append({"step": "team code checks", "fn": "attest.memory.codechecks.run", "input": applied_line or "(no line)",
                  "output": code, "verdict": "block" if code.get("violations") else "pass" if code.get("supports") else "none"})
    state = three_state(policy=bool(registered), counterfactual=None, code=code, reviewer=trusted, repeated=False)
    if secrets:  # as in the MCP server (D43): a candidate that records a secret is rejected before any other check counts
        state = {**state, "state": "rejected", "counter": ["contains a secret: " + ", ".join(secrets)] + state["counter"]}
    steps.append({"step": "three-state assessment (gateway v4)", "fn": "attest.memory.gateway.three_state",
                  "input": "evidence above; counterfactual test not run in the browser", "output": state, "verdict": state["state"]})
    # The preregistered gate (Attest as evaluated in the main experiment), on the same event
    m = EarnedMemory(None)  # exactly as preregistered: no secret scan, no trust list, no semantic review
    run = {"first_pass": False, "final_pass": True, "attempts": [{"review_comments": reviews, "conv_failed": []}]}
    diff = f"--- a/ledgerly/adjustments.py\n+++ b/ledgerly/adjustments.py\n@@ -1,1 +1,2 @@\n # context\n+{applied_line}\n" if applied else ""
    task = load_task("E04")
    cand = {"kind": "lesson", "type": "code_convention", "title": text[:60], "content": text,
            "evidence_quote": text if channel == "review" else "", "applied_in_diff": applied_line}
    events = m.learn(task, "1.0.0", run, "", diff, candidates=[cand])
    gate = [{"type": e["type"], "reason": e.get("reason", "")} for e in events]
    return json.dumps({"steps": steps, "state": state, "preregistered_gate": gate})


class Governance:
    """The demo run's memory (replayed from its event log), then live review decisions on it."""

    def __init__(self, events_json: str):
        from attest.memory.gateway import SecureMemoryV4
        self.m = SecureMemoryV4(None)
        for e in json.loads(events_json):
            self.m.store.append(e["type"], **{k: v for k, v in e.items() if k not in ("seq", "ts", "type")})
        self.task = load_task("H04")

    def _out(self, ok, msg, **kw):
        return json.dumps({"ok": ok, "message": msg, **kw}, default=str)

    def queue(self):
        return json.dumps(review.queue(self.m), default=str)

    def notes(self):
        return json.dumps(list(self.m.store.items().values()), default=str)

    def approve(self, note_id, who, reason, evidence):
        try:
            review.approve(self.m, note_id, by=who, reason=reason, evidence=[e for e in evidence.split(";") if e.strip()], approvers=APPROVERS)
            return self._out(True, f"approved by {who}")
        except (review.ReviewRefused, ValueError, KeyError) as exc:
            return self._out(False, f"{type(exc).__name__}: {exc}")

    def reject(self, note_id, who, reason):
        try:
            review.reject(self.m, note_id, by=who, reason=reason, approvers=APPROVERS)
            return self._out(True, f"rejected by {who}")
        except (review.ReviewRefused, ValueError, KeyError) as exc:
            return self._out(False, f"{type(exc).__name__}: {exc}")

    def new_threshold_note(self):
        """SIMULATED: the note a task on ledgerly 2.x would teach after FIN-2026-11."""
        import copy
        items = self.m.store.items()
        if "at-0008" in items:
            return self._out(True, "already in the queue")
        new = copy.deepcopy(items["at-0005"])
        new.update(id="at-0008", title="Refunds above 1000.00 require approved_by",
                   content="Since FIN-2026-11, support refunds and credits above 1000.00 need a keyword-only approved_by.",
                   assessment={"state": "uncertain", "counter": [], "hard": [], "soft": ["reviewer"]}, review=None)
        new["source"] = dict(new.get("source") or {}, proposed_by="agent:distiller", task_id="SIMULATED")
        self.m.store.append("add", item=new, reason="SIMULATED: a note learned after FIN-2026-11 raised the threshold")
        return self._out(True, "at-0008 added to the queue (simulated note)")

    def supersede(self, new_id, old_id, who, reason):
        try:
            review.supersede(self.m, new_id, [old_id], by=who, reason=reason, approvers=APPROVERS)
            return self._out(True, f"{old_id} superseded by {new_id}")
        except (review.ReviewRefused, ValueError, KeyError) as exc:
            return self._out(False, f"{type(exc).__name__}: {exc}")

    def policy_changed(self, policy, who, reason):
        ev = review.policy_changed(self.m, policy, by=who, reason=reason)
        return self._out(True, f"{len(ev)} approval(s) that relied on {policy} went back to review", ids=[e["id"] for e in ev])

    def forge(self, note_id, who):
        """Write an approval straight into the log, bypassing review.approve, as an attacker with log access would."""
        self.m.store.append("update", id=note_id, fields={"assessment": {"state": "approved", "hard": [], "soft": []},
                                                          "review": {"decision": "approved", "by": who, "evidence": []}},
                            reason="written straight into the log (forgery test)")
        return self._out(True, "forged approval written to the log")

    def audit(self):
        return json.dumps(review.audit_reviews(self.m, APPROVERS), default=str)

    def retrieve(self):
        r = self.m.retrieve(self.task, "1.0.0")
        return json.dumps({"injected": r.ids, "excluded": (r.debug.get("trace") or {}).get("excluded", {})}, default=str)

    def log(self, n=12):
        return json.dumps([{k: e.get(k) for k in ("seq", "type", "id", "reason")} | {"item": (e.get("item") or {}).get("id")}
                           for e in self.m.store.events[-int(n):]], default=str)
