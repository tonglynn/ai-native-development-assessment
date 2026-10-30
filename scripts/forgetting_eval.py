"""Dynamic forgetting experiment (exploratory, after the main experiment).

Start: Attest's memory after the learning phase of the main experiment
(runs/main/attest/r<rep>/memory/after_learn.json, 8-9 notes per repetition).

Then a simulated stream of 400 later tasks on ledgerly 1.0.0. In each, Attest's real
retrieval picks the notes to inject; a note counts as *used* when it is about a
convention the task needs (analysis.CONVENTION_PATTERNS), and the task is taken to pass.
Along the way one-off notes accumulate: one every two tasks, 200 in total, verified
and in scope but never needed again ("the refund export uses semicolons").
Every 50 tasks a forgetting policy runs.

Scenario (`rare`): the stream samples E01, E02, E03, E05, E06 but never E04, the only
task that needs the approval rule (C6). A correct but rarely needed rule must survive
400 tasks in which nobody needed it. (`steady` includes E04; offline only.)

Measures, after the stream, on the 11 held-out tasks as queries: share of needed
conventions with a note in the 6 injected (recall of what matters), one-off notes
injected per task, learned notes archived (false forgetting), one-off notes archived,
active notes. End to end: held-out first-attempt pass rate with each final memory.

Usage: python scripts/forgetting_eval.py --out runs/forgetting --reps 3 [--offline-only]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.analysis import CONVENTION_PATTERNS  # noqa: E402
from attest.benchmark import load_task, load_tasks  # noqa: E402
from attest.memory import forgetting  # noqa: E402
from attest.memory.earned import EarnedMemory  # noqa: E402
from attest.memory.forgetting import ForgettingMemory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

TICKS, CLUTTER_EVERY, MAINTAIN_EVERY = 400, 2, 50
E2E = ("none", "uniform", "type_aware", "exposure_ranked")  # exposure alone is dominated offline; offline only
LEARN = ("E01", "E02", "E03", "E04", "E05", "E06")
THINGS = ["discount", "customer-entered amount", "reporting window", "credit note", "prorated refund", "authorization void",
          "shipping fee refund", "partial capture", "write-off", "support refund request", "invoice", "payment",
          "subscription period"]
TEMPLATES = [
    "In the {thing} export the CSV columns are separated by semicolons for the finance spreadsheet.",
    "The {thing} admin screen lists the newest entries first and shows {n} rows per page.",
    "Task T{tid}: the {thing} helper was renamed for the migration; the old name stays as an alias for one release.",
    "Support asked for {thing} reasons as free text of at most {n} characters.",
    "The {thing} report pads values to {n} characters so the columns line up.",
    "In tests for {thing}, the fixture customer cus_test_{n} already has one draft entry.",
    "Keep {thing} functions short; move parsing into a private _parse helper in the same module.",
    "The {thing} feature flag is read from settings.FEATURES at import time.",
]
TYPES = ["lesson"] * 5 + ["code_convention"] * 3 + ["process"] * 2


def about(text: str) -> set[str]:
    return {c for c, p in CONVENTION_PATTERNS.items() if re.search(p, text, re.I)}


PRIMARY_ORDER = ("C6", "C5", "C3", "C4", "C1", "C2")  # most specific first


def primary(text: str) -> str | None:
    """The one convention a note is about, for deciding whether a task used it (a note on approval
    that mentions BillingError is an approval note, not an error-code note)."""
    tags = about(text)
    return next((c for c in PRIMARY_ORDER if c in tags), None)


FILE_OF = {"discount": "promotions.py", "customer-entered amount": "importers.py", "reporting window": "reporting.py",
           "credit note": "adjustments.py", "prorated refund": "subscriptions.py", "authorization void": "payments.py",
           "shipping fee refund": "adjustments.py", "partial capture": "payments.py", "write-off": "adjustments.py",
           "support refund request": "support.py", "invoice": "invoice.py", "payment": "payments.py",
           "subscription period": "subscriptions.py"}


def one_off_note(i: int, tick: int, rng: random.Random, with_files: bool = False) -> dict:
    thing = rng.choice(THINGS)
    content = rng.choice(TEMPLATES).format(thing=thing, n=rng.choice([20, 50, 120, 200]), tid=f"{4000 + i}")
    assert not about(content), content
    return {"id": f"at-c{i:04d}", "kind": "lesson", "type": rng.choice(TYPES), "topic": "one-off", "title": f"{thing.capitalize()} detail",
            "content": content, "created_tick": tick, "status": "active", "supersedes": [], "superseded_by": None,
            "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None,
                      "files": ["ledgerly/" + FILE_OF[thing]] if with_files else []},
            "source": {"task_id": f"T{4000 + i}", "first_pass": False, "review_comments": [], "references": []},
            "evidence": [{"task_id": f"T{4000 + i}", "version": "1.0.0", "source": {"kind": "review_comment", "quote": content[:60], "references": []},
                          "applied": {"kind": "code", "change": "added", "file": "ledgerly/x.py", "line": "..."},
                          "verification": {"passed": True, "first_pass": False, "how": "hidden tests"}, "independent_review": None}],
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}}


def learned_track(rep: int, item: dict) -> dict:
    """Reuse in other learning-phase tasks (not the task the note came from) counts as verification."""
    events = [json.loads(line) for line in (ROOT / f"runs/main/attest/r{rep}/memory/events.jsonl").read_text().splitlines()]
    tasks = set()
    for e in events:
        if e["type"] == "update" and e.get("id") == item["id"]:
            m = re.match(r"(?:cited in|confirmed again by verified task) (\w+)", e.get("reason", ""))
            if m and m.group(1) in LEARN and m.group(1) != item["source"]["task_id"]:
                tasks.add(m.group(1))
    return {"last_verified_tick": 0, "unused_exposures": 0, "verified_tasks": sorted(tasks)}


def simulate(rep: int, policy: str, scenario: str, seed: int = 0, tiered: bool = False, with_files: bool = False) -> EarnedMemory:
    clock = {"now": 0}
    memory = ForgettingMemory(None, policy, lambda: clock["now"], tiered=tiered)
    for i, it in sorted(json.loads((ROOT / f"runs/main/attest/r{rep}/memory/after_learn.json").read_text()).items()):
        memory.store.append("add", item=dict(it, created_tick=0, forgetting=learned_track(rep, it)), reason="main experiment after learning")
    pool = [load_task(t) for t in LEARN if scenario == "steady" or t != "E04"]
    rng = random.Random(seed * 1000 + rep)  # the same stream for every policy
    n_clutter = 0
    for tick in range(1, TICKS + 1):
        clock["now"] = tick
        if tick % CLUTTER_EVERY == 0:
            memory.store.append("add", item=one_off_note(n_clutter, tick, rng, with_files), reason="one-off note from a later task")
            n_clutter += 1
        task = rng.choice(pool)
        injected = memory.retrieve(task, "1.0.0").ids
        items = memory.store.items()
        used = [i for i in injected if primary(f"{items[i]['title']} {items[i]['content']}") in task.conventions]
        forgetting.observe(memory, tick, task.id, injected, used, passed=True)
        if tick % MAINTAIN_EVERY == 0:
            forgetting.maintain(memory, tick, policy)
    memory.clock = clock
    return memory


def offline_metrics(memory: EarnedMemory) -> dict:
    items = memory.store.items()
    learned = [i for i in items if not i.startswith("at-c")]
    clutter = [i for i in items if i.startswith("at-c")]
    needed = hit = clutter_injected = 0
    for task in load_tasks("heldout"):
        injected = memory.retrieve(task, "1.0.0").ids
        clutter_injected += sum(i.startswith("at-c") for i in injected)
        covered = set().union(*[about(f"{items[i]['title']} {items[i]['content']}") for i in injected]) if injected else set()
        for c in task.conventions:
            needed += 1
            hit += c in covered
    archived = lambda ids: [i for i in ids if items[i]["status"] == "archived"]  # noqa: E731
    return {"needed_rule_injected": hit / needed, "one_off_injected_per_task": clutter_injected / len(load_tasks("heldout")),
            "learned_archived": [f"{i} {primary(items[i]['title'] + ' ' + items[i]['content'])} ({items[i].get('type')})" for i in archived(learned)],
            "one_off_archived": len(archived(clutter)), "one_off_total": len(clutter),
            "active_notes": sum(it["status"] in ("active", "suspect") for it in items.values())}


def end_to_end(out: Path, rep: int, policy: str, memory: EarnedMemory) -> list[dict]:
    target = ForgettingMemory(out / policy / f"r{rep}" / "memory", policy, lambda: TICKS)
    if not target.store.items():
        for i, it in sorted(memory.store.items().items()):
            target.store.append("add", item=it, reason=f"final state after the {TICKS}-task stream ({policy})")
    rows = []
    for task in load_tasks("heldout"):
        r = run_task(task, target, out / policy / f"r{rep}" / task.id, settings=Settings(), update_memory=False)
        rows.append({"policy": policy, "rep": rep, "task": task.id, "first_pass": r["first_pass"], "crashed": r["attempts"][0]["crashed"],
                     "injected_one_off": sum(i.startswith("at-c") for i in r["shown_notes"]), "conv_failed": r["attempts"][0]["conv_failed"]})
        print(json.dumps(rows[-1]), flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--offline-only", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    offline, finals = [], {}
    for scenario in ("rare", "steady"):
        for policy in forgetting.POLICIES:
            for rep in range(1, args.reps + 1):
                mem = simulate(rep, policy, scenario)
                m = {"scenario": scenario, "policy": policy, "rep": rep, **offline_metrics(mem)}
                offline.append(m)
                print(json.dumps(m), flush=True)
                if scenario == "rare":
                    finals[(policy, rep)] = mem
    runs = []
    if not args.offline_only:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            for rows in pool.map(lambda k: end_to_end(args.out, k[1], k[0], finals[k]), sorted(k for k in finals if k[0] in E2E)):
                runs += rows
    summary = []
    for scenario in ("rare", "steady"):
        for policy in forgetting.POLICIES:
            ms = [m for m in offline if m["scenario"] == scenario and m["policy"] == policy]
            rs = [r for r in runs if r["policy"] == policy] if scenario == "rare" else []
            summary.append({"scenario": scenario, "policy": policy,
                            "needed_rule_injected": sum(m["needed_rule_injected"] for m in ms) / len(ms),
                            "one_off_injected_per_task": sum(m["one_off_injected_per_task"] for m in ms) / len(ms),
                            "learned_archived": sum(len(m["learned_archived"]) for m in ms),
                            "one_off_archived": sum(m["one_off_archived"] for m in ms) / max(1, sum(m["one_off_total"] for m in ms)),
                            "active_notes": sum(m["active_notes"] for m in ms) / len(ms),
                            "pass@1": (sum(r["first_pass"] for r in rs) / len(rs)) if rs else None,
                            "crashed": sum(r["crashed"] for r in rs)})
    (args.out / "results.json").write_text(json.dumps({"config": forgetting.half_life_note(), "offline": offline, "runs": runs,
                                                       "summary": summary}, indent=2) + "\n")
    pct = lambda x: "–" if x is None else f"{x:.0%}"  # noqa: E731
    lines = ["# Dynamic forgetting (exploratory)", "", f"Config: {forgetting.half_life_note()}. Stream of {TICKS} tasks, "
             f"{TICKS // CLUTTER_EVERY} one-off notes, maintenance every {MAINTAIN_EVERY}; {args.reps} repetitions (memories from runs/main).", "",
             "| Scenario | Policy | Needed rule injected | One-off notes injected / task | Learned notes archived (all reps) | One-off notes archived | Active notes | Held-out pass@1 |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['scenario']} | {s['policy']} | {pct(s['needed_rule_injected'])} | {s['one_off_injected_per_task']:.1f} | {s['learned_archived']} | "
              f"{pct(s['one_off_archived'])} | {s['active_notes']:.0f} | {pct(s['pass@1'])} |" for s in summary]
    lines += ["", "Learned notes archived (false forgetting), rare scenario:", ""]
    lines += [f"- {m['policy']} r{m['rep']}: {', '.join(m['learned_archived']) or 'none'}" for m in offline if m["scenario"] == "rare"]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
