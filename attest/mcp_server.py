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
  ATTEST_GATEWAY     checks (default) or off. With checks, every note the write gate admits is then assessed as
                     in gateway v4, deterministically (team code checks, registered policies, trusted reviewer
                     comments; no model, no API key): approved -> a rule; uncertain -> kept, never a rule, waits
                     for a person (python -m attest review); rejected -> retired with the reason. The
                     counterfactual test is not run here. off = the preregistered gate only.

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
    # UTF-8 explicitly: on a Chinese Windows the locale codec is GBK, and a diff with any non-ASCII
    # character (an em dash in CHANGELOG.md) raised UnicodeDecodeError and failed the whole tool call
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=60)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _identity(repo_path: str) -> tuple[Path, str, str, str]:
    """(path, repository name, version, memory key) for a working copy.

    The memory key is the full origin (host/owner/name), not the last path segment: with the
    name alone, any repository whose remote ends in ".../ledgerly.git" read and wrote ledgerly's
    memory (D43). A working copy without a remote is keyed by its path. If ATTEST_ALLOWED_REPOS is
    set (comma-separated keys), any other repository is refused."""
    import hashlib

    repo = Path(repo_path).expanduser().resolve()
    if not (repo / ".git").exists():
        raise ValueError(f"{repo} is not a git repository")
    remote = _git(repo, "remote", "get-url", "origin")
    name = re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1]) if remote else repo.name
    m = re.match(r"^(?:[a-z+]+://)?(?:[^@/]+@)?([^/:]+)[/:](.+?)(?:\.git)?/?$", remote) if remote else None
    key = f"{m.group(1)}/{m.group(2)}".lower() if m else f"local/{hashlib.sha256(str(repo).encode()).hexdigest()[:12]}-{repo.name}"
    allowed = [a.strip().lower() for a in os.environ.get("ATTEST_ALLOWED_REPOS", "").split(",") if a.strip()]
    if allowed and key not in allowed:
        raise PermissionError(f"repository {key} is not in ATTEST_ALLOWED_REPOS")
    version = _git(repo, "describe", "--tags", "--abbrev=0") or "0"
    return repo, name, version.lstrip("v"), key


class _McpMemory(EarnedMemory):
    """D78: an uncertain note (the gateway kept it for a person, observed_only) is never recalled as a rule:
    D75 said "kept, never a rule", but recall used EarnedMemory's exclusion, which does not know the flag.
    It is recalled once a person approves it (python -m attest.admin approve)."""

    def _exclusion(self, item: dict, task, version):
        why = super()._exclusion(item, task, version)
        if not why and item.get("observed_only"):
            return "uncertain: waits for a person's review"
        return why


def _memory(key: str) -> EarnedMemory:
    import hashlib

    # readable prefix plus a hash of the exact key, so two keys never share a directory
    slug = re.sub(r"[^A-Za-z0-9_.-]", "_", key)[:80] + "-" + hashlib.sha256(key.encode()).hexdigest()[:10]
    secret_scan = os.environ.get("ATTEST_SECRET_SCAN", "1") != "0"  # on by default here (D43)
    return _McpMemory(HOME / slug, backend=STORE, secret_scan=secret_scan)


def _task(name: str, task: str) -> SimpleNamespace:
    return SimpleNamespace(id="live", title=task[:80], issue=task, repo_name=name)


def _verify(repo: Path) -> tuple[bool, str]:
    import sys
    args = shlex.split(VERIFY_CMD, posix=os.name != "nt")
    if args and args[0] in ("python", "python3"):  # the server's own interpreter (on Windows "python" may be another one)
        args[0] = sys.executable
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(args, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=900, env=env)
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]


def _assess(memory: EarnedMemory, repo_name: str, ids: list[str], review_comments: list[str]) -> list[dict]:
    """Gateway v4's three states on newly admitted notes, with the deterministic evidence only (D75)."""
    from .memory import codechecks
    from .memory.admission import _norm
    from .memory.gateway import benchmark_trust, three_state
    trust = benchmark_trust()
    out = []
    for iid in ids:
        it = memory.store.items()[iid]
        ev = (it.get("evidence") or [{}])[0]
        text = f"{it.get('title') or ''} {it.get('content') or ''}"
        applied = (ev.get("applied") or {}).get("line") or ""
        quote = (ev.get("source") or {}).get("quote") or ""
        code = codechecks.run(repo_name, text, applied)
        policy = any(p in trust.registry for p in re.findall(r"\b(?:FIN|POL|SEC)-\d{4}-\d{2}\b|\bINC-\d+\b", quote))
        reviewer = any(_norm(c) in trust.trusted for c in review_comments if quote and _norm(quote) in _norm(c))
        a = three_state(policy=policy, counterfactual=None, code=code, reviewer=reviewer, repeated=False)
        fields = {"assessment": a}
        if a["state"] == "uncertain":
            fields["observed_only"] = True
        elif a["state"] == "rejected":
            fields.update(status="retired", retracted_by="gateway")
        memory.store.append("update", id=iid, fields=fields, reason=f"gateway checks: {a['state']} (counter {a['counter']}, hard {a['hard']}, soft {a['soft']})")
        out.append({"id": iid, "title": it.get("title"), **a})
    return out


