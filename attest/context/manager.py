"""Attest Context Manager: keep a long agent session under a token budget without losing what matters.

Exploratory extension (not part of the preregistered experiment; mini-swe-agent's
agent class stays unmodified, decision D7). It wraps the model: every time the agent
asks the model for the next step, the message list is reassembled.

Three data layers:
  archive        every original message, never modified (recoverable history)
  working state  structured facts extracted from the history: the current goal,
                 pinned constraints (review rules, policy references, thresholds),
                 the latest test result, files touched
  context        what the model actually receives, assembled under the budget

Four steps, in this order:
  1. structured extraction  constraints, test results and files, with the index of
                            the message each came from (deterministic rules, no model)
  2. importance filtering   pinned (system prompt, current task, constraints) >
                            recent (the last turns) > compressible (older turns)
  3. summarisation          older turns become one compressed block: extractive by
                            default (command + result), or a model summary whose
                            fidelity is checked against the pinned facts
  4. sliding window         the most recent turns are kept verbatim, cut only at
                            assistant-message boundaries so tool results never lose
                            the call they answer

The pinned constraints are never summarised: they are carried verbatim in the working
state, so a model summary that turns "above 1000.00" into "large refunds" cannot
remove the threshold. `fidelity()` reports which pinned tokens (numbers, ids,
identifiers) a summary dropped.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

CONSTRAINT_RE = re.compile(
    r"\[team convention\]|\[simkit convention\]|\b(?:FIN|INC|SEC|POL)-\d[\d-]*\b|\bmust\b|\bnever\b|\brequired?\b"
    r"|\bthreshold\b|\bapprov\w*|\bidempoten\w*", re.I)
TEST_RE = re.compile(r"\b\d+ (?:passed|failed)\b[^\n]*|FAILED [^\n]+|ERROR [^\n]+")
FILE_RE = re.compile(r"\b[\w./-]+\.py\b")
KEY_TOKEN_RE = re.compile(r"\b\d+\.\d{2}\b|\b(?:FIN|INC)-\d[\d-]*\d\b|`[^`]+`|\b[a-z]+_[a-z_]+\b")


def tokens_of(messages: list[dict]) -> int:
    """Approximate tokens (characters / 4), for budgeting only; real usage is measured by the API."""
    return sum(len(_text(m)) for m in messages) // 4


def _text(m: dict) -> str:
    content = str(m.get("content") or "")
    if m.get("role") == "tool":  # mini-swe-agent tool results are JSON: use the command output itself
        try:
            out = json.loads(content)
            content = str(out.get("output", content)) if isinstance(out, dict) else content
        except json.JSONDecodeError:
            pass
    parts = [content]
    for call in m.get("tool_calls") or []:
        parts.append(str((call.get("function") or {}).get("arguments", "")))
    return "\n".join(parts)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


@dataclass
class WorkingState:
    goal: str = ""
    constraints: list[tuple[int, str]] = field(default_factory=list)  # (source message index, sentence)
    last_tests: str = ""
    files: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = ["[Working state, extracted from earlier in this session; constraints are quoted verbatim]"]
        if self.constraints:
            lines.append("Constraints and rules seen earlier:")
            lines += [f"- {s} (from message {i})" for i, s in self.constraints]
        if self.last_tests:
            lines.append(f"Latest test result seen: {self.last_tests}")
        if self.files:
            lines.append("Files touched earlier: " + ", ".join(self.files[-12:]))
        return "\n".join(lines)

    def pinned_tokens(self) -> set[str]:
        return {t.strip("`").lower() for _, s in self.constraints for t in KEY_TOKEN_RE.findall(s)}


def extract_state(messages: list[dict], goal: str = "") -> WorkingState:
    """Step 1: deterministic structured extraction over the (older) history."""
    state, seen = WorkingState(goal=goal), set()
    for i, m in enumerate(messages):
        text = _text(m)
        if m.get("role") in ("user", "tool"):
            for s in _sentences(text):
                if CONSTRAINT_RE.search(s) and len(s) <= 400 and "tool call" not in s.lower():
                    key = " ".join(s.lower().split())
                    if key not in seen:
                        seen.add(key)
                        state.constraints.append((i, s))
            tests = TEST_RE.findall(text)
            if tests:
                state.last_tests = tests[-1][:200]
        if m.get("role") == "assistant":
            for f in FILE_RE.findall(text):
                if f not in state.files:
                    state.files.append(f)
    return state


def extractive_summary(messages: list[dict]) -> str:
    """Step 3 (default): one line per step, command and outcome; no model, nothing invented."""
    lines = []
    for m in messages:
        if m.get("role") == "assistant":
            for call in m.get("tool_calls") or []:
                try:
                    cmd = json.loads((call.get("function") or {}).get("arguments", "{}")).get("command", "")
                except json.JSONDecodeError:
                    cmd = ""
                lines.append(f"ran: {' '.join(cmd.split())[:140]}")
        elif m.get("role") == "tool":
            try:
                out = json.loads(m.get("content") or "{}")
                first = (out.get("output") or "").strip().splitlines()[:1]
                lines.append(f"  -> returncode {out.get('returncode')}{': ' + first[0][:100] if first else ''}")
            except (json.JSONDecodeError, AttributeError):
                lines.append("  -> " + " ".join(str(m.get("content"))[:100].split()))
        elif m.get("role") == "user":
            lines.append("user: " + " ".join(str(m.get("content"))[:160].split()))
    return "\n".join(lines)


def fidelity(summary: str, state: WorkingState) -> dict:
    """Which pinned tokens (amounts, policy ids, identifiers) a summary kept and which it dropped."""
    pinned = state.pinned_tokens()
    low = summary.lower()
    kept = sorted(t for t in pinned if t in low)
    return {"pinned": len(pinned), "kept": len(kept), "dropped": sorted(pinned - set(kept))}


class ContextManager:
    """Assembles the message list under a budget. Strategies (for the ablation):

    full       no management (the ceiling)
    window     system + current task + as many recent turns as fit (sliding window only)
    summary    window + a model summary of the older turns (plain LLM summarisation)
    manager    window + extractive summary + working state with pinned constraints
               (structured extraction + importance filtering + summarisation + window)
    """

    def __init__(self, strategy: str = "manager", budget_tokens: int = 6000, summarizer=None, min_recent: int = 4):
        assert strategy in ("full", "window", "summary", "manager"), strategy
        self.strategy, self.budget, self.summarizer, self.min_recent = strategy, budget_tokens, summarizer, min_recent
        self.archive: list[dict] = []
        self.log: list[dict] = []
        self._summary_cache: dict[int, str] = {}

    def assemble(self, messages: list[dict], task_index: int) -> list[dict]:
        """messages[0] is the system prompt, messages[task_index] the current task; everything else is history.
        The order of the kept messages never changes."""
        self.archive = list(messages)
        if self.strategy == "full" or tokens_of(messages) <= self.budget:
            self.log.append({"strategy": self.strategy, "in": tokens_of(messages), "out": tokens_of(messages), "dropped": 0})
            return messages
        system, task = messages[0], messages[task_index]
        history = [i for i in range(1, len(messages)) if i != task_index]
        reserve = 0 if self.strategy == "window" else 700  # room for the summary / working-state block
        budget_left = self.budget - tokens_of([system, task]) - reserve

        # Step 4: the window, built from the end in whole steps (an assistant message with its tool results).
        keep: list[int] = []
        pos = len(history)
        while pos > 0:
            start = pos - 1
            while start > 0 and messages[history[start]].get("role") == "tool":
                start -= 1
            step = history[start:pos]
            if keep and tokens_of([messages[i] for i in step + keep]) > budget_left:
                break
            keep = step + keep
            pos = start
        old = [messages[i] for i in history[:pos]]

        blocks = []
        if old and self.strategy == "summary":
            blocks.append({"role": "user", "content": "[Summary of earlier work in this session]\n" + self._model_summary(old)})
        elif old and self.strategy == "manager":
            # Steps 1-3: extract, keep constraints verbatim (importance: pinned), compress the rest.
            state = extract_state(old)
            state_text = state.render()
            kept_tokens = tokens_of([system, task] + [messages[i] for i in keep])
            room = max(0, (self.budget - kept_tokens) * 4 - len(state_text) - 100)
            summary = extractive_summary(old)
            text = state_text + ("\n\n[Earlier steps, compressed]\n" + summary[-room:] if room > 200 else "")
            blocks.append({"role": "user", "content": text})
        ctx = [system] + blocks + [messages[i] for i in sorted(keep + [task_index])]
        self.log.append({"strategy": self.strategy, "in": tokens_of(messages), "out": tokens_of(ctx), "dropped": len(old)})
        return ctx

    def _model_summary(self, old: list[dict]) -> str:
        key = len(old)
        if key not in self._summary_cache:
            transcript = "\n".join(f"{m.get('role')}: {_text(m)[:1500]}" for m in old)
            self._summary_cache[key] = self.summarizer(transcript) if self.summarizer else extractive_summary(old)
        return self._summary_cache[key]


class ManagedModel:
    """Wraps a mini-swe-agent model: optionally prepends an earlier session, then lets the manager assemble."""

    def __init__(self, inner, manager: ContextManager, prefix: list[dict] | None = None):
        self.inner, self.manager, self.prefix = inner, manager, list(prefix or [])

    def query(self, messages: list[dict], **kwargs) -> dict:
        full = [messages[0]] + self.prefix + list(messages[1:])
        ctx = self.manager.assemble(full, task_index=1 + len(self.prefix))
        return self.inner.query(ctx, **kwargs)

    def __getattr__(self, name):
        return getattr(self.inner, name)
