"""Attest's memory: experience that is verified, scoped, versioned and retractable.

Design rules (each one is enforced by deterministic code; the model only proposes):

1. Write gate.   Only tasks whose final result passed verification may write memory.
                 Every candidate needs typed evidence (see evidence.py), recorded
                 separately: a SOURCE (verbatim excerpt of a review comment or the
                 diff, with any policy/incident references it names) and an APPLIED
                 line (a changed line of the verified diff, typed code/test/doc/config,
                 added or removed). A rule someone merely said, but the verified change
                 never did, is not learned (this also blocks poisoned review advice).
                 VERIFICATION (did the change pass) is a third field: passing tests show
                 the code meets the tests, not that the rule is right. An optional
                 independent review by a second model can be switched on (off in the
                 experiment). Rejected candidates stay in the log with the reason.
2. Scope.        Every item records the repository, the files it was observed in, the
                 version it was learned on and the versions it is valid for
                 (valid_from .. valid_until). Retrieval only considers items valid for
                 the task's repository and checked-out version.
3. Version.      Items learned on an older major version and not yet re-verified are
                 shown with a warning to check the CHANGELOG (validity unknown). Items
                 known to be invalid for this version are not shown.
4. Accounting.   Every time an item is shown or cited is recorded. If a task that
                 cited an item fails a review check about the same thing, the item
                 becomes "suspect"; a second such failure retires it. A later
                 verified success that cites it clears the suspicion. The latest
                 verification of every item is kept (last_verification).
5. Lifecycle.    When newer verified evidence changes a rule, the old item is marked
                 "superseded" and points to its replacement (never deleted):
                   - the rule changed in a newer version ("supersedes"): the old item
                     stays valid for older versions (valid_until = the new version),
                     the new one is valid from that version;
                   - the old rule was wrong ("corrects", or a change on the same
                     version): the old item is invalid everywhere.

Ablations (same class, one mechanism switched off; preregistered):
  gate=False   learn from every finished task, verified or not, and admit any
               well-formed candidate without evidence (rule 1 off)
  scope=False  retrieve across repositories and versions, no version ranges or
               warnings (rules 2-3 off)
Accounting and supersede (rules 4-5) stay on in both.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import llm
from ..benchmark import Task
from .base import MemorySystem, Retrieved, experience_packet
from .evidence import find_applied, parse_diff, references, source_corpus
from .retrieval import check_retriever, timed_rank
from .sqlite_store import open_store
from .text import jaccard, normalise, related

MAX_SHOWN = 6        # notes injected into the prompt
MAX_RETRIEVED = 10   # notes ranked and recorded as retrieved (the first MAX_SHOWN are injected)
VISIBLE = ("active", "suspect")
TYPES = ("business_policy", "code_convention", "process", "lesson")

DISTILL_SYSTEM = """You turn a finished coding task into reusable experience for FUTURE tasks in the SAME repository.

Return JSON: {"candidates": [...]} with at most 3 candidates. Each candidate has:
  "kind": "project_fact" (how this repository works) or "lesson" (how to work in it),
  "type": "business_policy" (a rule set by a policy, incident or finance/legal decision), "code_convention" (how code is
          written here), "process" (docs, changelog, tests or review practice) or "lesson",
  "topic": short kebab-case label, e.g. "money-rounding",
  "title": at most 8 words,
  "content": one or two imperative sentences a developer can act on; name the exact modules and functions,
  "evidence_quote": an exact, verbatim excerpt (10-200 characters) copied from the REVIEW COMMENTS or the FINAL DIFF that proves the candidate,
  "applied_in_diff": an exact, verbatim piece (10-200 characters) of one changed line of the FINAL DIFF where the accepted change
                     applies this rule: an added line ("+"), or a removed line ("-") if the rule is about removing something.

Rules:
- Only include knowledge specific to this repository that the issue text alone would not tell a competent developer.
- Do not restate the issue or describe this task's feature.
- Prefer what the review comments corrected.
- Only include rules that the accepted change actually applies; if you cannot point to a changed line that applies it, leave it out.
- If nothing qualifies, return {"candidates": []}."""

RELATE_SYSTEM = """You compare a NEW piece of repository experience with EXISTING items from the same repository.
For each existing item decide how the NEW one relates to it:
  "duplicate"  - states the same rule,
  "supersedes" - is about the same rule, which CHANGED (e.g. a new version or a new policy changed it; the old one was right before),
  "corrects"   - is about the same rule and shows the old item was WRONG,
  "unrelated"  - a different topic.
