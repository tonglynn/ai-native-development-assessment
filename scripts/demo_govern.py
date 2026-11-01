"""Governance steps of the demo, offline and deterministic, on the memory the real demo run recorded (D72).

Replays runs/demo/memory/events.jsonl (real learning, real review decisions and the retraction) and then shows a
policy change handled by a person: a new threshold note is approved and SUPERSEDES the old one. The new note is
SIMULATED (it stands for a note learned after FIN-2026-11 raised the threshold); the owner is SIMULATED; every
check and every refusal is the real code. Writes runs/demo/govern_offline.json.

Usage: python scripts/demo_govern.py
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_task  # noqa: E402
from attest.memory import make_memory, review  # noqa: E402
from attest.runner import REPOS_DIR, repo_version  # noqa: E402

OWNER, APPROVERS = "owner:finance-lead", ("owner:finance-lead",)


def refused(fn):
    try:
        fn()
        return "went through (unexpected)"
    except (review.ReviewRefused, ValueError) as exc:
        return f"refused: {exc}"


def main():
    m = make_memory("attest_secure_v4", None)
    for line in (ROOT / "runs/demo/memory/events.jsonl").read_text().splitlines():
        e = json.loads(line)
        m.store.append(e["type"], **{k: v for k, v in e.items() if k not in ("seq", "ts", "type")})
    task = load_task("H04")
    ver = repo_version(REPOS_DIR / task.repo)
    steps = []
    r = m.retrieve(task, ver)
    excl = (r.debug.get("trace") or {}).get("excluded", {})
    steps.append({"step": "memory as recorded (after the real run, including the owner's retraction of at-0004)",
                  "injected": r.ids, "excluded": {k: v for k, v in excl.items() if k == "at-0004"}})
    old = m.store.items()["at-0005"]
    new = copy.deepcopy(old)
    new.update(id="at-0008", title="Refunds above 1000.00 require approved_by",
               content="Since FIN-2026-11, support refunds and credits above 1000.00 need a keyword-only approved_by; otherwise raise "
                       "BillingError(\"approval_required\").",
               assessment={"state": "uncertain", "counter": [], "hard": [], "soft": ["reviewer"]})
    new["source"] = dict(new.get("source") or {}, proposed_by="agent:distiller", task_id="SIMULATED")
    m.store.append("add", item=new, reason="SIMULATED: a note learned after FIN-2026-11 raised the threshold")
    steps.append({"step": "a new threshold note arrives, uncertain, waiting for a person", "queue": [q["id"] for q in review.queue(m)]})
    steps.append({"step": "the agent tries to approve it", "who": "agent:coder",
                  "result": refused(lambda: review.approve(m, "at-0008", by="agent:coder", reason="mine", evidence=["x"], approvers=APPROVERS))})
    steps.append({"step": "the agent tries to supersede the old rule", "who": "agent:coder",
                  "result": refused(lambda: review.supersede(m, "at-0008", ["at-0005"], by="agent:coder", reason="newer", approvers=APPROVERS))})
    review.approve(m, "at-0008", by=OWNER, reason="matches FIN-2026-11", evidence=["FIN-2026-11"], approvers=APPROVERS)
    review.supersede(m, "at-0008", ["at-0005"], by=OWNER, reason="FIN-2026-11 replaces FIN-2026-03", approvers=APPROVERS)
    steps.append({"step": "the owner approves it, citing FIN-2026-11, and records that it supersedes at-0005", "who": OWNER, "result": "approved; at-0005 superseded"})
    r = m.retrieve(task, ver)
    excl = (r.debug.get("trace") or {}).get("excluded", {})
    steps.append({"step": "retrieval for H04 now", "injected": r.ids, "excluded": {k: v for k, v in excl.items() if k in ("at-0004", "at-0005")},
                  "old_still_in_log": any(e["type"] == "add" and e["item"]["id"] == "at-0005" for e in m.store.events)})
    steps.append({"step": "audit of every decision in the log", "audit": review.audit_reviews(m, APPROVERS)})
    out = ROOT / "runs/demo/govern_offline.json"
    out.write_text(json.dumps(steps, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(steps, indent=1, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
