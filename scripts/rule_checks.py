"""Point 6 of forgetting V2: turn learned rules into executable checks (exploratory).

Question: a rule that no test checks looks, to the memory, like a rule nobody needs
(forgetting V1.1). If a verified rule can be turned into an automated check, it produces
its own verification signal. Can the agent's model write such checks, and are they right?

Input: the 25 active learned notes of the main experiment (runs/main/attest/r<rep>/memory/after_learn.json).
For each, the model (deepseek-flash, thinking off, temperature 0; one fixed prompt, below,
not changed after seeing results) writes `check(path, source) -> list[str]` for one piece of
added code, or says the rule cannot be checked from the code alone.

Ground truth, from the benchmark (not from the model): for the 17 ledgerly 1.0.0 tasks
(E01-E06, H01-H11), the reference solution follows every convention; the naive solution
breaks every convention listed for the task (benchmark/validation.json, naive_conv_failed).

Measures per check:
  usable       it compiled and ran on every case without an exception or a timeout
  detection    share of naive solutions breaking one of the note's conventions (C1-C6,
               by pattern) that the check flags
  false alarm  share of the 17 reference solutions it flags
Reading rule, fixed before running: a check is *useful* when it is usable, detects at least
half of the labelled violations and false-alarms on at most 10% of the references (at most 1
of 17). Notes outside C1-C6 have no labelled violations; only their false alarms are reported.
One prompt, one run; a rerun for a pipeline bug (not the prompt) is disclosed.

Safety: generated code runs in a separate `python -I` process with an empty environment (no
API key), a 10 s timeout and a memory limit, and gets the code to check on stdin.

Not tested here: whether a rule enforced by a check can leave the prompt (needs agent runs).
Limit: the naive solutions were written by the benchmark author to break conventions plainly,
so detection is likely easier than on real code.

Usage:
  python scripts/rule_checks.py --out runs/rule_checks             # generate (model) + evaluate
  python scripts/rule_checks.py --out runs/rule_checks --evaluate-only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest import llm  # noqa: E402
from attest.analysis import CONVENTION_PATTERNS  # noqa: E402

TASKS = [f"E0{i}" for i in range(1, 7)] + [f"H{i:02d}" for i in range(1, 12)]

SYSTEM = """You turn a software team's coding rule into an automated check used in code review.
The check receives one new piece of Python code that an engineer added to a module of the
`ledgerly` billing library, and reports whether that code breaks the rule.

Write a Python function:

def check(path: str, source: str) -> list[str]:
    # path: the module the code was added to, e.g. "ledgerly/adjustments.py"
    # source: the added code (one or more top-level functions)
    # return one short message per violation; [] if the code follows the rule
    # or the rule does not apply to this code

Use only the Python standard library (for example ast and re). Do not read files, use the
network or import ledgerly. If the rule cannot be checked from the added code alone, say so.

