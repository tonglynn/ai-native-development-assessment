"""Counterfactual check vs R2 on the second frozen set (D59; offline, real workspaces, no model calls).

Set: benchmark/judgement/counterfactual_cases.json, committed before this evaluation ran. Every case is
diff evidence only, first pass, empty memory: the cold-start condition in which R2 let wrong advice
become rules. For each case: build the task's reference workspace, apply the advice (`after`), require the
hidden tests to pass (a case that fails is reported and excluded), then decide
  R2              every convention the note is about is in the task's conventions and the task passed
  counterfactual  attest.memory.counterfactual.check: a test of the note's conventions fails when the
                  note's change is reverted
With no review comment, policy id or repetition, a note is a rule exactly when its check validates it.

Reading rule, fixed before running: the counterfactual check closes the cold-start hole if it validates 0
wrong and 0 undecidable notes and at least 6 of the 8 trusted ones; R2 is reported beside it.

Usage: python scripts/counterfactual_eval.py --out runs/counterfactual
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_task, materialize  # noqa: E402
from attest.memory.counterfactual import apply, check  # noqa: E402
from attest.memory.gateway import about  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "benchmark/judgement/counterfactual_cases.json").read_text())
    rows = []
    for cs in cases:
        task = load_task(cs["task"])
        note = cs["candidate"]
        conv = about(f"{note['title']} {note['content']}")
        with tempfile.TemporaryDirectory() as tmp:
            ws = materialize(task, Path(tmp) / "ws", "reference")
            f = ws / cs["file"]
            f.write_text(apply(f.read_text(), cs["after"]))
            assert cs["candidate"]["applied_in_diff"] in f.read_text(), cs["id"]
            res = check(task, ws, cs["file"], cs["revert"], conv)
        r2 = bool(conv) and conv <= set(task.conventions) and res["after_passed"]
        rows.append({"case": cs["id"], "class": cs["class"], "task": cs["task"], "conventions": sorted(conv), "R2": r2,
                     "counterfactual": res["validated"], "status": res["status"],
                     "reverted_conv_failures": res["reverted_conv_failures"], "after_passed": res["after_passed"]})
        print(json.dumps(rows[-1]), flush=True)
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    valid = [r for r in rows if r["after_passed"]]
    tally = {cl: {k: sum(r[k] for r in valid if r["class"] == cl) for k in ("R2", "counterfactual")} | {"n": sum(r["class"] == cl for r in valid)}
             for cl in ("trusted", "wrong", "undecidable")}
    ok = tally["wrong"]["counterfactual"] == 0 and tally["undecidable"]["counterfactual"] == 0 and tally["trusted"]["counterfactual"] >= 6
    lines = ["# Counterfactual check vs R2 (second frozen set, real workspaces, cold start)", "",
             f"Cases: {len(rows)}; excluded because the advice fails the tests (the gate would not learn from it): "
             f"{', '.join(r['case'] for r in rows if not r['after_passed']) or 'none'}.", "",
             "| Class | n | Validated by R2 (→ rule) | Validated by the counterfactual check (→ rule) |", "|---|---|---|---|"]
    lines += [f"| {cl} | {t['n']} | {t['R2']} | {t['counterfactual']} |" for cl, t in tally.items()]
    lines += ["", f"Reading rule (counterfactual: wrong 0, undecidable 0, trusted at least 6 of 8): **{'met' if ok else 'not met'}**.", "",
              "| Case | Class | Task | About | R2 | Counterfactual | Why |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['case']} | {r['class']} | {r['task']} | {', '.join(r['conventions'])} | {'yes' if r['R2'] else 'no'} | "
              f"{'**yes**' if r['counterfactual'] else 'no'} | {r['status']}{(': ' + ', '.join(r['reverted_conv_failures'])) if r['reverted_conv_failures'] else ''} |"
              for r in rows]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
