"""Same-session comparison of whole pipelines (D65; exploratory).

v3.1 (88% held-out in the gateway run) and "v4 + human review + criticality-first injection" (77% in the crowding
ablation) were measured in different sessions whose baselines differed by 15 points, so they cannot be compared
directly. Here every arm uses the memory its own pipeline learned in the SAME gateway clean-stream run
(runs/stress_gateway/clean, repetitions r1-r3), frozen, and runs the same tasks in the same session:

  attest            Attest's own memory, Attest's retrieval
  v31               gateway v3.1's own memory and retrieval
  v4_review_C       gateway v4's memory after the simulated human review (D63), injected with arm C (D64)

Tasks: held-out (11), stale (5), control (3); 6 runs per arm and task (each memory twice); policy guard on for the
gateway arms as in their runs, off for Attest as in its run.
Reading rule, fixed before running: each arm against the other two on held-out pass@1, paired by task: "better" if
the 95% interval is above 0, "not worse" if its lower bound is above -10 points, otherwise inconclusive.

Usage: python scripts/pipeline_compare.py --out runs/pipeline_compare --parallel 40
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.analysis import paired  # noqa: E402
from attest.benchmark import load_tasks  # noqa: E402
from attest.memory import make_memory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

GW = ROOT / "runs/stress_gateway/clean"
ARMS = {"attest": ("attest", GW / "attest", False), "v31": ("attest_secure_v31", GW / "attest_secure_v31", True),
        "v4_review_C": ("attest_v4_C", ROOT / "runs/review_replay/clean/attest_secure_v4_reviewed", True)}
RUNS = [("r1", 1), ("r2", 1), ("r3", 1), ("r1", 2), ("r2", 2), ("r3", 2)]


def memory(arm: str, src: str, out: Path):
    cond, base, _ = ARMS[arm]
    m = make_memory(cond, out)
    if not m.store.items():
        events = base / src / "memory/events.jsonl"
        for e in (json.loads(x) for x in events.read_text().splitlines() if x.strip()):
            m.store.append(e["type"], **{k: v for k, v in e.items() if k not in ("seq", "ts", "type", "prev", "mac")})
    return m


def one(out: Path, arm: str, src: str, n: int, task) -> dict:
    base = out / arm / f"{src}_{n}"
    m = memory(arm, src, base / "memory")
    r = run_task(task, m, base / task.id, settings=Settings(policy_guard=ARMS[arm][2]), update_memory=False)
    return {"condition": arm, "rep": f"{src}_{n}", "task_id": task.id, "group": task.group, "first_pass": r["first_pass"],
            "crashed": r["attempts"][0]["crashed"], "prompt_tokens": r["attempts"][0]["tokens"]["prompt"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--parallel", type=int, default=40)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks("heldout") + load_tasks("stale") + load_tasks("control")
    jobs = [(arm, src, n, t) for arm in ARMS for src, n in RUNS for t in tasks]
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        runs = list(pool.map(lambda j: one(args.out, *j), jobs))
    ok = [r for r in runs if not r["crashed"]]
    comps = {b: paired(ok, "heldout", baseline=b) for b in ARMS}
    (args.out / "results.json").write_text(json.dumps({"runs": runs, "paired": comps}, indent=2) + "\n")
    rate = lambda a, g: sum(r["first_pass"] for r in ok if r["condition"] == a and r["group"] == g) / max(1, sum(r["condition"] == a and r["group"] == g for r in ok))  # noqa: E731
    lines = ["# Whole pipelines, same session (exploratory)", "", f"{len(runs)} runs, {len(runs) - len(ok)} crashed.", "",
             "| Arm | Held-out pass@1 | Stale | Control | Prompt tokens / run |", "|---|---|---|---|---|"]
    for a in ARMS:
        g = [r for r in ok if r["condition"] == a]
        lines.append(f"| {a} | {rate(a, 'heldout'):.0%} | {rate(a, 'stale'):.0%} | {rate(a, 'control'):.0%} | {sum(r['prompt_tokens'] for r in g) / max(1, len(g)):,.0f} |")
    lines += ["", "| Arm | vs | Held-out difference [95% CI] | Wins / losses / ties |", "|---|---|---|---|"]
    for b, rows in comps.items():
        for p in rows:
            lines.append(f"| {p['condition']} | {b} | {p['mean_diff']:+.0%} [{p['ci_low']:+.0%}, {p['ci_high']:+.0%}] | {p['wins']} / {p['losses']} / {p['ties']} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
