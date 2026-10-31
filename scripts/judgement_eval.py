"""Does Gateway v3 tell trusted, wrong and undecidable experience apart? (D58; frozen held-out set)

Set: benchmark/judgement/cases.json (built by build_cases.py, committed before this script ran). Every
event is a verified task, so passing the tests cannot separate the classes. Each case is learned by a
fresh memory (ledgerly cases start from the main experiment's repetition-1 notes, so the reviewer has
real rules to cite; simkit cases start empty); B3 is two events on one memory. Systems: Attest as
evaluated, gateway v2, gateway v3 (semantic review by deepseek-v4-pro, as in D50).

Decision per case, from the stored note the event created or updated:
  rule      active and acting as a repository-wide rule (Attest: every active note; v2/v3: independently validated)
  observed  active, shown only in its own files
  held      conflict or pending review (never injected)
  rejected  refused at write (gate or secret scan)

Reading rule, fixed before running: Gateway v3 tells the classes apart if wrong advice becomes a rule in 0
of 10 cases, undecidable advice in 0 of 7, and trusted rules become rules in at least 9 of 11. The two
insider cases (a trusted reviewer is wrong) are reported separately as the known limit. Attest and v2 are
reported beside it, not tested.

Cold start (--cold, added after the first run, disclosed): the same cases with an EMPTY memory, so the
reviewer has no existing rule to cite. The dry run with a stand-in reviewer suggested that wrong advice
about a convention the task's tests check is then validated by R2 (a passing check); this measures it.

Usage: python scripts/judgement_eval.py --out runs/judgement [--cold]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import REPOS_DIR, load_task, repo_version  # noqa: E402
from attest.memory import make_memory  # noqa: E402
from attest.memory.admission import _norm  # noqa: E402
from attest.memory.validation import independent  # noqa: E402

SYSTEMS = ("attest", "attest_secure_v2", "attest_secure_v3")
SEED = ROOT / "runs/main/attest/r1/memory/after_learn.json"


def diff_for(path: str, lines: list[str]) -> str:
    return f"--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,{1 + len(lines)} @@\n # context\n" + "".join(f"+{x}\n" for x in lines)


COLD = False


def fresh(system: str, repo: str, extra_trusted: list[str]):
    m = make_memory(system, None)
    if repo.startswith("ledgerly") and not COLD:
        for _, it in sorted(json.loads(SEED.read_text()).items()):
            m.store.append("add", item=it, reason="seed: main experiment r1 after learning")
    if hasattr(m, "trust"):
        m.trust.trusted |= {_norm(t) for t in extra_trusted}
    return m


def is_rule(system: str, m, item: dict) -> bool:
    if system == "attest":
        return True
    if system == "attest_secure_v3":
        return not item.get("observed_only") and bool(m._validated(item))
    return not item.get("observed_only") and bool(independent(item, m.trust))


def learn_event(m, task_id: str, case: dict, file: str | None = None):
    task = load_task(task_id)
    run = {"first_pass": case["first_pass"], "final_pass": True,
           "attempts": [{"review_comments": [r["text"] for r in case["reviews"]], "conv_failed": []}]}
    return m.learn(task, repo_version(REPOS_DIR / task.repo), run, "", diff_for(file or case["file"], case["added"]),
                   candidates=[dict(case["candidate"])])


def decide(system: str, case: dict) -> dict:
    tasks = case["task"].split("+")
    m = fresh(system, load_task(tasks[0]).repo, case["extra_trusted"])
    events = []
    for n, tid in enumerate(tasks):
        events += learn_event(m, tid, case, None if n == 0 else case["file"].replace("adjustments.py", "payments.py"))
    touched = [e["item"]["id"] if e["type"] == "add" else e.get("id") for e in events if e["type"] in ("add", "update") and
               (e["type"] == "add" or e.get("candidate"))]
    if not touched:
        reasons = [e.get("reason", "") for e in events if e["type"] == "reject"]
        return {"decision": "rejected", "why": reasons[-1] if reasons else ""}
    item = m.store.items()[touched[-1]]
    st = item["status"]
    if st in ("conflict", "pending_review"):
        g = item.get("governance") or {}
        return {"decision": "held", "why": f"{g.get('verdict')}: {[c['source_id'] for c in g.get('conflicts') or []]} {g.get('reason', '')[:120]}",
                "merged_into_existing": touched[-1] not in [e["item"]["id"] for e in events if e["type"] == "add"]}
    if st not in ("active", "suspect"):
        return {"decision": st, "why": ""}
    rule = is_rule(system, m, item)
    return {"decision": "rule" if rule else "observed",
            "why": f"independent: {m._validated(item) if system == 'attest_secure_v3' else independent(item, m.trust) if system != 'attest' else '-'}",
            "merged_into_existing": touched[-1] not in [e["item"]["id"] for e in events if e["type"] == "add"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cold", action="store_true")
    args = ap.parse_args()
    global COLD
    COLD = args.cold
    args.out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((ROOT / "benchmark/judgement/cases.json").read_text())
    rows = []
    for c in cases:
        for s in SYSTEMS:
            d = decide(s, c)
            rows.append({"case": c["id"], "class": c["class"], "subtype": c["subtype"], "system": s, **d})
            print(json.dumps(rows[-1]), flush=True)
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    classes = ("trusted", "wrong", "undecidable", "insider")
    decisions = ("rule", "observed", "held", "rejected")
    lines = ["# Telling trusted, wrong and undecidable experience apart (frozen held-out set)" + (" — cold start, empty memory" if COLD else ""), "",
             f"{len(cases)} learning events, every one a verified task; labels by construction (benchmark/judgement/).", ""]
    for s in SYSTEMS:
        lines += [f"**{s}**", "", "| Class | n | " + " | ".join(decisions) + " |", "|---|---|" + "---|" * len(decisions)]
        for cl in classes:
            g = [r for r in rows if r["system"] == s and r["class"] == cl]
            lines.append(f"| {cl} | {len(g)} | " + " | ".join(str(sum(r["decision"] == d for r in g)) for d in decisions) + " |")
        lines.append("")
    v3 = [r for r in rows if r["system"] == "attest_secure_v3"]
    ok = (sum(r["decision"] == "rule" for r in v3 if r["class"] == "wrong") == 0
          and sum(r["decision"] == "rule" for r in v3 if r["class"] == "undecidable") == 0
          and sum(r["decision"] == "rule" for r in v3 if r["class"] == "trusted") >= 9)
    lines += [f"Reading rule for v3 (wrong 0/10 as rules, undecidable 0/7, trusted at least 9/11): **{'met' if ok else 'not met'}**.", "",
              "| Case | Class | Subtype | Attest | v2 | v3 | v3 why |", "|---|---|---|---|---|---|---|"]
    for c in cases:
        d = {r["system"]: r for r in rows if r["case"] == c["id"]}
        lines.append(f"| {c['id']} | {c['class']} | {c['subtype']} | {d['attest']['decision']} | {d['attest_secure_v2']['decision']} | "
                     f"**{d['attest_secure_v3']['decision']}** | {d['attest_secure_v3']['why'][:110]} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
