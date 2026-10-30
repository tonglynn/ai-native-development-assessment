"""Fixed regression scenarios for memory governance: small but important rules must not be lost.

Total pass rates hide these failures, so each is pinned here:
  1. a rule unused for a long time that a specific business task still needs
  2. a rule learned in one file that another file needs
  3. an old rule replaced by a new version
  4. a note archived, then confirmed again by new evidence: it must come back and stay back

These tests pin the expected behaviour in fixed scenarios. Passing them does not show that
a retention policy works overall; that is what scripts/forgetting_v11.py measures. The
xfail below is an unresolved limitation, not a passing case.
"""

import pytest

from attest import llm
from attest.benchmark import load_task
from attest.memory import admission, forgetting
from attest.memory.earned import DISTILL_SYSTEM, RELATE_SYSTEM
from attest.memory.forgetting import ForgettingMemory

APPROVAL = ('[team convention] Support-initiated refunds and credits above 500.00 need a second approver '
            '(finance policy FIN-2026-03): accept an optional keyword-only `approved_by=None`.')


def rule(i, title, content, *, type_="business_policy", refs=(), files=("ledgerly/adjustments.py",), kind="review_comment",
         comments=(), verified=(), tick=0, quote=""):
    return {"id": i, "kind": "project_fact", "type": type_, "title": title, "content": content, "status": "active",
            "created_tick": tick, "supersedes": [], "superseded_by": None,
            "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None, "files": list(files)},
            "source": {"task_id": "E04", "review_comments": list(comments), "references": list(refs)},
            "evidence": [{"task_id": "E04", "version": "1.0.0", "source": {"kind": kind, "quote": quote, "references": list(refs)},
                          "applied": {"kind": "code", "change": "added", "file": files[0], "line": "..."},
                          "verification": {"passed": True}, "independent_review": None}],
            "forgetting": {"last_verified_tick": tick, "unused_exposures": 0, "verified_tasks": list(verified)},
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}}


@pytest.mark.parametrize("policy", ["type_aware"])
@pytest.mark.parametrize("v11", [False, True])
def test_1_long_unused_policy_rule_survives_and_is_injected(policy, v11):
    clock = {"now": 0}
    m = ForgettingMemory(None, policy, lambda: clock["now"], tiered=True)
    m.store.append("add", item=rule("at-0001", "Refunds above 500 need approved_by",
                                    "Support refunds above 500.00 require approved_by, else BillingError('approval_required').",
                                    refs=["FIN-2026-03"]), reason="seed")
    params = {"utility_factor": 4} if v11 else None
    for tick in range(50, 1001, 50):  # 1,000 tasks in which nobody needed it
        clock["now"] = tick
        forgetting.maintain(m, tick, policy, params=params)
    assert m.store.items()["at-0001"]["status"] == "active"
    assert "at-0001" in m.retrieve(load_task("H04"), "1.0.0").ids  # the support refund task gets it


def test_2a_team_rule_learned_in_one_file_reaches_another():
    m = ForgettingMemory(None, "none", lambda: 0, tiered=True)
    m.store.append("add", item=rule("at-0001", "Record audit entry for every money movement",
                                    "Every operation that moves money writes ledgerly.audit.record(...).", type_="code_convention",
                                    files=("ledgerly/payments.py",), comments=["[team convention] Every operation that moves money must write an audit entry."],
                                    quote="every operation that moves money"), reason="seed")
    assert admission.tier(m.store.items()["at-0001"]) == "convention"
    assert "at-0001" in m.retrieve(load_task("H04"), "1.0.0").ids  # learned in payments.py, needed in adjustments.py


@pytest.mark.xfail(strict=True, reason="UNRESOLVED limitation of tiered admission: a real rule seen once, with "
                                        "diff-only evidence, is a candidate and is not injected outside its file (the "
                                        "audit rule in repetition 2 of runs/admission). strict: if this starts passing, "
                                        "the limitation must be re-examined, not silently dropped")
def test_2b_rule_seen_once_with_diff_evidence_reaches_another_file():
    m = ForgettingMemory(None, "none", lambda: 0, tiered=True)
    m.store.append("add", item=rule("at-0001", "Record state changes via audit.record",
                                    "Record every money movement with ledgerly.audit.record(...).", type_="code_convention",
                                    files=("ledgerly/payments.py",), kind="diff"), reason="seed")
    assert "at-0001" in m.retrieve(load_task("H04"), "1.0.0").ids


def test_3_superseded_rule_stays_out_of_the_new_version_but_serves_the_old():
    m = ForgettingMemory(None, "uniform", lambda: 1000, tiered=True)
    old = rule("at-0001", "Refunds above 500 need approved_by", "Above 500.00 require approved_by.", refs=["FIN-2026-03"])
    old["status"], old["superseded_by"] = "superseded", "at-0002"
    old["scope"]["valid_until"] = "2.0.0"
    new = rule("at-0002", "Refunds above 1000 need approved_by since 2.0", "Since 2.0.0 above 1000.00 require approved_by.",
               refs=["FIN-2026-09"], tick=1000)  # just learned on 2.0.0
    new["scope"]["valid_from"] = new["scope"]["observed_version"] = "2.0.0"
    for it in (old, new):
        m.store.append("add", item=it, reason="seed")
    # even the most aggressive policy: the old rule is 1,000 tasks old, but forgetting never touches a superseded note,
    # so it is neither archived nor revived as active
    assert forgetting.maintain(m, 1000, "uniform") == []
    assert m.store.items()["at-0001"]["status"] == "superseded"
    assert m.retrieve(load_task("S05"), "2.0.0").ids == ["at-0002"]
    assert m.retrieve(load_task("H04"), "1.0.0").ids == ["at-0001"]


