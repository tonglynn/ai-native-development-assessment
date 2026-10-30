"""Failure attribution, step 1: validate a generated check against the evidence that created its rule.

Forgetting V2 showed that three evidence states work when a failure can be pinned on the
note that caused it, and that one-prompt generated checks (scripts/rule_checks.py) cannot yet
be trusted to do that: narrow checks miss, broad checks false-alarm. This tests the cheapest
safeguard: before a check's verdicts count as evidence, it must reproduce the review that
created its rule. It must flag the attempt the reviewer rejected, and pass the accepted change.

Evidence: each learned note comes from a learning task of the main experiment. Only the
accepted diff was stored (final.diff), so the rejected first attempt is rebuilt by replaying
the agent's recorded shell commands in a fresh copy of the task's workspace. Fidelity check:
replaying both attempts must reproduce final.diff exactly; tasks that do not are excluded.
The code given to a check is, as in rule_checks, the top-level functions the agent added or
changed (a new module whole).

  full validation      the note's task was rejected first (13 notes): the check must flag the
                       rejected version and pass the accepted one
  accepted-only        the task passed first time (12 notes): the check must pass the accepted
                       version (a weaker filter, reported apart)

Then, on the 17 ledgerly 1.0.0 tasks minus the note's own source task (no evaluation on the
evidence used for validation): detection, false alarms and usefulness as in rule_checks, for
checks that pass validation vs those that fail it; and attribution precision, the share of a
check's flags that land on a solution that really breaks the note's primary convention.

Reading rule, fixed before running: validation is a useful filter if, among fully validated
notes, checks that pass have a lower false-alarm rate on references and a larger useful share
than checks that fail, and it keeps every check that was useful. With 13 notes this can show a
direction, not a rate.

Replay safety: the recorded commands run in a temporary copy with a minimal environment (no
API key), a timeout per command, and paths rewritten to the copy.

Usage: python scripts/failure_attribution.py --out runs/failure_attribution
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import rule_checks as rc  # noqa: E402
from forgetting_eval import primary  # noqa: E402

from attest.benchmark import load_task  # noqa: E402
from attest.runner import materialize, restore_tests, workspace_diff  # noqa: E402

WS_RE = re.compile(r"/tmp/attest_workspaces/[^/\s'\"]+/workspace")


def actions(traj: Path) -> list[str]:
    out = []
    for m in json.loads(traj.read_text())["messages"]:
        for a in (m.get("extra") or {}).get("actions") or []:
            if a.get("command"):
                out.append(a["command"])
    return out


def run_commands(cmds: list[str], ws: Path) -> int:
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin", "HOME": str(ws.parent), "LANG": "C.UTF-8", "PAGER": "cat"}
    failures = 0
    for c in cmds:
        c = WS_RE.sub(str(ws), c)
        try:
            p = subprocess.run(["bash", "-c", c], cwd=ws, env=env, capture_output=True, text=True, timeout=60)
            failures += p.returncode != 0
        except subprocess.TimeoutExpired:
            failures += 1
    return failures


def changed_code(task, ws: Path, tmp: Path) -> list[dict]:
    stub = materialize(task, tmp / "_stub", "stub")
    out = []
    for f in sorted(ws.rglob("*.py")):
        rel = f.relative_to(ws)
        if rel.parts[0] == "tests" or "__pycache__" in rel.parts or rel.name == "conftest.py":
            continue
        new = f.read_text()
        old = (stub / rel).read_text() if (stub / rel).exists() else None
        if new == old:
            continue
        if old is None:
            out.append({"path": rel.as_posix(), "source": new})
            continue
        try:
            before = {n.name: ast.get_source_segment(old, n) for n in ast.parse(old).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            tree = ast.parse(new)
        except SyntaxError:
            out.append({"path": rel.as_posix(), "source": new})
            continue
        parts = [ast.get_source_segment(new, n) for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and ast.get_source_segment(new, n) != before.get(n.name)]
        if parts:
            out.append({"path": rel.as_posix(), "source": "\n\n\n".join(parts) + "\n"})
    shutil.rmtree(stub, ignore_errors=True)
    return out


def replay(rep: str, task_id: str) -> dict:
    task = load_task(task_id)
    run = ROOT / "runs/main/attest" / rep / task_id
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ws = materialize(task, tmp / "workspace", "stub")
        fail1 = run_commands(actions(run / "attempt1.traj.json"), ws)
        restore_tests(task, ws)
        rejected = changed_code(task, ws, tmp) if (run / "attempt2.traj.json").exists() else None
        fail2 = run_commands(actions(run / "attempt2.traj.json"), ws) if (run / "attempt2.traj.json").exists() else 0
        restore_tests(task, ws)
        accepted = changed_code(task, ws, tmp)
        faithful = workspace_diff(task, ws, tmp / "d") == (run / "final.diff").read_text()
    return {"rejected": rejected, "accepted": accepted, "faithful": faithful, "failed_commands": fail1 + fail2}


def flags(code: str, cases: list[dict]) -> list[bool | None]:
    res = rc.run_check(code, cases) if cases else []
    return [None if "error" in r else bool(r.get("violations")) for r in res]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    gens = {g["key"]: g for g in json.loads((ROOT / "runs/rule_checks/checks.json").read_text())}
    validation = {t["task"]: t for t in json.loads((ROOT / "benchmark/validation.json").read_text())["tasks"]}
    cases = rc.cases()
    replays, rows = {}, []
    for n in rc.notes():
        rep, nid = n["key"].split("/")
        it = json.loads((ROOT / f"runs/main/attest/{rep}/memory/after_learn.json").read_text())[nid]
        src = it["source"]["task_id"]
        if (rep, src) not in replays:
            replays[(rep, src)] = replay(rep, src)
            print(json.dumps({"replay": f"{rep}/{src}", "faithful": replays[(rep, src)]["faithful"],
                              "failed_commands": replays[(rep, src)]["failed_commands"]}), flush=True)
        rp, g = replays[(rep, src)], gens[n["key"]]
        conv = primary(f"{n['title']} {n['content']}")
        row = {"key": n["key"], "title": n["title"], "source_task": src, "primary": conv, "faithful": rp["faithful"],
               "kind": "full" if rp["rejected"] else "accepted-only", "checkable": g["checkable"]}
        if not g["checkable"] or not g["code"].strip() or not rp["faithful"]:
            rows.append(dict(row, validated=None))
            continue
        acc = flags(g["code"], rp["accepted"])
        rej = flags(g["code"], rp["rejected"]) if rp["rejected"] else []
        passes_accepted = all(f is False for f in acc)
        flags_rejected = any(f for f in rej) if rp["rejected"] else None
        validated = passes_accepted and (flags_rejected if rp["rejected"] else True)
        evalc = [c for c in cases if c["task"] != src]
        res = rc.run_check(g["code"], evalc)
        flagged = {(c["task"], c["kind"]) for c, r in zip(evalc, res) if r.get("violations")}
        errors = sum("error" in r for r in res)
        refs = sorted({c["task"] for c in evalc if c["kind"] == "reference"})
        targets = sorted({c["task"] for c in evalc if c["kind"] == "naive" and conv in validation[c["task"]]["naive_conv_failed"]}) if conv else []
        detected = [t for t in targets if (t, "naive") in flagged]
        fa = sorted(t for t in refs if (t, "reference") in flagged)
        hits = [k for k in flagged if k[1] == "naive" and conv and conv in validation[k[0]]["naive_conv_failed"]]
        det = len(detected) / len(targets) if targets else None
        rows.append(dict(row, passes_accepted=passes_accepted, flags_rejected=flags_rejected, validated=validated,
                         detection=det, false_alarms=fa, false_alarm_rate=len(fa) / len(refs), errors=errors,
                         useful=(not errors and det is not None and det >= 0.5 and len(fa) <= 0.1 * len(refs)),
                         attribution_precision=(len(hits) / len(flagged)) if flagged else None, n_flags=len(flagged)))
    (args.out / "results.json").write_text(json.dumps({"rows": rows, "replays": {f"{k[0]}/{k[1]}": {kk: vv for kk, vv in v.items() if kk in ("faithful", "failed_commands")}
                                                                                for k, v in replays.items()}}, indent=2) + "\n")
    pct = lambda x: "–" if x is None else f"{x:.0%}"  # noqa: E731
    lines = ["# Validating generated checks against the evidence that created their rule (exploratory)", "",
             f"Replays faithful (both attempts reproduce final.diff): {sum(v['faithful'] for v in replays.values())} of {len(replays)}.", "",
             "| Note | Source task | Validation | Passes accepted | Flags rejected | Validated | Detection | False alarms (of 16) | Useful | Attribution precision |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("validated") is None:
            why = "not checkable" if not r["checkable"] else "replay not faithful"
            lines.append(f"| {r['key']} {r['title']} | {r['source_task']} | {r['kind']} | – | – | – ({why}) | – | – | – | – |")
            continue
        lines.append(f"| {r['key']} {r['title']} | {r['source_task']} | {r['kind']} | {'yes' if r['passes_accepted'] else 'no'} | "
                     f"{'–' if r['flags_rejected'] is None else 'yes' if r['flags_rejected'] else 'no'} | {'**yes**' if r['validated'] else 'no'} | "
                     f"{pct(r['detection'])} | {len(r['false_alarms'])} | {'yes' if r['useful'] else 'no'} | {pct(r['attribution_precision'])} |")
    lines += ["", "| Validation | Group | Checks | Mean false-alarm rate | Useful | Flags | Attribution precision (pooled) |", "|---|---|---|---|---|---|---|"]
    for kind in ("full", "accepted-only"):
        for v in (True, False):
            rs = [r for r in rows if r["kind"] == kind and r.get("validated") is v]
            if not rs:
                continue
            fl = sum(r["n_flags"] for r in rs)
            hit = sum(round((r["attribution_precision"] or 0) * r["n_flags"]) for r in rs)
            lines.append(f"| {kind} | {'pass' if v else 'fail'} | {len(rs)} | {sum(r['false_alarm_rate'] for r in rs) / len(rs):.0%} | "
                         f"{sum(r['useful'] for r in rs)} | {fl} | {pct(hit / fl if fl else None)} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
