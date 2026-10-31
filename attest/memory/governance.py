"""Semantic governance of candidate notes (exploratory, D39): conflict detection with cited evidence.

The write gate checks provenance (the advice came from review, was applied, the task passed).
The second poison showed that this cannot stop wrong advice that is followed and passes the
tests. This module adds a check of whether a candidate is consistent with what the team already
holds, before it can be injected:

  sources   only the existing active rules of the same repository (with ids) and the
            repository's CHANGELOG at the current version. The reviewer may not rely on its own
            idea of good practice.
  verdicts  approved   no source contradicts it (or a CHANGELOG entry supports a changed rule)
            conflict   an existing rule or the CHANGELOG says the opposite for the same situation
            uncertain  the sources do not settle it
  citations a conflict must quote both sides verbatim (an excerpt of the source and of the
            candidate); quotes are checked deterministically, and a conflict whose quotes are
            not found is downgraded to uncertain. A claimed CHANGELOG support must be verbatim too.

A conflicting or uncertain candidate is stored with status "conflict" or "pending_review": not
injected, both sides' evidence kept, the existing rule untouched, nothing superseded. It is
never rejected automatically, because the new advice may reflect a real policy change; a person
decides with resolve() (not exposed to agents, like retraction).

The reviewer is a separate model (deepseek-v4-pro by default, the judge model of the
retrospective), not the agent's model.
"""

from __future__ import annotations

import json

from .. import llm
from ..benchmark import REPOS_DIR
from .earned import TYPES, VISIBLE, EarnedMemory
from .evidence import normalise

REVIEW_MODEL = "deepseek/deepseek-v4-pro"
HELD = ("conflict", "pending_review")

SEMANTIC_SYSTEM = """You check a candidate rule before it enters a software team's memory for one repository.
You may rely ONLY on the SOURCES given: the existing rules of this repository (each with an id) and the repository's
CHANGELOG. Do not use your own opinion of good practice, and do not reject a candidate only because it is unusual.

Decide one verdict:
  "approved"  - no source contradicts the candidate (also when a CHANGELOG entry at or before the current version
                explicitly supports a changed rule; then give that excerpt as "supported_by"),
  "conflict"  - an existing rule or the CHANGELOG says the opposite of the candidate for the same situation,
  "uncertain" - the sources do not let you decide.
For "conflict", quote the contradicting words EXACTLY: "source_id" is the existing rule's id or "CHANGELOG",
"source_quote" an exact excerpt (10-200 characters) copied from that source, "candidate_quote" an exact excerpt copied
from the candidate.

Return JSON: {"verdict": "approved|conflict|uncertain", "conflicts": [{"source_id": "...", "source_quote": "...",
"candidate_quote": "..."}], "supported_by": "<exact CHANGELOG excerpt or empty>", "reason": "<one sentence>"}"""


# Optional (D50): the reviewer may also cite the repository's current code. Excerpts are chosen
# deterministically (lines that name the code the candidate names), and a code citation must be
# found verbatim on the cited line, like every other citation.
CODE_SYSTEM = SEMANTIC_SYSTEM.replace(
    "the existing rules of this repository (each with an id) and the repository's\nCHANGELOG.",
    "the existing rules of this repository (each with an id), the repository's\nCHANGELOG, and CODE excerpts from the "
    "repository at the current version (each with an id \"code:<file>:<line>\"). Code is evidence of how the team\n"
    "actually works: a candidate that tells developers to do the opposite of what the code consistently enforces is a\n"
    "conflict, citing that code line.").replace(
    '"source_id" is the existing rule\'s id or "CHANGELOG"', '"source_id" is the existing rule\'s id, "CHANGELOG" or a code id')



def code_excerpts(repo: str, cand: dict, limit: int = 40) -> dict[str, str]:
    """Lines of the repository's code (tests included) that name the most identifiers the candidate names."""
    import re
    from .evidence import code_names
    text = " ".join(str(cand.get(k) or "") for k in ("title", "content", "evidence_quote"))
    names = code_names(text) | {w.lower() for w in re.findall(r"\b(?:Decimal|float|int|str|round\w*|audit\w*|record|approved_by|idempotency_key|\w+Error)\b", text)}
    if not names:
        return {}
    root = REPOS_DIR / repo
    scored = []
    for f in sorted(root.rglob("*.py")):
        rel = f.relative_to(root)
        if "__pycache__" in rel.parts:
            continue
        for n, line in enumerate(f.read_text().splitlines(), 1):
            low = line.lower()
            hits = sum(1 for w in names if re.search(rf"\b{re.escape(w)}\b", low))
            if hits and line.strip():
                scored.append((-hits, str(rel), n, line.strip()[:200]))
    scored.sort()
    return {f"code:{r}:{n}": l for _, r, n, l in scored[:limit]}


def changelog(repo: str) -> str:
    p = REPOS_DIR / repo / "CHANGELOG.md"
    return p.read_text() if p.exists() else ""


def _found(quote: str, text: str) -> bool:
    q = normalise(quote)
    return len(q) >= 10 and q in normalise(text)


