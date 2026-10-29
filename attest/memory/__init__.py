"""Memory systems compared in the experiment.

Every memory system implements the same small interface so that the runner,
the prompt and the agent are identical across conditions; only the memory
block injected into the prompt differs.
"""

from __future__ import annotations

from pathlib import Path

from .ace import AcePlaybookMemory
from .base import MemorySystem, NoMemory, Retrieved
from .earned import EarnedMemory
from .reasoningbank import ReasoningBankMemory

CONDITIONS = ("no_memory", "reasoningbank", "ace", "attest")

__all__ = ["CONDITIONS", "MemorySystem", "NoMemory", "Retrieved", "make_memory"]


def make_memory(condition: str, store_dir: Path | None) -> MemorySystem:
    if condition == "no_memory":
        return NoMemory()
    if condition == "reasoningbank":
        return ReasoningBankMemory(store_dir)
    if condition == "ace":
        return AcePlaybookMemory(store_dir)
    if condition == "attest":
        return EarnedMemory(store_dir)
    raise ValueError(f"unknown memory condition {condition!r}; choose from {CONDITIONS}")
