from __future__ import annotations

from dataclasses import dataclass, field

from ..benchmark import Task


@dataclass
class Retrieved:
    """What a memory system decided to show the agent for one task."""

    ids: list[str] = field(default_factory=list)
    context: str = ""  # text injected into the prompt ("" = no memory section)
    debug: dict = field(default_factory=dict)  # why these items were chosen (for the report)


class MemorySystem:
    """Interface shared by all conditions.

    retrieve(): called before a task; returns the notes to show the agent.
    learn():    called after a task finished and was verified; may write memory.
    feedback(): called after verification with which notes were shown/cited,
                so a system can track whether its notes help or hurt.
    """

    name = "base"

    def retrieve(self, task: Task, repo_version: str) -> Retrieved:
        return Retrieved()

    def learn(self, task: Task, repo_version: str, run: dict, transcript: str, diff: str) -> list[dict]:
        return []

    def feedback(self, task: Task, repo_version: str, shown: list[str], cited: list[str], passed: bool) -> list[dict]:
        return []


class NoMemory(MemorySystem):
    name = "no_memory"
