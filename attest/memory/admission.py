"""Trust-tiered admission (exploratory, after the main experiment): stop memory pollution at injection.

The forgetting experiment showed that verified one-off details ("the refund export
uses semicolons") crowd the team's rules out of the injected notes, and that no
forgetting policy repairs it. Admission decides, before ranking, which notes may be
injected anywhere and which only where they were learned. Explainable rules, no model
score:

  policy      the evidence names a policy or incident (POLICY_PREFIXES: FIN-, POL-, SEC-, INC-)
  convention  the source review comment states it is a team convention
  repeated    verified in at least 2 independent tasks
  candidate   anything else: a detail seen once. Stored, never deleted, injected only
              when the task names a file the note was learned in; promoted
              automatically when a second independent task verifies it.

Ranking: rules (policy, convention, repeated) with any relevance come first, then
file-matched candidates; relevance orders notes within a tier.

Limit: the simulated review comments of this benchmark mark team rules explicitly
("[team convention]"); real reviewers rarely do (REAL_HISTORY.md). On real history the
reliable signals are policy references and repetition, which take time to accumulate.
"""

from __future__ import annotations

import re

RULE_TIERS = ("policy", "convention", "repeated")
CONVENTION_RE = re.compile(r"\[team convention\]|\bteam convention\b|\bour convention\b|\bwe always\b", re.I)
# Which recorded references count as a policy or an incident: finance (FIN-), general (POL-)
# and security (SEC-) policies, incidents (INC-). The evidence parser also records ADR-, RFC-
# and CVE- references; they stay in the evidence but do not make a note a policy rule.
POLICY_PREFIXES = ("FIN", "POL", "SEC", "INC")


def _norm(text: str) -> str:
    return " ".join((text or "").split()).lower()


def policy_references(item: dict) -> list[str]:
    refs = set((item.get("source") or {}).get("references") or [])
    for ev in item.get("evidence") or []:
        refs |= set((ev.get("source") or {}).get("references") or [])
    return sorted(r for r in refs if r.split("-", 1)[0] in POLICY_PREFIXES)


def independent_tasks(item: dict) -> set[str]:
    tasks = {ev.get("task_id") for ev in item.get("evidence") or [] if ev.get("task_id")}
    tasks |= set((item.get("forgetting") or {}).get("verified_tasks") or [])
    if (item.get("source") or {}).get("task_id"):
        tasks.add(item["source"]["task_id"])
    return tasks


def tier(item: dict) -> str:
    evidence = item.get("evidence") or []
    if policy_references(item):
        return "policy"
    comments = (item.get("source") or {}).get("review_comments") or []
    for ev in evidence:
        quote = _norm((ev.get("source") or {}).get("quote", ""))
        if (ev.get("source") or {}).get("kind") == "review_comment" and quote:
            if any(quote in _norm(c) and CONVENTION_RE.search(c) for c in comments):
                return "convention"
    if len(independent_tasks(item)) >= 2:
        return "repeated"
    return "candidate"


def files_named(task) -> set[str]:
    return set(re.findall(r"[\w./-]+\.py", f"{getattr(task, 'title', '')} {getattr(task, 'issue', '')}"))


def injectable_here(item: dict, task) -> bool:
    """Rules anywhere in their repository; a candidate only in a task that names one of its files."""
    if tier(item) in RULE_TIERS:
        return True
    files = set((item.get("scope") or {}).get("files") or [])
    return bool(files & files_named(task))
