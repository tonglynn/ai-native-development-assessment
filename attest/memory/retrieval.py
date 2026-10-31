"""The ranking step of retrieval, switchable between lexical and embedding (retrieval ablation).

Everything around it stays the same in both arms: which notes are candidates
(status and repository scope), k, the prompt block. The query is always the task
title and issue text only, so no review comment or fix of the task being solved
can influence what is retrieved.
"""

Hybrid retrieval and task-aware reranking (D47, exploratory, opt-in): after the hard filter (repository,
version, status: `candidates()`), BM25 and the embedding ranking are merged by reciprocal rank fusion;
`hybrid_rerank` then lets a model re-order the top 10 by whether each rule applies to this task's
business situation, given each note's type, files and version range. The k injected stays 6.

Reading rule, fixed before the end-to-end run (`retrieval_ablation` with arms attest, attest_hybrid,
attest_hybrid_rerank; same memory snapshots as the earlier ablation; 3 repetitions): the criterion is
the coding result, not Recall@5. Per arm against lexical Attest, held-out pass@1 paired by task with a
bootstrap 95% interval: "better" only if the lower bound is > 0; "not worse" if it is > -10 points
(the D26 margin); otherwise "inconclusive" or "worse". Stale and control groups, business-risk
failures, tokens and latency are reported beside it. Offline Recall@5/Precision@5 are reported but
decide nothing.

from __future__ import annotations

import time

from . import embedding, text

RETRIEVERS = ("lexical", "embedding", "hybrid", "hybrid_rerank")
RRF_K = 60          # reciprocal rank fusion constant (the usual default, not tuned)
RERANK_TOP = 10     # hybrid candidates the task-aware reranker sees
RERANK_MODEL = "deepseek/deepseek-flash"

RERANK_SYSTEM = """A developer is about to work on the TASK below in a repository. The NOTES are rules learned from
earlier verified work in the same repository, each with its type, the files it was learned in and the versions it holds for.
For each note, rate how much following it matters for THIS task, judging by the business situation and the conditions
under which the rule applies (what the task will touch, which operations, amounts, versions), not by shared words:
  3 = the task does what the rule governs, so ignoring it would very likely be a review comment;
  2 = probably relevant; 1 = possibly relevant; 0 = does not apply to this task.
Return JSON: {"scores": [{"id": "<note id>", "score": 0-3}]}"""


def check_retriever(name: str) -> str:
    if name not in RETRIEVERS:
        raise ValueError(f"unknown retriever {name!r}; choose from {RETRIEVERS}")
    return name


def hybrid(query: str, docs: dict[str, str], k: int | None) -> list[tuple[str, float]]:
    """BM25 and embedding rankings merged by reciprocal rank fusion (D47)."""
    fused: dict[str, float] = {}
    for ranked in (text.bm25_rank(query, docs, None), embedding.rank(query, docs, None)):
        for pos, (d, _) in enumerate(ranked):
            fused[d] = fused.get(d, 0.0) + 1.0 / (RRF_K + pos + 1)
    out = sorted(((d, round(v, 6)) for d, v in fused.items()), key=lambda x: (-x[1], x[0]))
    return out[:k]


_rerank_cache: dict[str, dict] = {}


def rerank(query: str, docs: dict[str, str], details: dict[str, str], k: int | None) -> list[tuple[str, float]]:
    """Hybrid top RERANK_TOP re-ordered by a model's task-aware applicability score (D47); the rest follow in
    hybrid order. If the model fails, the hybrid order is kept. Scores are cached per (query, notes)."""
    import hashlib
    import json

    from .. import llm

    base = hybrid(query, docs, None)
    top = [d for d, _ in base[:RERANK_TOP]]
    key = hashlib.sha256(json.dumps([query, [(d, docs[d]) for d in top]]).encode()).hexdigest()
    if key not in _rerank_cache:
        listing = "\n".join(f"[{d}] {docs[d]}\n    ({details.get(d, '')})" for d in top)
        try:
            out = llm.complete_json(RERANK_SYSTEM, f"TASK:\n{query[:3000]}\n\nNOTES:\n{listing}", model=RERANK_MODEL)
            _rerank_cache[key] = {str(x.get("id")): float(x.get("score", 0)) for x in out.get("scores", []) if isinstance(x, dict)}
        except Exception:  # noqa: BLE001 - keep the hybrid order
            _rerank_cache[key] = {}
    scores = _rerank_cache[key]
    order = {d: n for n, (d, _) in enumerate(base)}
    head = sorted(top, key=lambda d: (-scores.get(d, -1.0), order[d]))
    ranked = [(d, scores.get(d, -1.0)) for d in head] + [(d, -1.0) for d, _ in base[RERANK_TOP:]]
    return ranked[:k]


def timed_rank(retriever: str, query: str, docs: dict[str, str], k: int | None,
               details: dict[str, str] | None = None) -> tuple[list[tuple[str, float]], float]:
    started = time.perf_counter()
    if retriever == "hybrid":
        ranked = hybrid(query, docs, k)
    elif retriever == "hybrid_rerank":
        ranked = rerank(query, docs, details or {}, k)
    else:
        ranked = (embedding.rank if retriever == "embedding" else text.rank)(query, docs, k)
    return ranked, round((time.perf_counter() - started) * 1000, 2)
