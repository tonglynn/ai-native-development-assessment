"""Just-in-time verification at retrieval, end to end on the stale tasks (exploratory).

After GitHub Copilot's agentic memory: before a note is injected, check it against the
checkout (attest/memory/verify.py). Offline, the injected context is byte-identical to plain
Attest on every experience, held-out and control task (18/18, 33/33, 9/9 task runs with the
main-experiment memories), so only the stale tasks (ledgerly 2.0.0) can change; only they run.

Arms, each with Attest's memory after the learning phase of the main experiment (repetitions
1-3), memory not updated: plain Attest · annotate (drifted and review notes get a "check before
use" line) · drop (drifted notes excluded, review notes annotated). 5 stale tasks x 3
repetitions x 3 arms = 45 runs, deepseek-flash as in the main experiment.

Measures: first-attempt pass rate; on S01-S03 any C1 failure (applying the old half-up rule);
on S04-S05 approvals wrongly demanded for legitimate amounts (test_conv_c6_allows_*) and
unapproved amounts let through (test_conv_c6_blocks_*).
Reading rule, fixed before running: verification is kept as an option if pass@1 is not lower
than plain Attest and neither C1 failures nor wrongly demanded approvals rise. 15 runs per arm
show a direction, not an effect size.

Usage: python scripts/verify_eval.py --out runs/verify_eval --reps 3 --parallel 6
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_tasks  # noqa: E402
from attest.memory.earned import EarnedMemory  # noqa: E402
from attest.memory.verify import VerifiedMemory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

ARMS = ("plain", "annotate", "drop")


def make(arm: str, store: Path):
    return EarnedMemory(store) if arm == "plain" else VerifiedMemory(store, mode=arm)


def run_arm(out: Path, arm: str, rep: int) -> list[dict]:
    memory = make(arm, out / arm / f"r{rep}" / "memory")
    if not memory.store.items():
        for i, it in sorted(json.loads((ROOT / f"runs/main/attest/r{rep}/memory/after_learn.json").read_text()).items()):
            memory.store.append("add", item=it, reason="main experiment after learning")
    rows = []
    for task in load_tasks("stale"):
        r = run_task(task, memory, out / arm / f"r{rep}" / task.id, settings=Settings(), update_memory=False)
        a = r["attempts"][0]
        failed = a.get("tests_failed") or []
        rows.append({"arm": arm, "rep": rep, "task": task.id, "first_pass": r["first_pass"], "crashed": a["crashed"],
                     "conv_failed": a["conv_failed"], "c1_failed": "C1" in a["conv_failed"],
                     "approval_wrongly_demanded": any("c6_allows" in t for t in failed),
                     "unapproved_let_through": any("c6_blocks" in t for t in failed),
                     "verification": (r.get("retrieval_debug") or {}).get("verification")})
        print(json.dumps(rows[-1]), flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(a, r) for a in ARMS for r in range(1, args.reps + 1)]
    rows = []
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for rs in pool.map(lambda j: run_arm(args.out, *j), jobs):
            rows += rs
    summary = []
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        rnd = [r for r in rs if r["task"] in ("S01", "S02", "S03")]
        thr = [r for r in rs if r["task"] in ("S04", "S05")]
        summary.append({"arm": arm, "runs": len(rs), "pass@1": sum(r["first_pass"] for r in rs) / len(rs),
                        "c1_failed": f"{sum(r['c1_failed'] for r in rnd)}/{len(rnd)}",
                        "approval_wrongly_demanded": f"{sum(r['approval_wrongly_demanded'] for r in thr)}/{len(thr)}",
                        "unapproved_let_through": f"{sum(r['unapproved_let_through'] for r in thr)}/{len(thr)}",
                        "crashed": sum(r["crashed"] for r in rs)})
    (args.out / "results.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2) + "\n")
    lines = ["# Just-in-time verification on the stale tasks (exploratory)", "",
             f"Main-experiment Attest memories after learning, {args.reps} repetitions, ledgerly 2.0.0.", "",
             "| Arm | Runs | Stale pass@1 | C1 failed (S01-S03) | Approval wrongly demanded (S04-S05) | Unapproved let through (S04-S05) | Crashed |",
             "|---|---|---|---|---|---|---|"]
    lines += [f"| {s['arm']} | {s['runs']} | {s['pass@1']:.0%} | {s['c1_failed']} | {s['approval_wrongly_demanded']} | "
              f"{s['unapproved_let_through']} | {s['crashed']} |" for s in summary]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
