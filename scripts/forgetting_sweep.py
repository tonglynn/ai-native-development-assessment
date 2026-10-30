"""Sensitivity of dynamic forgetting to its parameters (offline, no model calls).

The decay half-lives and the archive threshold of forgetting V1 were fixed before any
run, not tuned. This sweep asks whether the conclusions depend on them, and what the
trade-off between a clean memory and wrongly forgotten rules looks like.

Grid (rare scenario: no task in the 400-task stream needs the approval rule):
  uniform      half-life {25, 50, 100, 200, 400, 800} tasks
  type_aware   every finite type half-life x {0.25, 0.5, 1, 2, 4} (policy rules never decay)
  exposure     half-life {5, 10, 20, 40} unused injections
  each with archive threshold {0.1, 0.2, 0.3}; plus no forgetting. 3 repetitions each.

Selection rule, fixed before running: among configurations that archive no policy rule
(a learned note citing a policy or incident, or typed business_policy) and at most one
other learned note over the 3 repetitions, take the one with the highest share of
needed rules injected on the held-out tasks (ties: fewer active notes). Select on
stream seed 0, then validate the selected and the default configurations on seed 1.

Usage: python scripts/forgetting_sweep.py --out runs/forgetting_sweep [--workers 2]
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

REPS = 3
GRID = ([("none", {}, 0.2)]
        + [("uniform", {"half_life": h}, t) for h in (25, 50, 100, 200, 400, 800) for t in (0.1, 0.2, 0.3)]
        + [("type_aware", {"type_scale": s}, t) for s in (0.25, 0.5, 1, 2, 4) for t in (0.1, 0.2, 0.3)]
        + [("exposure", {"exposure_half_life": h}, t) for h in (5, 10, 20, 40) for t in (0.1, 0.2, 0.3)])
DEFAULTS = [("uniform", {"half_life": 50}, 0.2), ("type_aware", {"type_scale": 1}, 0.2), ("exposure", {"exposure_half_life": 10}, 0.2)]


def run_one(args):
    policy, params, threshold, rep, seed = args
    from forgetting_eval import offline_metrics, simulate

    from attest.memory import admission

    mem = simulate(rep, policy, "rare", seed=seed, threshold=threshold, params=params)
    items = mem.store.items()
    learned_archived = [i for i, it in items.items() if not i.startswith("at-c") and it["status"] == "archived"]
    policy_archived = [i for i in learned_archived
                       if admission.tier(items[i]) == "policy" or items[i].get("type") == "business_policy"]
    m = offline_metrics(mem)
    return {"policy": policy, "params": params, "threshold": threshold, "rep": rep, "seed": seed,
            "needed_rule_injected": m["needed_rule_injected"], "active_notes": m["active_notes"],
            "one_off_archived": m["one_off_archived"] / m["one_off_total"],
            "learned_archived": len(learned_archived), "policy_archived": len(policy_archived),
            "policy_archived_ids": policy_archived}


def aggregate(rows):
    groups = {}
    for r in rows:
        key = (r["policy"], json.dumps(r["params"], sort_keys=True), r["threshold"], r["seed"])
        groups.setdefault(key, []).append(r)
    out = []
    for (policy, params, threshold, seed), rs in groups.items():
        out.append({"policy": policy, "params": json.loads(params), "threshold": threshold, "seed": seed, "reps": len(rs),
                    "needed_rule_injected": sum(r["needed_rule_injected"] for r in rs) / len(rs),
                    "active_notes": sum(r["active_notes"] for r in rs) / len(rs),
                    "one_off_archived": sum(r["one_off_archived"] for r in rs) / len(rs),
                    "learned_archived": sum(r["learned_archived"] for r in rs),
                    "policy_archived": sum(r["policy_archived"] for r in rs)})
    return out


def label(c):
    p = c["params"]
    value = p.get("half_life") or p.get("type_scale") or p.get("exposure_half_life") or "-"
    return f"{c['policy']} {value} / thr {c['threshold']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(p, params, t, rep, 0) for p, params, t in GRID for rep in range(1, REPS + 1)]
    with Pool(args.workers) as pool:
        rows = pool.map(run_one, jobs)
    configs = aggregate(rows)
    feasible = [c for c in configs if c["policy"] != "none" and c["policy_archived"] == 0 and c["learned_archived"] <= 1]
    chosen = max(feasible, key=lambda c: (c["needed_rule_injected"], -c["active_notes"])) if feasible else None
    validate = [chosen] if chosen else []
    validate += [{"policy": p, "params": params, "threshold": t} for p, params, t in DEFAULTS]
    validate.append({"policy": "none", "params": {}, "threshold": 0.2})
    with Pool(args.workers) as pool:
        vrows = pool.map(run_one, [(c["policy"], c["params"], c["threshold"], rep, 1) for c in validate for rep in range(1, REPS + 1)])
    vconfigs = aggregate(vrows)
    (args.out / "sweep.json").write_text(json.dumps({"grid": configs, "rows": rows, "chosen_on_seed0": chosen,
                                                     "validation_seed1": vconfigs, "validation_rows": vrows}, indent=2) + "\n")
    pct = lambda x: f"{x:.0%}"  # noqa: E731
    lines = ["# Forgetting parameter sensitivity (offline, rare scenario)", "",
             "Rows: configuration (policy, half-life or scale, archive threshold), 3 repetitions, stream seed 0. "
             "Policy rules archived counts learned notes citing a policy or incident or typed business_policy.", "",
             "| Configuration | Needed rule injected | Active notes | One-off archived | Learned archived | Policy rules archived |",
             "|---|---|---|---|---|---|"]
    for c in sorted(configs, key=lambda c: (c["policy"], json.dumps(c["params"]), c["threshold"])):
        lines.append(f"| {label(c)} | {pct(c['needed_rule_injected'])} | {c['active_notes']:.0f} | {pct(c['one_off_archived'])} | "
                     f"{c['learned_archived']} | {c['policy_archived']} |")
    lines += ["", f"Feasible (no policy rule archived, at most 1 other learned note): {len(feasible)} of {len(configs) - 1}.",
              f"Chosen on seed 0: **{label(chosen) if chosen else 'none feasible'}**.", "", "Validation on stream seed 1:", "",
              "| Configuration | Needed rule injected | Active notes | One-off archived | Learned archived | Policy rules archived |",
              "|---|---|---|---|---|---|"]
    for c in vconfigs:
        lines.append(f"| {label(c)} | {pct(c['needed_rule_injected'])} | {c['active_notes']:.0f} | {pct(c['one_off_archived'])} | "
                     f"{c['learned_archived']} | {c['policy_archived']} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
