"""Memory systems compared in the experiment.

Every memory system implements the same small interface so that the runner,
the prompt and the agent are identical across conditions; only the memory
block injected into the prompt differs.
"""

from __future__ import annotations

from .base import MemorySystem, NoMemory, Retrieved

__all__ = ["MemorySystem", "NoMemory", "Retrieved", "make_memory"]


def make_memory(condition: str, store_dir) -> MemorySystem:
    if condition == "no_memory":
        return NoMemory()
    raise ValueError(f"memory condition {condition!r} is not implemented yet")
