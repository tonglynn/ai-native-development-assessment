"""Check that every benchmark task measures what it claims to measure.

For each task we build three workspaces and verify them:

  stub       the unsolved task the agent receives        -> must FAIL hidden tests
  naive      a plausible solution without team knowledge -> must PASS public tests
             (for stale tasks: a stale v1 habit;            and FAIL >=1 convention test
              for control tasks: ledgerly habits)           (and pass behaviour tests,
                                                            except for control tasks)
  reference  a correct solution                          -> must PASS everything

Usage: python scripts/validate_benchmark.py [--json benchmark/validation.json]
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest.benchmark import load_tasks, materialize  # noqa: E402
from attest.verify import verify  # noqa: E402


def check(task, tmp: Path) -> dict:
    out = {}
    for variant in ("stub", "naive", "reference"):
        ws = materialize(task, tmp / f"{task.id}_{variant}", variant)
        out[variant] = verify(ws, task)
    stub, naive, ref = out["stub"], out["naive"], out["reference"]
    problems = []
    if stub["passed"] or not stub["func_failed"]:
        problems.append("stub already passes behaviour tests")
    if not naive["public"]["passed"]:
        problems.append("naive fails public tests")
    if not naive["conv_failed"]:
        problems.append("naive passes every convention test (no knowledge gap)")
    if task.group != "control" and naive["func_failed"]:
        problems.append(f"naive fails behaviour tests {naive['func_failed']}")
    if not ref["passed"]:
        failed = [h["name"] + ": " + h["error"] for h in ref["hidden"] if not h["passed"]]
        problems.append(f"reference fails: public={ref['public']['passed']} {failed}")
    return {
        "task": task.id,
        "group": task.group,
        "conventions": list(task.conventions),
        "naive_kind": task.naive_kind,
        "naive_conv_failed": naive["conv_failed"],
        "ok": not problems,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, help="write the validation report here")
    args = parser.parse_args()

    rows = []
    with tempfile.TemporaryDirectory(prefix="validate_") as tmp:
        for task in load_tasks():
            row = check(task, Path(tmp))
            rows.append(row)
            status = "OK  " if row["ok"] else "FAIL"
            print(f"{status} {row['task']:4} {row['group']:10} conventions={','.join(row['conventions']):9} "
                  f"naive({row['naive_kind']}) misses {','.join(row['naive_conv_failed']) or '-'}")
            for p in row["problems"]:
                print("       -", p)
    ok = all(r["ok"] for r in rows)
    print(f"\n{sum(r['ok'] for r in rows)}/{len(rows)} tasks valid")
    if args.json:
        args.json.write_text(json.dumps({"all_valid": ok, "tasks": rows}, indent=2) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
