"""Dynamic forgetting V1: retention scoring, archiving (never deleting), eligibility first, reactivation."""

from attest.benchmark import load_task
from attest.memory import forgetting
from attest.memory.earned import EarnedMemory


def note(i, type_="lesson", refs=(), tick=0, verified=(), status="active"):
    return {"id": i, "kind": "lesson", "type": type_, "title": f"Note {i}", "content": f"refund helper detail {i}",
            "status": status, "created_tick": tick,
            "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None},
            "source": {"task_id": "E01", "references": list(refs)},
            "evidence": [{"source": {"kind": "review_comment", "references": list(refs)}, "applied": {"kind": "code"}}],
            "forgetting": {"last_verified_tick": tick, "unused_exposures": 0, "verified_tasks": list(verified)},
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}}


def test_retention_by_policy():
    policy_rule = note("p", "business_policy", refs=["FIN-2026-09"])
    one_off = note("o", "lesson")
    assert forgetting.retention(policy_rule, 400, "type_aware")["R"] == 1.0          # policies never decay by age
    assert forgetting.retention(policy_rule, 400, "uniform")["R"] < 0.01             # uniform decay forgets it
    assert forgetting.retention(one_off, 400, "type_aware")["R"] < forgetting.THRESHOLD
    reused = note("r", verified=["E02", "E02", "E05"])                                # repeats count once
    assert forgetting.retention(reused, 400, "uniform")["U"] == 0.75
    assert forgetting.retention(one_off, 400, "none")["R"] == 0.7


def test_maintain_archives_but_keeps_everything_in_the_log():
    m = EarnedMemory(None)
    for it in (note("at-0001", "business_policy", refs=["FIN-2026-03"]), note("at-0002"), note("at-0003", status="retired")):
        m.store.append("add", item=it, reason="seed")
    events = forgetting.maintain(m, 400, "type_aware")
    items = m.store.items()
    assert [e["id"] for e in events] == ["at-0002"] and items["at-0002"]["status"] == "archived"
    assert items["at-0001"]["status"] == "active" and items["at-0003"]["status"] == "retired"  # retired stays retired
    assert len(items) == 3 and "R=" in events[0]["reason"]
    # archived notes are not retrieved, but their record is intact
    shown = m.retrieve(load_task("H01"), "1.0.0")
    assert "at-0002" not in shown.ids and shown.debug["trace"]["excluded"]["at-0002"] == "status archived"
    forgetting.reactivate(m, "at-0002", "a person needs it for a v1 maintenance task")
    assert m.store.items()["at-0002"]["status"] == "active"


def test_observe_reinforces_used_and_counts_unused_exposures():
    m = EarnedMemory(None)
    m.store.append("add", item=note("at-0001"), reason="seed")
    m.store.append("add", item=note("at-0002"), reason="seed")
    forgetting.observe(m, 10, "E04", injected=["at-0001", "at-0002"], used=["at-0001"], passed=True)
    items = m.store.items()
    assert items["at-0001"]["forgetting"]["verified_tasks"] == ["E04"] and items["at-0001"]["forgetting"]["last_verified_tick"] == 10
    assert items["at-0002"]["forgetting"]["unused_exposures"] == 1


def test_forgetting_never_overrides_eligibility():
    """A superseded rule stays out of the newer version whatever its retention."""
    m = EarnedMemory(None)
    old = note("at-0001", "business_policy", refs=["FIN-2026-03"], status="superseded")
    old["scope"]["valid_until"] = "2.0.0"
    m.store.append("add", item=old, reason="seed")
    assert forgetting.maintain(m, 400, "uniform") == []           # only active notes are considered
    assert m.retrieve(load_task("S04"), "2.0.0").ids == []
    assert m.retrieve(load_task("H04"), "1.0.0").ids == ["at-0001"]  # still valid for 1.x


def test_admission_tiers_and_file_scoped_candidates():
    from types import SimpleNamespace

    from attest.memory import admission

    base = note("x")
    base["source"]["review_comments"] = ["Please keep the export columns in this order."]
    base["evidence"][0]["source"]["quote"] = "keep the export columns"
    base["scope"]["files"] = ["ledgerly/reporting.py"]
    assert admission.tier(base) == "candidate"
    conv = dict(base, source=dict(base["source"], review_comments=["[team convention] keep the export columns in order."]))
    assert admission.tier(conv) == "convention"
    assert admission.tier(note("p", refs=["INC-204"])) == "policy"
    assert admission.tier(dict(base, forgetting={"verified_tasks": ["E05"], "last_verified_tick": 0, "unused_exposures": 0})) == "repeated"
    elsewhere = SimpleNamespace(title="Credit notes", issue="Add issue_credit_note to `ledgerly/adjustments.py`.")
    here = SimpleNamespace(title="Report", issue="Change `ledgerly/reporting.py`.")
    assert not admission.injectable_here(base, elsewhere) and admission.injectable_here(base, here)
    assert admission.injectable_here(conv, elsewhere)  # rules apply repository-wide


def test_tiered_memory_ranks_rules_before_candidates():
    from attest.memory.forgetting import ForgettingMemory

    m = ForgettingMemory(None, "none", lambda: 0, tiered=True)
    rule = note("at-0001", refs=["INC-204"])
    rule["content"] = "credit note idempotency"
    detail = note("at-0002")
    detail["content"] = "credit note export credit note columns credit note"
    detail["scope"]["files"] = ["ledgerly/adjustments.py"]
    for it in (rule, detail):
        m.store.append("add", item=it, reason="seed")
    ids = m.retrieve(load_task("H04"), "1.0.0").ids  # H04 names ledgerly/adjustments.py
    assert ids == ["at-0001", "at-0002"]
    trace = m.retrieve(load_task("H01"), "1.0.0").debug["trace"]  # H01 names promotions.py
    assert "candidate" in trace["excluded"]["at-0002"]
