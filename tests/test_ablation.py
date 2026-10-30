"""Retrieval ablation: only the ranking differs between arms; metrics and leakage checks are right."""

import json
import re

import pytest

from attest import ablation, llm
from attest.benchmark import load_task
from attest.memory import make_memory
from attest.memory import embedding


def _attest_item(i, repo, title, content, source="E04"):
    return {"id": f"at-{i:04d}", "status": "active", "title": title, "content": content,
            "scope": {"repo": repo, "observed_version": "1.0.0"}, "usage": {"cited": 0, "cited_pass": 0, "cited_fail": 0},
            "source": {"task_id": source}}


def _rb_item(i, title, content, source="E04"):
    return {"id": f"rb-{i:04d}", "title": title, "description": "", "content": content, "source": {"task_id": source}}


ATTEST_ITEMS = {it["id"]: it for it in [
    _attest_item(1, "ledgerly", "Retries", "Accept idempotency_key and return early when the audit log already has that key."),
    _attest_item(2, "ledgerly", "Rounding", "Round money with round_money."),
    _attest_item(3, "ledgerly", "Errors", "Raise BillingError with a code."),
    _attest_item(4, "simkit", "Floats", "simkit uses floats."),
]}
RB_ITEMS = {it["id"]: it for it in [
    _rb_item(1, "Retries", "Accept idempotency_key and return early when the audit log already has that key."),
    _rb_item(2, "Rounding", "Round money with round_money."),
]}
LABELS = {"idempotency_key": ["C5"], "round_money": ["C1"], "BillingError": ["C2"], "floats": ["K1"]}


def reverse_ranker(query, docs, k):
    """A stand-in 'embedding' ranker: reverse id order, so it visibly differs from the lexical one."""
    ranked = [(i, 1.0 - n / 100) for n, i in enumerate(sorted(docs, reverse=True))]
    return ranked if k is None else ranked[:k]


def fake_judge(system, user):
    notes = re.findall(r"^(\d+)\. (.*)$", user, re.M)
    return {"labels": [{"n": int(n), "rules": [r for key, rules in LABELS.items() if key in t for r in rules]} for n, t in notes]}


@pytest.fixture
def fakes():
    embedding.set_ranker(reverse_ranker)
    llm.set_llm(fake_judge)
    yield
    embedding.set_ranker(None)
    llm.set_llm(None)


def test_arms_share_candidates_and_differ_only_in_ranking(fakes):
    lex, emb = make_memory("attest", None), make_memory("attest_emb", None)
    for m in (lex, emb):
        ablation.seed(m, ATTEST_ITEMS)
    task = load_task("H04")
    assert lex.candidates(task) == emb.candidates(task)
    assert "at-0004" not in lex.candidates(task)  # the simkit note stays out of scope in both arms
    a, b = lex.retrieve(task, "1.0.0"), emb.retrieve(task, "1.0.0")
    assert set(a.ids) == set(b.ids) and a.ids != b.ids  # 3 candidates < k: same notes, different order
    assert a.debug["retriever"] == "lexical" and b.debug["retriever"] == "embedding"
    assert isinstance(b.debug["retrieval_ms"], float)
    assert emb.name == "attest_emb" and make_memory("reasoningbank_emb", None).name == "reasoningbank_emb"


def test_seed_is_idempotent_and_keeps_state():
    m = make_memory("attest", None)
    assert ablation.seed(m, ATTEST_ITEMS) == 4
    assert ablation.seed(m, ATTEST_ITEMS) == 0
    assert m.store.items() == ATTEST_ITEMS
    assert m.store.next_id("at") == "at-0005"


def test_leakage_check():
    ablation.check_no_leakage(ATTEST_ITEMS, {"H01", "S04"})
    with pytest.raises(RuntimeError):
        ablation.check_no_leakage({"x": {"source": {"task_id": "H04"}}}, {"H04"})


def test_metrics():
    m = ablation.metrics(["a", "b", "c", "d", "e", "f"], {"b", "f"})
    assert m["recall"] == 0.5 and m["precision"] == 1 / 5 and m["rr"] == 0.5
    assert ablation.metrics(["a"], {"a"})["precision"] == 1.0  # over the notes actually returned
    none = ablation.metrics(["a", "b"], set())
    assert none["recall"] is None and none["rr"] is None and none["irrelevant_returned"] == 2


def test_retrieval_quality_end_to_end(tmp_path, fakes):
    for system, items in (("attest", ATTEST_ITEMS), ("reasoningbank", RB_ITEMS)):
        p = ablation.snapshot_path(tmp_path / "main", system, 1)
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps(items))
    res = ablation.retrieval_quality(tmp_path / "main", tmp_path / "out", reps=1)
    assert {(r["system"], r["retriever"]) for r in res["summary"]} == {
        ("attest", "lexical"), ("attest", "embedding"), ("reasoningbank", "lexical"), ("reasoningbank", "embedding")}
    h04 = [r for r in res["per_query"] if r["task"] == "H04" and r["system"] == "attest"]
    assert all(r["relevant"] == 2 for r in h04)  # idempotency (C5) and BillingError (C2) notes; rounding is not needed
    b01 = [r for r in res["per_query"] if r["task"] == "B01" and r["system"] == "attest"]
    assert all(r["candidates"] == 1 and r["relevant"] == 1 for r in b01)  # only the simkit note is in scope
    labels = json.loads((tmp_path / "out" / "labels.json").read_text())
    assert len(labels) == 4  # each note text labelled once, shared by both arms
    assert (tmp_path / "out" / "retrieval_quality.md").read_text().startswith("# Retrieval quality")


def test_run_ablation_requires_main_snapshots(tmp_path):
    with pytest.raises(SystemExit):
        ablation.run_ablation(tmp_path / "abl", tmp_path / "missing", reps=1)
