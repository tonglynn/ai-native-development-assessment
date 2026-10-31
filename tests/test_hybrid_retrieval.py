"""Hybrid retrieval and task-aware reranking (D47), with stand-ins for the embedding model and the reranker."""

from attest.memory import embedding, retrieval, text


def fake_embed(query, docs, k):
    order = sorted(docs, key=lambda d: (-("approval" in docs[d]), d))
    return [(d, 1.0 - n / 10) for n, d in enumerate(order)][:k]


DOCS = {"a": "round money with round_money", "b": "refunds above the threshold need approval",
        "c": "audit every refund with audit.record"}


def test_bm25_prefers_matching_terms():
    assert text.bm25_rank("refund audit record", DOCS, 1)[0][0] == "c"


def test_hybrid_fuses_both(monkeypatch):
    embedding.set_ranker(fake_embed)
    try:
        ranked = [d for d, _ in retrieval.hybrid("refund audit record", DOCS, None)]
        assert set(ranked) == set(DOCS) and ranked[0] in ("b", "c")
    finally:
        embedding.set_ranker(None)


def test_rerank_orders_by_model_and_falls_back(monkeypatch):
    from attest import llm
    embedding.set_ranker(fake_embed)
    retrieval._rerank_cache.clear()
    try:
        monkeypatch.setattr(llm, "complete_json", lambda *a, **k: {"scores": [{"id": "a", "score": 3}, {"id": "b", "score": 0}]})
        assert [d for d, _ in retrieval.rerank("refund", DOCS, {}, None)][0] == "a"
        retrieval._rerank_cache.clear()
        monkeypatch.setattr(llm, "complete_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
        assert [d for d, _ in retrieval.rerank("refund", DOCS, {}, None)] == [d for d, _ in retrieval.hybrid("refund", DOCS, None)]
    finally:
        embedding.set_ranker(None)
