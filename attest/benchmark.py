"""Loading tasks and building isolated task workspaces.

Each task lives in ``benchmark/tasks/<ID>/`` (see benchmark/README.md for the
layout). A workspace is: base repository + ``setup/`` overlay + one code overlay
(``stub`` for the agent, ``naive``/``reference`` for benchmark validation).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_DIR = PROJECT_ROOT / "benchmark"
TASKS_DIR = BENCHMARK_DIR / "tasks"
REPOS_DIR = BENCHMARK_DIR / "repos"

GROUP_ORDER = {"experience": 0, "heldout": 1, "stale": 2, "control": 3}


@dataclass(frozen=True)
class Task:
    id: str
    group: str  # experience | heldout | stale | control
    repo: str  # directory name under benchmark/repos
    title: str
    issue: str
    conventions: tuple[str, ...]
    naive_kind: str
    dir: Path
    transfer: str = ""  # held-out only: "near" (mirrors one experience task) or "far" (audit M4)

    @property
    def repo_name(self) -> str:
        """Logical repository name used for memory scoping (ledgerly_v2 -> ledgerly)."""
        return self.repo.split("_v")[0]

    @property
    def hidden_test(self) -> Path:
        return self.dir / "hidden_test.py"


def load_task(task_id: str) -> Task:
    tdir = TASKS_DIR / task_id
    meta = json.loads((tdir / "task.json").read_text())
    return Task(
        id=meta["id"],
        group=meta["group"],
        repo=meta["repo"],
        title=meta["title"],
        issue=meta["issue"],
        conventions=tuple(meta["conventions"]),
        naive_kind=meta.get("naive_kind", "naive"),
        dir=tdir,
        transfer=meta.get("transfer", ""),
    )


def load_tasks(group: str | None = None) -> list[Task]:
    tasks = [load_task(p.name) for p in sorted(TASKS_DIR.iterdir()) if (p / "task.json").exists()]
    if group:
        tasks = [t for t in tasks if t.group == group]
    return sorted(tasks, key=lambda t: (GROUP_ORDER[t.group], t.id))


def repo_version(repo_dir: Path) -> str:
    """Read ``__version__`` from the package's __init__.py."""
    for init in repo_dir.glob("*/__init__.py"):
        for line in init.read_text().splitlines():
            if line.startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    return "unknown"


def _apply_overlay(src: Path, dest: Path) -> None:
    if not src.exists():
        return
    for f in sorted(src.rglob("*")):
        if f.is_dir():
            continue
        rel = f.relative_to(src)
        if f.name.endswith(".append"):
            target = dest / rel.parent / f.name[: -len(".append")]
            target.parent.mkdir(parents=True, exist_ok=True)
            existing = target.read_text() if target.exists() else ""
            target.write_text(existing.rstrip("\n") + "\n\n\n" + f.read_text())
        else:
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, target)


def materialize(task: Task, dest: Path, variant: str = "stub") -> Path:
    """Create a fresh workspace for ``task`` at ``dest`` using the given code overlay."""
    if variant not in {"stub", "naive", "reference"}:
        raise ValueError(f"unknown variant {variant!r}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        REPOS_DIR / task.repo,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
    )
    _apply_overlay(task.dir / "setup", dest)
    _apply_overlay(task.dir / variant, dest)
    return dest
