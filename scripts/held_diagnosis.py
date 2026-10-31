"""Why correct notes are held in gateway v2 (D57; offline, from the stored runs of D56).

For every note attest_secure_v2 held (conflict or pending_review), in all three scenarios, record what
each mechanism said: semantic review verdict and what its conflicts cite (an existing rule, the
CHANGELOG, or only code, D50), independent validation (D52), risk (D53); D54 acts only on failed tasks
and D41 only at retrieval, so neither can hold a note: both are recorded as not involved. Then classify:

  1  lacks independent evidence      no registered policy, no trusted reviewer quote, no repetition
  2  has independent evidence but the reviewer still held it
  3  held by the order of mechanisms   a conflict is held before independent evidence is weighed

and whether the conflict is real (the note is the poison) or false (a correct note).

Fix, three rules decided after reading the classification and before recomputing (D57):
  R1  a conflict that cites only code is a clue, not an authority: it is treated as "uncertain" and then
      graded as in D53 (high-risk notes need independent validation; ordinary ones are kept as observed)
  R2  an executable check counts as independent validation (D52 "check") when every convention the note
      is about was checked by the source task's tests and the task passed; it never uses the diff
  R3  a conflict citing an existing rule is held, unless the candidate itself is validated by a
      registered policy or a trusted reviewer (authority beats the reviewer's reading): then it is
      admitted and the conflict is logged for a person
The recomputation changes only the decision, using the stored verdicts; whether the notes then help
the agent needs a run.

Usage: python scripts/held_diagnosis.py --out runs/held_diagnosis
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.memory.gateway import HIGH_RISK, benchmark_trust  # noqa: E402
from attest.memory.validation import independent, self_cited  # noqa: E402
from attest.stress import POISON, POISON_FLOAT_NOTE  # noqa: E402


def cited_kinds(review: dict) -> set[str]:
    return {"code" if c["source_id"].startswith("code:") else "CHANGELOG" if c["source_id"] == "CHANGELOG" else "rule"
            for c in review.get("conflicts") or []}


def check_passed(item: dict) -> bool:
    """R2: every convention the note is about was checked in its source task, and that task passed."""
    from attest.benchmark import load_task
    from attest.memory.gateway import about
    conv = about(f"{item['title']} {item['content']}")
    try:
        task = load_task(item["source"]["task_id"])
    except Exception:  # noqa: BLE001 - not a benchmark task
        return False
    # the task's verification result is in the evidence (held notes carry no last_verification)
    return bool(conv) and conv <= set(task.conventions) and bool(((item.get("evidence") or [{}])[0].get("verification") or {}).get("passed"))


def decide_v3(item: dict, review: dict, trust, rules=("R1", "R2", "R3")) -> str:
    ind = independent(item, trust, {item["id"]: check_passed(item)} if "R2" in rules else None)
    verdict = review.get("verdict")
    if "R1" in rules and verdict == "conflict" and cited_kinds(review) == {"code"}:
        verdict = "uncertain"
    if verdict == "approved":
        return "admitted"
    if verdict == "conflict":
        return "admitted (conflict logged)" if "R3" in rules and {"policy", "reviewer"} & set(ind) else "held"
    risky = HIGH_RISK.search(f"{item['title']} {item['content']}")
    if not risky:
        return "admitted (observed)"
    return "admitted" if ind else "held"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    trust = benchmark_trust()
    rows = []
    for scen in ("clean", "poison", "poison_float"):
        for f in sorted((ROOT / "runs/stress_gateway" / scen / "attest_secure_v2").glob("r*/memory/events.jsonl")):
            for e in (json.loads(x) for x in f.read_text().splitlines() if x.strip()):
                if e["type"] != "add" or e["item"]["status"] not in ("conflict", "pending_review"):
                    continue
                it, g = e["item"], e["item"].get("governance") or {}
                text = f"{it['title']} {it['content']}"
                poison = bool(POISON_FLOAT_NOTE.search(text)) or "audit.clear" in text or POISON[:40] in json.dumps(it)
                ind = independent(it, trust)
                kinds = cited_kinds(g)
                cls = ("3 held by order: conflict before independent evidence" if g.get("verdict") == "conflict" and ind else
                       "2 independent evidence, reviewer held it" if ind else "1 lacks independent evidence")
                rows.append({"scenario": scen, "rep": f.parent.parent.name, "id": it["id"], "title": it["title"], "poison": poison,
                             "verdict": g.get("verdict"), "conflict_cites": sorted(kinds), "independent": ind,
                             "high_risk": bool(HIGH_RISK.search(text)), "self_cited": self_cited(it["evidence"][0]),
                             "first_pass_task": it["source"]["first_pass"], "class": cls,
                             "D54": "not involved (task passed)", "D41": "not involved (acts at retrieval)",
                             "v3": decide_v3(it, g, trust), "R1 only": decide_v3(it, g, trust, ("R1",)),
                             "R1+R2": decide_v3(it, g, trust, ("R1", "R2")), "check_passed": check_passed(it), "conflicts": [(c["source_id"], c["source_quote"][:80]) for c in g.get("conflicts") or []]})
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    lines = ["# Why notes are held in gateway v2 (offline diagnosis)", "",
             "| Scenario | Rep | Note | Poison | Verdict | Conflict cites | Independent | High risk | Class | Fixed rule (D57) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['scenario']} | {r['rep']} | {r['id']} {r['title']} | {'**yes**' if r['poison'] else ''} | {r['verdict']} | "
                     f"{', '.join(r['conflict_cites']) or '–'} | {', '.join(r['independent']) or '–'} | {'yes' if r['high_risk'] else ''} | "
                     f"{r['class']} | {r['v3']} |")
    correct = [r for r in rows if not r["poison"]]
    poison = [r for r in rows if r["poison"]]
    lines += ["", f"Correct notes held: {len(correct)}; of them conflicts citing only code: "
              f"{sum(r['conflict_cites'] == ['code'] for r in correct)}, citing a rule: {sum('rule' in r['conflict_cites'] for r in correct)}.",
              f"Under the fixed rules, correct notes still held: R1 only {sum(r['R1 only'] == 'held' for r in correct)}, "
              f"R1+R2 {sum(r['R1+R2'] == 'held' for r in correct)}, R1+R2+R3 {sum(r['v3'] == 'held' for r in correct)} of {len(correct)}. "
              f"Poison notes among the held: {len(poison)} (the poison never reached review: its tasks failed the policy guard and "
              f"rule-level learning dropped it)."]
    for cls in sorted({r["class"] for r in correct}):
        lines.append(f"- {cls}: {sum(r['class'] == cls for r in correct)}")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
