"""Forgetting V2 mechanisms (opt-in): stability growth, scoped exposure, three evidence states, demand."""

from attest.benchmark import load_task
from attest.memory import forgetting
from attest.memory.forgetting import ForgettingMemory


def note(i, *, type_="lesson", files=("ledgerly/adjustments.py",), verified=(), tick=0, refs=(), title="Credit note rounding detail"):
    return {"id": i, "kind": "lesson", "type": type_, "title": title, "content": "credit note amounts are shown with two decimals",
            "status": "active", "created_tick": tick, "supersedes": [], "superseded_by": None,
            "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None, "files": list(files)},
            "source": {"task_id": "T1", "review_comments": [], "references": list(refs)},
            "evidence": [{"task_id": "T1", "version": "1.0.0", "source": {"kind": "review_comment", "quote": "x", "references": list(refs)},
                          "applied": {"kind": "code", "change": "added", "file": files[0], "line": "..."}, "verification": {"passed": True}}],
            "forgetting": {"last_verified_tick": tick, "unused_exposures": 0, "verified_tasks": list(verified)},
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}}


def test_stability_removes_the_utility_floor_but_rewards_repetition():
    once, thrice = note("a", verified=["T2"]), note("b", verified=["T2", "T3", "T4"])
    assert forgetting.retention(once, 1000, "type_aware")["R"] >= forgetting.THRESHOLD  # V1: kept for ever
    assert forgetting.retention(once, 1000, "type_aware", {"stability": 2})["R"] < forgetting.THRESHOLD
    assert forgetting.retention(thrice, 200, "type_aware", {"stability": 2})["R"] > forgetting.retention(once, 200, "type_aware", {"stability": 2})["R"]


def test_three_states_dormant_without_negative_evidence_archived_with_it():
    clock = {"now": 400}
    m = ForgettingMemory(None, "type_aware", lambda: clock["now"], tiered=True)
    for it in (note("at-0001"), note("at-0002")):
        m.store.append("add", item=it, reason="seed")
    forgetting.observe(m, 390, "H04", ["at-0002"], ["at-0002"], False, [], negative=["at-0002"])
    forgetting.maintain(m, 400, "type_aware", params={"dormant": True})
    items = m.store.items()
    assert items["at-0001"]["status"] == "dormant" and items["at-0002"]["status"] == "archived"
    assert "at-0001" in m.retrieve(load_task("H04"), "1.0.0").ids  # H04 names ledgerly/adjustments.py
    assert "at-0001" not in m.retrieve(load_task("H03"), "1.0.0").ids  # reporting.py: not its file
    forgetting.observe(m, 401, "H07", ["at-0001"], ["at-0001"], True, ["at-0001"])  # a verified use wakes it
    assert m.store.items()["at-0001"]["status"] == "active"


def test_demand_reactivates_and_resets_but_never_revives_negative_evidence():
    m = ForgettingMemory(None, "type_aware", lambda: 400, tiered=True)
    for it in (note("at-0001"), note("at-0002")):
        m.store.append("add", item=it, reason="seed")
    forgetting.observe(m, 100, "E06", ["at-0002"], ["at-0002"], False, [], negative=["at-0002"])
    forgetting.maintain(m, 400, "type_aware")  # V1 archiving
    forgetting.observe(m, 401, "H04", [], [], False, [], demand=["at-0001", "at-0002"])
    items = m.store.items()
    assert items["at-0001"]["status"] == "active" and items["at-0001"]["forgetting"]["last_verified_tick"] == 401
    assert items["at-0002"]["status"] == "archived" and not items["at-0002"]["forgetting"].get("demand_tasks")
    assert forgetting.maintain(m, 410, "type_aware") == []  # not archived again straight away


def test_scoped_exposure_counts_only_tasks_that_touch_the_note():
    m = ForgettingMemory(None, "exposure", lambda: 0)
    m.store.append("add", item=note("at-0001"), reason="seed")
    forgetting.observe(m, 1, "H03", ["at-0001"], [], True, relevant=[])  # injected into an unrelated task
    assert m.store.items()["at-0001"]["forgetting"]["unused_exposures"] == 0
    forgetting.observe(m, 2, "H04", ["at-0001"], [], True, relevant=["at-0001"])
    assert m.store.items()["at-0001"]["forgetting"]["unused_exposures"] == 1
    forgetting.observe(m, 3, "H03", ["at-0001"], [], True)  # V1: every injection counts
    assert m.store.items()["at-0001"]["forgetting"]["unused_exposures"] == 2


def test_v1_defaults_unchanged_by_v2_fields():
    plain = note("a", verified=["T2"])
    assert forgetting.retention(plain, 1000, "type_aware") == forgetting.retention(dict(plain), 1000, "type_aware", {})
