"""Human review of uncertain notes, as part of the memory's lifecycle (D62). Human-only: not exposed via MCP.

    new experience -> automatic evidence check (v4) -> uncertain -> review queue -> a business owner decides
        -> approved: a rule in long-term memory          -> rejected: retired, kept in the log
    later: a policy the approval relied on changes      -> the note goes back to uncertain, for a person again

Every decision records who decided, why, which evidence they relied on, and the repository and versions it
applies to. Rules: only a registered approver may decide; an agent identity ("agent:..."), and whoever
proposed the note, may not decide on it; only uncertain or held notes can be decided.
"""

from __future__ import annotations

import re
import time

QUEUE_STATES = ("uncertain",)
HELD = ("conflict", "pending_review")
POLICY_RE = re.compile(r"\b(?:FIN|POL|SEC|INC)-[\w-]+\b")


class ReviewRefused(PermissionError):
    pass


def queue(memory) -> list[dict]:
    """What waits for a person: uncertain notes (kept, never rules) and notes held by the reviewer."""
    out = []
    for i, it in sorted(memory.store.items().items()):
        a = it.get("assessment") or {}
        if (it["status"] in ("active", "suspect") and a.get("state") in QUEUE_STATES) or it["status"] in HELD:
            out.append({"id": i, "title": it["title"], "content": it["content"], "status": it["status"],
                        "state": a.get("state", it["status"]), "counter": a.get("counter", []), "hard": a.get("hard", []),
                        "soft": a.get("soft", []), "scope": it.get("scope"), "learned_in": (it.get("source") or {}).get("task_id"),
                        "evidence": [{"task": e.get("task_id"), "quote": (e.get("source") or {}).get("quote"),
                                      "applied": (e.get("applied") or {}).get("line")} for e in it.get("evidence") or []]})
    return out


def _check(memory, item_id: str, by: str, approvers) -> dict:
    items = memory.store.items()
    if item_id not in items:
        raise KeyError(item_id)
    it = items[item_id]
    if not by or by.startswith("agent:") or by == (it.get("source") or {}).get("proposed_by"):
        raise ReviewRefused(f"{by!r} may not decide on {item_id}: agents and the note's proposer cannot approve it")
    if by not in set(approvers or ()):
        raise ReviewRefused(f"{by!r} is not a registered approver")
    a = it.get("assessment") or {}
    if not ((it["status"] in ("active", "suspect") and a.get("state") in QUEUE_STATES) or it["status"] in HELD):
        raise ValueError(f"{item_id} is not waiting for review")
    return it


def approve(memory, item_id: str, *, by: str, reason: str, evidence: list[str], approvers, scope: dict | None = None) -> dict:
    """A person approves: the note becomes a rule, with the review recorded and its policy dependencies kept."""
    it = _check(memory, item_id, by, approvers)
    if not evidence:
        raise ValueError("say which evidence the approval relies on")
    a = dict(it.get("assessment") or {"counter": [], "hard": [], "soft": []})
    record = {"decision": "approved", "by": by, "at": round(time.time(), 3), "reason": reason, "evidence": list(evidence),
              "scope": dict(it.get("scope") or {}, **(scope or {})), "depends_on": sorted(set(POLICY_RE.findall(" ".join(evidence) + " " + reason)))}
    a.update(state="approved", hard=list(a.get("hard") or []) + [f"human review by {by}"])
    fields = {"status": "active", "assessment": a, "observed_only": False, "review": record, "scope": record["scope"]}
    return memory.store.append("update", id=item_id, fields=fields, reason=f"approved by {by}: {reason}")


def reject(memory, item_id: str, *, by: str, reason: str, approvers) -> dict:
    it = _check(memory, item_id, by, approvers)
    a = dict(it.get("assessment") or {}, state="rejected")
    record = {"decision": "rejected", "by": by, "at": round(time.time(), 3), "reason": reason}
    return memory.store.append("update", id=item_id, fields={"status": "retired", "retracted_by": by, "assessment": a, "review": record},
                               reason=f"rejected by {by}: {reason}")


def policy_changed(memory, policy_id: str, *, by: str, reason: str) -> list[dict]:
    """A policy changed: notes whose human approval relied on it go back to uncertain, for a person again."""
    events = []
    for i, it in memory.store.items().items():
        rv = it.get("review") or {}
        if rv.get("decision") == "approved" and policy_id in (rv.get("depends_on") or []) and it["status"] in ("active", "suspect"):
            a = dict(it.get("assessment") or {}, state="uncertain",
                     hard=[h for h in (it.get("assessment") or {}).get("hard", []) if not h.startswith("human review")])
            events.append(memory.store.append("update", id=i, fields={"assessment": a, "review": dict(rv, superseded_by=policy_id),
                                                                       "observed_only": True},
                                              reason=f"{policy_id} changed ({reason}; recorded by {by}): back to review"))
    return events
