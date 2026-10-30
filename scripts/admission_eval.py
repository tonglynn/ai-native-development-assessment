"""Trust-tiered admission vs memory pollution (exploratory, after the forgetting experiment).

Same setup as scripts/forgetting_eval.py (main-experiment memories, a 400-task stream,
200 verified one-off notes, the `rare` scenario in which no task needs the approval
rule), with one change: every one-off note is tied to the real module file its topic
belongs to (credit-note details to ledgerly/adjustments.py, ...), so details still reach
tasks that touch that file.

Arms: none (no forgetting, no tiers) · type_aware forgetting only · tiered admission only ·
tiered admission + type_aware forgetting. Measures as in the forgetting experiment, plus
held-out first-attempt pass rate.

Usage: python scripts/admission_eval.py --out runs/admission --reps 3 [--offline-only]
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from forgetting_eval import TICKS, offline_metrics, simulate  # noqa: E402

from attest.benchmark import load_tasks  # noqa: E402
from attest.memory import admission  # noqa: E402
from attest.memory.forgetting import ForgettingMemory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

ARMS = {"none": ("none", False), "type_aware": ("type_aware", False), "tiered": ("none", True),
        "tiered+type_aware": ("type_aware", True)}


def tiers(memory) -> dict:
    out = {}
    for i, it in memory.store.items().items():
        if it.get("status") in ("active", "suspect"):
            key = ("one-off " if i.startswith("at-c") else "learned ") + admission.tier(it)
            out[key] = out.get(key, 0) + 1
    return out


def end_to_end(out: Path, arm: str, rep: int, memory) -> list[dict]:
    policy, tiered = ARMS[arm]
    target = ForgettingMemory(out / arm.replace("+", "_") / f"r{rep}" / "memory", policy, lambda: TICKS, tiered=tiered)
    if not target.store.items():
        for i, it in sorted(memory.store.items().items()):
            target.store.append("add", item=it, reason=f"final state after the {TICKS}-task stream ({arm})")
    rows = []
    for task in load_tasks("heldout"):
        r = run_task(task, target, out / arm.replace("+", "_") / f"r{rep}" / task.id, settings=Settings(), update_memory=False)
        rows.append({"arm": arm, "rep": rep, "task": task.id, "first_pass": r["first_pass"], "crashed": r["attempts"][0]["crashed"],
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
    for arm, (policy, tiered) in ARMS.items():
        for rep in range(1, args.reps + 1):
            mem = simulate(rep, policy, "rare", tiered=tiered, with_files=True)
            m = {"arm": arm, "rep": rep, **offline_metrics(mem), "tiers": tiers(mem)}
            offline.append(m)
            finals[(arm, rep)] = mem
            print(json.dumps(m), flush=True)
    runs = []
    if not args.offline_only:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            for rows in pool.map(lambda k: end_to_end(args.out, k[0], k[1], finals[k]), sorted(finals)):
                runs += rows
    summary = []
    for arm in ARMS:
        ms = [m for m in offline if m["arm"] == arm]
        rs = [r for r in runs if r["arm"] == arm]
        c6 = [r for r in rs if r["task"] in ("H04", "H07", "H11")]
        summary.append({"arm": arm, "needed_rule_injected": sum(m["needed_rule_injected"] for m in ms) / len(ms),
                        "one_off_injected_per_task": sum(m["one_off_injected_per_task"] for m in ms) / len(ms),
                        "learned_archived": sum(len(m["learned_archived"]) for m in ms),
                        "active_notes": sum(m["active_notes"] for m in ms) / len(ms),
                        "pass@1": (sum(r["first_pass"] for r in rs) / len(rs)) if rs else None,
                        "c6_violated": f"{sum('C6' in r['conv_failed'] for r in c6)}/{len(c6)}" if c6 else None,
                        "crashed": sum(r["crashed"] for r in rs)})
    (args.out / "results.json").write_text(json.dumps({"offline": offline, "runs": runs, "summary": summary}, indent=2) + "\n")
    pct = lambda x: "–" if x is None else f"{x:.0%}"  # noqa: E731
    lines = ["# Trust-tiered admission vs memory pollution (exploratory)", "",
             f"Stream of {TICKS} tasks with 200 one-off notes tied to their module files; rare scenario; {args.reps} repetitions.", "",
             "| Arm | Needed rule injected | One-off notes injected / task | Learned notes archived | Active notes | Held-out pass@1 | C6 violated (H04, H07, H11) | Crashed |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {s['arm']} | {pct(s['needed_rule_injected'])} | {s['one_off_injected_per_task']:.1f} | {s['learned_archived']} | "
              f"{s['active_notes']:.0f} | {pct(s['pass@1'])} | {s['c6_violated'] or '–'} | {s['crashed']} |" for s in summary]
    lines += ["", "Tiers of active notes at the end (rep 1):", ""]
    lines += [f"- {m['arm']}: {m['tiers']}" for m in offline if m["rep"] == 1]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
