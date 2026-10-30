"""Context-management experiment (exploratory; not part of the preregistered study).

Scenario: one long agent session. Earlier in it the agent worked on four ledgerly
2.0.0 tasks (S04, S01, S02, S03; their real no-memory trajectories from
runs/pilot5_nomem, 72 messages, about 20k tokens). In S04 the reviewer stated the
approval rule: "accept an optional keyword-only `approved_by=None` ... raise
BillingError("approval_required") ... 1000.00 since 2.0.0". Now, in the same session,
the agent gets S05 (outage refunds), which needs exactly that rule. No long-term
memory is used: the only place the rule exists is the session history.

Arms (same agent, model and task; only the context handling differs):
  no_session  S05 alone, without the earlier session (what the agent knows without history)
  full        the whole session, no budget (ceiling)
  window      budget, sliding window only
  summary     budget, sliding window + a plain model summary of the older turns
  manager     budget, Attest Context Manager (structured extraction, pinned constraints,
              extractive summary, sliding window)

Measures: offline, whether the facts the task needs (1000.00, approved_by,
approval_required) are in the context the model receives, at several budgets, and
how many pinned tokens the model summary dropped; end to end, S05 first-attempt
pass rate and its C6 checks, prompt tokens per run.

Usage (needs DEEPSEEK_API_KEY): python scripts/context_eval.py --out runs/context_eval --reps 3
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

from attest import llm  # noqa: E402
from attest.benchmark import load_task  # noqa: E402
from attest.context.manager import ContextManager, ManagedModel, extract_state, fidelity, sanitize, tokens_of  # noqa: E402
from attest.memory.base import NoMemory  # noqa: E402
from attest.runner import Settings, run_task  # noqa: E402

SOURCE = ROOT / "runs" / "pilot5_nomem" / "no_memory"
SESSION = ("S04", "S01", "S02", "S03")
NEEDED = ("1000.00", "approved_by", "approval_required")
ARMS = ("no_session", "full", "window", "summary", "manager")
SUMMARY_PROMPT = ("You compress the earlier part of a coding agent's session so it can continue working. "
                  "Write a concise summary of what was done and anything it should remember. "
                  'Return JSON: {"summary": "<text>"}')


def session_prefix() -> list[dict]:
    msgs = []
    for task in SESSION:
        for attempt in (1, 2):
            path = SOURCE / task / "r1" / f"attempt{attempt}.traj.json"
            if path.exists():
                msgs += [m for m in json.loads(path.read_text())["messages"] if m["role"] in ("user", "assistant", "tool")]
    return sanitize(msgs)


def summarizer(transcript: str) -> str:
    return str(llm.complete_json(SUMMARY_PROMPT, transcript[-60000:]).get("summary", ""))


def offline(prefix: list[dict], budgets=(4000, 6000, 8000)) -> list[dict]:
    system = {"role": "system", "content": "You are a helpful assistant that can interact with a computer."}
    task = {"role": "user", "content": "New task in the same repository: " + load_task("S05").issue + FOLLOW_UP}
    full = [system] + prefix + [task]
    rows = []
    for budget in budgets:
        for strategy in ("full", "window", "summary", "manager"):
            cm = ContextManager(strategy, budget, summarizer=summarizer)
            ctx = cm.assemble(full, task_index=len(full) - 1)
            text = "\n".join(str(m.get("content") or "") for m in ctx)
            row = {"budget": budget, "strategy": strategy, "tokens": tokens_of(ctx),
                   "needed_facts_in_context": {f: f in text for f in NEEDED}, "dropped_messages": cm.log[-1]["dropped"]}
            if strategy == "summary" and cm._summary_cache:
                summary = next(iter(cm._summary_cache.values()))
                row["summary_fidelity"] = fidelity(summary, extract_state(prefix))
                row["summary_excerpt"] = summary[:600]
            rows.append(row)
            print(json.dumps({k: v for k, v in row.items() if k != "summary_excerpt"}), flush=True)
    return rows


# Design 2 (after design 1 had a ceiling of 0: with the whole session in context the agent still did not
# apply the earlier review rule to a new task). The user now says what a user would say; the no_session
# arm gets the same sentence. Design 1 is kept in runs/context_eval_design1.
FOLLOW_UP = " Apply the review guidance you received earlier in this session."


def one(arm: str, rep: int, prefix: list[dict], out: Path, budget: int) -> dict:
    task = dataclasses.replace(load_task("S05"), issue=load_task("S05").issue + FOLLOW_UP)
    if arm == "no_session":
        settings = Settings()
    else:
        cm = ContextManager("full" if arm == "full" else arm, budget, summarizer=summarizer)
        settings = Settings(wrap_model=lambda m, cm=cm: ManagedModel(m, cm, prefix))
    r = run_task(task, NoMemory(), out / arm / f"r{rep}", settings=settings, update_memory=False)
    first = r["attempts"][0]
    row = {"arm": arm, "rep": rep, "first_pass": r["first_pass"], "crashed": first["crashed"], "tests_failed": first["tests_failed"],
           "prompt_tokens": first["tokens"]["prompt"], "steps": first["steps"]}
    if arm != "no_session":
        row["context_log"] = cm.log[-3:]
    print(json.dumps(row), flush=True)
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--budget", type=int, default=6000)
    ap.add_argument("--parallel", type=int, default=5)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    prefix = session_prefix()
    print(f"session prefix: {len(prefix)} messages, ~{tokens_of(prefix)} tokens", flush=True)
    rows = offline(prefix)
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        runs = list(pool.map(lambda ar: one(ar[0], ar[1], prefix, args.out, args.budget),
                             [(a, r) for r in range(1, args.reps + 1) for a in ARMS]))
    summary = []
    for arm in ARMS:
        rs = [r for r in runs if r["arm"] == arm]
        summary.append({"arm": arm, "runs": len(rs), "crashed": sum(r["crashed"] for r in rs),
                        "pass@1": sum(r["first_pass"] for r in rs) / len(rs),
                        "c6_blocks_failed": sum(any("c6_blocks" in t for t in r["tests_failed"]) for r in rs),
                        "c6_allows_failed": sum(any("c6_allows" in t for t in r["tests_failed"]) for r in rs),
                        "prompt_tokens_mean": sum(r["prompt_tokens"] for r in rs) / len(rs)})
    (args.out / "results.json").write_text(json.dumps({"budget": args.budget, "offline": rows, "runs": runs,
                                                       "summary": summary}, indent=2, default=str) + "\n")
    lines = ["# Context management on a long session (exploratory)", "",
             f"Earlier session: {len(prefix)} messages (~{tokens_of(prefix)} tokens) from S04, S01, S02, S03; then task S05. "
             f"Budget {args.budget} tokens for window / summary / manager. No long-term memory.", "",
             "| Arm | Runs | Crashed | pass@1 | C6 blocks failed | C6 allows failed | Prompt tokens / run |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {s['arm']} | {s['runs']} | {s['crashed']} | {s['pass@1']:.0%} | {s['c6_blocks_failed']} | {s['c6_allows_failed']} | "
              f"{s['prompt_tokens_mean']:,.0f} |" for s in summary]
    lines += ["", "Facts S05 needs, present in the context the model receives (offline):", "",
              "| Budget | Strategy | Tokens | 1000.00 | approved_by | approval_required | Summary kept pinned tokens |",
              "|---|---|---|---|---|---|---|"]
    for r in rows:
        f = r["needed_facts_in_context"]
        fid = r.get("summary_fidelity")
        lines.append(f"| {r['budget']} | {r['strategy']} | {r['tokens']:,} | {'yes' if f['1000.00'] else 'no'} | "
                     f"{'yes' if f['approved_by'] else 'no'} | {'yes' if f['approval_required'] else 'no'} | "
                     f"{'' if not fid else str(fid['kept']) + '/' + str(fid['pinned'])} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
