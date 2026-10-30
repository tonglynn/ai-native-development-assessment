"""Run one task under one memory condition, end to end.

    stub workspace -> [memory.retrieve] -> mini-swe-agent attempt -> restore tests
    -> verify (hidden tests) -> if failed: simulated review -> second attempt
    -> [memory.feedback, memory.learn] -> result.json

The agent itself is mini-swe-agent's unmodified DefaultAgent. This module only
builds its prompt variables, runs it, verifies the outcome and records everything.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .benchmark import PROJECT_ROOT, REPOS_DIR, Task, materialize, repo_version
from .memory import MemorySystem
from .verify import verify

CONFIG_PATH = Path(__file__).with_name("config") / "agent.yaml"
WORKSPACE_ROOT = Path(os.environ.get("ATTEST_WORKSPACE_ROOT", "/tmp/attest_workspaces"))

# USD per 1M tokens for deepseek-flash, off-peak. Source: third-party price page
# checked 2026-10-29 (DeepSeek's own page was not reachable). Estimates only.
PRICE_PER_M = {"input_miss": 0.15, "input_hit": 0.003, "output": 0.60}

# Paths an honest agent never needs. Touching them means the run saw answers.
LEAK_PATTERNS = ["hidden_test", "benchmark/tasks", "validation.json", "/reference/", "/naive/", str(PROJECT_ROOT)]


@dataclass
class Settings:
    model: str = os.environ.get("ATTEST_MODEL", "deepseek/deepseek-flash")
    thinking: str = os.environ.get("ATTEST_THINKING", "off")  # off | low | high
    max_attempts: int = 2  # first attempt + one round of simulated review
    # Exploratory poisoning experiment only: task id -> an extra (wrong) review comment
    # added whenever that task's attempt fails verification. Empty in the main experiment.
    extra_review: dict = field(default_factory=dict)


def load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def make_model(settings: Settings, config: dict, mock_outputs: list[dict] | None = None):
    model_cfg = dict(config["model"])
    if mock_outputs is not None:
        from minisweagent.models.test_models import DeterministicToolcallModel

        return DeterministicToolcallModel(outputs=mock_outputs, observation_template=model_cfg["observation_template"])
    from minisweagent.models.litellm_model import LitellmModel

    kwargs: dict = {"drop_params": True, "temperature": 0.0}
    if settings.thinking == "off":
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    else:
        kwargs["reasoning_effort"] = settings.thinking
    model = LitellmModel(model_name=settings.model, model_kwargs=kwargs, cost_tracking="ignore_errors", **model_cfg)
    # Environment errors will not fix themselves: fail at once instead of retrying for minutes
    # (the first smoke run spent ~12 minutes retrying a missing-module error).
    model.abort_exceptions = [*model.abort_exceptions, ImportError]
    return model


# ----------------------------------------------------------------- trajectory helpers

def _assistant_messages(messages: list[dict]) -> list[dict]:
    return [m for m in messages if m.get("role") == "assistant"]


def commands_of(messages: list[dict]) -> list[str]:
    return [a.get("command", "") for m in _assistant_messages(messages) for a in m.get("extra", {}).get("actions", [])]


def token_usage(messages: list[dict]) -> dict:
    total = {"prompt": 0, "completion": 0, "cache_hit": 0, "reasoning": 0}
    for m in _assistant_messages(messages):
        usage = (m.get("extra", {}).get("response") or {}).get("usage") or {}
        total["prompt"] += usage.get("prompt_tokens") or 0
        total["completion"] += usage.get("completion_tokens") or 0
        total["cache_hit"] += usage.get("prompt_cache_hit_tokens") or 0
        total["reasoning"] += (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    return total


def cost_estimate(tokens: dict) -> float:
    miss = tokens["prompt"] - tokens["cache_hit"]
    return round(
        (miss * PRICE_PER_M["input_miss"] + tokens["cache_hit"] * PRICE_PER_M["input_hit"]
         + tokens["completion"] * PRICE_PER_M["output"]) / 1e6,
        6,
    )


def leak_flags(messages: list[dict]) -> list[str]:
    """Benchmark paths that appear in the agent's commands or in what it saw back."""
    observations = [str(m.get("content", "")) for m in messages[2:] if m.get("role") in ("tool", "user")]
    texts = commands_of(messages) + observations
    return sorted({p for p in LEAK_PATTERNS for t in texts if p in t})


