"""Three states on the third frozen set (D60; offline, real workspaces, empty memory, no model calls).

Set: benchmark/judgement/set3_cases.json (committed before this ran). For each case: the task's reference
workspace with the advice applied; the change's diff against the task's starting code; the hidden tests
must pass (else the case is excluded, as the gate would not learn from it). Evidence, all deterministic:
policy (a registered id in the evidence), trusted reviewer (the quote is in a trusted comment; the insider
cases extend the trust list), counterfactual test (D59, now with signature rules), team code checks (D60).
The semantic reviewer is not called: with an empty memory it has no rule to cite.

Compared: v3.1 (a note is a rule if it has a policy, a trusted reviewer or a counterfactual test) and v4
(three states). Critical errors, fixed before running: a correct note Rejected, a wrong or undecidable note
Approved (or, for v3.1, made a rule). Uncertain counts as human review, not as an error.

Changed after the first evaluation (disclosed): code checks read only the note's applied line, and a code
convention is not validated by the counterfactual test (routing by rule kind). The first evaluation's
report is kept as report_first.md.

Usage: python scripts/three_state_eval.py --out runs/three_state
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_task, materialize  # noqa: E402
from attest.memory import codechecks  # noqa: E402
from attest.memory.admission import _norm, policy_references  # noqa: E402
from attest.memory.counterfactual import apply, check_all, counterfactuals  # noqa: E402
from attest.memory.evidence import references  # noqa: E402
from attest.memory.gateway import about, benchmark_trust, three_state  # noqa: E402

SETS = {"set3": "benchmark/judgement/set3_cases.json", "set2": "benchmark/judgement/counterfactual_cases.json"}


def evaluate(cs: dict, trust) -> dict:
    task = load_task(cs["task"])
    note = cs["candidate"]
    text = f"{note['title']} {note['content']}"
    with tempfile.TemporaryDirectory() as tmp:
        ws = materialize(task, Path(tmp) / "ws", "reference")
        stub = materialize(task, Path(tmp) / "stub", "stub")
        f = ws / cs["file"]
        f.write_text(apply(f.read_text(), cs.get("after") or []))
        before = (stub / cs["file"]).read_text().splitlines(keepends=True) if (stub / cs["file"]).exists() else []
        diff = "".join(difflib.unified_diff(before, f.read_text().splitlines(keepends=True), f"a/{cs['file']}", f"b/{cs['file']}"))
        cf = check_all(task, ws, cs["file"], counterfactuals(f.read_text(), note["applied_in_diff"], text), about(text))
    reviews = cs.get("reviews") or []
    trusted = trust.trusted | {_norm(t) for t in cs.get("insider_trusted") or []}
    reviewer = any(_norm(note["evidence_quote"]) in _norm(r) and _norm(r) in trusted for r in reviews)
    policy = any(r.split("-", 1)[0] in ("FIN", "POL", "SEC", "INC") and r in trust.registry for r in references(note["evidence_quote"]))
    code = codechecks.run(task.repo, text, note["applied_in_diff"])
    v4 = three_state(policy=policy, counterfactual=cf, code=code, reviewer=reviewer, repeated=False)
    v31 = "rule" if (policy or reviewer or cf.get("validated")) else "not a rule"
    truth = cs.get("truth") or {"trusted": "correct", "wrong": "wrong", "undecidable": "undecidable"}[cs["class"]]
    return {"case": cs["id"], "truth": truth, "kind": cs.get("kind_by_construction", ""), "after_passed": cf.get("after_passed", True),
            "counterfactual": cf.get("status"), "code": code, "reviewer": reviewer, "policy": policy,
            "v31": v31, "v4": v4["state"], "v4_detail": v4}


def critical(r: dict, system: str) -> bool:
    d = r[system]
    if system == "v31":
        return d == "rule" and r["truth"] != "correct"
    return (r["truth"] == "correct" and d == "rejected") or (r["truth"] != "correct" and d == "approved")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    trust = benchmark_trust()
    out, lines = {}, ["# Three states on frozen sets (offline, real workspaces, empty memory)", ""]
    for name, path in SETS.items():
        rows = [evaluate(cs, trust) for cs in json.loads((ROOT / path).read_text())]
        for r in rows:
            print(name, json.dumps({k: r[k] for k in ("case", "truth", "v31", "v4", "counterfactual")}), flush=True)
        valid = [r for r in rows if r["after_passed"]]
        out[name] = rows
        lines += [f"## {name} ({len(valid)} cases; excluded, advice fails the tests: {', '.join(r['case'] for r in rows if not r['after_passed']) or 'none'})", "",
                  "| Truth | n | v3.1 rule | v4 approved | v4 uncertain | v4 rejected |", "|---|---|---|---|---|---|"]
        for t in ("correct", "wrong", "undecidable"):
            g = [r for r in valid if r["truth"] == t]
            lines.append(f"| {t} | {len(g)} | {sum(r['v31'] == 'rule' for r in g)} | {sum(r['v4'] == 'approved' for r in g)} | "
                         f"{sum(r['v4'] == 'uncertain' for r in g)} | {sum(r['v4'] == 'rejected' for r in g)} |")
        lines += ["", f"Critical errors: v3.1 {sum(critical(r, 'v31') for r in valid)}, v4 {sum(critical(r, 'v4') for r in valid)}.", "",
                  "| Case | Truth | Kind | v3.1 | v4 | Counter-evidence | Hard | Soft | Counterfactual |", "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            d = r["v4_detail"]
            lines.append(f"| {r['case']} | {r['truth']} | {r['kind']} | {r['v31']} | **{r['v4']}** | {', '.join(d['counter']) or '–'} | "
                         f"{', '.join(d['hard']) or '–'} | {', '.join(d['soft']) or '–'} | {r['counterfactual']} |")
        lines.append("")
    (args.out / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
