"""Attest's memory: experience that is verified, scoped, versioned and retractable.

Design rules (each one is enforced by deterministic code; the model only proposes):

1. Write gate.   Only tasks whose final result passed the hidden tests may write
                 memory, and every candidate must quote its evidence verbatim from
                 the review comments or the final diff. Rejected candidates are kept
                 in the log with the reason.
2. Scope.        Every item records the repository and version it was learned on.
                 Retrieval only considers items from the task's repository.
3. Version.      Items learned on an older major version are still shown, but with
                 a warning to check the CHANGELOG.
4. Accounting.   Every time an item is shown or cited is recorded. If a task that
                 cited an item fails a review check about the same thing, the item
                 becomes "suspect"; a second such failure retires it. A later
                 verified success that cites it clears the suspicion.
5. Supersede.    When new verified evidence replaces an old rule, the old item is
                 marked "superseded" (never deleted) and points to its replacement.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import llm
from ..benchmark import Task
from .base import MemorySystem, Retrieved, experience_packet
from .store import EventStore
from .text import normalise, rank, related

MAX_SHOWN = 6
VISIBLE = ("active", "suspect")

DISTILL_SYSTEM = """You turn a finished coding task into reusable experience for FUTURE tasks in the SAME repository.

Return JSON: {"candidates": [...]} with at most 3 candidates. Each candidate has:
  "kind": "project_fact" (how this repository works) or "lesson" (how to work in it),
  "topic": short kebab-case label, e.g. "money-rounding",
  "title": at most 8 words,
  "content": one or two imperative sentences a developer can act on; name the exact modules and functions,
  "evidence_quote": an exact, verbatim excerpt (10-200 characters) copied from the REVIEW COMMENTS or the FINAL DIFF that proves the candidate.

Rules:
- Only include knowledge specific to this repository that the issue text alone would not tell a competent developer.
- Do not restate the issue or describe this task's feature.
- Prefer what the review comments corrected.
- If nothing qualifies, return {"candidates": []}."""

RELATE_SYSTEM = """You compare a NEW piece of repository experience with EXISTING items from the same repository.
For each existing item decide how the NEW one relates to it:
  "duplicate"  - states the same rule,
  "supersedes" - is about the same rule but replaces it (the rule changed or the old one was wrong),
  "unrelated"  - a different topic.
