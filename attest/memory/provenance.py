"""Are two pieces of soft evidence really independent? (D61)

v4 approves a note on two kinds of soft evidence (a trusted reviewer, repetition). Repetition used to mean
"two or more tasks with different quotes". An attacker can manufacture that: post the same comment on two
pull requests, quote different fragments of it, or paraphrase it. Each piece of evidence is therefore traced
to its ORIGIN, and only distinct origins count:

  origin of a review-comment quote   the full comment it was quoted from (normalised), so two fragments of
                                     one comment, or the same comment on two tasks, share one origin
  origin of a diff quote             the agent's own change in that task: never independent of the task
  near-duplicates                    comments whose word sets overlap by JACCARD_SAME or more are one origin
                                     (paraphrase, copy with small edits)
  common upstream                    comments citing the same external reference (FIN-, INC-, a URL) count
                                     as one origin for repetition (one source quoted twice); the reference
                                     itself is judged by the policy registry, not by repetition

independent_origins(item) returns the distinct origins; repetition needs two, and a trusted reviewer plus
repetition needs a repeated origin that is not the reviewer's own comment.
"""

from __future__ import annotations

import re

from .admission import _norm
from .text import jaccard

JACCARD_SAME = 0.6
REF_RE = re.compile(r"\b(?:FIN|POL|SEC|INC|ADR|RFC|CVE)-[\w-]+\b|https?://\S+", re.I)


def origin_of(ev: dict, comments: list[str], task_id: str | None) -> str:
    src = ev.get("source") or {}
    quote = _norm(src.get("quote", ""))
    if src.get("kind") == "review_comment" and quote:
        full = src.get("comment") or next((c for c in comments if quote in _norm(c)), None)
        if full is not None:
            return "comment:" + _norm(full)
        return "comment:" + quote
    return f"diff:{ev.get('task_id') or task_id}"


def merge(origins: list[str]) -> list[str]:
    """Collapse near-duplicate comments and comments sharing an external reference into one origin."""
    groups: list[list[str]] = []
    for o in origins:
        refs = set(m.lower() for m in REF_RE.findall(o))
        for g in groups:
            g_refs = set(m.lower() for x in g for m in REF_RE.findall(x))
            a, b = o[len("comment:"):], g[0][len("comment:"):]
            if o.startswith("comment:") and g[0].startswith("comment:") and (
                    a in b or b in a or jaccard(o, g[0]) >= JACCARD_SAME or (refs and refs & g_refs)):
                g.append(o)
                break
            if o == g[0]:
                g.append(o)
                break
        else:
            groups.append([o])
    return [g[0] for g in groups]


def independent_origins(item: dict) -> list[str]:
    comments = list((item.get("source") or {}).get("review_comments") or [])
    for ev in item.get("evidence") or []:  # later confirmations carry their own comments
        comments += list(ev.get("review_comments") or [])
    return merge([origin_of(ev, comments, (item.get("source") or {}).get("task_id")) for ev in item.get("evidence") or []])