Return JSON: {"relations": [{"id": "<existing id>", "relation": "duplicate|supersedes|corrects|unrelated"}]}"""

REVIEW_SYSTEM = """You review a note that a coding agent wants to keep as experience for future work in one repository.
Accept it only if it is a reusable rule of this repository (not a one-off detail of the change), it is supported by the
quoted evidence, and the stated scope is right. Return JSON: {"verdict": "accept" | "reject", "reason": "<one line>"}"""


def _major(version: str) -> str:
    return version.split(".")[0]


def _version_tuple(version: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in version.split("."))


def validity(item: dict, version: str | None) -> str:
    """"" if the item may be used on this version, otherwise why not (for the retrieval trace)."""
    status, scope = item.get("status"), item.get("scope", {})
    if status == "retired":
        return "retired" + (f" by {item['retracted_by']}" if item.get("retracted_by") else "")
    if status == "superseded" and not scope.get("valid_until"):
        return f"superseded by {item.get('superseded_by')} (the old rule was wrong)"
    if version is not None:
        if scope.get("valid_from") and _version_tuple(version) < _version_tuple(scope["valid_from"]):
            return f"not yet effective: valid from {scope['valid_from']}"
        if scope.get("valid_until") and _version_tuple(version) >= _version_tuple(scope["valid_until"]):
            return f"superseded by {item.get('superseded_by')} from {scope['valid_until']}"
    if status not in VISIBLE and status != "superseded":
        return f"status {status}"
    return ""


class EarnedMemory(MemorySystem):
    def __init__(self, store_dir: Path | None, *, gate: bool = True, scope: bool = True, backend: str | None = None,
                 retriever: str = "lexical", review_model: str | None = None):
        self.store = open_store(store_dir, backend)
        self.gate, self.scope = gate, scope
        self.review_model = review_model  # optional independent review in the write gate (off in the experiment)
        self.retriever = check_retriever(retriever)
        self.name = ("attest" + ("" if gate else "_no_gate") + ("" if scope else "_no_scope")
                     + ("_emb" if retriever == "embedding" else ""))

    def _same_scope(self, item: dict, task: Task) -> bool:
        return not self.scope or item["scope"]["repo"] == task.repo_name

    def _exclusion(self, item: dict, task: Task, version: str | None) -> str:
        """Why an item may not be used for this task ("" if it may)."""
        if not self._same_scope(item, task):
            return f"other repository: {item['scope']['repo']}"
        if not self.scope:  # ablation: no version ranges, only the status counts
            return "" if item["status"] in VISIBLE else f"status {item['status']}"
        return validity(item, version)

    # ------------------------------------------------------------------ read path

    def candidates(self, task: Task, version: str | None = None) -> dict[str, str]:
        """The notes retrieval may choose from (valid for this repository and version), as id -> text to rank."""
        return {i: f"{it['title']} {it['content']}" for i, it in self.store.items().items()
                if not self._exclusion(it, task, version)}

    def ranking(self, task: Task, k: int | None = MAX_SHOWN, version: str | None = None) -> tuple[list[tuple[str, float]], float]:
        """(ranked candidates, milliseconds). Only this step differs between the retrieval arms."""
        return timed_rank(self.retriever, f"{task.title} {task.issue}", self.candidates(task, version), k)

    def retrieve(self, task: Task, repo_version: str) -> Retrieved:
        items = self.store.items()
        excluded = {i: why for i, it in items.items() if (why := self._exclusion(it, task, repo_version))}
        ranked, ms = self.ranking(task, MAX_RETRIEVED, repo_version)
        chosen = [items[i] for i, _ in ranked[:MAX_SHOWN]]
        version_warnings = [it["id"] for it in chosen
                            if self.scope and _major(it["scope"]["observed_version"]) != _major(repo_version)
                            and _major(it["scope"].get("revalidated_on") or it["scope"]["observed_version"]) != _major(repo_version)]
        debug = {
            "in_scope": sorted(i for i, it in items.items() if self._same_scope(it, task) and items[i]["status"] in VISIBLE),
            "out_of_scope": sorted(i for i, it in items.items() if not self._same_scope(it, task) and it["status"] in VISIBLE),
            "not_visible": sorted(i for i in excluded if self._same_scope(items[i], task) or items[i]["status"] not in VISIBLE),
            "scores": dict(ranked),
            "retriever": self.retriever,
            "retrieval_ms": ms,
            "version_warnings": version_warnings,
        }
        lines = []
        if chosen:
            lines.append("These notes were distilled from earlier work in this repository that passed verification. "
                         "Follow them unless the code or CHANGELOG.md shows they no longer hold.")
        for it in chosen:
            u, sc = it["usage"], it["scope"]
            lines.append(f"- [{it['id']}] {it['title']}: {it['content']}")
            valid = f"valid from {sc['valid_from']}" if sc.get("valid_from") and sc["valid_from"] != sc["observed_version"] else ""
            refs = ", ".join((it.get("source") or {}).get("references") or [])
            lines.append(
                f"  (learned from task {it['source']['task_id']} on {sc['repo']} {sc['observed_version']}"
                f"{'; ' + valid if valid else ''}{'; source ' + refs if refs else ''}; "
                f"relied on {u['cited']}x, {u['cited_pass']} passed, {u['cited_fail']} failed)"
            )
            if it["status"] == "suspect":
                lines.append("  WARNING: a recent task that relied on this note failed a related review check.")
            if it["id"] in version_warnings:
                lines.append(
                    f"  WARNING: learned on version {sc['observed_version']}, this checkout is {repo_version}. "
                    "Check CHANGELOG.md before relying on it."
                )
        context = "\n".join(lines)
        debug["trace"] = {
            "excluded": excluded,
            "candidates": len(items) - len(excluded),
            "retrieved": [i for i, _ in ranked],
            "injected": [it["id"] for it in chosen],
            "memory_tokens_approx": len(context) // 4,
            "texts": {i: f"{it['title']} {it['content']}"[:300] for i, it in items.items()},
        }
        return Retrieved(ids=[it["id"] for it in chosen], context=context, debug=debug)

    # ------------------------------------------------------------------ usage accounting

    def feedback(self, task: Task, repo_version: str, run: dict) -> list[dict]:
        items = self.store.items()
        first = run["attempts"][0]
        cited = set(run["cited_notes"]) & set(run["shown_notes"])
        events = []
        for item_id in run["shown_notes"]:
            it = items.get(item_id)
            if not it:
                continue
            usage = dict(it["usage"], shown=it["usage"]["shown"] + 1)
            fields, reason = {"usage": usage}, f"shown in {task.id}"
            if item_id in cited:
                usage["cited"] += 1
                note_text = f"{it['title']} {it['content']}"
                blame = [c for c in first["review_comments"] if related(note_text, c)]
                if first["passed"]:
                    usage["cited_pass"] += 1
                    usage["fail_streak"] = 0
                    reason = f"cited in {task.id}, which passed"
                    fields["last_verification"] = {"task_id": task.id, "version": repo_version, "result": "passed",
                                                   "how": "cited by a task whose first attempt passed verification"}
                    if it["status"] == "suspect":
                        fields["status"] = "active"
                        reason += "; suspicion cleared"
                    if _major(it["scope"]["observed_version"]) != _major(repo_version):
                        fields["scope"] = dict(it["scope"], revalidated_on=repo_version)
                elif blame:
                    usage["cited_fail"] += 1
                    usage["fail_streak"] += 1
                    fields["status"] = "suspect" if usage["fail_streak"] == 1 else "retired"
                    fields["last_failure"] = {"task_id": task.id, "review_comment": blame[0]}
                    fields["last_verification"] = {"task_id": task.id, "version": repo_version, "result": "failed",
                                                   "how": "cited by a task that failed a related review check",
                                                   "review_comment": blame[0]}
                    reason = f"cited in {task.id}, which failed a related review check -> {fields['status']}"
                else:
                    reason = f"cited in {task.id}, which failed for an unrelated reason (no blame)"
            events.append(self.store.append("update", id=item_id, fields=fields, reason=reason))
        return events

    def retract(self, item_id: str, reason: str, by: str = "human") -> dict:
        """A person withdraws a note. It stays in the log as retired, with who and why."""
        if item_id not in self.store.items():
            raise KeyError(item_id)
        return self.store.append("update", id=item_id, fields={"status": "retired", "retracted_by": by},
                                 reason=f"retracted by {by}: {reason}")

    # ------------------------------------------------------------------ write path

    def learn(self, task: Task, repo_version: str, run: dict, transcript: str, diff: str,
              candidates: list[dict] | None = None) -> list[dict]:
        """Distill (or accept proposed) candidates and admit those that pass the gate.

        ``candidates`` lets a caller that is itself a model (e.g. an agent using the MCP
        server) propose notes; they go through exactly the same gate."""
        if self.gate and not run["final_pass"]:
            return [self.store.append("reject", task_id=task.id, candidate=None, reason="task not verified: nothing is learned")]
        data = ({"candidates": candidates} if candidates is not None
                else llm.complete_json(DISTILL_SYSTEM, experience_packet(task, repo_version, run, transcript, diff)))
        comments = run["attempts"][0]["review_comments"]
        corpus, changed = source_corpus(comments, diff), parse_diff(diff)
        events = []
        for cand in (data.get("candidates") or [])[:3]:
            problem = self._gate(cand, corpus, changed, require_evidence=self.gate)
            if not problem and self.gate and self.review_model:
                problem = self._independent_review(task, cand)
            if problem:
                events.append(self.store.append("reject", task_id=task.id, candidate=cand, reason=problem))
                continue
            events.extend(self._admit(task, repo_version, run, cand, changed))
        return events

    @staticmethod
    def _gate(cand: dict, corpus: str, changed: list, require_evidence: bool = True) -> str:
        if not isinstance(cand, dict):
            return "malformed candidate"
        if cand.get("kind") in TYPES and cand.get("kind") != "lesson":  # the model put the type into "kind"
            cand.setdefault("type", cand["kind"])
            cand["kind"] = "project_fact"
        if cand.get("kind") not in ("project_fact", "lesson"):
            return f"unknown kind {cand.get('kind')!r}"
        content = (cand.get("content") or "").strip()
        if not 20 <= len(content) <= 400:
            return "content must be 20-400 characters"
        if not require_evidence:
            return ""
        quote = normalise(cand.get("evidence_quote") or "")
        if len(quote) < 10:
            return "missing evidence quote"
        if quote not in corpus:
            return "source: evidence quote not found verbatim in the review comments or the diff"
        if find_applied(cand.get("applied_in_diff") or "", changed) is None:
            return "not applied in the verified change: no changed line of the diff matches applied_in_diff"
        return ""

    def _independent_review(self, task: Task, cand: dict) -> str:
        prompt = json.dumps({"repository": task.repo_name, "note": {k: cand.get(k) for k in ("title", "content", "type")},
                             "evidence_quote": cand.get("evidence_quote"), "applied_in_diff": cand.get("applied_in_diff")},
                            ensure_ascii=False)
        verdict = llm.complete_json(REVIEW_SYSTEM, prompt, model=self.review_model)
        cand["_review"] = {"model": self.review_model, "verdict": verdict.get("verdict"), "reason": verdict.get("reason", "")}
        return "" if verdict.get("verdict") == "accept" else f"independent review rejected it: {verdict.get('reason', '')}"

    @staticmethod
    def _evidence(task: Task, repo_version: str, run: dict, cand: dict, changed: list) -> dict:
        quote = cand.get("evidence_quote") or ""
        comments = run["attempts"][0]["review_comments"]
        from_review = next((c for c in comments if normalise(quote) and normalise(quote) in normalise(c)), None)
        return {
            "task_id": task.id,
            "version": repo_version,
            "source": {"kind": "review_comment" if from_review else ("diff" if quote else "none"), "quote": quote,
                       "references": references(quote, from_review or "")},
            "applied": find_applied(cand.get("applied_in_diff") or "", changed),
            "verification": {"passed": bool(run["final_pass"]), "first_pass": bool(run["first_pass"]),
                             "how": run.get("verified_by", "hidden tests")},
            "independent_review": cand.get("_review"),
        }

    def _admit(self, task: Task, repo_version: str, run: dict, cand: dict, changed: list) -> list[dict]:
        items = self.store.items()
        # Items this one may duplicate or replace: same repository, still in use for some version.
        existing = [it for it in items.values() if self._same_scope(it, task)
                    and (it["status"] in VISIBLE or it["status"] == "archived"
                         or (it["status"] == "superseded" and it["scope"].get("valid_until")))]
        relations = {}
        if existing:
            listing = [{"id": it["id"], "title": it["title"], "content": it["content"],
                        "versions": _range(it["scope"])} for it in existing]
            prompt = json.dumps({"new": {"title": cand.get("title"), "content": cand["content"], "version": repo_version},
                                 "existing": listing}, ensure_ascii=False)
            try:
                data = llm.complete_json(RELATE_SYSTEM, prompt)
            except Exception:  # noqa: BLE001 - no model available: fall back to lexical duplicate detection
                data = {"relations": [{"id": it["id"], "relation": "duplicate"} for it in existing
                                      if jaccard(cand["content"], it["content"]) >= 0.6]}
            relations = {r.get("id"): r.get("relation") for r in data.get("relations") or [] if isinstance(r, dict)}
        evidence = self._evidence(task, repo_version, run, cand, changed)
        verification = {"task_id": task.id, "version": repo_version, "result": "passed" if run["final_pass"] else "unverified",
                        "how": f"learned from a task whose final change {'passed' if run['final_pass'] else 'did not pass'} verification"}

        duplicate = next((it for it in existing if relations.get(it["id"]) == "duplicate"
                          and (it["status"] == "archived" or not validity(it, repo_version))), None)
        if duplicate:
            fields = {
                "evidence": duplicate["evidence"] + [evidence],
                "usage": dict(duplicate["usage"], fail_streak=0),
                "status": "active",
                "last_verification": verification,
            }
            was = " (reactivated from the archive)" if duplicate["status"] == "archived" else ""
            return [self.store.append("update", id=duplicate["id"], fields=fields, candidate=cand,
                                      reason=f"confirmed again by verified task {task.id}{was}")]

        # Only newer (or same-version) verified evidence may replace an older rule.
        replaced = [
            it for it in existing
            if relations.get(it["id"]) in ("supersedes", "corrects")
            and _version_tuple(repo_version) >= _version_tuple(it["scope"]["observed_version"])
        ]
        changes = {it["id"]: ("version" if relations[it["id"]] == "supersedes"
                              and _version_tuple(repo_version) > _version_tuple(it["scope"]["observed_version"]) else "correction")
                   for it in replaced}
        new_id = self.store.next_id("at")
        applied = evidence["applied"]
        corrected_from = [it["scope"].get("valid_from") or it["scope"]["observed_version"] for it in replaced if changes[it["id"]] == "correction"]
        item = {
            "id": new_id,
            "kind": cand["kind"],
            "type": cand.get("type") if cand.get("type") in TYPES else ("lesson" if cand["kind"] == "lesson" else "code_convention"),
            "topic": cand.get("topic", ""),
            "title": (cand.get("title") or cand["content"][:40]).strip(),
            "content": cand["content"].strip(),
            "scope": {"repo": task.repo_name, "observed_version": repo_version,
                      # a correction inherits the range of the rule it fixes; a changed rule starts at this version
                      "valid_from": min(corrected_from, key=_version_tuple) if corrected_from else repo_version,
                      "valid_until": None, "files": [applied["file"]] if applied else []},
            "source": {"task_id": task.id, "first_pass": run["first_pass"], "review_comments": run["attempts"][0]["review_comments"],
                       "references": evidence["source"]["references"]},
            "evidence": [evidence],
            "status": "active",
            "supersedes": [it["id"] for it in replaced],
            "superseded_by": None,
            "last_verification": verification,
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0},
        }
        events = [self.store.append("add", item=item, reason=f"distilled from verified task {task.id}")]
        for old in replaced:
            if changes[old["id"]] == "version":
                fields = {"status": "superseded", "superseded_by": new_id, "supersede_kind": "rule changed",
                          "scope": dict(old["scope"], valid_until=repo_version)}
                reason = (f"rule changed: {new_id} applies from {task.repo_name} {repo_version}; "
                          f"this item stays valid for {_range(fields['scope'])}")
            else:
                fields = {"status": "superseded", "superseded_by": new_id, "supersede_kind": "corrected",
                          "scope": dict(old["scope"], valid_until=None)}
                reason = f"corrected by {new_id} from verified task {task.id} on {task.repo_name} {repo_version}"
            events.append(self.store.append("update", id=old["id"], fields=fields, reason=reason))
        return events


def _range(scope: dict) -> str:
    start = scope.get("valid_from") or scope.get("observed_version")
    return f">= {start}" + (f", < {scope['valid_until']}" if scope.get("valid_until") else "")
