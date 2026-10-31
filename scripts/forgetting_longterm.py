"""Long-term check of forgetting, by checkpoint (D48; exploratory, after the main experiment).

The forgetting experiment (scripts/forgetting_eval.py) measured memory after one 400-task stream.
This asks whether the agent is better after forgetting, along the way and after a rule comes back:

Stream (simulated, as in forgetting_eval): Attest's memory after the main experiment's learning
phase, then 400 later ledgerly tasks drawn from E01-E06, one one-off note every 2 tasks, a
forgetting policy every 50. E04, the only task that needs the approval rule (C6), is absent for
tasks 1-300 and returns for 301-400 ("rare, then back"). When a task needs a convention whose note
is archived, the simulated review names it, the task counts as a miss, and the same verified rule
reactivates the note (forgetting.reactivate with the current clock), as a re-learned duplicate would.

Policies: none, uniform decay, type-aware decay (forgetting.py defaults, not tuned here).
Checkpoints: after 100, 200 and 400 tasks.

Offline, at each checkpoint: share of notes still active by type (business_policy,
code_convention, process; one-off); important notes wrongly archived (learned notes; business
policy rules separately); needed rules injected on held-out queries; one-off notes injected per
held-out task; stale use: on the 2.0 tasks S04/S05 whose threshold changed, the 1.x "500" approval
note is injected (Attest adds a version warning); reactivations so far and stream tasks that
missed a needed rule because its note was archived.
End to end, at each checkpoint: the 11 held-out tasks and S04/S05 with that memory, real agent,
memory frozen.

Reading rule, fixed before running: the criterion is the agent's result, not how many notes are
archived. Per policy against "none", held-out pass@1 at each checkpoint, paired by task with a
bootstrap 95% interval: "better" if the lower bound is > 0, "not worse" if > -10 points, otherwise
"inconclusive"/"worse". Wrongly archived business-policy rules and blocked legitimate operations on
S04/S05 are reported as costs whatever the pass rate. The simulated stream decides what is "used"
by the convention a note is about (perfect attribution), which favours forgetting.

Usage: python scripts/forgetting_longterm.py --out runs/forgetting_longterm --reps 3 [--offline-only]
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from attest.analysis import paired  # noqa: E402
from attest.benchmark import REPOS_DIR, load_task, load_tasks, repo_version  # noqa: E402
from attest.memory import forgetting  # noqa: E402
from attest.memory.forgetting import ForgettingMemory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402
from forgetting_eval import CLUTTER_EVERY, LEARN, MAINTAIN_EVERY, about, learned_track, one_off_note, primary  # noqa: E402

TICKS, RETURN_AT = 400, 301
CHECKPOINTS = (100, 200, 400)
POLICIES = ("none", "uniform", "type_aware")
STALE = ("S04", "S05")
OLD_THRESHOLD = re.compile(r"\b500(\.00)?\b")


def simulate(rep: int, policy: str, seed: int = 0):
    clock = {"now": 0}
    memory = ForgettingMemory(None, policy, lambda: clock["now"])
    for i, it in sorted(json.loads((ROOT / f"runs/main/attest/r{rep}/memory/after_learn.json").read_text()).items()):
        memory.store.append("add", item=dict(it, created_tick=0, forgetting=learned_track(rep, it)), reason="main experiment after learning")
    rng = random.Random(seed * 1000 + rep)  # the same stream for every policy
    early = [load_task(t) for t in LEARN if t != "E04"]
    late = [load_task(t) for t in LEARN]
    n_clutter, misses, reactivated, snaps = 0, [], [], {}
    for tick in range(1, TICKS + 1):
        clock["now"] = tick
        if tick % CLUTTER_EVERY == 0:
            memory.store.append("add", item=one_off_note(n_clutter, tick, rng), reason="one-off note from a later task")
            n_clutter += 1
        task = rng.choice(early if tick < RETURN_AT else late)
        injected = memory.retrieve(task, "1.0.0").ids
        items = memory.store.items()
        covered = {primary(f"{items[i]['title']} {items[i]['content']}") for i in injected}
        for conv in task.conventions:
            if conv in covered:
                continue
            archived = [i for i, it in items.items() if not i.startswith("at-c") and it["status"] == "archived"
                        and primary(f"{it['title']} {it['content']}") == conv]
            if archived:  # the review names the rule; the verified task re-learns it
                misses.append({"tick": tick, "task": task.id, "convention": conv})
                for i in archived:
                    forgetting.reactivate(memory, i, f"confirmed again by verified task {task.id}", tick, task.id)
                    reactivated.append({"tick": tick, "id": i, "convention": conv})
        items = memory.store.items()
        used = [i for i in injected if primary(f"{items[i]['title']} {items[i]['content']}") in task.conventions]
        forgetting.observe(memory, tick, task.id, injected, used, passed=True)
        if tick % MAINTAIN_EVERY == 0:
            forgetting.maintain(memory, tick, policy)
        if tick in CHECKPOINTS:
            snaps[tick] = {"items": copy.deepcopy(memory.store.items()), "misses": list(misses), "reactivated": list(reactivated)}
    return memory, snaps


def view(items: dict, policy: str, tick: int):
    m = ForgettingMemory(None, policy, lambda: tick)
    for _, it in sorted(items.items()):
        m.store.append("add", item=it, reason=f"state at task {tick} ({policy})")
    return m


def offline_metrics(items: dict, policy: str, tick: int, snap: dict) -> dict:
    m = view(items, policy, tick)
    learned = {i: it for i, it in items.items() if not i.startswith("at-c")}
    active = lambda it: it["status"] in ("active", "suspect")  # noqa: E731
    by_type = {}
    for t in ("business_policy", "code_convention", "process"):
        ids = [i for i, it in learned.items() if it.get("type") == t]
        by_type[t] = [sum(active(learned[i]) for i in ids), len(ids)]
    one = [it for i, it in items.items() if i.startswith("at-c")]
    by_type["one_off"] = [sum(active(it) for it in one), len(one)]
    needed = hit = clutter = 0
    for task in load_tasks("heldout"):
        ids = m.retrieve(task, "1.0.0").ids
        clutter += sum(i.startswith("at-c") for i in ids)
        cov = set().union(*[about(f"{items[i]['title']} {items[i]['content']}") for i in ids]) if ids else set()
        needed += len(task.conventions)
        hit += sum(c in cov for c in task.conventions)
    stale = []
    for tid in STALE:
        task = load_task(tid)
        r = m.retrieve(task, repo_version(REPOS_DIR / task.repo))
        stale.append(any(primary(f"{items[i]['title']} {items[i]['content']}") == "C6" and OLD_THRESHOLD.search(items[i]["content"]) for i in r.ids))
    return {"tick": tick, "policy": policy, "active_by_type": by_type,
            "learned_archived": sorted(i for i, it in learned.items() if it["status"] == "archived"),
            "business_policy_archived": sorted(i for i, it in learned.items() if it["status"] == "archived" and it.get("type") == "business_policy"),
            "needed_rule_injected": hit / needed, "one_off_injected_per_task": clutter / len(load_tasks("heldout")),
            "stale_old_threshold_injected": sum(stale), "stale_queries": len(stale),
            "stream_misses_so_far": len(snap["misses"]), "reactivations_so_far": len(snap["reactivated"]),
            "active_notes": sum(active(it) for it in items.values())}


def end_to_end(out: Path, rep: int, policy: str, tick: int, items: dict) -> list[dict]:
    target = ForgettingMemory(out / policy / f"t{tick}" / f"r{rep}" / "memory", policy, lambda: tick)
    if not target.store.items():
        for _, it in sorted(items.items()):
            target.store.append("add", item=it, reason=f"state after {tick} tasks ({policy})")
    rows = []
    for task in load_tasks("heldout") + [load_task(t) for t in STALE]:
        r = run_task(task, target, out / policy / f"t{tick}" / f"r{rep}" / task.id, settings=Settings(), update_memory=False)
        rows.append({"policy": policy, "tick": tick, "rep": rep, "task": task.id, "group": task.group, "first_pass": r["first_pass"],
                     "crashed": r["attempts"][0]["crashed"], "conv_failed": r["attempts"][0]["conv_failed"],
                     "injected_one_off": sum(i.startswith("at-c") for i in r["shown_notes"])})
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
    offline, states = [], {}
    for policy in POLICIES:
        for rep in range(1, args.reps + 1):
            _, snaps = simulate(rep, policy)
            for tick, snap in snaps.items():
                offline.append({"rep": rep, **offline_metrics(snap["items"], policy, tick, snap),
                                "misses": snap["misses"], "reactivated": snap["reactivated"]})
                states[(policy, tick, rep)] = snap["items"]
    runs = []
    if not args.offline_only:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            for rows in pool.map(lambda k: end_to_end(args.out, k[2], k[0], k[1], states[k]), sorted(states)):
                runs += rows
    compare = {}
    for tick in CHECKPOINTS:
        res = [{"condition": r["policy"], "task_id": f"{r['task']}", "group": r["group"], "first_pass": r["first_pass"]}
               for r in runs if r["tick"] == tick and not r["crashed"]]
        compare[tick] = paired(res, "heldout", baseline="none") if res else []
    (args.out / "results.json").write_text(json.dumps({"config": forgetting.half_life_note(), "offline": offline, "runs": runs,
                                                       "paired_vs_none": compare}, indent=2, default=str) + "\n")
    pct = lambda x: "–" if x is None else f"{x:.0%}"  # noqa: E731
    lines = ["# Forgetting over time (exploratory)", "", f"Config: {forgetting.half_life_note()}. E04 absent for tasks 1-{RETURN_AT - 1}, back after; "
             f"{args.reps} repetitions.", "",
             "| Tasks | Policy | Active: business policy / code / process / one-off | Learned archived | Policy rules archived | Needed rule injected | One-off / task | Old threshold on S04/S05 | Misses → reactivations | Held-out pass@1 | S04/S05 pass@1 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for tick in CHECKPOINTS:
        for policy in POLICIES:
            ms = [m for m in offline if m["tick"] == tick and m["policy"] == policy]
            agg = {t: [sum(m["active_by_type"][t][0] for m in ms), sum(m["active_by_type"][t][1] for m in ms)] for t in ms[0]["active_by_type"]}
            rs = [r for r in runs if r["tick"] == tick and r["policy"] == policy and not r["crashed"]]
            ho = [r for r in rs if r["group"] == "heldout"]
            st = [r for r in rs if r["group"] == "stale"]
            lines.append(
                f"| {tick} | {policy} | " + " / ".join(f"{a}/{n}" for a, n in agg.values()) +
                f" | {sum(len(m['learned_archived']) for m in ms)} | {sum(len(m['business_policy_archived']) for m in ms)} | "
                f"{pct(sum(m['needed_rule_injected'] for m in ms) / len(ms))} | {sum(m['one_off_injected_per_task'] for m in ms) / len(ms):.1f} | "
                f"{sum(m['stale_old_threshold_injected'] for m in ms)}/{sum(m['stale_queries'] for m in ms)} | "
                f"{sum(m['stream_misses_so_far'] for m in ms)} → {sum(m['reactivations_so_far'] for m in ms)} | "
                f"{pct(sum(r['first_pass'] for r in ho) / len(ho)) if ho else '–'} | {pct(sum(r['first_pass'] for r in st) / len(st)) if st else '–'} |")
    lines += ["", "Held-out pass@1 against no forgetting, paired by task (bootstrap 95% interval):", ""]
    for tick, rows in compare.items():
        for p in rows:
            lines.append(f"- after {tick} tasks, {p['condition']}: {p['mean_diff']:+.0%} [{p['ci_low']:+.0%}, {p['ci_high']:+.0%}]")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
