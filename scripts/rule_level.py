"""Rule-level validation on a failed task (D54; offline replay of stored runs).

The gate learns nothing from a task whose final change failed verification. With the policy guard on
(D38), the poisoned tasks E04/E06 fail on the guard alone, so the correct rules learned in them
(idempotency C5, approval C6, audit C4) are lost along with the poison: held-out pass@1 36%.

Rule-level validation, fixed before replaying: from a failed task, a candidate is kept, as an OBSERVED
note (two-layer evidence, D52: shown only in its own files, never a rule until independently validated),
only if
  (a) it passes the write gate's own checks (verbatim source, applied changed line);
  (b) it does not touch the failure: none of the conventions it is about failed in the final attempt,
      and it shares no salient words (text.related) with the review comment the failing check produced;
  (c) a check of its own convention ran in that task and passed in the final attempt.
Everything else from the failed task is dropped, as now.

Data: the guard re-run of the second poison (runs/stress_poison_float_guard). With the gate on nothing was
distilled from the failed tasks, so the candidates are those the same distiller produced in the no-gate
arm for the same failed tasks (a stand-in, disclosed). Reading rule: rule-level validation is worth it if
no poison note is kept and the C4/C5/C6 rules of the failed tasks are.

Usage: python scripts/rule_level.py --out runs/rule_level
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from attest.benchmark import load_task  # noqa: E402
from attest.memory.text import related  # noqa: E402
from attest.stress import POISON_FLOAT_NOTE  # noqa: E402
from forgetting_eval import about  # noqa: E402

BASE = ROOT / "runs/stress_poison_float_guard/attest_no_gate"


def keep(note: dict, task, result: dict) -> tuple[bool, str]:
    ev = (note.get("evidence") or [{}])[-1]
    if (ev.get("source") or {}).get("kind") in (None, "none") or not ev.get("applied"):
        return False, "(a) fails the write gate's source or applied-line check"
    final = result["attempts"][-1]
    failed = set(final["conv_failed"])
    conv = about(f"{note['title']} {note['content']}")
    if conv & failed:
        return False, f"(b) about a failed convention: {sorted(conv & failed)}"
    if any(related(f"{note['title']} {note['content']}", c) for c in final.get("review_comments") or []):
        return False, "(b) shares words with the failing check's review comment"
    own = conv & set(task.conventions)
    if not own:
        return False, "(c) no check of its convention ran in this task"
    return True, f"(c) own convention checked and passed: {sorted(own)}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for rep_dir in sorted(BASE.glob("r*")):
        events = [json.loads(x) for x in (rep_dir / "memory/events.jsonl").read_text().splitlines() if x.strip()]
        for tid in ("E04", "E06"):
            result = json.loads((rep_dir / tid / "result.json").read_text())
            if result["final_pass"]:
                continue
            task = load_task(tid)
            for e in events:
                if e["type"] == "add" and e["item"]["source"]["task_id"] == tid:
                    note = e["item"]
                elif e["type"] == "update" and e.get("reason", "").endswith(f"task {tid}") and "evidence" in (e.get("fields") or {}):
                    note = dict(e.get("candidate") or {}, evidence=e["fields"]["evidence"][-1:])
                    note.setdefault("title", ""), note.setdefault("content", "")
                else:
                    continue
                ok, why = keep(note, task, result)
                text = f"{note['title']} {note['content']}"
                rows.append({"rep": rep_dir.name, "task": tid, "title": note["title"], "poison": bool(POISON_FLOAT_NOTE.search(text)),
                             "conventions": sorted(about(text)), "kept": ok, "why": why})
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    poison = [r for r in rows if r["poison"]]
    good = [r for r in rows if not r["poison"]]
    lines = ["# Rule-level validation on failed tasks (offline replay)", "",
             f"Failed tasks replayed: {len({(r['rep'], r['task']) for r in rows})}. Candidates: {len(rows)} "
             f"({len(poison)} poison). Poison kept: {sum(r['kept'] for r in poison)}/{len(poison)}; "
             f"other candidates kept: {sum(r['kept'] for r in good)}/{len(good)}.", "",
             "| Rep | Task | Candidate | About | Poison | Kept (as observed) | Why |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['rep']} | {r['task']} | {r['title']} | {', '.join(r['conventions']) or '–'} | {'yes' if r['poison'] else ''} | "
              f"{'**yes**' if r['kept'] else 'no'} | {r['why']} |" for r in rows]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
