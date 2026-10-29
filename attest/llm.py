"""Small JSON-in/JSON-out model client used by memory systems to distill experience.

Uses the same model and settings as the agent. Tests replace it with a scripted
function via ``set_llm``.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Callable

LLMFn = Callable[[str, str], dict]

_override: LLMFn | None = None
_lock = threading.Lock()
USAGE = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0}


def set_llm(fn: LLMFn | None) -> None:
    """Replace the model with ``fn(system, user) -> dict`` (``None`` restores the real model)."""
    global _override
    _override = fn


def complete_json(system: str, user: str) -> dict:
    """Ask the model for a JSON object. Returns {} if no valid JSON comes back after one retry."""
    if _override is not None:
        return _override(system, user)
    import litellm

    model = os.environ.get("ATTEST_MODEL", "deepseek/deepseek-flash")
    kwargs: dict = {"temperature": 0.0, "drop_params": True, "response_format": {"type": "json_object"}}
    if os.environ.get("ATTEST_THINKING", "off") == "off":
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for _ in range(2):
        resp = litellm.completion(model=model, messages=messages, **kwargs)
        with _lock:
            USAGE["calls"] += 1
            USAGE["prompt_tokens"] += resp.usage.prompt_tokens or 0
            USAGE["completion_tokens"] += resp.usage.completion_tokens or 0
        try:
            data = json.loads(resp.choices[0].message.content or "")
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}
