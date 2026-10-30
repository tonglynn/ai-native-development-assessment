"""Attest as an MCP server, so a real coding agent (Claude Code, Cursor, ...) can use it.

Prototype; not part of the evaluated experiment.

The server does not take the agent's word for anything that matters:
  * the diff is computed here with ``git diff`` in the repository, and
  * "verified" means the verification command passed when run here. That command
    comes from the person who configured the server (ATTEST_VERIFY_CMD), never
    from the agent, so an agent cannot choose how it is checked.
Notes are proposed by the agent itself (it is a model) or by Attest's distiller,
and go through the same write gate as in the experiment.

Configuration (environment):
  ATTEST_HOME        where memory lives (default ~/.attest), one store per repository
  ATTEST_STORE       sqlite (default here: one memory.db per repository that several
                     agents or people can share) or jsonl (the experiments' format)
  ATTEST_VERIFY_CMD  verification command run in the repository (default: python -m pytest -q)

Claude Code:  claude mcp add attest -- python -m attest.mcp_server
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace

from .memory.earned import EarnedMemory

HOME = Path(os.environ.get("ATTEST_HOME", "~/.attest")).expanduser()
VERIFY_CMD = os.environ.get("ATTEST_VERIFY_CMD", "python -m pytest -q")
STORE = os.environ.get("ATTEST_STORE", "sqlite")


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=60)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _identity(repo_path: str) -> tuple[Path, str, str]:
    """(path, repository name, version) for a working copy."""
    repo = Path(repo_path).expanduser().resolve()
    if not (repo / ".git").exists():
        raise ValueError(f"{repo} is not a git repository")
    remote = _git(repo, "remote", "get-url", "origin")
    name = re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1]) if remote else repo.name
    version = _git(repo, "describe", "--tags", "--abbrev=0") or "0"
    return repo, name, version.lstrip("v")


def _memory(name: str) -> EarnedMemory:
    slug = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    return EarnedMemory(HOME / slug, backend=STORE)


def _task(name: str, task: str) -> SimpleNamespace:
    return SimpleNamespace(id="live", title=task[:80], issue=task, repo_name=name)


def _verify(repo: Path) -> tuple[bool, str]:
    proc = subprocess.run(shlex.split(VERIFY_CMD), cwd=repo, capture_output=True, text=True, timeout=900)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]


# ------------------------------------------------------------------ tool functions (plain Python, tested directly)

def recall(repo_path: str, task: str) -> dict:
    """Notes this team has verified for this repository that are relevant to the task."""
    repo, name, version = _identity(repo_path)
    shown = _memory(name).retrieve(_task(name, task), version)
    return {"repository": name, "version": version, "note_ids": shown.ids,
            "notes": shown.context or "No verified notes for this repository yet.",
            "instructions": "Follow the notes unless the code or CHANGELOG shows they no longer hold. "
                            "When you finish, call report_outcome with the ids you relied on."}


def learn(repo_path: str, task: str, review_comments: list[str], candidates: list[dict] | None = None,
          base_ref: str = "HEAD") -> dict:
    """Submit an accepted change. Attest computes the diff and runs the verification command itself."""
    repo, name, version = _identity(repo_path)
    diff = _git(repo, "diff", base_ref)
    if not diff:
        return {"admitted": [], "rejected": [], "message": f"no changes against {base_ref}: nothing to learn"}
    verified, output = _verify(repo)
    run = {"first_pass": not review_comments, "final_pass": verified, "shown_notes": [], "cited_notes": [],
           "attempts": [{"passed": not review_comments, "review_comments": list(review_comments)}]}
    events = _memory(name).learn(_task(name, task), version, run, "", diff, candidates=candidates)
    return {
        "verified": verified,
        "verification_output": output if not verified else "",
        "admitted": [e["item"]["id"] for e in events if e["type"] == "add"],
        "confirmed": [e["id"] for e in events if e["type"] == "update"],
        "rejected": [{"reason": e["reason"], "candidate": e.get("candidate")} for e in events if e["type"] == "reject"],
    }


def report_outcome(repo_path: str, task: str, shown: list[str], cited: list[str], review_comments: list[str]) -> dict:
    """After a task: which notes were shown and relied on. Attest runs verification to judge the outcome."""
    repo, name, version = _identity(repo_path)
    passed, _ = _verify(repo)
    run = {"first_pass": passed, "final_pass": passed, "shown_notes": list(shown), "cited_notes": list(cited),
           "attempts": [{"passed": passed, "review_comments": list(review_comments)}]}
    events = _memory(name).feedback(_task(name, task), version, run)
    return {"passed": passed, "changes": [e["reason"] for e in events if "status" in (e.get("fields") or {})]}


def list_notes(repo_path: str, include_inactive: bool = False) -> list[dict]:
    """Every note for this repository with its status, provenance and usage."""
    _, name, _ = _identity(repo_path)
    items = _memory(name).store.items().values()
    return [
        {k: it.get(k) for k in ("id", "title", "content", "status", "scope", "evidence", "usage", "superseded_by")}
        for it in items if include_inactive or it["status"] in ("active", "suspect")
    ]


def retract(repo_path: str, note_id: str, reason: str) -> dict:
    """A person withdraws a note (kept in the log as retired, with the reason)."""
    _, name, _ = _identity(repo_path)
    event = _memory(name).retract(note_id, reason, by="human")
    return {"retired": note_id, "reason": event["reason"]}


def build_server():
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(
        "attest",
        instructions="Verified, scoped, retractable team experience. Call recall before starting a coding task "
                     "in a repository, learn after a change has been accepted, and report_outcome when you finish.",
    )
    # retract is deliberately not exposed: withdrawing team knowledge is a human decision
    # (python -m attest retract ...), so an agent cannot delete a rule it finds inconvenient.
    for fn in (recall, learn, report_outcome, list_notes):
        server.tool()(fn)
    return server


if __name__ == "__main__":
    build_server().run("stdio")
