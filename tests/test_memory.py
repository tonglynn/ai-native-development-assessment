"""Unit tests for the memory systems with a scripted model (no API calls)."""

import pytest

from attest import llm
from attest.benchmark import load_task
from attest.memory import make_memory
from attest.memory.earned import DISTILL_SYSTEM, RELATE_SYSTEM

ROUND_COMMENT = ("[team convention] Round money only with ledgerly.money.round_money (half-up to the cent). "
                 "Python's round() and a bare Decimal.quantize() use banker's rounding and give wrong invoice totals.")
ROUND_V2_COMMENT = ("[team convention] Round money only with ledgerly.money.round_money, which implements the current "
                    "finance rounding policy (since 2.0.0 this is banker's rounding, see CHANGELOG). Never hard-code a rounding mode.")
ERROR_COMMENT = "[team convention] Invalid billing input must raise ledgerly.errors.BillingError with a short snake_case code."

ROUND_NOTE = {
    "kind": "project_fact", "topic": "money-rounding", "title": "Round money with round_money",
    "content": "Round every money value with ledgerly.money.round_money, which rounds half-up to the cent.",
    "evidence_quote": "Round money only with ledgerly.money.round_money (half-up to the cent)",
}


class ScriptedLLM:
    """Returns queued answers per system prompt; records every call."""

    def __init__(self):
        self.answers = {DISTILL_SYSTEM: [], RELATE_SYSTEM: []}
        self.calls = []

    def __call__(self, system, user):
        self.calls.append(system)
        queue = self.answers.get(system)
        return queue.pop(0) if queue else {}


@pytest.fixture
def scripted():
    fake = ScriptedLLM()
    llm.set_llm(fake)
    yield fake
    llm.set_llm(None)


def run(first_pass, final_pass=True, comments=(), shown=(), cited=()):
    return {
        "first_pass": first_pass,
        "final_pass": final_pass,
        "attempts": [{"passed": first_pass, "review_comments": list(comments)}],
        "shown_notes": list(shown),
        "cited_notes": list(cited),
    }


def learn_round_note(mem, scripted):
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [ROUND_NOTE]})
    return mem.learn(load_task("E01"), "1.0.0", run(False, True, [ROUND_COMMENT]), "transcript", "diff")


def test_write_gate(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    # an unverified task writes nothing and does not even call the model
    events = mem.learn(load_task("E01"), "1.0.0", run(False, False, [ROUND_COMMENT]), "t", "d")
    assert events[0]["type"] == "reject" and not scripted.calls
    # a candidate whose evidence is not a verbatim quote is rejected
    bad = dict(ROUND_NOTE, evidence_quote="the team likes careful rounding a lot")
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [bad]})
    events = mem.learn(load_task("E01"), "1.0.0", run(False, True, [ROUND_COMMENT]), "t", "d")
    assert events[0]["type"] == "reject" and "verbatim" in events[0]["reason"]
    # a grounded candidate from a verified task is admitted
    events = learn_round_note(mem, scripted)
    assert events[0]["type"] == "add"
    assert mem.store.items()["at-0001"]["scope"] == {"repo": "ledgerly", "observed_version": "1.0.0"}


def test_scope_and_version_warning(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    learn_round_note(mem, scripted)
    assert mem.retrieve(load_task("H01"), "1.0.0").ids == ["at-0001"]
    simkit = mem.retrieve(load_task("B01"), "0.4.0")
    assert simkit.ids == [] and simkit.debug["out_of_scope"] == ["at-0001"]
    v2 = mem.retrieve(load_task("S01"), "2.0.0")
    assert v2.debug["version_warnings"] == ["at-0001"] and "CHANGELOG" in v2.context


def test_blame_suspect_retire_and_recover(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    learn_round_note(mem, scripted)
    s01 = load_task("S01")
    # cited, but the failure is about errors, not rounding: no blame
    mem.feedback(s01, "2.0.0", run(False, comments=[ERROR_COMMENT], shown=["at-0001"], cited=["at-0001"]))
    assert mem.store.items()["at-0001"]["status"] == "active"
    # cited and failed a rounding review check: suspect, then retired
    mem.feedback(s01, "2.0.0", run(False, comments=[ROUND_V2_COMMENT], shown=["at-0001"], cited=["at-0001"]))
    assert mem.store.items()["at-0001"]["status"] == "suspect"
    assert "WARNING: a recent task" in mem.retrieve(load_task("S02"), "2.0.0").context
    mem.feedback(s01, "2.0.0", run(False, comments=[ROUND_V2_COMMENT], shown=["at-0001"], cited=["at-0001"]))
    assert mem.store.items()["at-0001"]["status"] == "retired"
    assert mem.retrieve(load_task("S02"), "2.0.0").ids == []


def test_suspicion_cleared_by_verified_success(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    learn_round_note(mem, scripted)
    mem.feedback(load_task("H01"), "1.0.0", run(False, comments=[ROUND_COMMENT], shown=["at-0001"], cited=["at-0001"]))
    mem.feedback(load_task("H05"), "1.0.0", run(True, shown=["at-0001"], cited=["at-0001"]))
    item = mem.store.items()["at-0001"]
    assert item["status"] == "active" and item["usage"]["cited_pass"] == 1 and item["usage"]["fail_streak"] == 0


def test_supersede_and_duplicate(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    learn_round_note(mem, scripted)
    new_rule = {
        "kind": "project_fact", "topic": "money-rounding", "title": "Rounding policy is banker's since 2.0",
        "content": "Since ledgerly 2.0.0 round money only via ledgerly.money.round_money; it implements banker's rounding.",
        "evidence_quote": "since 2.0.0 this is banker's rounding, see CHANGELOG",
    }
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [new_rule]})
    scripted.answers[RELATE_SYSTEM].append({"relations": [{"id": "at-0001", "relation": "supersedes"}]})
    mem.learn(load_task("S01"), "2.0.0", run(False, True, [ROUND_V2_COMMENT]), "t", "d")
    items = mem.store.items()
    assert items["at-0001"]["status"] == "superseded" and items["at-0001"]["superseded_by"] == "at-0002"
    assert items["at-0002"]["supersedes"] == ["at-0001"]
    # the same rule confirmed again becomes extra evidence, not a second item
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [new_rule]})
    scripted.answers[RELATE_SYSTEM].append({"relations": [{"id": "at-0002", "relation": "duplicate"}]})
    mem.learn(load_task("S02"), "2.0.0", run(False, True, [ROUND_V2_COMMENT]), "t", "d")
    items = mem.store.items()
    assert len(items) == 2 and len(items["at-0002"]["evidence"]) == 2


