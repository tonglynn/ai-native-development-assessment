"""Context management on a longer session with several policy changes (D49; exploratory).

Extends scripts/context_eval.py, whose single scenario (72 messages, one rule) was designed after
seeing results. This scenario is fixed before any run:

Session (about 170 messages): the real no-memory trajectories of E01, E02, E03, E05, E06
(ledgerly 1.x maintenance) and then S04, S01, S02, S03 (ledgerly 2.0), from runs/main and
runs/pilot5_nomem, with five SYNTHETIC product-owner messages interleaved (labelled as such):
  P1 (start)        FIN-2026-03: support credits and refunds above 500.00 need approved_by     -> outdated by P3
  P2 (after E03)    FIN-2026-05: CSV exports use semicolons                                     -> irrelevant to the task
  P3 (after S04)    FIN-2026-11 supersedes FIN-2026-03 on 2.x: the threshold is 1000.00
  P4 (after S01)    FIN-2026-12: every credit or refund writes ledgerly.audit.record(...)
  P5 (after S02)    FIN-2026-05 is withdrawn                                                     -> irrelevant to the task
Then the task S05 (outage refunds on 2.0), which needs the latest threshold (1000.00, not 500.00),
approved_by and BillingError("approval_required") (C6), the audit entry (C4) and BillingError codes (C2).

Arms: no_session, full (ceiling), window, summary (plain model summary), manager (Attest Context
Manager), at budgets 4k, 8k and 12k tokens (full and no_session once); and the same session with a
second agent model (deepseek-v4-pro) for full and manager at 8k.

Measures: offline, whether each needed fact is in the context the model receives (fact retention),
whether the outdated 500.00 rule is there too (an outdated constraint kept), tokens (saving against
full); end to end, S05 first-attempt pass, its C6 and C4 checks, prompt tokens.

Reading rule, fixed before running: 3 runs per arm and budget, so end-to-end results are described,
not tested; the offline retention table is deterministic and is the main result; a strategy that keeps
the outdated 500.00 alongside 1000.00 without marking it superseded is reported as a defect even if
the task passes. Multi-model: one extra model only; 100+ turn sessions with tool use are what this is.

Usage (needs DEEPSEEK_API_KEY): python scripts/context_long.py --out runs/context_long --reps 3
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from attest.benchmark import load_task  # noqa: E402
from attest.context.manager import ContextManager, ManagedModel, sanitize, tokens_of  # noqa: E402
from attest.memory.base import NoMemory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402
from context_eval import summarizer  # noqa: E402

V1 = (ROOT / "runs/main/no_memory/r1", ("E01", "E02", "E03", "E05", "E06"))
V2 = (ROOT / "runs/pilot5_nomem/no_memory", ("S04", "S01", "S02", "S03"))
TAG = "[synthetic product-owner message, part of the benchmark scenario]"
POLICY = {
    "P1": f"{TAG} Policy FIN-2026-03: support credits and refunds above 500.00 need an `approved_by`; otherwise raise BillingError(\"approval_required\").",
    "P2": f"{TAG} Policy FIN-2026-05: CSV exports for finance must use semicolons as separators.",
    "P3": f"{TAG} Policy FIN-2026-11 supersedes FIN-2026-03 on ledgerly 2.x: the approval threshold for support credits and refunds is now 1000.00 (amounts above 1000.00 need `approved_by`).",
    "P4": f"{TAG} Policy FIN-2026-12: every support credit or refund must write an audit entry with ledgerly.audit.record(...).",
    "P5": f"{TAG} FIN-2026-05 is withdrawn; exports keep their previous format.",
}
AFTER = {"start": "P1", "E03": "P2", "S04": "P3", "S01": "P4", "S02": "P5"}
NEEDED = {"1000.00": "latest threshold", "approved_by": "approval argument", "approval_required": "error code",
          "audit.record": "audit entry (C4)", "FIN-2026-11": "the superseding policy"}
OUTDATED = "500.00"
FOLLOW_UP = " Apply the review guidance and the policy updates you received earlier in this session."
BUDGETS = (4000, 8000, 12000)
STRATEGIES = ("window", "summary", "manager")
SECOND_MODEL = "deepseek/deepseek-v4-pro"


def _traj(base: Path, task: str) -> list[dict]:
    msgs = []
    for attempt in (1, 2):
        for path in (base / task / f"attempt{attempt}.traj.json", base / task / "r1" / f"attempt{attempt}.traj.json"):
            if path.exists():
                msgs += [m for m in json.loads(path.read_text())["messages"] if m["role"] in ("user", "assistant", "tool")]
                break
    return msgs


def session_prefix() -> list[dict]:
    msgs = [{"role": "user", "content": POLICY[AFTER["start"]]}]
    for base, tasks in (V1, V2):
        for t in tasks:
            msgs += _traj(base, t)
            if t in AFTER:
                msgs.append({"role": "user", "content": POLICY[AFTER[t]]})
    return sanitize(msgs)


def task_message() -> dict:
    return {"role": "user", "content": "New task in the same repository: " + load_task("S05").issue + FOLLOW_UP}


def offline(prefix: list[dict]) -> list[dict]:
    system = {"role": "system", "content": "You are a helpful assistant that can interact with a computer."}
    full = [system] + prefix + [task_message()]
    rows = []
    for budget in BUDGETS:
        for strategy in ("full",) + STRATEGIES:
            if strategy == "full" and budget != BUDGETS[0]:
                continue
            cm = ContextManager(strategy, budget, summarizer=summarizer)
            ctx = cm.assemble(full, task_index=len(full) - 1)
            text = "\n".join(str(m.get("content") or "") for m in ctx)
            rows.append({"budget": None if strategy == "full" else budget, "strategy": strategy, "tokens": tokens_of(ctx),
                         "facts": {f: f in text for f in NEEDED}, "outdated_500_present": OUTDATED in text,
                         "superseded_marked": "supersedes FIN-2026-03" in text})
            print(json.dumps(rows[-1]), flush=True)
    return rows


def one(arm: str, budget: int | None, rep: int, prefix: list[dict], out: Path, model: str | None = None) -> dict:
    task = dataclasses.replace(load_task("S05"), issue=load_task("S05").issue + FOLLOW_UP)
    base = Settings() if model is None else Settings(model=model)
    if arm == "no_session":
        settings = base
    else:
        cm = ContextManager(arm, budget or 10**9, summarizer=summarizer)
        settings = dataclasses.replace(base, wrap_model=lambda m, cm=cm: ManagedModel(m, cm, prefix))
    tag = f"{arm}" + (f"_{budget}" if budget else "") + ("_v4pro" if model else "")
    r = run_task(task, NoMemory(), out / tag / f"r{rep}", settings=settings, update_memory=False)
    first = r["attempts"][0]
    row = {"arm": arm, "budget": budget, "model": model or "deepseek-flash", "rep": rep, "first_pass": r["first_pass"],
           "crashed": first["crashed"], "tests_failed": first["tests_failed"], "prompt_tokens": first["tokens"]["prompt"]}
    print(json.dumps(row), flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--offline-only", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    prefix = session_prefix()
    print(f"session prefix: {len(prefix)} messages, ~{tokens_of(prefix)} tokens", flush=True)
    rows = offline(prefix)
    jobs = [("no_session", None, r, None) for r in range(1, args.reps + 1)] + [("full", None, r, None) for r in range(1, args.reps + 1)]
    jobs += [(s, b, r, None) for b in BUDGETS for s in STRATEGIES for r in range(1, args.reps + 1)]
    jobs += [(a, b, r, SECOND_MODEL) for a, b in (("full", None), ("manager", 8000)) for r in range(1, args.reps + 1)]
    runs = []
    if not args.offline_only:
        with ThreadPoolExecutor(max_workers=args.parallel) as pool:
            runs = list(pool.map(lambda j: one(j[0], j[1], j[2], prefix, args.out, j[3]), jobs))
    full_tokens = next(r["tokens"] for r in rows if r["strategy"] == "full")
    summary = []
    for arm, budget, model in sorted({(r["arm"], r["budget"], r["model"]) for r in runs}, key=lambda x: (x[2], x[0], x[1] or 0)):
        rs = [r for r in runs if (r["arm"], r["budget"], r["model"]) == (arm, budget, model)]
        summary.append({"arm": arm, "budget": budget, "model": model, "runs": len(rs), "pass@1": sum(r["first_pass"] for r in rs) / len(rs),
                        "c6_failed": sum(any("c6" in t for t in r["tests_failed"]) for r in rs),
                        "c4_failed": sum(any("c4" in t for t in r["tests_failed"]) for r in rs),
                        "prompt_tokens_mean": sum(r["prompt_tokens"] for r in rs) / len(rs)})
    (args.out / "results.json").write_text(json.dumps({"prefix_messages": len(prefix), "prefix_tokens": tokens_of(prefix),
                                                       "offline": rows, "runs": runs, "summary": summary}, indent=2, default=str) + "\n")
    lines = ["# Context management, long session with policy changes (exploratory)", "",
             f"Session: {len(prefix)} messages (~{tokens_of(prefix):,} tokens), 9 real task trajectories and 5 synthetic policy messages; then S05.", "",
             "Offline: is each needed fact in the context the model receives?", "",
             "| Budget | Strategy | Tokens (saving vs full) | " + " | ".join(NEEDED) + " | outdated 500.00 present | supersession present |",
             "|---|---|---|" + "---|" * len(NEEDED) + "---|---|"]
    for r in rows:
        saving = "–" if r["strategy"] == "full" else f"{1 - r['tokens'] / full_tokens:.0%}"
        lines.append(f"| {r['budget'] or '–'} | {r['strategy']} | {r['tokens']:,} ({saving}) | " + " | ".join("yes" if r["facts"][f] else "**no**" for f in NEEDED)
                     + f" | {'yes' if r['outdated_500_present'] else 'no'} | {'yes' if r['superseded_marked'] else 'no'} |")
    if summary:
        lines += ["", "End to end (S05, first attempt):", "", "| Model | Arm | Budget | Runs | pass@1 | C6 failed | C4 failed | Prompt tokens / run |",
                  "|---|---|---|---|---|---|---|---|"]
        lines += [f"| {s['model']} | {s['arm']} | {s['budget'] or '–'} | {s['runs']} | {s['pass@1']:.0%} | {s['c6_failed']} | {s['c4_failed']} | "
                  f"{s['prompt_tokens_mean']:,.0f} |" for s in summary]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
