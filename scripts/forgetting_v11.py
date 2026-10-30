"""Forgetting V1.1 vs V1 (offline, no model calls; exploratory, after the sensitivity sweep).

Why: in V1, R = E x max(D, U) with U = 1 - 0.5^k. One verified use gives U >= 0.5 for ever,
so R >= 0.5 x 0.5 = 0.25 > 0.2: a note used once is never archived, however long it goes
unused (21 of 26 learned notes in the forgetting and admission runs were protected this way).
And V1 counted "used in a task that passed" as a contribution.

V1.1 changes, each switchable:
  verified-only   reinforce a note only when the task's hidden tests check its convention
                  (simulated: a proxy signal for "behaviour verified", not real attribution);
                  a note adopted in a passing task but not checked is counted, not reinforced.
                  A self-reported citation in the main experiment counts only under the same
                  condition (D10: a citation is a demotion trigger, not proof of use).
  utility decay   U decays too, `utility_factor` (default 4) times slower than D.
  protect cited   a note whose evidence cites a policy or incident never decays, whatever
                  type label the distiller gave it.

Noise: each injected one-off note is "adopted" with probability 0.3 (the agent follows a detail
the task did not need, and the task passes anyway). Under V1 that adoption reinforces the note.

Setup as in scripts/forgetting_eval.py: main-experiment memories, 400-task stream, 200 one-off
notes, rare scenario (no task needs the approval rule). Tiered runs tie one-off notes to their
module files, as in scripts/admission_eval.py. Stream seeds 0 and 1, 3 repetitions each.

Measures (all reported; no single number picks a winner):
  needed rule injected       share of held-out needed conventions with a note among the 6 injected
  active notes
  one-offs permanent         active one-off notes that would never be archived even if never used again
  learned permanent          the same for learned notes
  important misarchived      learned notes about a convention a held-out task needs (C1-C6), archived
  policy archived            learned notes citing a policy/incident or typed business_policy, archived
  other learned archived     learned notes outside C1-C6 (e.g. "reject bool as an integer"): real
                             rules whose use the simulation cannot observe, reported separately
Reading rule, fixed before running: V1.1 is better than V1 only if, with noise, it lowers
one-offs permanent and active notes without archiving a policy rule and without raising the
important misarchive rate. Ablation (type_aware x0.25, noise, seed 0) and utility_factor
{2, 4, 8} are reported as sensitivity, not used to choose.

Usage: python scripts/forgetting_v11.py --out runs/forgetting_v11 [--workers 2]
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

REPS, SEEDS, NOISE = 3, (0, 1), 0.3
CONFIGS = {"type_aware x1": ("type_aware", {"type_scale": 1}, False),
           "type_aware x0.25": ("type_aware", {"type_scale": 0.25}, False),
           "tiered + type_aware x1": ("type_aware", {"type_scale": 1}, True)}
V11 = {"utility_factor": 4, "protect_cited": True}
ABLATION = {"V1": (False, {}), "+ verified-only": (True, {}), "+ utility decay": (False, {"utility_factor": 4}),
            "+ protect cited": (False, {"protect_cited": True}), "V1.1 (all three)": (True, V11)}


def run_one(job: dict) -> dict:
    from forgetting_eval import TICKS, offline_metrics, primary, simulate

    from attest.benchmark import load_tasks
    from attest.memory import admission, forgetting

    params = dict(job["params"])
    mem = simulate(job["rep"], job["policy"], "rare", seed=job["seed"], tiered=job["tiered"], with_files=job["tiered"],
                   params=params, adopt_noise=job["noise"], v11=job["v11"])
    items = mem.store.items()
    needed = set().union(*[set(t.conventions) for t in load_tasks("heldout")])
    text = lambda i: f"{items[i]['title']} {items[i]['content']}"  # noqa: E731
    learned = [i for i in items if not i.startswith("at-c")]
    one_offs = [i for i in items if i.startswith("at-c")]
    important = [i for i in learned if primary(text(i)) in needed]
    other = [i for i in learned if i not in important]
    policy_rules = [i for i in learned if admission.tier(items[i]) == "policy" or items[i].get("type") == "business_policy"]
    active = lambda i: items[i]["status"] in forgetting.ACTIVE  # noqa: E731
    archived = lambda ids: [i for i in ids if items[i]["status"] == "archived"]  # noqa: E731

    def permanent(ids):
        if job["policy"] == "none":
            return sum(active(i) for i in ids)
        return sum(active(i) and forgetting.retention(items[i], 10**9, job["policy"], params)["R"] >= forgetting.THRESHOLD for i in ids)

    tracks = [(items[i].get("forgetting") or {}) for i in one_offs]
    m = offline_metrics(mem)
    return {**{k: job[k] for k in ("arm", "variant", "seed", "rep", "noise")},
            "needed_rule_injected": m["needed_rule_injected"], "active_notes": m["active_notes"],
            "one_off_permanent": permanent(one_offs), "learned_permanent": permanent(learned), "learned_total": len(learned),
            "important_total": len(important), "important_archived": archived(important),
            "policy_archived": archived(policy_rules), "other_archived": archived(other), "other_total": len(other),
            "one_off_reinforced": sum(bool(t.get("verified_tasks")) for t in tracks),
            "one_off_adopted_unverified": sum(t.get("adopted_unverified", 0) for t in tracks),
            "learned_archived_detail": [f"{i} {primary(text(i))} ({items[i].get('type')})" for i in archived(learned)],
            "ticks": TICKS}


def jobs() -> list[dict]:
    out = []
    for seed in SEEDS:
        for rep in range(1, REPS + 1):
            out.append(dict(arm="no forgetting", variant="-", policy="none", params={}, tiered=False, v11=False, noise=NOISE, seed=seed, rep=rep))
            for arm, (policy, params, tiered) in CONFIGS.items():
                for noise in (0.0, NOISE):
                    out.append(dict(arm=arm, variant="V1", policy=policy, params=params, tiered=tiered, v11=False, noise=noise, seed=seed, rep=rep))
                    out.append(dict(arm=arm, variant="V1.1", policy=policy, params={**params, **V11}, tiered=tiered, v11=True,
                                    noise=noise, seed=seed, rep=rep))
    for rep in range(1, REPS + 1):
        for name, (v11, extra) in ABLATION.items():
            if name not in ("V1", "V1.1 (all three)"):  # those two are in the main grid
                out.append(dict(arm="ablation type_aware x0.25", variant=name, policy="type_aware", params={"type_scale": 0.25, **extra},
                                tiered=False, v11=v11, noise=NOISE, seed=0, rep=rep))
        for arm, (policy, params, tiered) in CONFIGS.items():
            if tiered:
                continue
            for f in (2, 8):
                out.append(dict(arm=f"sensitivity {arm}", variant=f"utility_factor {f}", policy=policy,
                                params={**params, **V11, "utility_factor": f}, tiered=False, v11=True, noise=NOISE, seed=0, rep=rep))
    return out


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    total = lambda k: sum(len(r[k]) for r in rows)  # noqa: E731
    return {"runs": n, "needed_rule_injected": sum(r["needed_rule_injected"] for r in rows) / n,
            "active_notes": sum(r["active_notes"] for r in rows) / n,
            "one_off_permanent": sum(r["one_off_permanent"] for r in rows) / n,
            "learned_permanent": f"{sum(r['learned_permanent'] for r in rows)}/{sum(r['learned_total'] for r in rows)}",
            "important_misarchived": total("important_archived") / sum(r["important_total"] for r in rows),
            "important_misarchived_n": f"{total('important_archived')}/{sum(r['important_total'] for r in rows)}",
            "policy_archived": total("policy_archived"),
            "other_archived": f"{total('other_archived')}/{sum(r['other_total'] for r in rows)}",
            "one_off_reinforced": sum(r["one_off_reinforced"] for r in rows) / n}


def table(groups: dict) -> list[str]:
    lines = ["| Arm | Variant | Noise | Runs | Needed rule injected | Active notes | One-offs permanent | Learned permanent | "
             "Important rules misarchived | Policy rules archived | Other learned archived | One-offs reinforced |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (arm, variant, noise), s in groups.items():
        lines.append(f"| {arm} | {variant} | {noise:.1f} | {s['runs']} | {s['needed_rule_injected']:.0%} | {s['active_notes']:.0f} | "
                     f"{s['one_off_permanent']:.0f} | {s['learned_permanent']} | {s['important_misarchived']:.0%} ({s['important_misarchived_n']}) | "
                     f"{s['policy_archived']} | {s['other_archived']} | {s['one_off_reinforced']:.0f} |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with Pool(args.workers) as pool:
        rows = pool.map(run_one, jobs())
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["arm"], r["variant"], r["noise"]), []).append(r)
    main_groups = {k: summarise(v) for k, v in groups.items() if not k[0].startswith(("ablation", "sensitivity"))}
    ablation = {k: summarise(v) for k, v in groups.items()
                if k[0].startswith("ablation") or (k[0] == "type_aware x0.25" and k[2] == NOISE)}
    ablation = {k: summarise([r for r in groups[k] if r["seed"] == 0]) for k in ablation}
    sens = {k: summarise([r for r in groups[k] if r["seed"] == 0]) for k in groups
            if k[0].startswith("sensitivity") or (k[0] in ("type_aware x1", "type_aware x0.25") and k[1] == "V1.1" and k[2] == NOISE)}
    (args.out / "results.json").write_text(json.dumps({"rows": rows, "main": {" | ".join(map(str, k)): v for k, v in main_groups.items()}},
                                                     indent=2) + "\n")
    lines = ["# Forgetting V1.1 vs V1 (offline, rare scenario)", "",
             f"Stream seeds {SEEDS}, {REPS} repetitions each. Noise: share of injected one-off notes adopted without being needed. "
             "\"Verified\" in the simulation is a proxy signal (the task's hidden tests check the note's convention), not attribution.", "",
             *table(main_groups), "", "Ablation (stream seed 0):", "", *table(ablation), "",
             "Sensitivity to utility_factor (V1.1, stream seed 0):", "", *table(sens), "",
             "Learned notes archived, per run (main grid):", ""]
    for r in rows:
        if r["learned_archived_detail"] and not r["arm"].startswith(("ablation", "sensitivity")):
            lines.append(f"- {r['arm']} {r['variant']} noise {r['noise']} seed {r['seed']} r{r['rep']}: {', '.join(r['learned_archived_detail'])}")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
