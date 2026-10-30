"""Deterministic verification of a task workspace.

The agent never sees hidden tests. After it finishes, we copy the hidden test
file into a separate temporary directory, run it against the workspace in a
subprocess, and turn each failing test's docstring into a simulated code-review
comment. Nothing here calls a model.
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .benchmark import BENCHMARK_DIR, Task

RUNNER = Path(__file__).with_name("_hidden_runner.py")
MARKER = "__HIDDEN_RESULT__"


@dataclass
class HiddenTest:
    name: str
    kind: str  # "func" (behaviour) or "conv" (team convention)
    convention: str | None  # e.g. "C1", "K2"
    doc: str
    passed: bool = False
    error: str = ""


def _parse_hidden_tests(path: Path) -> list[HiddenTest]:
    tree = ast.parse(path.read_text())
    tests = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            parts = node.name.split("_")
            kind = parts[1] if len(parts) > 1 else "func"
            convention = parts[2].upper() if kind == "conv" and len(parts) > 2 else None
            tests.append(HiddenTest(node.name, kind, convention, ast.get_docstring(node) or ""))
    return tests


def run_public_tests(workspace: Path, timeout: int = 120) -> dict:
    # Only the repository's tests/ (restored before verification): stray test files the agent
    # left elsewhere must not decide the result (audit minor 10).
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + (["tests"] if (workspace / "tests").is_dir() else [])
    try:
        proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": f"timeout after {timeout}s"}
    output = (proc.stdout + proc.stderr).strip()
    return {"passed": proc.returncode == 0, "output": output[-2000:]}


def run_hidden_tests(workspace: Path, task: Task, timeout: int = 60) -> list[HiddenTest]:
    tests = _parse_hidden_tests(task.hidden_test)
    with tempfile.TemporaryDirectory(prefix="hidden_") as tmp:
        shutil.copyfile(task.hidden_test, Path(tmp) / "hidden_test.py")
        shutil.copyfile(BENCHMARK_DIR / "hidden_support.py", Path(tmp) / "hidden_support.py")
        cmd = [sys.executable, "-I", str(RUNNER), str(Path(tmp) / "hidden_test.py"), str(workspace)]
        try:
            proc = subprocess.run(cmd, cwd=workspace, capture_output=True, text=True, timeout=timeout)
            raw = next((ln for ln in proc.stdout.splitlines() if ln.startswith(MARKER)), None)
            results = json.loads(raw[len(MARKER):]) if raw else {"__import__": {"passed": False, "error": proc.stderr[-500:]}}
        except subprocess.TimeoutExpired:
            results = {"__import__": {"passed": False, "error": f"timeout after {timeout}s"}}
    import_error = results.get("__import__")
    for t in tests:
        r = results.get(t.name) or import_error or {"passed": False, "error": "not run"}
        t.passed, t.error = r["passed"], r["error"]
    return tests


def verify(workspace: Path, task: Task) -> dict:
    """Run public and hidden tests. ``passed`` is True only if everything passes."""
    public = run_public_tests(workspace)
    hidden = run_hidden_tests(workspace, task)
    failed = [t for t in hidden if not t.passed]
    comments = list(dict.fromkeys(t.doc for t in failed if t.doc))
    return {
        "task_id": task.id,
        "passed": public["passed"] and not failed,
        "public": public,
        "hidden": [asdict(t) for t in hidden],
        "func_failed": [t.name for t in failed if t.kind == "func"],
        "conv_failed": sorted({t.convention for t in failed if t.kind == "conv"}),
        "review_comments": comments,
    }
