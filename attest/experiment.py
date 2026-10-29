"""The experiment protocol (identical for every condition and repetition).

    phase 1  learn     E01-E06 on ledgerly 1.0.0, in order, memory may be written
    phase 2  heldout   H01-H06 on ledgerly 1.0.0, memory frozen (read-only)
    phase 3  control   B01-B03 on simkit, memory frozen
    phase 4  stale     S01-S03 on ledgerly 2.0.0, in order, memory may be updated
                       (this is where outdated experience must be noticed and replaced)

Each (condition, repetition) starts from an empty memory store. The memory
state after every phase is saved as a snapshot for the report.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .benchmark import load_tasks
from .memory import CONDITIONS, make_memory
from .runner import Settings, run_task

PHASES = [("learn", "experience", True), ("heldout", "heldout", False), ("control", "control", False), ("stale", "stale", True)]


def run_sequence(condition: str, rep: int, root: Path, settings: Settings, log=print) -> list[dict]:
    base = root / condition / f"r{rep}"
    memory = make_memory(condition, base / "memory")
    results = []
    for phase, group, update in PHASES:
        for task in load_tasks(group):
            out = base / task.id
            if (out / "result.json").exists():
                result = json.loads((out / "result.json").read_text())  # resume an interrupted experiment
            else:
                result = run_task(task, memory, out, settings=settings, update_memory=update)
                result["phase"] = phase
                result["rep"] = rep
                (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n")
            results.append(result)
            log(f"{condition:14} r{rep} {phase:8} {task.id} first={'PASS' if result['first_pass'] else 'fail'} "
                f"final={'PASS' if result['final_pass'] else 'fail'} shown={len(result['shown_notes'])} cited={result['cited_notes']}")
        snapshot = getattr(memory, "store", None)
        if snapshot is not None:
            (base / "memory").mkdir(parents=True, exist_ok=True)
            (base / "memory" / f"after_{phase}.json").write_text(
                json.dumps(snapshot.items(), indent=2, ensure_ascii=False, default=str) + "\n"
            )
    return results


def run_experiment(root: Path, conditions=CONDITIONS, reps: int = 3, parallel: int = 4, settings: Settings | None = None):
    settings = settings or Settings()
    jobs = [(c, r) for r in range(1, reps + 1) for c in conditions]
    print(f"{len(jobs)} sequences x 18 tasks, {parallel} sequences in parallel -> {root}")
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {pool.submit(run_sequence, c, r, root, settings, lambda m: print(m, flush=True)): (c, r) for c, r in jobs}
        for f in as_completed(futures):
            c, r = futures[f]
            try:
                f.result()
                print(f"== finished {c} r{r}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"== FAILED {c} r{r}: {type(exc).__name__}: {exc}", flush=True)