def test_old_evidence_cannot_supersede_newer_rule(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [ROUND_NOTE]})
    mem.learn(load_task("S01"), "2.0.0", run(False, True, [ROUND_COMMENT]), "t", "d")
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [dict(ROUND_NOTE, title="Old rule")]})
    scripted.answers[RELATE_SYSTEM].append({"relations": [{"id": "at-0001", "relation": "supersedes"}]})
    mem.learn(load_task("E01"), "1.0.0", run(False, True, [ROUND_COMMENT]), "t", "d")
    assert mem.store.items()["at-0001"]["status"] == "active"


def test_event_log_replays_from_disk(tmp_path, scripted):
    mem = make_memory("attest", tmp_path)
    learn_round_note(mem, scripted)
    again = make_memory("attest", tmp_path)
    assert again.store.items() == mem.store.items()


def test_reasoningbank_has_no_scope(tmp_path):
    llm.set_llm(lambda s, u: {"items": [{"title": "Use Decimal", "description": "money", "content": "Always use Decimal for costs and amounts."}]})
    try:
        mem = make_memory("reasoningbank", tmp_path)
        mem.learn(load_task("E01"), "1.0.0", run(True), "t", "d")
        assert mem.retrieve(load_task("B01"), "0.4.0").ids == ["rb-0001"]  # ledgerly experience reaches simkit
    finally:
        llm.set_llm(None)


def test_ace_counters_prune_and_dedupe(tmp_path):
    answers = [
        {"new_bullets": [{"section": "common_mistakes", "content": "Do not use float for money amounts."}]},
        {"harmful": ["ace-0001"], "new_bullets": [{"section": "common_mistakes", "content": "Do not use float for money amounts!"}]},
        {"harmful": ["ace-0001"]},
    ]
    llm.set_llm(lambda s, u: answers.pop(0))
    try:
        mem = make_memory("ace", tmp_path)
        for _ in range(3):
            mem.learn(load_task("E01"), "1.0.0", run(True), "t", "d")
        assert mem.store.items()["ace-0001"]["status"] == "pruned"
        assert sum(1 for e in mem.store.events if e["type"] == "reject") == 1
        assert mem.retrieve(load_task("H01"), "1.0.0").ids == []
    finally:
        llm.set_llm(None)


def test_ablation_without_gate_learns_unverified_and_ungrounded(tmp_path, scripted):
    mem = make_memory("attest_no_gate", tmp_path)
    assert mem.name == "attest_no_gate"
    bad = dict(ROUND_NOTE, evidence_quote="")
    scripted.answers[DISTILL_SYSTEM].append({"candidates": [bad]})
    events = mem.learn(load_task("E01"), "1.0.0", run(False, False, [ROUND_COMMENT]), "t", "d")
    assert [e["type"] for e in events] == ["add"]
    assert mem.store.items()["at-0001"]["evidence"][0]["verified"] is False


def test_ablation_without_scope_leaks_and_drops_version_warning(tmp_path, scripted):
    mem = make_memory("attest_no_scope", tmp_path)
    learn_round_note(mem, scripted)
    assert mem.retrieve(load_task("B01"), "0.4.0").ids == ["at-0001"]
    v2 = mem.retrieve(load_task("S01"), "2.0.0")
    assert v2.debug["version_warnings"] == [] and "CHANGELOG" not in v2.context.split("\n", 1)[1]
