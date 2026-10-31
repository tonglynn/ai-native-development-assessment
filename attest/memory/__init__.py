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

CONDITIONS = ("no_memory", "reasoningbank", "ace", "attest", "attest_no_gate", "attest_no_scope")
# Retrieval ablation (exploratory, reported separately): same systems, embedding instead of lexical ranking.
ABLATION_CONDITIONS = ("attest", "attest_emb", "reasoningbank", "reasoningbank_emb")

__all__ = ["ABLATION_CONDITIONS", "CONDITIONS", "MemorySystem", "NoMemory", "Retrieved", "make_memory"]


def make_memory(condition: str, store_dir: Path | None) -> MemorySystem:
    if condition == "no_memory":
        return NoMemory()
    if condition == "reasoningbank":
        return ReasoningBankMemory(store_dir)
    if condition == "ace":
        return AcePlaybookMemory(store_dir)
    if condition == "attest":
        return EarnedMemory(store_dir)
    if condition == "attest_no_gate":
        return EarnedMemory(store_dir, gate=False)
    if condition == "attest_no_scope":
        return EarnedMemory(store_dir, scope=False)
    if condition == "attest_emb":
        return EarnedMemory(store_dir, retriever="embedding")
    if condition in ("attest_hybrid", "attest_hybrid_rerank"):  # D47, exploratory
        return EarnedMemory(store_dir, retriever=condition.removeprefix("attest_"))
    if condition == "attest_secure":  # D51, exploratory: every optional safeguard together
        from .gateway import SecureMemory
        return SecureMemory(store_dir)
    if condition == "attest_secure_v2":  # D56: D51 plus two-layer evidence, graded review, rule-level learning
        from .gateway import SecureMemoryV2
        return SecureMemoryV2(store_dir)
    if condition == "attest_general":  # D46, exploratory: general notes + 2 slots for repository-wide rules
        return EarnedMemory(store_dir, general=True, reserved=2)
    if condition == "reasoningbank_emb":
        return ReasoningBankMemory(store_dir, retriever="embedding")
    raise ValueError(f"unknown memory condition {condition!r}; choose from {CONDITIONS}")
