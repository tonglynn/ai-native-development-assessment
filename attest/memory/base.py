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
    feedback(): called after verification; ``run`` says which notes were shown and
                cited and whether the attempt passed, so a system can track whether
                its notes help or hurt.
    learn():    called after a finished task when learning is enabled; may write memory.

    All systems receive exactly the same information (see ``experience_packet``),
    so differences between conditions come from how memory is managed, not from
    what each system was allowed to see.
    """

    name = "base"

    def retrieve(self, task: Task, repo_version: str) -> Retrieved:
        return Retrieved()

    def feedback(self, task: Task, repo_version: str, run: dict) -> list[dict]:
        return []

    def learn(self, task: Task, repo_version: str, run: dict, transcript: str, diff: str) -> list[dict]:
        return []


class NoMemory(MemorySystem):
    name = "no_memory"


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + f"\n... [{len(text) - limit} characters cut]"


def experience_packet(task: Task, repo_version: str, run: dict, transcript: str, diff: str) -> str:
    """The one description of a finished task that every memory system distills from."""
    first = run["attempts"][0]
    review = "\n".join(f"- {c}" for c in first["review_comments"]) or "(none: the first attempt was accepted)"
    return "\n".join([
        f"REPOSITORY: {task.repo_name} {repo_version}",
        f"ISSUE: {task.issue}",
        f"OUTCOME: first attempt {'accepted' if run['first_pass'] else 'rejected'}; "
        f"final result {'accepted (verified by hidden tests)' if run['final_pass'] else 'rejected'}",
        "REVIEW COMMENTS ON THE FIRST ATTEMPT:",
        review,
        "FINAL DIFF:",
        _clip(diff, 6000) or "(no changes)",
        "TRANSCRIPT EXCERPT:",
        _clip(transcript, 6000),
    ])
