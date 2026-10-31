"""Memory-to-code impact trace (D55; offline, from stored runs, no model calls).

Quarantining a poison note (D45) stops it being injected again, but code already written under it
stays. Steps, for each repetition of the second poison run (runs/stress_poison_float/attest):
  1. the poison note (as in D45) and the held-out tasks whose injected notes included it
  2. in each such task's final change, the files and added lines that apply it (the marker)
  3. rebuild the task's final workspace (task stub + the stored final diff) and run a regression check:
     the business-policy guard (D38: money written to the audit trail must be Decimal) with the hidden
     tests
  4. a review list: task, file, line, guard result. Nothing is rolled back: a change can mix the
     poison with correct work, so a person decides.
Control: exposed tasks whose diff does not apply the poison, rebuilt and checked the same way.

Reading rule, fixed before running: the trace is useful if every task that applied the poison is on the
list and fails the regression check, and the controls pass it (a regression failure there would be a
false alarm).

Usage: python scripts/impact_trace.py --out runs/impact_trace
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_task, materialize  # noqa: E402
from attest.memory.quarantine import trace  # noqa: E402
from attest.stress import POISON_FLOAT_APPLIED, POISON_FLOAT_NOTE  # noqa: E402
from attest.verify import verify  # noqa: E402

BASE = ROOT / "runs/stress_poison_float/attest"


def rebuild(task_id: str, diff: str, dest: Path) -> bool:
    ws = materialize(load_task(task_id), dest, "stub")
    if not diff.strip():
        return True
    p = subprocess.run(["patch", "-p1", "--forward", "-s"], cwd=ws, input=diff, text=True, capture_output=True)
    return p.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for rep_dir in sorted(BASE.glob("r*")):
        snap = json.loads((rep_dir / "memory/after_learn.json").read_text())
        events = [json.loads(x) for x in (rep_dir / "memory/events.jsonl").read_text().splitlines() if x.strip()]
        pid = next(i for i, it in snap.items() if POISON_FLOAT_NOTE.search(f"{it['title']} {it['content']}"))
        t = trace(events, rep_dir, pid, POISON_FLOAT_APPLIED)
        for tid in [x for x in t["exposed"] if x.startswith("H")]:
            diff = (rep_dir / tid / "final.diff").read_text()
            lines, cur = [], None
            for ln in diff.splitlines():
                if ln.startswith("+++ b/"):
                    cur = ln[6:]
                elif ln.startswith("+") and not ln.startswith("+++") and POISON_FLOAT_APPLIED.search(ln):
                    lines.append(f"{cur}: {ln[1:].strip()}")
            with tempfile.TemporaryDirectory() as tmp:
                ok = rebuild(tid, diff, Path(tmp) / "ws")
                res = verify(Path(tmp) / "ws", load_task(tid), policy_guard=True) if ok else None
            rows.append({"rep": rep_dir.name, "note": pid, "task": tid, "applied_lines": lines, "applied": tid in t["obeyed"],
                         "rebuilt": ok, "guard_failed": None if res is None else any("policy" in h["name"] for h in res["hidden"] if not h["passed"]),
                         "hidden_failed": None if res is None else [h["name"] for h in res["hidden"] if not h["passed"]]})
            print(json.dumps({k: rows[-1][k] for k in ("rep", "task", "applied", "rebuilt", "guard_failed")}), flush=True)
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    app = [r for r in rows if r["applied"]]
    ctl = [r for r in rows if not r["applied"]]
    lines = ["# Memory-to-code impact trace (offline)", "",
             f"Held-out runs that were shown the poison: {len(rows)}; applied it: {len(app)}; rebuilt: {sum(r['rebuilt'] for r in rows)}.",
             f"Regression check (policy guard) failed: {sum(bool(r['guard_failed']) for r in app)}/{len(app)} of the runs that applied it; "
             f"{sum(bool(r['guard_failed']) for r in ctl)}/{len(ctl)} of the exposed runs that did not (false alarms).", "",
             "Review list (no automatic rollback):", "", "| Rep | Task | Poison note | Lines that apply it | Regression check |", "|---|---|---|---|---|"]
    for r in app:
        lines.append(f"| {r['rep']} | {r['task']} | {r['note']} | {'<br>'.join(f'`{x}`' for x in r['applied_lines'])} | "
                     f"{'fails' if r['guard_failed'] else 'passes' if r['rebuilt'] else 'not rebuilt'} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
