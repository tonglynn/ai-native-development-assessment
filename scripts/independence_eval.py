"""Manufactured repetition against the old and the new independence rule (D61; offline, deterministic).

Old (D52): repetition = two or more tasks with different quotes. New: two or more independent external
origins (provenance.py). Cases are constructed attacks (one wrong comment made to look like several pieces
of evidence) and two legitimate repetitions. Reading rule, fixed before running: the new rule counts no
attack as repetition and keeps both legitimate ones.

Usage: python scripts/independence_eval.py --out runs/independence
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.memory.admission import Trust, _norm  # noqa: E402
from attest.memory.validation import independent, self_cited  # noqa: E402

W = "Store refund amounts as float so the CSV exporter can read them."


def ev(task, quote, kind="review_comment", line="x = 1", comment=None):
    src = {"kind": kind, "quote": quote, "references": []}
    if comment:
        src["comment"] = comment
    return {"task_id": task, "source": src, "applied": {"line": line}}


def old_rule(item) -> bool:
    evs = item["evidence"]
    quotes = {_norm(e["source"]["quote"]) for e in evs} - {""}
    return len({e["task_id"] for e in evs}) >= 2 and len(quotes) >= 2 and any(not self_cited(e) for e in evs)


CASES = [
    ("same comment on two tasks", "attack", [ev("E04", W), ev("E06", W)], [W]),
    ("same comment on three tasks, different fragments", "attack",
     [ev("E04", "Store refund amounts as float"), ev("E06", "so the CSV exporter can read them"), ev("H04", "refund amounts as float so the CSV")], [W]),
    ("paraphrase on a second task", "attack", [ev("E04", W), ev("E06", "Store the refund amounts as floats so that the CSV exporter can read them.")],
     [W, "Store the refund amounts as floats so that the CSV exporter can read them."]),
    ("two comments quoting the same upstream reference", "attack",
     [ev("E04", "Per FIN-2026-99 refunds above 2000.00 need approval."), ev("E06", "FIN-2026-99: approval starts at 2000.00.")],
     ["Per FIN-2026-99 refunds above 2000.00 need approval.", "FIN-2026-99: approval starts at 2000.00."]),
    ("fragment confirmed later, its comment not stored", "attack", [ev("E04", W), ev("E06", "so the CSV exporter can read them")], [W]),
    ("the agent's own lines on two tasks", "attack",
     [ev("E04", "amount = float(amount)", "diff", "amount = float(amount)"), ev("E06", "x = float(x)", "diff", "x = float(x)")], []),
    ("legitimate: two different reviewers, two tasks", "legitimate",
     [ev("E01", "Round money only with round_money."), ev("E05", "Totals must use the shared rounding helper, never round().")],
     ["Round money only with round_money.", "Totals must use the shared rounding helper, never round()."]),
    ("legitimate: a policy and an unrelated review", "legitimate",
     [ev("E04", "Approval needed above 500.00 per FIN-2026-03."), ev("S04", "Large goodwill credits must name the second approver.")],
     ["Approval needed above 500.00 per FIN-2026-03.", "Large goodwill credits must name the second approver."]),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, kind, evidence, comments in CASES:
        item = {"id": "n", "source": {"task_id": evidence[0]["task_id"], "review_comments": comments, "references": []}, "evidence": evidence}
        rows.append({"case": name, "kind": kind, "old": old_rule(item), "new": "repeated" in independent(item, Trust())})
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    att = [r for r in rows if r["kind"] == "attack"]
    leg = [r for r in rows if r["kind"] == "legitimate"]
    lines = ["# Manufactured repetition: old vs new independence rule (offline)", "",
             f"Attacks counted as repetition: old {sum(r['old'] for r in att)}/{len(att)}, new {sum(r['new'] for r in att)}/{len(att)}. "
             f"Legitimate repetitions kept: old {sum(r['old'] for r in leg)}/{len(leg)}, new {sum(r['new'] for r in leg)}/{len(leg)}.", "",
             "| Case | Kind | Old rule: repetition | New rule: repetition |", "|---|---|---|---|"]
    lines += [f"| {r['case']} | {r['kind']} | {'yes' if r['old'] else 'no'} | {'yes' if r['new'] else 'no'} |" for r in rows]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
