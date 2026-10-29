"""Command line entry point.

    python -m earned_memory run --task E01                 # one task, no memory
    python -m earned_memory pilot --name pilot_nomem       # every task, no memory, no learning
    python -m earned_memory summary runs/pilot_nomem       # table of results
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .benchmark import PROJECT_ROOT, load_task, load_tasks
from .memory import make_memory
from .runner import Settings, run_task

RUNS_DIR = PROJECT_ROOT / "runs"


def _one_line(r: dict) -> str:
    first = r["attempts"][0]
    status = "PASS" if r["first_pass"] else ("pass@2" if r["final_pass"] else "FAIL")
    missed = ",".join(first["conv_failed"]) or "-"
    leak = f" LEAK={r['leaks']}" if r["leaks"] else ""
    return (f"{r['task_id']:4} {r['condition']:14} {status:6} missed={missed:8} steps={r['steps']:3} "
            f"${r['cost_usd']:.4f} {first['exit_status']}{leak}")


def cmd_run(args) -> int:
    task = load_task(args.task)
    out = RUNS_DIR / args.name / args.condition / task.id / f"r{args.rep}"
    memory = make_memory(args.condition, RUNS_DIR / args.name / args.condition / "memory")
    result = run_task(task, memory, out, settings=Settings(thinking=args.thinking), learn=not args.no_learn)
    print(_one_line(result))
    print(f"trajectories and result.json: {out}")
    return 0


def cmd_pilot(args) -> int:
    groups = args.groups.split(",")
    tasks = [t for t in load_tasks() if t.group in groups]
    jobs = [(t, rep) for rep in range(1, args.reps + 1) for t in tasks]
    print(f"running {len(jobs)} runs (no memory, no learning) with {args.parallel} in parallel")
    settings = Settings(thinking=args.thinking)

    def job(task, rep):
        out = RUNS_DIR / args.name / "no_memory" / task.id / f"r{rep}"
        if (out / "result.json").exists() and not args.force:
            return json.loads((out / "result.json").read_text())
        return run_task(task, make_memory("no_memory", None), out, settings=settings, learn=False)

    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {pool.submit(job, t, rep): (t, rep) for t, rep in jobs}
        for f in as_completed(futures):
            t, rep = futures[f]
            try:
                print(_one_line(f.result()), f"rep={rep}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"{t.id} rep={rep} ERROR {type(exc).__name__}: {exc}", flush=True)
    return cmd_summary(argparse.Namespace(path=RUNS_DIR / args.name))


def cmd_summary(args) -> int:
    results = [json.loads(p.read_text()) for p in sorted(Path(args.path).rglob("result.json"))]
    if not results:
        print("no results found")
        return 1
    table = defaultdict(list)
    for r in results:
        table[(r["condition"], r["group"])].append(r)
    print(f"\n{'condition':14} {'group':10} {'runs':>4} {'pass@1':>7} {'pass@2':>7} {'steps':>6} {'cost$':>8}  convention misses (attempt 1)")
    for (cond, group), rs in sorted(table.items()):
        n = len(rs)
        misses = defaultdict(int)
        for r in rs:
            for c in r["attempts"][0]["conv_failed"]:
                misses[c] += 1
        print(f"{cond:14} {group:10} {n:4} {sum(r['first_pass'] for r in rs) / n:7.0%} "
              f"{sum(r['final_pass'] for r in rs) / n:7.0%} {sum(r['steps'] for r in rs) / n:6.1f} "
              f"{sum(r['cost_usd'] for r in rs):8.4f}  {dict(sorted(misses.items()))}")
    leaks = [r["task_id"] for r in results if r["leaks"]]
    print(f"\nruns that touched benchmark files: {leaks or 'none'}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m earned_memory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="run one task")
    p.add_argument("--task", required=True)
    p.add_argument("--condition", default="no_memory")
    p.add_argument("--name", default="smoke")
    p.add_argument("--rep", type=int, default=1)
    p.add_argument("--thinking", default=Settings().thinking, choices=["off", "low", "high"])
    p.add_argument("--no-learn", action="store_true")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("pilot", help="run every task without memory (difficulty calibration)")
    p.add_argument("--name", default="pilot_nomem")
    p.add_argument("--groups", default="experience,heldout,stale,control")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--thinking", default=Settings().thinking, choices=["off", "low", "high"])
    p.add_argument("--force", action="store_true", help="rerun even if result.json exists")
    p.set_defaults(fn=cmd_pilot)

    p = sub.add_parser("summary", help="summarise results under a runs/ directory")
    p.add_argument("path")
    p.set_defaults(fn=cmd_summary)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