# ------------------------------------------------------------------ tool functions (plain Python, tested directly)

def recall(repo_path: str, task: str) -> dict:
    """Notes this team has verified for this repository that are relevant to the task."""
    repo, name, version, key = _identity(repo_path)
    shown = _memory(key).retrieve(_task(name, task), version)
    return {"repository": name, "version": version, "note_ids": shown.ids,
            "notes": shown.context or "No verified notes for this repository yet.",
            "instructions": "Follow the notes unless the code or CHANGELOG shows they no longer hold. "
                            "When you finish, call report_outcome with the ids you relied on."}


def learn(repo_path: str, task: str, review_comments: list[str], candidates: list[dict] | None = None,
          base_ref: str = "HEAD") -> dict:
    """Submit an accepted change. Attest computes the diff and runs the verification command itself.

    review_comments: the reviewer's comments, verbatim. candidates: the notes you propose (up to 3), each
    {"kind": "lesson", "type": "business_policy" | "code_convention" | "process" | "lesson",
     "title": "<at most 8 words>", "content": "<one or two imperative sentences naming modules/functions>",
     "evidence_quote": "<10-200 characters copied verbatim from a review comment; if the comment names its source
                        (an incident such as INC-204 or a policy id), quote the part that names it>",
     "applied_in_diff": "<10-200 characters copied verbatim from one added line of your change>"}.
    Without candidates Attest distils them with its own model, which needs a model key on this machine."""
    repo, name, version, key = _identity(repo_path)
    diff = _git(repo, "diff", base_ref)
    if not diff:
        return {"admitted": [], "rejected": [], "message": f"no changes against {base_ref}: nothing to learn"}
    verified, output = _verify(repo)
    run = {"first_pass": not review_comments, "final_pass": verified, "verified_by": f"verification command: {VERIFY_CMD}", "shown_notes": [], "cited_notes": [],
           "attempts": [{"passed": not review_comments, "review_comments": list(review_comments)}]}
    memory = _memory(key)
    try:
        events = memory.learn(_task(name, task), version, run, "", diff, candidates=candidates)
    except Exception as exc:  # say why, instead of an opaque tool error
        hint = ("pass candidates (see this tool's description); distilling them here needs a model key"
                if candidates is None else "check the candidates' fields against this tool's description")
        return {"verified": verified, "admitted": [], "error": f"{type(exc).__name__}: {str(exc)[:300]}", "hint": hint}
    assessed = _assess(memory, name, [e["item"]["id"] for e in events if e["type"] == "add"], review_comments) \
        if os.environ.get("ATTEST_GATEWAY", "checks") != "off" else []
    return {
        "assessed": assessed,
        "verified": verified,
        "verification_output": output if not verified else "",
        "admitted": [e["item"]["id"] for e in events if e["type"] == "add"],
        "confirmed": [e["id"] for e in events if e["type"] == "update"],
        "rejected": [{"reason": e["reason"], "candidate": e.get("candidate")} for e in events if e["type"] == "reject"],
    }


def report_outcome(repo_path: str, task: str, shown: list[str], cited: list[str], review_comments: list[str]) -> dict:
    """After a task: which notes were shown and relied on. Attest runs verification to judge the outcome."""
    repo, name, version, key = _identity(repo_path)
    passed, _ = _verify(repo)
    run = {"first_pass": passed, "final_pass": passed, "shown_notes": list(shown), "cited_notes": list(cited),
           "attempts": [{"passed": passed, "review_comments": list(review_comments)}]}
    events = _memory(key).feedback(_task(name, task), version, run)
    return {"passed": passed, "changes": [e["reason"] for e in events if "status" in (e.get("fields") or {})]}


def list_notes(repo_path: str, include_inactive: bool = False) -> list[dict]:
    """Every note for this repository with its status, provenance and usage."""
    _, name, _, key = _identity(repo_path)
    items = _memory(key).store.items().values()
    return [
        {**{k: it.get(k) for k in ("id", "title", "content", "status", "scope", "evidence", "usage", "superseded_by")},
         "state": (it.get("assessment") or {}).get("state"), "waiting_for_review": bool(it.get("observed_only"))}
        for it in items if include_inactive or it["status"] in ("active", "suspect")
    ]


def retract(repo_path: str, note_id: str, reason: str) -> dict:
    """A person withdraws a note (kept in the log as retired, with the reason)."""
    _, name, _, key = _identity(repo_path)
    event = _memory(key).retract(note_id, reason, by="human")
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
