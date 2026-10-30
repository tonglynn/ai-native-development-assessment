"""Simplified reproduction of ReasoningBank (Ouyang et al., ICLR 2026). Not the official code.

What is kept from the paper: memory items with title / description / content,
distilled from both successful and failed tasks, appended to the bank without
consolidation, and retrieved by similarity to the new task.

Simplifications: lexical instead of embedding retrieval; the verified outcome is
given to the extractor instead of an LLM-as-judge self-assessment (this is
generous to the baseline: it receives the same ground truth as Attest).
"""

from __future__ import annotations

from pathlib import Path

from .. import llm
from ..benchmark import Task
from .base import MemorySystem, Retrieved, experience_packet
from .sqlite_store import open_store
from .text import rank

MAX_SHOWN = 6

EXTRACT_SYSTEM = """You extract reusable reasoning strategies ("memory items") from a coding agent's finished task.
Learn from successes (what worked) and from failures (what to avoid).
Return JSON: {"items": [{"title": "...", "description": "one sentence", "content": "1-3 sentences of actionable insight"}]}
with at most 3 items."""


class ReasoningBankMemory(MemorySystem):
    name = "reasoningbank"

    def __init__(self, store_dir: Path | None):
        self.store = open_store(store_dir)

    def retrieve(self, task: Task, repo_version: str) -> Retrieved:
        items = self.store.items()
        docs = {i: f"{it['title']} {it['description']} {it['content']}" for i, it in items.items()}
        ranked = rank(f"{task.title} {task.issue}", docs, MAX_SHOWN)
        if not ranked:
            return Retrieved()
        lines = ["Memory items from past tasks:"]
        for i, _ in ranked:
            it = items[i]
            lines.append(f"- [{i}] {it['title']}: {it['description']}\n  {it['content']}")
        return Retrieved(ids=[i for i, _ in ranked], context="\n".join(lines), debug={"scores": dict(ranked)})

    def learn(self, task: Task, repo_version: str, run: dict, transcript: str, diff: str) -> list[dict]:
        data = llm.complete_json(EXTRACT_SYSTEM, experience_packet(task, repo_version, run, transcript, diff))
        events = []
        for raw in (data.get("items") or [])[:3]:
            if not isinstance(raw, dict) or not raw.get("content"):
                continue
            item = {
                "id": self.store.next_id("rb"),
                "title": str(raw.get("title", "")).strip(),
                "description": str(raw.get("description", "")).strip(),
                "content": str(raw["content"]).strip(),
                "source": {"task_id": task.id, "repo": task.repo_name, "version": repo_version, "final_pass": run["final_pass"]},
                "status": "active",
            }
            events.append(self.store.append("add", item=item, reason=f"extracted from task {task.id}"))
        return events
