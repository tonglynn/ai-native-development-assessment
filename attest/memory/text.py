"""Deterministic text helpers: tokenising, lexical relevance and relatedness."""

from __future__ import annotations

import math
import re

STOPWORDS = set(
    """a an and are as at be by can for from has have if in into is it its must never not of on only or so
    that the their them then there these this to use used using was were when which while will with without
    you your should does each every any all also than more most same such other new add adds return returns
    value values function functions module code issue task python file files test tests ledgerly simkit""".split()
)


def tokens(text: str) -> list[str]:
    """Lower-case word tokens; identifiers like round_money and money.round_money are kept whole as well as split."""
    out = []
    for raw in re.findall(r"[A-Za-z_][A-Za-z0-9_.]*", text or ""):
        word = raw.strip(".").lower()
        parts = [p for p in re.split(r"[._]", word) if p]
        for t in {word, *parts}:
            if len(t) >= 3 and t not in STOPWORDS:
                out.append(t)
    return out


def rank(query: str, docs: dict[str, str], k: int) -> list[tuple[str, float]]:
    """Return the top-k (doc_id, score) by idf-weighted token overlap with the query."""
    if not docs:
        return []
    doc_tokens = {d: set(tokens(t)) for d, t in docs.items()}
    n = len(docs)
    df: dict[str, int] = {}
    for toks in doc_tokens.values():
        for t in toks:
            df[t] = df.get(t, 0) + 1
    q = set(tokens(query))
    scored = []
    for d, toks in doc_tokens.items():
        score = sum(math.log(1 + n / df[t]) for t in q & toks)
        scored.append((d, round(score, 3)))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


def bm25_rank(query: str, docs: dict[str, str], k: int | None, k1: float = 1.5, b: float = 0.75) -> list[tuple[str, float]]:
    """Okapi BM25 (used by the hybrid retriever, D47); ties broken by id like rank()."""
    if not docs:
        return []
    toks = {d: tokens(t) for d, t in docs.items()}
    n = len(docs)
    avg = sum(len(v) for v in toks.values()) / n or 1.0
    df: dict[str, int] = {}
    for v in toks.values():
        for t in set(v):
            df[t] = df.get(t, 0) + 1
    q = set(tokens(query))
    scored = []
    for d, v in toks.items():
        tf: dict[str, int] = {}
        for t in v:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        for t in q & tf.keys():
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * tf[t] * (k1 + 1) / (tf[t] + k1 * (1 - b + b * len(v) / avg))
        scored.append((d, round(score, 4)))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


def salient(text: str) -> set[str]:
    return {t for t in tokens(text) if len(t) >= 5}


def related(a: str, b: str, min_overlap: int = 2) -> bool:
    """True when two texts share at least ``min_overlap`` salient tokens (used to attribute failures)."""
    return len(salient(a) & salient(b)) >= min_overlap


def jaccard(a: str, b: str) -> float:
    sa, sb = set(tokens(a)), set(tokens(b))
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def normalise(text: str) -> str:
    return " ".join((text or "").split()).lower()
