"""Forgetting V2, points 1-4 (offline, no model calls; exploratory).

Mechanisms (attest/memory/forgetting.py, all opt-in; V1 stays the default):
  1 stability    no utility floor: each independent verified (or demanded) task doubles the
                 half-life, as in spaced repetition; a detail verified once still fades
  2 scoped       an injected but unused note counts as unused only when the task touches the
                 note's files (exposure decay failed in V1 because lexical retrieval put rules
                 into unrelated tasks)
  3 three-state  negative evidence (adopted, then its check failed) archives a note; low
                 retention without negative evidence makes it *dormant*: still injected in its
                 own files, woken by verified use or demand
  4 demand       a convention that fails because no note about it was used is named by the
                 test or the review: notes about it get positive evidence although they were
                 not injected, and archived or dormant ones are reactivated

Stream: as scripts/admission_eval.py (main-experiment memories, 400 tasks, rare scenario: no
task needs the approval rule, 200 one-off notes tied to their module files, trust-tiered
admission), 30% adoption noise on injected one-off notes, plus three constructed cases:
  verified once  every 5th one-off note gets exactly one genuine verified use, 20-100 tasks
                 after it was written, and is never needed again
  wrong notes    12 plausible but wrong rules about C1-C3, worded like the correct rules with
                 the instruction inverted ("round monetary results with round()"), admitted as
                 team-convention rules (as if a review comment had been misremembered); when
                 one is injected into a task that needs its convention, the agent follows it
                 half the time and that convention fails. (Changed after a smoke run of two
                 arms, before the experiment: as single-task candidates they were never
                 injected, because rules fill the six slots first.)
  outcomes       per convention a task needs: passes when a correct learned note about it was
                 used and no wrong note was followed; without a note it passes with
                 probability 0.5 for C1-C4 (discoverable) and 0 for C5-C6 (review-only)
These cases are what the mechanisms are designed for, by construction. The test shows whether
each mechanism does what it is designed to do and what it costs, not that the cases occur in
real repositories with these frequencies.

Arms (type-aware decay x1 unless named; stream seeds 0 and 1 x 3 repetitions):
  V1 · V1.1 · base = verified-only reinforcement + citation protection (the useful part of V1.1)
  base + stability · base + three-state · base + demand · all four (on base)
  exposure decay (V1 reinforcement) · exposure decay + scoped
  V1 x0.25 · all four x0.25 (does three-state + demand make aggressive decay safe?)

Measures at the end of the stream, held-out tasks as queries: needed rules injected (correct
learned notes only), injectable notes (active; dormant counted apart), useful rules archived
(learned notes about C1-C6 and the known-correct others, unavailable), verified-once details
still active although their one use was 150+ tasks ago, wrong-note injections into tasks that
needed their convention during the stream, wrong notes still injectable, policy rules
archived, demand reactivations.

Reading rules, fixed before running: a mechanism helps if it improves its target measure
against its comparison arm without more useful rules archived or any policy rule archived:
  1 stability vs base: stale verified-once details still active, down
  2 scoped vs exposure: policy and useful rules archived, down, with injectable notes not up
    by more than 25%
  3 three-state vs base: useful rules archived and wrong-note injections, down
  4 demand vs base: useful rules archived, down; reported cost: wrong notes credited by demand
  x0.25: all four x0.25 vs V1 x0.25 on useful rules archived.

Usage: python scripts/forgetting_v2.py --out runs/forgetting_v2 [--workers 2]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

REPS, SEEDS, NOISE, FOLLOW_WRONG = 3, (0, 1), 0.3, 0.5
DISCOVER = {"C1": 0.5, "C2": 0.5, "C3": 0.5, "C4": 0.5, "C5": 0.0, "C6": 0.0}
WRONG = {  # convention: (title, content, files); worded like the correct rules, with the instruction inverted
    "C1": ("Round invoice money with round()", "Round monetary results on invoices and prices with Python's round(value, 2) and keep "
           "them as Decimal; ledgerly's helper is not needed.", ["ledgerly/invoice.py", "ledgerly/pricing.py"]),
    "C2": ("Reject invalid input with ValueError", "Reject invalid input by raising ValueError with a readable message; BillingError "
           "is only for payment provider failures.", ["ledgerly/invoice.py", "ledgerly/payments.py"]),
    "C3": ("Compare incoming datetimes as given", "Compare incoming datetimes as they are passed in; naive datetimes are already UTC "
           "in ledgerly, so no conversion is needed.", ["ledgerly/renewals.py", "ledgerly/payments.py"]),
}
BASE = {"protect_cited": True}
ARMS = {  # name: (policy, params, verified_only, negative, demand, scoped)
    "V1": ("type_aware", {}, False, False, False, False),
    "V1.1": ("type_aware", {"utility_factor": 4, "protect_cited": True}, True, False, False, False),
    "base (verified-only)": ("type_aware", BASE, True, False, False, False),
    "base + stability": ("type_aware", {**BASE, "stability": 2}, True, False, False, False),
    "base + three-state": ("type_aware", {**BASE, "dormant": True}, True, True, False, False),
    "base + demand": ("type_aware", BASE, True, False, True, False),
    "all four": ("type_aware", {**BASE, "stability": 2, "dormant": True}, True, True, True, False),
    "exposure (V1)": ("exposure", {}, False, False, False, False),
    "exposure + scoped": ("exposure", {}, False, False, False, True),
    "V1 x0.25": ("type_aware", {"type_scale": 0.25}, False, False, False, False),
    "all four x0.25": ("type_aware", {**BASE, "type_scale": 0.25, "stability": 2, "dormant": True}, True, True, True, False),
}


def wrong_notes() -> list[dict]:
    out, n = [], 0
    for conv, (title, content, files) in WRONG.items():
        for j in range(4):
            f = files[j % 2]
            out.append({"id": f"at-w{n:03d}", "kind": "lesson", "type": "code_convention", "topic": "wrong", "title": title,
                        "content": content, "created_tick": 5 + 15 * n, "status": "active", "supersedes": [], "superseded_by": None,
                        "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None, "files": [f]},
                        "source": {"task_id": f"W{n}", "first_pass": False, "review_comments": [f"[team convention] {content}"], "references": []},
                        "evidence": [{"task_id": f"W{n}", "version": "1.0.0", "source": {"kind": "review_comment", "quote": content[:60], "references": []},
                                      "applied": {"kind": "code", "change": "added", "file": f, "line": "..."},
                                      "verification": {"passed": True}, "independent_review": None}],
                        "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}, "_conv": conv})
            n += 1
    return out


def simulate(arm: str, rep: int, seed: int):
    from forgetting_eval import CLUTTER_EVERY, LEARN, MAINTAIN_EVERY, TICKS, learned_track, one_off_note, primary

    from attest.benchmark import load_task
    from attest.memory import admission, forgetting
    from attest.memory.forgetting import ForgettingMemory

    policy, params, vo, use_negative, use_demand, scoped = ARMS[arm]
    clock = {"now": 0}
    memory = ForgettingMemory(None, policy, lambda: clock["now"], tiered=True)
    for i, it in sorted(json.loads((ROOT / f"runs/main/attest/r{rep}/memory/after_learn.json").read_text()).items()):
        memory.store.append("add", item=dict(it, created_tick=0, forgetting=learned_track(rep, it, vo)), reason="main experiment after learning")
    wrongs = {w["created_tick"]: w for w in wrong_notes()}
    pool = [load_task(t) for t in LEARN if t != "E04"]
    rng = random.Random(seed * 1000 + rep)  # task stream and one-off notes: the same for every arm
    noise = random.Random(seed * 1000 + rep + 7919)
    outcome = random.Random(seed * 1000 + rep + 104729)
    once = random.Random(seed * 1000 + rep + 1299709)
    conv_of, verified_once, schedule = {}, {}, {}
    stats = {"wrong_injected": 0, "wrong_followed": 0, "demand_reactivated": 0, "wrong_demanded": 0}
    n_clutter = 0
    for tick in range(1, TICKS + 1):
        clock["now"] = tick
        if tick % CLUTTER_EVERY == 0:
            note = one_off_note(n_clutter, tick, rng, with_files=True)
            memory.store.append("add", item=note, reason="one-off note from a later task")
            if n_clutter % 5 == 0:
                when = tick + once.randint(20, 100)
                schedule.setdefault(when, []).append(note["id"])
                verified_once[note["id"]] = when
            n_clutter += 1
        if tick in wrongs:
            w = dict(wrongs[tick])
            conv_of[w["id"]] = w.pop("_conv")
            memory.store.append("add", item=w, reason="a wrong rule, misremembered from a review")
        for nid in schedule.get(tick, []):  # the one genuine later use of a verified-once detail
            forgetting.observe(memory, tick, f"V{nid}", [nid], [nid], True, None if not vo else [nid])
        task = rng.choice(pool)
        injected = memory.retrieve(task, "1.0.0").ids
        items = memory.store.items()
        prim = {i: (conv_of.get(i) or primary(f"{items[i]['title']} {items[i]['content']}")) for i in items}
        learned = lambda i: not i.startswith(("at-c", "at-w"))  # noqa: E731
        correct_used = [i for i in injected if learned(i) and prim[i] in task.conventions]
        wrong_inj = [i for i in injected if i.startswith("at-w") and prim[i] in task.conventions]
        followed = [i for i in wrong_inj if noise.random() < FOLLOW_WRONG]
        stats["wrong_injected"] += len(wrong_inj)
        stats["wrong_followed"] += len(followed)
        failed = []
        for c in task.conventions:
            if any(prim[w] == c for w in followed):
                failed.append(c)
            elif not any(prim[i] == c for i in correct_used) and outcome.random() >= DISCOVER[c]:
                failed.append(c)
        adopted_one_offs = [i for i in injected if i.startswith("at-c") and noise.random() < NOISE]
        used = correct_used + followed + adopted_one_offs
        verified = [i for i in correct_used if prim[i] not in failed] if vo else None
        negative = followed if use_negative else ()
        demand = []
        if use_demand:
            demand = [i for i in items if prim[i] in failed and i not in injected and i not in followed
                      and items[i]["status"] not in ("retired", "superseded")]
        relevant = None
        if scoped:
            named = admission.files_named(task)
            relevant = [i for i in injected if set((items[i].get("scope") or {}).get("files") or []) & named]
        n_events = len(memory.store.events)
        forgetting.observe(memory, tick, task.id, injected, used, not failed, verified, negative=negative, demand=demand, relevant=relevant)
        # counted from what observe actually did (the first run counted the demand list before
        # observe's rules skip negative-evidence notes; fixed after that run, then rerun)
        credited = [e for e in memory.store.events[n_events:] if "needed in" in (e.get("reason") or "")]
        stats["demand_reactivated"] += sum("reactivated" in e["reason"] for e in credited)
        stats["wrong_demanded"] += sum(e["id"].startswith("at-w") for e in credited)
        if tick % MAINTAIN_EVERY == 0:
            forgetting.maintain(memory, tick, policy, forgetting.THRESHOLD, params)
    return memory, conv_of, verified_once, stats, params, policy


def run_one(job: dict) -> dict:
    from forgetting_eval import TICKS, about, primary
    from forgetting_v11 import other_label

    from attest.benchmark import load_tasks
    from attest.memory import admission, forgetting

    memory, conv_of, verified_once, stats, params, policy = simulate(job["arm"], job["rep"], job["seed"])
    items = memory.store.items()
    text = lambda i: f"{items[i]['title']} {items[i]['content']}"  # noqa: E731
    prim = {i: conv_of.get(i) or primary(text(i)) for i in items}
    heldout = load_tasks("heldout")
    needed_convs = set().union(*[set(t.conventions) for t in heldout])
    learned = [i for i in items if not i.startswith(("at-c", "at-w"))]
    useful = [i for i in learned if prim[i] in needed_convs or other_label(text(i))[0] == "known correct, unchecked"]
    policy_rules = [i for i in learned if admission.tier(items[i]) == "policy" or items[i].get("type") == "business_policy"]
    st = lambda i: items[i]["status"]  # noqa: E731
    needed = hit = wrong_end = one_off_end = 0
    for task in heldout:
        injected = memory.retrieve(task, "1.0.0").ids
        # as in forgetting_eval.offline_metrics: any convention a correct learned note is about
        covered = set().union(*[about(text(i)) for i in injected if i in learned]) if injected else set()
        wrong_end += sum(i.startswith("at-w") for i in injected)
        one_off_end += sum(i.startswith("at-c") for i in injected)
        for c in task.conventions:
            needed += 1
            hit += c in covered
    stale_once = [i for i, when in verified_once.items() if when <= TICKS - 150]

    def permanent(i):
        return st(i) in forgetting.ACTIVE and forgetting.retention(items[i], 10**9, policy, params)["R"] >= forgetting.THRESHOLD

    return {**{k: job[k] for k in ("arm", "seed", "rep")},
            "needed_rule_injected": hit / needed,
            "injectable": sum(st(i) in forgetting.ACTIVE for i in items), "dormant": sum(st(i) == "dormant" for i in items),
            "useful_total": len(useful), "useful_archived": [i for i in useful if st(i) == "archived"],
            "useful_dormant": [i for i in useful if st(i) == "dormant"],
            "policy_archived": [i for i in policy_rules if st(i) == "archived"],
            "stale_once_total": len(stale_once), "stale_once_active": sum(st(i) in forgetting.ACTIVE for i in stale_once),
            "one_off_permanent": sum(permanent(i) for i in items if i.startswith("at-c")),
            "wrong_injected_stream": stats["wrong_injected"], "wrong_followed_stream": stats["wrong_followed"],
            "wrong_injectable_end": sum(st(i) in (*forgetting.ACTIVE, "dormant") for i in items if i.startswith("at-w")),
            "wrong_injected_heldout": wrong_end, "one_off_injected_heldout": one_off_end / len(heldout), "demand_reactivated": stats["demand_reactivated"], "wrong_demanded": stats["wrong_demanded"],
            "learned_archived_detail": [f"{i} {prim[i]} ({items[i].get('type')})" for i in learned if st(i) == "archived"]}


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    mean = lambda k: sum(r[k] for r in rows) / n  # noqa: E731
    tot = lambda k: sum(len(r[k]) for r in rows)  # noqa: E731
    return {"runs": n, "needed_rule_injected": mean("needed_rule_injected"), "injectable": mean("injectable"), "dormant": mean("dormant"),
            "useful_archived": f"{tot('useful_archived')}/{sum(r['useful_total'] for r in rows)}",
            "useful_dormant": tot("useful_dormant"), "policy_archived": tot("policy_archived"),
            "stale_once_active": f"{sum(r['stale_once_active'] for r in rows)}/{sum(r['stale_once_total'] for r in rows)}",
            "one_off_permanent": mean("one_off_permanent"), "wrong_injected_stream": mean("wrong_injected_stream"),
            "wrong_injectable_end": mean("wrong_injectable_end"), "wrong_injected_heldout": mean("wrong_injected_heldout"),
            "one_off_injected_heldout": mean("one_off_injected_heldout"),
            "demand_reactivated": mean("demand_reactivated"), "wrong_demanded": mean("wrong_demanded")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [{"arm": a, "seed": s, "rep": r} for a in ARMS for s in SEEDS for r in range(1, REPS + 1)]
    with Pool(args.workers) as pool:
        rows = pool.map(run_one, jobs)
    summary = {a: summarise([r for r in rows if r["arm"] == a]) for a in ARMS}
    (args.out / "results.json").write_text(json.dumps({"rows": rows, "summary": summary}, indent=2) + "\n")
    lines = ["# Forgetting V2, points 1-4 (offline, constructed cases)", "",
             f"Stream seeds {SEEDS} x {REPS} repetitions; tiered admission; 30% adoption noise; verified-once details, wrong notes and "
             "convention outcomes constructed as described in scripts/forgetting_v2.py.", "",
             "| Arm | Needed rule injected | Injectable notes | Dormant | Useful rules archived | Useful rules dormant | Policy rules archived | "
             "Stale verified-once still active | One-offs permanent | One-off notes injected / held-out task | Wrong-note injections (stream) | Wrong notes injectable at end | "
             "Wrong notes injected (held-out, per run) | Demand reactivations | Wrong notes credited by demand |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, s in summary.items():
        lines.append(f"| {a} | {s['needed_rule_injected']:.0%} | {s['injectable']:.0f} | {s['dormant']:.0f} | {s['useful_archived']} | "
                     f"{s['useful_dormant']} | {s['policy_archived']} | {s['stale_once_active']} | {s['one_off_permanent']:.0f} | {s['one_off_injected_heldout']:.1f} | "
                     f"{s['wrong_injected_stream']:.1f} | {s['wrong_injectable_end']:.1f} | {s['wrong_injected_heldout']:.1f} | "
                     f"{s['demand_reactivated']:.1f} | {s['wrong_demanded']:.1f} |")
    lines += ["", "Learned notes archived, per run:", ""]
    lines += [f"- {r['arm']} seed {r['seed']} r{r['rep']}: {', '.join(r['learned_archived_detail'])}" for r in rows if r["learned_archived_detail"]]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
