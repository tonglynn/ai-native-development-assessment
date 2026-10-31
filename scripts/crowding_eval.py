"""Memory crowding ablation (D64; exploratory, separate from the frozen main experiment).

Question: when many approved notes compete for the injected slots, does value-aware injection keep the
rules that matter in the prompt, and does that change the coding result?

Memory: the same snapshot for every arm, the v4 memory after human review in the clean stream
(runs/review_replay/clean/attest_secure_v4_reviewed/r1-r3), the condition in which approved low-value rules
displaced the idempotency rule (D63). Arms (attest/memory/tiers.py): A v4 as evaluated; B relevance only;
C relevance + criticality; D tiers + dynamic k. Only the injection policy differs.
Tasks: held-out (11), stale (S01-S05, ledgerly 2.0, where the remembered 500.00 threshold is wrong), control
(B01-B03, simkit). Memory frozen; policy guard on, as in the v4 arm; 6 runs per arm and task (each of the 3
memories twice).

Offline (deterministic, from retrieval): share of needed core rules (C1 Decimal, C4, C5, C6) injected; displacement
(a needed core rule is relevant and available but not injected while a non-core note is); effective notes per task
(injected notes about a convention the task needs); wrong injections (the 500.00 rule on 2.0 tasks; any note on
simkit tasks); memory tokens per task.
End to end: pass@1 per group; held-out paired by task against arm A.

Reading rule, fixed before running: an arm is better than A if its held-out pass@1 interval lies above 0, not
worse if its lower bound is above -10 points, otherwise inconclusive; the offline measures are reported whatever
the pass rate, and a lower displacement without a pass-rate gain is reported as such.

D66 (--arms A,C,D2,E, same memory, A and C rerun in the same session): D2 soft budget (every relevant core rule kept,
others by relevance above half the best, at most 10, and over a 600-token memory budget the non-core notes are
compressed to their titles, never dropped; core notes are kept even without word overlap, changed after an offline dry
run showed 72/81 needed core rules injected, disclosed); E task-type criticality (the rules the task's operation needs, read from
the task text, come first instead of a fixed core list) with the same soft budget. Reading rule, fixed before
running: as above, each arm against A, and D2 and E also against C.

Usage: python scripts/crowding_eval.py --out runs/crowding --parallel 40 [--offline-only] [--arms A,C,D2,E]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.analysis import paired  # noqa: E402
from attest.benchmark import REPOS_DIR, load_tasks, repo_version  # noqa: E402
from attest.memory import make_memory, tiers  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

SRC = ROOT / "runs/review_replay/clean/attest_secure_v4_reviewed"
ARMS = ["A", "B", "C", "D"]
CORE = {"C1", "C4", "C5", "C6"}
OLD = re.compile(r"\b500(\.00)?\b")
RUNS = [("r1", 1), ("r2", 1), ("r3", 1), ("r1", 2), ("r2", 2), ("r3", 2)]


def memory(arm: str, src: str, out: Path | None):
    m = make_memory(f"attest_v4_{arm}", out)
    if not m.store.items():
        for e in (json.loads(x) for x in (SRC / src / "memory/events.jsonl").read_text().splitlines() if x.strip()):
            m.store.append(e["type"], **{k: v for k, v in e.items() if k not in ("seq", "ts", "type", "prev", "mac")})
    return m


def tasks():
    return load_tasks("heldout") + load_tasks("stale") + load_tasks("control")


def offline() -> list[dict]:
    rows = []
    for arm in ARMS:
        for src in ("r1", "r2", "r3"):
            m = memory(arm, src, None)
            items = m.store.items()
            for t in tasks():
                v = repo_version(REPOS_DIR / t.repo)
                r = m.retrieve(t, v)
                scores = dict(m.ranking(t, None, v)[0])
                inj = r.ids
                need = set(t.conventions) & CORE
                got = {c for i in inj for c in tiers.topics(items[i]["title"] + " " + items[i]["content"])}
                avail = {c for i, it in items.items() if i in scores and scores[i] > 0 and tiers.tier(it) != "candidate"
                         for c in tiers.topics(it["title"] + " " + it["content"])}
                displaced = [c for c in need if c in avail and c not in got and any(tiers.tier(items[i]) != "core" for i in inj)]
                effective = sum(bool(tiers.topics(items[i]["title"] + " " + items[i]["content"]) & set(t.conventions)
                                     or any(re.search(rx, items[i]["content"], re.I) for c, rx in
                                            {"C2": r"BillingError", "C3": r"ensure_utc|time[- ]?zone"}.items() if c in t.conventions))
                                for i in inj)
                wrong = (sum(bool(OLD.search(items[i]["content"]) and "approv" in items[i]["content"].lower()) for i in inj)
                         if t.group == "stale" else len(inj) if t.repo == "simkit" else 0)
                rows.append({"arm": arm, "memory": src, "task": t.id, "group": t.group, "injected": len(inj), "need_core": len(need),
                             "core_injected": len(need & got), "displaced": len(displaced), "effective": effective, "wrong": wrong,
                             "tokens": len(r.context) // 4, "c5_need": "C5" in need, "c5_got": "C5" in got})
    return rows


def one(out: Path, arm: str, src: str, n: int, task) -> dict:
    base = out / f"attest_v4_{arm}" / f"{src}_{n}"
    m = memory(arm, src, base / "memory")
    r = run_task(task, m, base / task.id, settings=Settings(policy_guard=True), update_memory=False)
    return {"condition": f"attest_v4_{arm}", "rep": f"{src}_{n}", "task_id": task.id, "group": task.group, "first_pass": r["first_pass"],
            "crashed": r["attempts"][0]["crashed"], "prompt_tokens": r["attempts"][0]["tokens"]["prompt"]}


def summarise(off: list[dict], runs: list[dict]) -> list[str]:
    lines = ["# Memory crowding ablation (exploratory)", "", "Offline, same memories, per task (held-out, stale, control):", "",
             "| Arm | Needed core rules injected | C5 injected when needed | Displaced | Effective notes / task | Notes / task | Wrong injections | Memory tokens / task |",
             "|---|---|---|---|---|---|---|---|"]
    for arm in ARMS:
        g = [r for r in off if r["arm"] == arm]
        nc = sum(r["need_core"] for r in g)
        c5 = [r for r in g if r["c5_need"]]
        lines.append(f"| {arm} | {sum(r['core_injected'] for r in g)}/{nc} ({sum(r['core_injected'] for r in g) / max(1, nc):.0%}) | "
                     f"{sum(r['c5_got'] for r in c5)}/{len(c5)} | {sum(r['displaced'] for r in g)} | {sum(r['effective'] for r in g) / len(g):.1f} | "
                     f"{sum(r['injected'] for r in g) / len(g):.1f} | {sum(r['wrong'] for r in g)} | {sum(r['tokens'] for r in g) / len(g):.0f} |")
    if runs:
        ok = [r for r in runs if not r["crashed"]]
        lines += ["", f"End to end ({len(runs)} runs, {len(runs) - len(ok)} crashed):", "",
                  "| Arm | Held-out pass@1 | vs A (paired by task) | vs C | Stale | Control | Prompt tokens / run |", "|---|---|---|---|---|---|---|"]
        pa = {p["condition"]: p for p in paired(ok, "heldout", baseline="attest_v4_A")}
        pc = {p["condition"]: p for p in paired(ok, "heldout", baseline="attest_v4_C")} if "C" in ARMS else {}
        for arm in ARMS:
            c = f"attest_v4_{arm}"
            g = [r for r in ok if r["condition"] == c]
            rate = lambda grp: sum(r["first_pass"] for r in g if r["group"] == grp) / max(1, sum(r["group"] == grp for r in g))  # noqa: E731
            p = pa.get(c)
            vs = "–" if arm == "A" else f"{p['mean_diff']:+.0%} [{p['ci_low']:+.0%}, {p['ci_high']:+.0%}]"
            q = pc.get(c)
            vc = "–" if q is None else f"{q['mean_diff']:+.0%} [{q['ci_low']:+.0%}, {q['ci_high']:+.0%}]"
            lines.append(f"| {arm} | {rate('heldout'):.0%} | {vs} | {vc} | {rate('stale'):.0%} | {rate('control'):.0%} | "
                         f"{sum(r['prompt_tokens'] for r in g) / max(1, len(g)):,.0f} |")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--parallel", type=int, default=40)
    ap.add_argument("--offline-only", action="store_true")
    ap.add_argument("--arms", default="")
    args = ap.parse_args()
    if args.arms:
        ARMS[:] = [a.upper() for a in args.arms.split(",")]
    args.out.mkdir(parents=True, exist_ok=True)
    off = offline()
    runs = []
    if not args.offline_only:
        jobs = [(arm, src, n, t) for arm in ARMS for src, n in RUNS for t in tasks()]
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            runs = list(pool.map(lambda j: one(args.out, *j), jobs))
    (args.out / "results.json").write_text(json.dumps({"offline": off, "runs": runs}, indent=2) + "\n")
    lines = summarise(off, runs)
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
