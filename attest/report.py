"""Builds the static HTML results report from a runs/<experiment> directory.

    python -m attest.report runs/main report/index.html

Everything shown comes from files in the experiment directory: result.json,
trajectories, final diffs and each memory store's event log. The page embeds
that data as JSON and renders it in the browser; it needs no server.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from . import analysis
from .benchmark import PROJECT_ROOT, load_task

TEMPLATE = Path(__file__).with_name("report_template.html")
NOTES_RE = re.compile(r"## Notes from earlier work\n(.*?)(?:\n## |\Z)", re.S)


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT,
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n… [{len(text) - limit} more characters in the repository]"


def _run_record(path: Path, root: Path) -> dict:
    r = json.loads(path.read_text())
    run_dir = path.parent
    notes, commands = "", []
    for traj_path in sorted(run_dir.glob("attempt*.traj.json")):
        attempt = int(traj_path.name[len("attempt")].strip() or 1)
        messages = json.loads(traj_path.read_text()).get("messages", [])
        if attempt == 1 and len(messages) > 1:
            m = NOTES_RE.search(str(messages[1].get("content", "")))
            notes = m.group(1).strip() if m else ""
        for msg in messages:
            if msg.get("role") == "assistant":
                for action in msg.get("extra", {}).get("actions", []):
                    commands.append({"attempt": attempt, "cmd": _clip(action.get("command", ""), 700)})
    diff_path = run_dir / "final.diff"
    task = load_task(r["task_id"])
    return {
        "key": str(run_dir.relative_to(root)),
        "condition": r["condition"],
        "rep": r.get("rep", 1),
        "task": r["task_id"],
        "title": task.title,
        "issue": task.issue,
        "group": r["group"],
        "phase": r.get("phase", ""),
        "conventions": r.get("conventions", []),
        "repo_version": r.get("repo_version", ""),
        "first_pass": r["first_pass"],
        "final_pass": r["final_pass"],
        "steps": r["steps"],
        "cost": r["cost_usd"],
        "seconds": r.get("seconds", 0),
        "shown": r["shown_notes"],
        "cited": r["cited_notes"],
        "leaks": r.get("leaks", []),
        "notes": notes,
        "attempts": [
            {k: a.get(k) for k in ("n", "exit_status", "crashed", "steps", "passed", "public_passed",
                                   "func_failed", "conv_failed", "review_comments", "cited")}
            for a in r["attempts"]
        ],
        "memory_events": [
            {"type": e["type"], "id": e.get("id") or (e.get("item") or {}).get("id"), "reason": e.get("reason", "")}
            for e in r.get("memory_events", [])
            if e["type"] != "update" or set((e.get("fields") or {})) - {"usage"}
        ],
        "commands": commands[:60],
        "diff": _clip(diff_path.read_text(), 6000) if diff_path.exists() else "",
    }


def _ledgers(root: Path) -> list[dict]:
    out = []
    for events_path in sorted(root.glob("*/r*/memory/events.jsonl")):
        events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
        items: dict[str, dict] = {}
        history: dict[str, list] = {}
        rejected = []
        for e in events:
            if e["type"] == "add":
                items[e["item"]["id"]] = dict(e["item"])
                history.setdefault(e["item"]["id"], []).append({"seq": e["seq"], "what": "added", "reason": e.get("reason", "")})
            elif e["type"] == "update" and e["id"] in items:
                items[e["id"]].update(e["fields"])
                if set(e["fields"]) - {"usage"}:
                    history.setdefault(e["id"], []).append({"seq": e["seq"], "what": "changed", "reason": e.get("reason", "")})
            elif e["type"] == "reject":
                cand = e.get("candidate")
                rejected.append({"task": e.get("task_id"), "reason": e.get("reason", ""),
                                 "content": cand.get("content", "") if isinstance(cand, dict) else ""})
        condition, rep = events_path.parts[-4], events_path.parts[-3]
        out.append({
            "condition": condition,
            "rep": int(rep[1:]) if rep[1:].isdigit() else rep,
            "items": [dict(it, history=history.get(i, [])) for i, it in items.items()],
            "rejected": rejected,
            "events": len(events),
        })
    return out


def _hypotheses(summary: dict) -> list[dict]:
    rows = {(h["condition"], h["group"]): h for h in summary["headline"]}

    def p1(cond, group):
        row = rows.get((cond, group))
        return None if row is None else row["pass1"]

    def fmt(x):
        return "n/a" if x is None else f"{x:.0%}"

    regress = {}
    for r in summary["regressions"]:
        if r["task_id"][0] in "HB":
            regress[r["condition"]] = regress.get(r["condition"], 0) + 1
    contamination = {c["condition"]: c for c in summary["contamination"]}

    def verdict(ok):
        return "insufficient" if ok is None else ("supported" if ok else "not supported")

    a, n = p1("attest", "heldout"), p1("no_memory", "heldout")
    h1 = None if a is None or n is None else a > n
    ab, nb = p1("attest", "control"), p1("no_memory", "control")
    foreign = contamination.get("attest", {}).get("foreign_notes_shown")
    h2 = None if ab is None or nb is None or foreign is None else (foreign == 0 and ab >= nb)
    as_, ns = p1("attest", "stale"), p1("no_memory", "stale")
    h3 = None if as_ is None or ns is None else as_ >= ns
    rb, ace = p1("reasoningbank", "heldout"), p1("ace", "heldout")
    h4 = None if None in (a, rb, ace) else (a >= rb and a >= ace and all(
        regress.get("attest", 0) <= regress.get(c, 0) for c in ("reasoningbank", "ace")))
    return [
        {"id": "H1", "claim": "Attest improves held-out tasks", "verdict": verdict(h1),
         "evidence": f"pass@1 on H: attest {fmt(a)} vs no memory {fmt(n)}"},
        {"id": "H2", "claim": "Attest does not leak across repositories", "verdict": verdict(h2),
         "evidence": f"ledgerly notes shown on simkit: {foreign if foreign is not None else 'n/a'}; pass@1 on B: attest {fmt(ab)} vs no memory {fmt(nb)}"},
        {"id": "H3", "claim": "Outdated experience does not make Attest worse than none", "verdict": verdict(h3),
         "evidence": f"pass@1 on S: attest {fmt(as_)} vs no memory {fmt(ns)}"},
        {"id": "H4", "claim": "Attest is at least as good as published designs, with fewer regressions", "verdict": verdict(h4),
         "evidence": f"pass@1 on H: attest {fmt(a)}, ReasoningBank {fmt(rb)}, ACE {fmt(ace)}; "
                     f"H/B regressions: attest {regress.get('attest', 0)}, ReasoningBank {regress.get('reasoningbank', 0)}, ACE {regress.get('ace', 0)}"},
    ]


def build(root: Path, out: Path) -> Path:
    root = root.resolve()
    summary = analysis.summarise(root)
    runs = [_run_record(p, root) for p in sorted(root.rglob("result.json"))]
    models = sorted({json.loads(p.read_text()).get("model", "") for p in root.rglob("result.json")})
    data = {
        "meta": {
            "experiment": root.name,
            "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
            "commit": _git_commit(),
            "models": models,
            "runs": summary["runs"],
            "excluded": summary["excluded_for_leaks"],
            "cost": summary["total_cost_usd"],
            "reps": sorted({r["rep"] for r in runs}),
            "conditions": sorted({r["condition"] for r in runs}, key=lambda c: analysis.CONDITIONS.index(c) if c in analysis.CONDITIONS else 99),
        },
        "hypotheses": _hypotheses(summary),
        "summary": summary,
        "ledgers": _ledgers(root),
        "runs": runs,
    }
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.read_text().replace("__DATA__", payload))
    return out


if __name__ == "__main__":
    target = build(Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else "report/index.html"))
    print(f"wrote {target} ({target.stat().st_size // 1024} KB)")
