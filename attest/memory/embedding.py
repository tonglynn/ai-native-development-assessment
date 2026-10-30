"""Embedding retrieval for the retrieval ablation (exploratory, reported separately).

A small local model (no API, no cost, deterministic on CPU) ranks notes by cosine
similarity between the task (title + issue) and each note. It plugs into the same
place as the lexical ranker (``text.rank``): same candidates, same k, same output
shape, so only the ranking function differs between the two arms.

Model and versions are pinned and recorded with every ranking (``info()``).
Document embeddings are cached by text, so a note is encoded once per process;
the cache never changes a score, only latency.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path

MODEL = "BAAI/bge-small-en-v1.5"          # fastembed's ONNX build: Qdrant/bge-small-en-v1.5-onnx-Q
MODEL_REVISION = "aa8f8b060edb00e03bfdd08813a2949946c8ba55"  # Hugging Face snapshot used in development
CACHE_DIR = Path(os.environ.get("ATTEST_EMBED_CACHE", "~/.cache/attest-fastembed")).expanduser()

_lock = threading.Lock()
_model = None
_doc_cache: dict[str, list[float]] = {}
_ranker = None  # tests can install a deterministic stand-in with set_ranker()


def set_ranker(fn) -> None:
    """Replace the embedding ranker (tests). ``fn(query, docs, k) -> [(id, score)]``; None restores the model."""
    global _ranker
    _ranker = fn


def _load():
    global _model
    if _model is None:
        from fastembed import TextEmbedding

        _model = TextEmbedding(MODEL, cache_dir=str(CACHE_DIR))
    return _model


def info() -> dict:
    import importlib.metadata as md

    def ver(pkg):
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return None

    return {"model": MODEL, "revision": MODEL_REVISION, "fastembed": ver("fastembed"), "onnxruntime": ver("onnxruntime"),
            "similarity": "cosine (normalised embeddings, dot product)", "query_prefix": "fastembed query_embed default"}


def rank(query: str, docs: dict[str, str], k: int | None) -> list[tuple[str, float]]:
    """Top-k (doc_id, cosine) for the query; ties broken by id like the lexical ranker. k=None ranks all."""
    if _ranker is not None:
        return _ranker(query, docs, k)
    if not docs:
        return []
    import numpy as np

    with _lock:  # the experiment runs sequences in threads; one model instance, encoded serially
        model = _load()
        missing = [t for t in dict.fromkeys(docs.values()) if t not in _doc_cache]
        if missing:
            for text, vec in zip(missing, model.embed(missing)):
                _doc_cache[text] = vec
        q = np.asarray(next(iter(model.query_embed([query]))))
    ids = list(docs)
    mat = np.asarray([_doc_cache[docs[i]] for i in ids])
    mat = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    scores = mat @ (q / np.linalg.norm(q))
    scored = sorted(((i, round(float(s), 4)) for i, s in zip(ids, scores)), key=lambda x: (-x[1], x[0]))
    return scored if k is None else scored[:k]