ROUND = {"kind": "project_fact", "type": "lesson", "topic": "money-rounding", "title": "Round money with round_money",
         "content": "Round every money value with ledgerly.money.round_money, which rounds half-up to the cent.",
         "evidence_quote": "Round money only with ledgerly.money.round_money (half-up to the cent)",
         "applied_in_diff": "return round_money(weighted_total / total_quantity)"}
ROUND_COMMENT = ("[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). Python's round() "
                 "and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals.")
DIFF = "--- a/ledgerly/invoice.py\n+++ b/ledgerly/invoice.py\n@@ -1 +1,3 @@\n+def average_unit_price(invoice):\n+    return round_money(weighted_total / total_quantity)\n"


def test_4_reactivated_note_is_not_archived_again_at_the_next_maintenance():
    answers = {DISTILL_SYSTEM: [{"candidates": [ROUND]}, {"candidates": [ROUND]}], RELATE_SYSTEM: [{"relations": [{"id": "at-0001", "relation": "duplicate"}]}]}
    llm.set_llm(lambda system, user: answers[system].pop(0) if answers.get(system) else {})
    try:
        clock = {"now": 0}
        m = ForgettingMemory(None, "type_aware", lambda: clock["now"])
        run = {"first_pass": False, "final_pass": True, "attempts": [{"passed": False, "review_comments": [ROUND_COMMENT]}],
               "shown_notes": [], "cited_notes": []}
        m.learn(load_task("E01"), "1.0.0", run, "t", DIFF)
        clock["now"] = 400
        assert [e["id"] for e in forgetting.maintain(m, 400, "type_aware")] == ["at-0001"]  # a lesson, unused for 400 tasks
        m.learn(load_task("E05"), "1.0.0", run, "t", DIFF)  # a new verified task yields the same rule
        item = m.store.items()["at-0001"]
        assert item["status"] == "active" and item["forgetting"]["last_verified_tick"] == 400
        assert forgetting.maintain(m, 450, "type_aware") == []  # not archived again straight away
    finally:
        llm.set_llm(None)


def test_4b_manual_reactivation_resets_the_clock():
    m = ForgettingMemory(None, "type_aware", lambda: 400)
    m.store.append("add", item=rule("at-0001", "Old detail", "detail", type_="lesson", tick=0), reason="seed")
    forgetting.maintain(m, 400, "type_aware")
    forgetting.reactivate(m, "at-0001", "needed for a v1 maintenance task", now=400)
    assert forgetting.maintain(m, 410, "type_aware") == []


def test_v11_utility_decays_but_policy_rules_keep_theirs():
    used_once = rule("a", "Detail", "detail", type_="lesson", verified=["E02"], tick=0)
    policy = rule("p", "Policy", "policy", refs=["FIN-2026-03"], verified=["E02"], tick=0)
    v1 = forgetting.retention(used_once, 1000, "type_aware")
    v11 = forgetting.retention(used_once, 1000, "type_aware", {"utility_factor": 4})
    assert v1["R"] >= forgetting.THRESHOLD > v11["R"]  # V1 keeps a note used once forever, V1.1 does not
    assert forgetting.retention(policy, 1000, "type_aware", {"utility_factor": 4})["R"] == 1.0


def test_v11_protects_a_cited_rule_whatever_its_type_label():
    idem = rule("i", "Money operations take idempotency_key", "check idempotency_key first", type_="process",
                refs=["INC-2025-11"], tick=0)
    assert forgetting.retention(idem, 1000, "type_aware")["R"] < forgetting.THRESHOLD  # V1 trusts the type label
    assert forgetting.retention(idem, 1000, "type_aware", {"utility_factor": 4, "protect_cited": True})["R"] == 1.0


@pytest.mark.parametrize("ref,protected", [("FIN-2026-03", True), ("INC-204", True), ("POL-12", True), ("SEC-7", True),
                                           ("ADR-0042", False), ("RFC-9110", False), ("CVE-2024-1234", False)])
def test_only_policy_and_incident_references_make_a_policy_rule(ref, protected):
    note = rule("n", "Some rule", "some rule", type_="code_convention", refs=[ref], tick=0)
    assert (admission.tier(note) == "policy") is protected
    assert (forgetting.evidence_quality(note) == 1.0) is protected
    r = forgetting.retention(note, 1000, "type_aware", {"utility_factor": 4, "protect_cited": True})["R"]
    assert (r == 1.0) is protected


def test_v11_type_protection_is_kept_beside_citation_protection():
    # V1.1 adds citation protection; it does not drop the business_policy label's protection
    uncited_policy = rule("p", "Audit every money movement", "audit", type_="business_policy", tick=0)
    assert forgetting.retention(uncited_policy, 1000, "type_aware", {"utility_factor": 4, "protect_cited": True})["R"] > 0.2


def test_v11_adopted_but_unverified_is_not_reinforced():
    m = ForgettingMemory(None, "type_aware", lambda: 0)
    m.store.append("add", item=rule("at-0001", "Export detail", "exports use semicolons", type_="lesson"), reason="seed")
    forgetting.observe(m, 10, "H03", injected=["at-0001"], used=["at-0001"], passed=True, verified=[])
    t = m.store.items()["at-0001"]["forgetting"]
    assert t["verified_tasks"] == [] and t["adopted_unverified"] == 1
    forgetting.observe(m, 11, "H03", injected=["at-0001"], used=["at-0001"], passed=True)  # V1 would reinforce it
    assert m.store.items()["at-0001"]["forgetting"]["verified_tasks"] == ["H03"]
