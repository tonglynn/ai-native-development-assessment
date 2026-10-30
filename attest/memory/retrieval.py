"""The ranking step of retrieval, switchable between lexical and embedding (retrieval ablation).

Everything around it stays the same in both arms: which notes are candidates
(status and repository scope), k, the prompt block. The query is always the task
title and issue text only, so no review comment or fix of the task being solved
can influence what is retrieved.
"""

from __future__ import annotations

import time

from . import embedding, text

RETRIEVERS = ("lexical", "embedding")


def check_retriever(name: str) -> str:
    if name not in RETRIEVERS:
        raise ValueError(f"unknown retriever {name!r}; choose from {RETRIEVERS}")
    return name


def timed_rank(retriever: str, query: str, docs: dict[str, str], k: int | None) -> tuple[list[tuple[str, float]], float]:
    started = time.perf_counter()
    ranked = (embedding.rank if retriever == "embedding" else text.rank)(query, docs, k)
    return ranked, round((time.perf_counter() - started) * 1000, 2)