Answer with a JSON object: {"checkable": true or false, "code": "<the full function, or empty>",
"why": "<one sentence>"}"""

RUNNER = r'''
import json, resource, sys
resource.setrlimit(resource.RLIMIT_AS, (512 * 2**20, 512 * 2**20))
job = json.load(sys.stdin)
ns = {}
try:
    exec(compile(job["code"], "<check>", "exec"), ns)
    fn = ns["check"]
except Exception as e:
    print(json.dumps({"error": f"compile: {type(e).__name__}: {e}"})); sys.exit(0)
out = []
for case in job["cases"]:
    try:
        r = fn(case["path"], case["source"])
        out.append({"violations": [str(x) for x in (r or [])]})
    except Exception as e:
        out.append({"error": f"{type(e).__name__}: {e}"})
print(json.dumps({"results": out}))
'''


def about(text: str) -> set[str]:
    import re

    return {c for c, p in CONVENTION_PATTERNS.items() if re.search(p, text, re.I)}


def notes() -> list[dict]:
    out = []
    for rep in (1, 2, 3):
        items = json.loads((ROOT / f"runs/main/attest/r{rep}/memory/after_learn.json").read_text())
        for i, it in sorted(items.items()):
            if it.get("status") in ("active", "suspect"):
                out.append({"key": f"r{rep}/{i}", "title": it["title"], "content": it["content"],
                            "files": (it.get("scope") or {}).get("files") or [],
                            "conventions": sorted(about(f"{it['title']} {it['content']}"))})
    return out


def cases() -> list[dict]:
    validation = {t["task"]: t for t in json.loads((ROOT / "benchmark/validation.json").read_text())["tasks"]}
    out = []
    for task in TASKS:
        for kind in ("reference", "naive"):
            base = ROOT / "benchmark/tasks" / task / kind
            for f in sorted([*base.rglob("*.py.append"), *base.rglob("*.py")]):  # added code, or a whole new module
                rel = f.relative_to(base).as_posix().removesuffix(".append")
                out.append({"task": task, "kind": kind, "path": rel, "source": f.read_text(),
                            "broken": validation[task]["naive_conv_failed"] if kind == "naive" else []})
    return out


def generate(note: dict) -> dict:
    user = (f"Rule: {note['title']}\n{note['content']}\n"
            f"Learned while changing: {', '.join(note['files']) or 'unknown'}\n")
    answer = llm.complete_json(SYSTEM, user)
    return {"key": note["key"], "checkable": bool(answer.get("checkable")), "code": answer.get("code") or "",
            "why": answer.get("why") or "", "raw_ok": bool(answer)}


def run_check(code: str, cs: list[dict], timeout: int = 10) -> list[dict]:
    job = json.dumps({"code": code, "cases": [{"path": c["path"], "source": c["source"]} for c in cs]})
    try:
        p = subprocess.run([sys.executable, "-I", "-c", RUNNER], input=job, capture_output=True, text=True,
                           timeout=timeout, env={}, cwd="/")
    except subprocess.TimeoutExpired:
        return [{"error": "timeout"}] * len(cs)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return [{"error": f"no result: {p.stderr.strip()[-200:]}"}] * len(cs)
    if "error" in out:
        return [{"error": out["error"]}] * len(cs)
    return out["results"]


def evaluate(note: dict, gen: dict, cs: list[dict]) -> dict:
    row = {"key": note["key"], "title": note["title"], "conventions": note["conventions"], "checkable": gen["checkable"]}
    if not gen["checkable"] or not gen["code"].strip():
        return dict(row, usable=False, why=gen["why"])
    results = run_check(gen["code"], cs)
    errors = [r["error"] for r in results if "error" in r]
    flagged = {}
    for c, r in zip(cs, results):
        if r.get("violations"):
            flagged.setdefault((c["task"], c["kind"]), []).extend(r["violations"])
    targets = sorted({c["task"] for c in cs if c["kind"] == "naive" and set(c["broken"]) & set(note["conventions"])})
    detected = [t for t in targets if (t, "naive") in flagged]
    false_alarms = sorted({t for (t, k) in flagged if k == "reference"})
    n_ref = len({c["task"] for c in cs if c["kind"] == "reference"})
    usable = not errors
    det = len(detected) / len(targets) if targets else None
    useful = usable and det is not None and det >= 0.5 and len(false_alarms) <= 0.1 * n_ref
    return dict(row, usable=usable, errors=errors[:3], n_errors=len(errors), targets=targets, detected=detected,
                detection=det, false_alarms=false_alarms, false_alarm_rate=len(false_alarms) / n_ref, useful=useful,
                sample_messages={f"{t}/{k}": v[:2] for (t, k), v in list(flagged.items())[:4]})


def report(rows: list[dict]) -> list[str]:
    pct = lambda x: "–" if x is None else f"{x:.0%}"  # noqa: E731
    lines = ["# Learned rules as executable checks (exploratory)", "",
             "25 active learned notes of the main experiment; checks written by deepseek-flash from the note alone; evaluated on the "
             "reference (follows every convention) and naive (breaks the task's conventions) solutions of the 17 ledgerly 1.0.0 tasks.", "",
             "| Note | Conventions | Checkable | Usable | Detection | False alarms (of 17 references) | Useful |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['key']} {r['title']} | {', '.join(r['conventions']) or 'outside C1-C6'} | {'yes' if r['checkable'] else 'no'} | "
                     f"{'yes' if r.get('usable') else 'no'} | {pct(r.get('detection'))} | "
                     f"{len(r.get('false_alarms') or []) if r.get('usable') else '–'} | {'**yes**' if r.get('useful') else 'no'} |")
    by_conv = {}
    for r in rows:
        for c in r["conventions"] or ["outside C1-C6"]:
            by_conv.setdefault(c, []).append(r)
    lines += ["", "| Convention | Notes | Checkable | Usable | Useful |", "|---|---|---|---|---|"]
    for c in sorted(by_conv):
        rs = by_conv[c]
        lines.append(f"| {c} | {len(rs)} | {sum(r['checkable'] for r in rs)} | {sum(bool(r.get('usable')) for r in rs)} | "
                     f"{sum(bool(r.get('useful')) for r in rs)} |")
    useful = sum(bool(r.get("useful")) for r in rows)
    lines += ["", f"Useful checks: **{useful} of {len(rows)}**. Usable: {sum(bool(r.get('usable')) for r in rows)}. "
              f"Declared not checkable: {sum(not r['checkable'] for r in rows)}."]
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--evaluate-only", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    ns, cs = notes(), cases()
    path = args.out / "checks.json"
    if args.evaluate_only:
        gens = {g["key"]: g for g in json.loads(path.read_text())}
    else:
        gens = {}
        for n in ns:
            gens[n["key"]] = generate(n)
            print(json.dumps({k: gens[n["key"]][k] for k in ("key", "checkable", "why")}), flush=True)
        path.write_text(json.dumps(list(gens.values()), indent=2) + "\n")
    rows = [evaluate(n, gens[n["key"]], cs) for n in ns]
    (args.out / "results.json").write_text(json.dumps({"prompt": SYSTEM, "rows": rows}, indent=2) + "\n")
    lines = report(rows)
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