def cited_notes(submission: str) -> list[str]:
    match = re.search(r"USED_NOTES:\s*(.*)", submission or "")
    if not match or match.group(1).strip().lower() in {"", "none"}:
        return []
    return [x.strip() for x in re.split(r"[,\s]+", match.group(1)) if x.strip() and x.strip().lower() != "none"]


def transcript_text(messages: list[dict], limit: int = 12000) -> str:
    """Compact text version of a trajectory, used by memory systems that distill experience."""
    parts = []
    for m in messages[2:]:
        role = m.get("role")
        if role == "assistant":
            cmds = [a.get("command", "") for a in m.get("extra", {}).get("actions", [])]
            parts.append(f"AGENT: {(m.get('content') or '').strip()[:600]}\n$ " + "\n$ ".join(cmds))
        elif role in ("tool", "user"):
            parts.append(f"OUTPUT: {str(m.get('content', ''))[:800]}")
    text = "\n".join(parts)
    return text if len(text) <= limit else text[: limit // 2] + "\n...\n" + text[-limit // 2:]


def agent_test_runs(messages: list[dict]) -> int:
    """How many of the agent's commands ran the tests."""
    return sum(bool(re.search(r"\bpytest\b|unittest", c)) for c in commands_of(messages))


def workspace_diff(task: Task, workspace: Path, tmp_root: Path) -> str:
    """Unified diff of source files (tests excluded) between the stub and the final workspace."""
    stub = materialize(task, tmp_root / "_stub_for_diff", "stub")
    out = []
    for f in sorted(workspace.rglob("*.py")):
        rel = f.relative_to(workspace)
        if rel.parts[0] == "tests" or "__pycache__" in rel.parts or rel.name == "conftest.py":
            continue
        before = (stub / rel).read_text().splitlines(keepends=True) if (stub / rel).exists() else []
        after = f.read_text().splitlines(keepends=True)
        out.extend(difflib.unified_diff(before, after, f"a/{rel}", f"b/{rel}"))
    shutil.rmtree(stub, ignore_errors=True)
    return "".join(out)


def restore_tests(task: Task, workspace: Path) -> None:
    """Undo any edits the agent made to tests before we verify."""
    base = REPOS_DIR / task.repo
    for name in ("tests", "conftest.py"):
        target = workspace / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        src = base / name
        if src.is_dir():
            shutil.copytree(src, target)
        elif src.exists():
            shutil.copyfile(src, target)
    setup_tests = task.dir / "setup"
    for f in setup_tests.rglob("*"):
        if f.is_file():
            dest = workspace / f.relative_to(setup_tests)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)


def format_review(verification: dict) -> str:
    lines = [f"- {c}" for c in verification["review_comments"]]
    if not verification["public"]["passed"]:
        lines.append("- The public test suite (`python -m pytest -q`) fails.")
    return "\n".join(lines) or "- The change was not accepted."


# ----------------------------------------------------------------- main entry point

