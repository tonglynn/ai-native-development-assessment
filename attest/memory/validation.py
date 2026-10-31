"""Two layers of evidence: adoption and independent validation (D52; optional).

The write gate's evidence shows that advice was ADOPTED: a quote, a changed line that applies it, a
task that passed. Across the main experiment, 166 of 207 pieces of evidence quote the diff and 97 quote
the very line they cite as applied: the agent's own change is then both the claim and its proof, and
an obeyed injection or a test-passing poison produces exactly that.

So a note is

  observed   adoption only: kept, shown only where it was learned (like a candidate), never a rule
  approved   adoption plus at least one INDEPENDENT validation, which never uses the same changed line:
               policy     a policy or incident id in the human-maintained registry (Trust.registry)
               reviewer   the evidence quote comes from a trusted reviewer's comment (Trust.trusted)
               check      an executable policy check that covers the claim passed (e.g. the D38 guard)
               repeated   two or more independent tasks with DIFFERENT quotes, at least one of which is
                          not the agent's own line

`self_cited` evidence (quote taken from the diff and contained in, or containing, the applied line)
never counts as independent.
"""

from __future__ import annotations

from . import admission
from .evidence import normalise
from .admission import _norm


def self_cited(ev: dict) -> bool:
    src, app = ev.get("source") or {}, ev.get("applied") or {}
    if src.get("kind") != "diff":
        return False
    q, a = normalise(src.get("quote", "")).lstrip("+- "), normalise(app.get("line", "")).lstrip("+- ")
    return bool(q and a and (q in a or a in q))


def independent(item: dict, trust: admission.Trust, checks: dict | None = None) -> list[str]:
    """The independent validations a note has (empty: observed only)."""
    found = []
    if [r for r in admission.policy_references(item) if r in trust.registry]:
        found.append("policy")
    trusted = [c for c in (item.get("source") or {}).get("review_comments") or [] if admission._norm(c) in trust.trusted]
    for ev in item.get("evidence") or []:
        q = admission._norm((ev.get("source") or {}).get("quote", ""))
        if (ev.get("source") or {}).get("kind") == "review_comment" and q and any(q in admission._norm(c) for c in trusted):
            found.append("reviewer")
            break
    if checks and checks.get(item.get("id")):
        found.append("check")
    # repetition (D61): two or more INDEPENDENT external origins (review comments traced to their source,
    # near-duplicates and shared references merged); the agent's own diff lines never count; a trusted
    # reviewer's comment already counted as "reviewer" cannot also count toward repetition
    from .provenance import independent_origins
    tasks = {ev.get("task_id") for ev in item.get("evidence") or []}
    external = [o for o in independent_origins(item) if o.startswith("comment:")]
    if "reviewer" in found:
        trusted_origins = {"comment:" + _norm(c) for c in trusted}
        external = [o for o in external if o not in trusted_origins]
        enough = len(external) >= 1
    else:
        enough = len(external) >= 2
    if len(tasks) >= 2 and enough:
        found.append("repeated")
    return found


def status(item: dict, trust: admission.Trust, checks: dict | None = None) -> str:
    return "approved" if independent(item, trust, checks) else "observed"
