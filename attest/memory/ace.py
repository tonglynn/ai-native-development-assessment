"""Simplified reproduction of ACE, Agentic Context Engineering (Zhang et al., arXiv 2510.04618). Not the official code.

What is kept: an evolving playbook of itemised bullets in sections, each with
helpful / harmful counters; after each task a Reflector tags bullets as helpful or
harmful and a Curator proposes incremental additions; deterministic merging with
de-duplication; the whole playbook is placed in the context.

Simplifications: Reflector and Curator share one model call; pruning removes a
bullet once harmful exceeds helpful by 2; no multi-epoch offline training.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import llm
from ..benchmark import Task
from .base import MemorySystem, Retrieved, experience_packet
from .sqlite_store import open_store
from .text import jaccard

SECTIONS = ("strategies", "common_mistakes", "domain_facts")
DUPLICATE_JACCARD = 0.6

REFLECT_SYSTEM = """You are the Reflector and Curator of an evolving playbook used by a coding agent.
Given a finished task and the current playbook:
1. list the ids of playbook bullets that were helpful or harmful in this task;
2. propose at most 3 NEW bullets with insights that are not already in the playbook.
Return JSON: {"helpful": [ids], "harmful": [ids], "new_bullets": [{"section": "strategies|common_mistakes|domain_facts", "content": "..."}]}"""


class AcePlaybookMemory(MemorySystem):
    name = "ace"

    def __init__(self, store_dir: Path | None):
        self.store = open_store(store_dir)

    def _bullets(self) -> dict[str, dict]:
        return {i: it for i, it in self.store.items().items() if it["status"] == "active"}

    def _render(self, bullets: dict[str, dict]) -> str:
        lines = ["Playbook (accumulated from past tasks):"]
        for section in SECTIONS:
            rows = [it for it in bullets.values() if it["section"] == section]
            if rows:
                lines.append(f"## {section}")
                lines += [f"[{it['id']}] helpful={it['helpful']} harmful={it['harmful']} :: {it['content']}" for it in rows]
        return "\n".join(lines)

    def retrieve(self, task: Task, repo_version: str) -> Retrieved:
        bullets = self._bullets()
        if not bullets:
            return Retrieved()
        return Retrieved(ids=sorted(bullets), context=self._render(bullets))

    def learn(self, task: Task, repo_version: str, run: dict, transcript: str, diff: str) -> list[dict]:
        bullets = self._bullets()
        packet = experience_packet(task, repo_version, run, transcript, diff)
        playbook = self._render(bullets) if bullets else "(empty)"
        data = llm.complete_json(REFLECT_SYSTEM, f"CURRENT PLAYBOOK:\n{playbook}\n\nFINISHED TASK:\n{packet}")
        events = []
        for key in ("helpful", "harmful"):
            for bid in data.get(key) or []:
                if bid in bullets:
                    it = bullets[bid]
                    fields = {key: it[key] + 1}
                    counts = {"helpful": it["helpful"], "harmful": it["harmful"], **fields}
                    if counts["harmful"] - counts["helpful"] >= 2:
                        fields["status"] = "pruned"
                    events.append(self.store.append("update", id=bid, fields=fields, reason=f"reflector: {key} in {task.id}"))
                    it.update(fields)
        for raw in (data.get("new_bullets") or [])[:3]:
            if not isinstance(raw, dict) or not raw.get("content"):
                continue
            content = str(raw["content"]).strip()
            if any(jaccard(content, b["content"]) >= DUPLICATE_JACCARD for b in self._bullets().values()):
                events.append(self.store.append("reject", task_id=task.id, candidate=raw, reason="curator: duplicate bullet"))
                continue
            section = raw.get("section") if raw.get("section") in SECTIONS else "strategies"
            item = {
                "id": self.store.next_id("ace"),
                "section": section,
                "content": content,
                "helpful": 0,
                "harmful": 0,
                "source": {"task_id": task.id, "repo": task.repo_name, "version": repo_version},
                "status": "active",
            }
            events.append(self.store.append("add", item=item, reason=f"curator: new bullet from {task.id}"))
        return events

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return json.dumps(self._bullets(), indent=2)
