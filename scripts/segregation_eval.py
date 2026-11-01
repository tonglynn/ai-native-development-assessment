"""Segregation of duties in the memory lifecycle, as executable cases (D69; offline, no model).

Each case tries one way around the rule "only a registered person, never an agent or the note's proposer, decides what
becomes a rule, and every decision says on which evidence". Expected outcome is fixed in the case table. Bypass attempts
must be refused at the call, or, when written straight into the log, listed by review.audit_reviews. Controls (legitimate
decisions) must go through. Reported as n/n, like the tamper tests.

Usage: python scripts/segregation_eval.py --out runs/segregation
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.memory import review  # noqa: E402
from attest.memory.earned import EarnedMemory, validity  # noqa: E402

APPROVERS = ("owner:finance-lead", "owner:tech-lead")


def note(i, state="uncertain", proposer="agent:distiller", status="active"):
    return {"id": i, "kind": "lesson", "type": "business_policy", "title": f"note {i}", "content": f"rule {i}", "status": status,
            "scope": {"repo": "ledgerly", "valid_from": "1.0.0", "valid_until": None, "files": []},
            "source": {"task_id": "E05", "proposed_by": proposer}, "assessment": {"state": state, "counter": [], "hard": [], "soft": ["reviewer"]},
            "evidence": []}


def fresh(tmp, *notes):
    m = EarnedMemory(Path(tempfile.mkdtemp(dir=tmp)))
    for n in notes:
        m.store.append("add", item=n, reason="case setup")
    return m


def refused(fn):
    try:
        fn()
    except (review.ReviewRefused, ValueError, KeyError) as exc:
        return True, f"{type(exc).__name__}: {exc}"
    return False, "went through"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        def case(name, kind, expect_blocked, fn):
            ok_blocked, detail = fn()
            rows.append({"case": name, "kind": kind, "expected": "blocked" if expect_blocked else "allowed",
                         "got": "blocked" if ok_blocked else "allowed", "pass": ok_blocked == expect_blocked, "detail": detail})

        A = lambda m, i, by, ev=("FIN-2026-09 policy",): lambda: review.approve(m, i, by=by, reason="r", evidence=list(ev), approvers=APPROVERS)  # noqa: E731
        m = fresh(tmp, note("n1"))
        case("agent approves an uncertain note", "bypass at call", True, lambda: refused(A(m, "n1", "agent:distiller")))
        m = fresh(tmp, note("n1", proposer="owner:tech-lead"))
        case("the proposer approves their own note", "bypass at call", True, lambda: refused(A(m, "n1", "owner:tech-lead")))
        m = fresh(tmp, note("n1"))
        case("an unregistered person approves", "bypass at call", True, lambda: refused(A(m, "n1", "dev:alice")))
        case("approval with no decider", "bypass at call", True, lambda: refused(A(m, "n1", "")))
        case("approval without evidence", "bypass at call", True, lambda: refused(A(m, "n1", "owner:finance-lead", ev=())))
        m = fresh(tmp, note("n1", state="approved"))
        case("replay: approve a note that is already a rule", "bypass at call", True, lambda: refused(A(m, "n1", "owner:finance-lead")))
        m = fresh(tmp, note("n1"))
        case("agent rejects (retires) a note", "bypass at call", True,
             lambda: refused(lambda: review.reject(m, "n1", by="agent:coder", reason="inconvenient", approvers=APPROVERS)))
        m = fresh(tmp, note("new", state="approved"), note("old", state="approved"))
        case("agent supersedes a rule", "bypass at call", True,
             lambda: refused(lambda: review.supersede(m, "new", ["old"], by="agent:coder", reason="r", approvers=APPROVERS)))
        case("unregistered person supersedes a rule", "bypass at call", True,
             lambda: refused(lambda: review.supersede(m, "new", ["old"], by="dev:alice", reason="r", approvers=APPROVERS)))
        m = fresh(tmp, note("new"), note("old", state="approved"))
        case("supersede with a replacement that is not an approved rule", "bypass at call", True,
             lambda: refused(lambda: review.supersede(m, "new", ["old"], by="owner:finance-lead", reason="r", approvers=APPROVERS)))

        def forged(by, evidence=("x",)):
            m = fresh(tmp, note("n1"))
            m.store.append("update", id="n1", fields={"assessment": {"state": "approved"}, "review": {"decision": "approved", "by": by, "evidence": list(evidence)}},
                           reason="written straight into the log")
            found = review.audit_reviews(m, APPROVERS)
            return bool(found), json.dumps(found)
        case("forged approval in the log, by an agent", "bypass in log", True, lambda: forged("agent:distiller"))
        case("forged approval in the log, by an unregistered name", "bypass in log", True, lambda: forged("ceo"))
        case("forged approval in the log, without evidence", "bypass in log", True, lambda: forged("owner:finance-lead", ()))

        def forged_auto():
            m = fresh(tmp, note("n1"))
            m.store.append("update", id="n1", fields={"assessment": {"state": "approved", "hard": [], "soft": ["reviewer"]}},
                           reason="automatic approval written straight into the log, no hard evidence")
            found = review.audit_reviews(m, APPROVERS)
            return bool(found), json.dumps(found)
        case("forged automatic approval without hard evidence", "bypass in log", True, forged_auto)

        def mcp_surface():
            src = (ROOT / "attest/mcp_server.py").read_text()
            exposed = src.split("for fn in (", 1)[1].split(")", 1)[0]
            bad = [w for w in ("approve", "reject", "retract", "supersede", "review") if w in exposed]
            return bool(not bad), f"exposed to agents: {exposed.strip()}"
        case("agents can reach approve/reject/retract/supersede via MCP", "surface", True, mcp_surface)

        def legit_approve():
            m = fresh(tmp, note("n1"))
            review.approve(m, "n1", by="owner:finance-lead", reason="matches FIN-2026-09", evidence=["FIN-2026-09"], approvers=APPROVERS)
            return bool(review.audit_reviews(m, APPROVERS)) or m.store.items()["n1"]["assessment"]["state"] != "approved", "approved, audit clean"
        case("registered owner approves with evidence (control)", "control", False, legit_approve)

        def legit_supersede():
            m = fresh(tmp, note("new", state="approved"), note("old", state="approved"))
            review.supersede(m, "new", ["old"], by="owner:finance-lead", reason="FIN-2026-11 replaces FIN-2026-03", approvers=APPROVERS)
            it = m.store.items()
            ok = it["old"]["status"] == "superseded" and validity(it["old"], "2.0.0") and not review.audit_reviews(m, APPROVERS) \
                and any(e["type"] == "add" and e["item"]["id"] == "old" for e in m.store.events)
            return not ok, f"old: {it['old']['status']}, excluded: {validity(it['old'], '2.0.0')!r}, still in log"
        case("registered owner supersedes an old rule (control)", "control", False, legit_supersede)

    n_ok = sum(r["pass"] for r in rows)
    (args.out / "results.json").write_text(json.dumps({"passed": n_ok, "cases": len(rows), "rows": rows}, indent=2) + "\n")
    lines = ["# Segregation of duties in the memory lifecycle (D69, offline)", "",
             f"**{n_ok}/{len(rows)} cases behave as fixed in advance** "
             f"(bypasses blocked: {sum(r['pass'] for r in rows if r['kind'] != 'control')}/{sum(r['kind'] != 'control' for r in rows)}; "
             f"controls allowed: {sum(r['pass'] for r in rows if r['kind'] == 'control')}/{sum(r['kind'] == 'control' for r in rows)}).", "",
             "| Case | Kind | Expected | Got | Detail |", "|---|---|---|---|---|"]
    lines += [f"| {r['case']} | {r['kind']} | {r['expected']} | {r['got']}{'' if r['pass'] else ' **FAIL**'} | {r['detail'][:110]} |" for r in rows]
    lines += ["", "Limits: the log check runs after the fact (it lists, it does not prevent); a person with write access to the",
              "log file is covered by the sealed store's hash chain (D42), not by these cases; identities are names, not signatures."]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