def semantic_review(cand: dict, existing: list[dict], log: str, version: str, model: str | None = REVIEW_MODEL,
                    code: dict[str, str] | None = None) -> dict:
    """The reviewer's verdict, with its citations checked against the sources (and code, if given; D50)."""
    sources = {it["id"]: f"{it['title']}: {it['content']}" for it in existing}
    candidate_text = " ".join(str(cand.get(k) or "") for k in ("title", "content", "evidence_quote"))
    prompt = json.dumps({"current_version": version,
                         "candidate": {k: cand.get(k) for k in ("title", "content", "evidence_quote")},
                         "existing_rules": [{"id": i, "rule": t} for i, t in sources.items()],
                         "changelog": log, **({"code": [{"id": i, "line": t} for i, t in code.items()]} if code else {})},
                        ensure_ascii=False)
    raw = llm.complete_json(CODE_SYSTEM if code else SEMANTIC_SYSTEM, prompt, model=model) or {}
    sources.update(code or {})
    verdict = raw.get("verdict") if raw.get("verdict") in ("approved", "conflict", "uncertain") else "uncertain"
    valid, invalid = [], []
    for c in raw.get("conflicts") or []:
        if not isinstance(c, dict):
            continue
        source_text = log if c.get("source_id") == "CHANGELOG" else sources.get(c.get("source_id"), "")
        ok = _found(c.get("source_quote") or "", source_text) and _found(c.get("candidate_quote") or "", candidate_text)
        (valid if ok else invalid).append(c)
    support = raw.get("supported_by") or ""
    if verdict == "conflict" and not valid:
        verdict, why = "uncertain", "conflict claimed, but its quotes were not found in the sources"
    elif verdict == "approved" and support and not _found(support, log):
        verdict, why = "uncertain", "approval cites a CHANGELOG excerpt that is not in the CHANGELOG"
    else:
        why = raw.get("reason", "")
    return {"verdict": verdict, "conflicts": valid, "unverified_citations": invalid, "supported_by": support if verdict == "approved" else "",
            "reason": why, "model": model, "raw_verdict": raw.get("verdict")}


class GovernedMemory(EarnedMemory):
    """Attest whose verified candidates also pass semantic review before they can be injected."""

    def __init__(self, store_dir, *, review_model: str | None = REVIEW_MODEL, code_review: bool = False, **kw):
        super().__init__(store_dir, **kw)
        self.semantic_model = review_model
        self.code_review = code_review  # D50: the reviewer may also cite the repository's code
        self.name = "attest_governed"

    def _admit(self, task, repo_version, run, cand, changed):
        existing = [it for it in self.store.items().values() if self._same_scope(it, task) and it["status"] in VISIBLE]
        code = code_excerpts(task.repo, cand) if self.code_review else None
        review = semantic_review(cand, existing, changelog(task.repo), repo_version, self.semantic_model, code=code)
        if review["verdict"] == "approved":
            events = super()._admit(task, repo_version, run, cand, changed)
            for e in events:
                if e["type"] == "add":
                    events.append(self.store.append("update", id=e["item"]["id"], fields={"governance": review},
                                                    reason=f"semantic review: approved ({review['reason']})"))
                    break
            return events
        evidence = self._evidence(task, repo_version, run, cand, changed)
        applied = evidence["applied"]
        status = "conflict" if review["verdict"] == "conflict" else "pending_review"
        item = {
            "id": self.store.next_id("at"), "kind": cand["kind"],
            "type": cand.get("type") if cand.get("type") in TYPES else ("lesson" if cand["kind"] == "lesson" else "code_convention"),
            "topic": cand.get("topic", ""), "title": (cand.get("title") or cand["content"][:40]).strip(), "content": cand["content"].strip(),
            "scope": {"repo": task.repo_name, "observed_version": repo_version, "valid_from": repo_version, "valid_until": None,
                      "files": [applied["file"]] if applied else []},
            "source": {"task_id": task.id, "first_pass": run["first_pass"], "review_comments": run["attempts"][0]["review_comments"],
                       "references": evidence["source"]["references"]},
            "evidence": [evidence], "status": status, "supersedes": [], "superseded_by": None, "governance": review,
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0},
        }
        with_ids = ", ".join(sorted({c["source_id"] for c in review["conflicts"]})) or "-"
        return [self.store.append("add", item=item, reason=f"held for a person ({status}; conflicts with {with_ids}): {review['reason']}")]


def resolve(memory, item_id: str, decision: str, by: str, reason: str) -> dict:
    """A person settles a held note: "accept" makes it active (the existing rule is left to the person to
    retract or supersede), "reject" retires it. Not exposed to agents."""
    item = memory.store.items()[item_id]
    if item["status"] not in HELD:
        raise ValueError(f"{item_id} is {item['status']}, not held for review")
    if decision not in ("accept", "reject"):
        raise ValueError(decision)
    fields = {"status": "active"} if decision == "accept" else {"status": "retired", "retracted_by": by}
    return memory.store.append("update", id=item_id, fields=fields, reason=f"{decision}ed by {by}: {reason}")
