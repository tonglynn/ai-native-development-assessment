"""Extension task X01 (business step 6: provider timeouts and retries), end to end (exploratory).

Question: does experience learned at step 2 (C5, idempotent requests, taught by E04 and E06)
carry over to step 6, where a provider timeout must be retried with the same idempotency key
(C7, which no learning task teaches)? benchmark/extension/author_x01.py describes the task.

Arms: no memory, ReasoningBank-style, ACE-style and Attest, each with its own memory after the
learning phase of the main experiment (repetitions 1-3), memory not updated; each memory state
runs twice, so 6 runs per arm, 24 runs, deepseek-flash as in the main experiment.

Measures: first-attempt pass rate; per convention, the share of runs whose first attempt
meets it (C2, C4, C5, C7); whether the injected notes mention idempotency.
Reading rule, fixed before running: the primary measure is C7 (transfer to step 6) for Attest
against no memory; C4 and C5 are secondary (they replicate the held-out benefit on a new
module). 6 runs per arm show a direction only; no interval is claimed.

Usage: python scripts/x01_eval.py --out runs/x01 --parallel 6
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_task  # noqa: E402
from attest.memory import make_memory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

ARMS = ("no_memory", "reasoningbank", "ace", "attest")
CONVS = ("C2", "C4", "C5", "C7")


def run_one(out: Path, arm: str, rep: int, k: int) -> dict:
    task = load_task("X01")
    base = out / arm / f"r{rep}_{k}"
    memory = make_memory(arm, None if arm == "no_memory" else base / "memory")
    if arm != "no_memory" and not memory.store.items():
        for i, it in sorted(json.loads((ROOT / f"runs/main/{arm}/r{rep}/memory/after_learn.json").read_text()).items()):
            memory.store.append("add", item=it, reason="main experiment after learning")
    r = run_task(task, memory, base / "X01", settings=Settings(), update_memory=False)
    a = r["attempts"][0]
    row = {"arm": arm, "rep": rep, "run": k, "first_pass": r["first_pass"], "final_pass": r["final_pass"], "crashed": a["crashed"],
           "conv_failed": a["conv_failed"], "func_failed": a["func_failed"], "injected": r.get("shown_notes") or [],
           "notes_mention_idempotency": "idempot" in (r.get("notes_context") or "").lower()}
    print(json.dumps(row), flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--parallel", type=int, default=6)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(a, rep, k) for a in ARMS for rep in (1, 2, 3) for k in (1, 2)]
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        rows = list(pool.map(lambda j: run_one(args.out, *j), jobs))
    summary = []
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm and not r["crashed"]]
        n = len(rs) or 1
        summary.append({"arm": arm, "runs": len(rs), "crashed": sum(r["crashed"] for r in rows if r["arm"] == arm),
                        "pass@1": sum(r["first_pass"] for r in rs) / n,
                        **{f"{c}_met": sum(c not in r["conv_failed"] for r in rs) / n for c in CONVS},
                        "func_failed_runs": sum(bool(r["func_failed"]) for r in rs)})
    (args.out / "results.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2) + "\n")
    pct = lambda x: f"{x:.0%}"  # noqa: E731
    lines = ["# X01: refunds through the payment provider, timeouts and retries (exploratory)", "",
             "First attempt; each arm's memory after the main experiment's learning phase; 3 memory states x 2 runs.", "",
             "| Arm | Runs | pass@1 | C2 met | C4 met | C5 met | **C7 met** (not taught) | Runs failing behaviour tests | Crashed |",
             "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['arm']} | {s['runs']} | {pct(s['pass@1'])} | {pct(s['C2_met'])} | {pct(s['C4_met'])} | {pct(s['C5_met'])} | "
              f"**{pct(s['C7_met'])}** | {s['func_failed_runs']} | {s['crashed']} |" for s in summary]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