Return JSON: {"relations": [{"id": "<existing id>", "relation": "duplicate|supersedes|unrelated"}]}"""


def _major(version: str) -> str:
    return version.split(".")[0]


def _version_tuple(version: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in version.split("."))


class EarnedMemory(MemorySystem):
    name = "attest"

    def __init__(self, store_dir: Path | None):
        self.store = EventStore(store_dir / "events.jsonl" if store_dir else None)

    # ------------------------------------------------------------------ read path

    def retrieve(self, task: Task, repo_version: str) -> Retrieved:
        items = self.store.items()
        visible = {i: it for i, it in items.items() if it["status"] in VISIBLE}
        in_scope = {i: it for i, it in visible.items() if it["scope"]["repo"] == task.repo_name}
        ranked = rank(f"{task.title} {task.issue}", {i: f"{it['title']} {it['content']}" for i, it in in_scope.items()}, MAX_SHOWN)
        chosen = [items[i] for i, _ in ranked]
        version_warnings = [it["id"] for it in chosen if _major(it["scope"]["observed_version"]) != _major(repo_version)]
        debug = {
            "in_scope": sorted(in_scope),
            "out_of_scope": sorted(set(visible) - set(in_scope)),
            "not_visible": sorted(i for i, it in items.items() if it["status"] not in VISIBLE),
            "scores": dict(ranked),
            "version_warnings": version_warnings,
        }
        if not chosen:
            return Retrieved(debug=debug)
        lines = [
            "These notes were distilled from earlier work in this repository that passed verification. "
            "Follow them unless the code or CHANGELOG.md shows they no longer hold.",
        ]
        for it in chosen:
            u = it["usage"]
            lines.append(f"- [{it['id']}] {it['title']}: {it['content']}")
            lines.append(
                f"  (learned from task {it['source']['task_id']} on {it['scope']['repo']} {it['scope']['observed_version']}; "
                f"relied on {u['cited']}x, {u['cited_pass']} passed, {u['cited_fail']} failed)"
            )
            if it["status"] == "suspect":
                lines.append("  WARNING: a recent task that relied on this note failed a related review check.")
            if it["id"] in version_warnings:
                lines.append(
                    f"  WARNING: learned on version {it['scope']['observed_version']}, this checkout is {repo_version}. "
                    "Check CHANGELOG.md before relying on it."
                )
        return Retrieved(ids=[it["id"] for it in chosen], context="\n".join(lines), debug=debug)

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
                    reason = f"cited in {task.id}, which failed a related review check -> {fields['status']}"
                else:
                    reason = f"cited in {task.id}, which failed for an unrelated reason (no blame)"
            events.append(self.store.append("update", id=item_id, fields=fields, reason=reason))
        return events

    # ------------------------------------------------------------------ write path

    def learn(self, task: Task, repo_version: str, run: dict, transcript: str, diff: str) -> list[dict]:
        if not run["final_pass"]:
            return [self.store.append("reject", task_id=task.id, candidate=None, reason="task not verified: nothing is learned")]
        data = llm.complete_json(DISTILL_SYSTEM, experience_packet(task, repo_version, run, transcript, diff))
        corpus = normalise("\n".join(run["attempts"][0]["review_comments"]) + "\n" + diff)
        events = []
        for cand in (data.get("candidates") or [])[:3]:
            problem = self._gate(cand, corpus)
            if problem:
                events.append(self.store.append("reject", task_id=task.id, candidate=cand, reason=problem))
                continue
            events.extend(self._admit(task, repo_version, run, cand))
        return events

    @staticmethod
    def _gate(cand: dict, corpus: str) -> str:
        if not isinstance(cand, dict):
            return "malformed candidate"
        if cand.get("kind") not in ("project_fact", "lesson"):
            return f"unknown kind {cand.get('kind')!r}"
        content = (cand.get("content") or "").strip()
        if not 20 <= len(content) <= 400:
            return "content must be 20-400 characters"
        quote = normalise(cand.get("evidence_quote") or "")
        if len(quote) < 10:
            return "missing evidence quote"
        if quote not in corpus:
            return "evidence quote not found verbatim in the review comments or the diff"
        return ""

    def _admit(self, task: Task, repo_version: str, run: dict, cand: dict) -> list[dict]:
        items = self.store.items()
        existing = [it for it in items.values() if it["status"] in VISIBLE and it["scope"]["repo"] == task.repo_name]
        relations = {}
        if existing:
            listing = [{"id": it["id"], "title": it["title"], "content": it["content"]} for it in existing]
            prompt = json.dumps({"new": {"title": cand.get("title"), "content": cand["content"]}, "existing": listing}, ensure_ascii=False)
            data = llm.complete_json(RELATE_SYSTEM, prompt)
            relations = {r.get("id"): r.get("relation") for r in data.get("relations") or [] if isinstance(r, dict)}
        evidence = {"task_id": task.id, "version": repo_version, "quote": cand["evidence_quote"]}

        duplicate = next((it for it in existing if relations.get(it["id"]) == "duplicate"), None)
        if duplicate:
            fields = {
                "evidence": duplicate["evidence"] + [evidence],
                "usage": dict(duplicate["usage"], fail_streak=0),
                "status": "active",
            }
            return [self.store.append("update", id=duplicate["id"], fields=fields, reason=f"confirmed again by verified task {task.id}")]

        # Only newer (or same-version) verified evidence may replace an older rule.
        replaced = [
            it for it in existing
            if relations.get(it["id"]) == "supersedes"
            and _version_tuple(repo_version) >= _version_tuple(it["scope"]["observed_version"])
        ]
        new_id = self.store.next_id("at")
        item = {
            "id": new_id,
            "kind": cand["kind"],
            "topic": cand.get("topic", ""),
            "title": (cand.get("title") or cand["content"][:40]).strip(),
            "content": cand["content"].strip(),
            "scope": {"repo": task.repo_name, "observed_version": repo_version},
            "source": {"task_id": task.id, "first_pass": run["first_pass"], "review_comments": run["attempts"][0]["review_comments"]},
            "evidence": [evidence],
            "status": "active",
            "supersedes": [it["id"] for it in replaced],
            "superseded_by": None,
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0},
        }
        events = [self.store.append("add", item=item, reason=f"distilled from verified task {task.id}")]
        for old in replaced:
            events.append(self.store.append(
                "update", id=old["id"], fields={"status": "superseded", "superseded_by": new_id},
                reason=f"replaced by {new_id} from verified task {task.id} on {task.repo_name} {repo_version}",
            ))
        return events