def run_task(
    task: Task,
    memory: MemorySystem,
    out_dir: Path,
    *,
    settings: Settings | None = None,
    update_memory: bool = True,
    mock_outputs: list[list[dict]] | None = None,
) -> dict:
    """Run ``task`` with ``memory`` and write trajectories and result.json into ``out_dir``."""
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments.local import LocalEnvironment

    settings = settings or Settings()
    config = load_config()
    out_dir.mkdir(parents=True, exist_ok=True)
    # Workspaces live outside the project so the agent's surroundings contain no benchmark files.
    tmp_root = WORKSPACE_ROOT / "__".join(out_dir.resolve().parts[1:][-4:])
    workspace = materialize(task, tmp_root / "workspace", "stub")
    version = repo_version(REPOS_DIR / task.repo)

    retrieved = memory.retrieve(task, version)
    started = time.time()
    attempts, all_messages, review = [], [], ""
    for n in range(1, settings.max_attempts + 1):
        model = make_model(settings, config, None if mock_outputs is None else mock_outputs[n - 1])
        env = LocalEnvironment(cwd=str(workspace), **config["environment"])
        agent = DefaultAgent(model, env, **config["agent"], output_path=out_dir / f"attempt{n}.traj.json")
        t0 = time.time()
        try:
            info = agent.run(task=task.issue, memory_context=retrieved.context, review_feedback=review)
        except Exception as exc:  # noqa: BLE001 - a crashed attempt is a failed attempt, not a crashed experiment
            info = {"exit_status": f"crash:{type(exc).__name__}", "submission": ""}
        restore_tests(task, workspace)
        verification = verify(workspace, task)
        if not verification["passed"] and task.id in settings.extra_review:
            verification["review_comments"].append(settings.extra_review[task.id])
        tokens = token_usage(agent.messages)
        attempts.append({
            "n": n,
            "exit_status": info.get("exit_status", ""),
            "crashed": str(info.get("exit_status", "")).startswith("crash:"),
            "steps": agent.n_calls,
            "seconds": round(time.time() - t0, 1),
            "tokens": tokens,
            "cost_usd": cost_estimate(tokens),
            "cited": cited_notes(info.get("submission", "")),
            "leaks": leak_flags(agent.messages),
            "passed": verification["passed"],
            "public_passed": verification["public"]["passed"],
            "func_failed": verification["func_failed"],
            "conv_failed": verification["conv_failed"],
            "tests_failed": [h["name"] for h in verification["hidden"] if not h["passed"]],
            "review_comments": verification["review_comments"],
        })
        all_messages.extend(agent.messages)
        if verification["passed"]:
            break
        review = format_review(verification)

    diff = workspace_diff(task, workspace, tmp_root)
    (out_dir / "final.diff").write_text(diff)
    cited = sorted({c for a in attempts for c in a["cited"]})
    result = {
        "task_id": task.id,
        "group": task.group,
        "repo": task.repo,
        "repo_version": version,
        "conventions": list(task.conventions),
        "condition": memory.name,
        "model": "mock" if mock_outputs is not None else settings.model,
        "thinking": settings.thinking,
        "first_pass": attempts[0]["passed"],
        "final_pass": attempts[-1]["passed"],
        "n_attempts": len(attempts),
        "steps": sum(a["steps"] for a in attempts),
        "cost_usd": round(sum(a["cost_usd"] for a in attempts), 6),
        "seconds": round(time.time() - started, 1),
        "shown_notes": retrieved.ids,  # = injected_notes (kept for older analyses)
        "retrieved_notes": (retrieved.debug.get("trace") or {}).get("retrieved", retrieved.ids),
        "injected_notes": retrieved.ids,
        "memory_tokens_approx": (retrieved.debug.get("trace") or {}).get("memory_tokens_approx", len(retrieved.context) // 4),
        "agent_test_runs": agent_test_runs(all_messages),
        "files_changed": sorted({ln[6:] for ln in diff.splitlines() if ln.startswith("+++ b/")}),
        "notes_context": retrieved.context,
        "cited_notes": cited,
        "retrieval_debug": retrieved.debug,
        "leaks": sorted({x for a in attempts for x in a["leaks"]}),
        "attempts": attempts,
    }
    result["memory_events"] = []
    if update_memory:  # frozen evaluation phases pass False: memory is read-only there
        result["memory_events"] += memory.feedback(task, version, result)
        result["memory_events"] += memory.learn(task, version, result, transcript_text(all_messages), diff)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n")
    shutil.rmtree(tmp_root, ignore_errors=True)
    return result
