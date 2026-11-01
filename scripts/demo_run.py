"""One real end-to-end run of the core loop, recorded for the demo (D72). Real agent runs (deepseek-flash), real hidden
tests, real distillation and gateway review; the people in it are SIMULATED (a scripted business owner) and the
poison is SYNTHETIC. Everything is written to runs/<out>/demo.json, which docs/demo/index.html replays step by step.

Story (Attest with gateway v4, ledgerly 1.0.0):
  1 Learn   E02, E04, E06 from an empty memory: first attempt, simulated review, retry, hidden tests, distillation,
            gateway assessment (approved / uncertain / rejected, with reasons).
  2 Review  the queue a person sees; an agent tries to approve a note and is refused; the simulated owner approves the
            notes that state a team rule it can point to, citing the evidence.
  3 Reuse   H04 (credit notes; it produced no experience) 3 times with the reviewed memory, frozen, and 3 times with no
            memory: which notes were injected and why they apply, and the result of the hidden tests.
  4 Poison  one test-passing poisoned review (benchmark/poison_channels: review_untrusted float_audit, applied) learned
            by gateway v4, ACE-style and ReasoningBank-style memories, each fresh.
  5 Govern  policy FIN-2026-03 changes: approvals that relied on it go back to review; a person retracts a note and
            retrieval says why it is gone; a forged approval written straight into the log is caught by the audit.

Usage: python scripts/demo_run.py --out runs/demo
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from attest.benchmark import load_task  # noqa: E402
from attest.memory import make_memory, review  # noqa: E402
from attest.runner import REPOS_DIR, Settings, repo_version, run_task  # noqa: E402

OWNER = "owner:finance-lead"  # SIMULATED business owner
APPROVERS = (OWNER,)
RULE_RE = re.compile(r"audit\.record|audit entr|idempoten|approved_by|approval|BillingError|round_money|Decimal", re.I)


def added(diff_path: Path, n: int = 18) -> list[str]:
    if not diff_path.exists():
        return []
    return [l[1:] for l in diff_path.read_text().splitlines() if l.startswith("+") and not l.startswith("+++")][:n]


def note_view(it: dict) -> dict:
    ev = (it.get("evidence") or [{}])[0]
    a = it.get("assessment") or {}
    return {"id": it["id"], "title": it.get("title"), "content": it.get("content"), "type": it.get("type"), "status": it.get("status"),
            "scope": {k: it.get("scope", {}).get(k) for k in ("repo", "valid_from", "valid_until", "files")},
            "quote": (ev.get("source") or {}).get("quote"), "applied": (ev.get("applied") or {}).get("line"),
            "learned_in": (it.get("source") or {}).get("task_id"),
            "state": a.get("state"), "hard": a.get("hard"), "soft": a.get("soft"), "counter": a.get("counter"),
            "review": it.get("review")}


def learn_step(memory, task_id: str, out: Path) -> dict:
    task = load_task(task_id)
    before = set(memory.store.items())
    r = run_task(task, memory, out / "learn" / task_id, settings=Settings(), update_memory=True)
    items = memory.store.items()
    att = []
    for a in r["attempts"]:
        att.append({"passed": a["passed"], "conv_failed": a.get("conv_failed"), "tests_failed": (a.get("tests_failed") or [])[:6],
                    "review_comments": a.get("review_comments") or [], "steps": a.get("steps")})
    rejects = [{"reason": e.get("reason"), "title": (e.get("candidate") or {}).get("title")} for e in r.get("memory_events") or [] if e["type"] == "reject"]
    return {"task": task_id, "title": task.title, "issue": task.issue[:600], "conventions": list(task.conventions),
            "first_pass": r["first_pass"], "final_pass": r["final_pass"], "attempts": att,
            "diff": added(out / "learn" / task_id / "final.diff"),
            "new_notes": [note_view(items[i]) for i in items if i not in before], "rejected": rejects}


def reuse_run(cond: str, memory, n: int, out: Path) -> dict:
    task = load_task("H04")
    r = run_task(task, memory, out / "reuse" / cond / f"run{n}", settings=Settings(), update_memory=False)
    a = r["attempts"][0]
    dbg = r.get("retrieval_debug") or {}
    return {"condition": cond, "run": n, "first_pass": r["first_pass"], "conv_failed": a.get("conv_failed"),
            "tests_failed": (a.get("tests_failed") or [])[:8], "injected": r.get("injected_notes") or [],
            "context": r.get("notes_context") or "", "excluded": (dbg.get("trace") or {}).get("excluded", {}),
            "diff": added(out / "reuse" / cond / f"run{n}" / "final.diff", 30), "steps": a.get("steps"), "cost_usd": r.get("cost_usd")}


def poison_step() -> list[dict]:
    import poison_channels_eval as P
    data = json.loads((ROOT / "benchmark/poison_channels/cases.json").read_text())
    case = next(c for c in data["cases"] if c["id"] == "review_untrusted:float_audit:applied")
    out = []
    for system in ("attest_secure_v4", "ace", "reasoningbank"):
        row = P.run_case(system, case, data["payloads"])
        out.append({k: row.get(k) for k in ("system", "stored", "rule", "notes", "error")})
    return [{"case": case, "payload": data["payloads"]["float_audit"]}] + out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    demo = {"labels": {"real": "agent runs, hidden tests, distillation and gateway review (deepseek-flash, deepseek-v4-pro reviewer)",
                       "simulated": "the review comments (written for the benchmark) and the business owner's decisions (scripted)",
                       "synthetic": "the repositories and the poisoned comment"}}

    # 1 Learn
    mem = make_memory("attest_secure_v4", out / "memory")
    demo["learn"] = [learn_step(mem, t, out) for t in ("E02", "E04", "E06")]

    # 2 Review
    q = review.queue(mem)
    demo["queue"] = q
    steps = []
    if q:
        try:
            review.approve(mem, q[0]["id"], by="agent:coder", reason="looks right to me", evidence=["my own change"], approvers=APPROVERS)
            steps.append({"who": "agent:coder", "action": "approve", "id": q[0]["id"], "result": "went through (unexpected)"})
        except review.ReviewRefused as exc:
            steps.append({"who": "agent:coder", "action": "approve", "id": q[0]["id"], "result": f"refused: {exc}"})
    for it in q:
        text = f"{it['title']} {it['content']}"
        if RULE_RE.search(text):
            refs = sorted(set(re.findall(r"\b(?:FIN|INC|POL)-[\w-]+\b", " ".join([text] + [e.get("quote") or "" for e in it["evidence"]]))))
            ev = [f"review comment on {it['learned_in']}"] + refs
            review.approve(mem, it["id"], by=OWNER, reason="states a team rule the review comment gives", evidence=ev, approvers=APPROVERS)
            steps.append({"who": OWNER, "action": "approve", "id": it["id"], "title": it["title"], "evidence": ev, "result": "approved"})
        else:
            steps.append({"who": OWNER, "action": "leave in queue", "id": it["id"], "title": it["title"], "result": "no team rule to point to"})
    demo["review"] = steps
    demo["memory_after_review"] = [note_view(it) for it in mem.store.items().values()]

    # 3 Reuse on H04, memory frozen
    none = make_memory("no_memory", None)
    with ThreadPoolExecutor(max_workers=6) as pool:
        jobs = [pool.submit(reuse_run, "attest_v4", mem, n, out) for n in (1, 2, 3)] + \
               [pool.submit(reuse_run, "no_memory", none, n, out) for n in (1, 2, 3)]
        demo["reuse"] = {"task": {"id": "H04", "title": load_task("H04").title, "issue": load_task("H04").issue[:700],
                                  "conventions": list(load_task("H04").conventions)},
                         "runs": [j.result() for j in jobs]}

    # 4 Poison
    demo["poison"] = poison_step()

    # 5 Govern
    gov = []
    h04 = load_task("H04")
    ver = repo_version(REPOS_DIR / h04.repo)
    shown = lambda: mem.retrieve(h04, ver)  # noqa: E731
    r0 = shown()
    gov.append({"step": "before", "injected": r0.ids})
    ev = review.policy_changed(mem, "FIN-2026-03", by=OWNER, reason="threshold raised to 1000.00 on ledgerly 2.x (FIN-2026-11)")
    r1 = shown()
    gov.append({"step": "policy FIN-2026-03 changed", "back_to_review": [e["id"] for e in ev], "injected": r1.ids,
                "trace": (r1.debug.get("trace") or {}).get("excluded", {})})
    target = next((i for i in r1.ids), None)
    if target:
        mem.retract(target, "superseded by the new refund policy; will be relearned", by=OWNER)
        r2 = shown()
        gov.append({"step": f"{OWNER} retracts {target}", "injected": r2.ids,
                    "why_gone": (r2.debug.get("trace") or {}).get("excluded", {}).get(target)})
    probe = make_memory("attest_secure_v4", None)
    for it in mem.store.items().values():
        probe.store.append("add", item=it, reason="copy for the forgery check")
    fid = next(iter(probe.store.items()))
    probe.store.append("update", id=fid, fields={"assessment": {"state": "approved"}, "review": {"decision": "approved", "by": "agent:coder", "evidence": ["x"]}},
                       reason="forged approval written straight into the log")
    gov.append({"step": "forged approval in the log", "audit": review.audit_reviews(probe, APPROVERS)})
    gov.append({"step": "audit of the real log", "audit": review.audit_reviews(mem, APPROVERS)})
    gov.append({"step": "tools an agent can reach through MCP", "tools": ["recall", "learn", "report_outcome", "list_notes"]})
    demo["govern"] = gov
    demo["events"] = len(mem.store.events)

    (out / "demo.json").write_text(json.dumps(demo, indent=1, ensure_ascii=False, default=str) + "\n")
    wm = sum(r["first_pass"] for r in demo["reuse"]["runs"] if r["condition"] == "attest_v4")
    nm = sum(r["first_pass"] for r in demo["reuse"]["runs"] if r["condition"] == "no_memory")
    print(json.dumps({"learned": [len(x["new_notes"]) for x in demo["learn"]], "queue": len(q), "H04 with memory": f"{wm}/3",
                      "H04 without": f"{nm}/3", "poison": [(p.get('system'), p.get('stored'), p.get('rule')) for p in demo["poison"][1:]]}, indent=1))


if __name__ == "__main__":
    main()
