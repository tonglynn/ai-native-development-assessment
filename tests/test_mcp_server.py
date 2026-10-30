"""The MCP prototype against a real git working copy (no model: the caller proposes candidates)."""

import asyncio
import shutil
import subprocess
import sys

import pytest

from attest import mcp_server
from attest.benchmark import REPOS_DIR

NOTE = {
    "kind": "project_fact", "topic": "money-rounding", "title": "Round money with round_money",
    "content": "Round every computed money value with ledgerly.money.round_money.",
    "evidence_quote": "Round money only with ledgerly.money.round_money",
    "applied_in_diff": "return round_money(total / qty)",
}
REVIEW = ["Round money only with ledgerly.money.round_money (half-up to the cent)."]


@pytest.fixture
def repo(tmp_path, monkeypatch):
    work = tmp_path / "ledgerly"
    shutil.copytree(REPOS_DIR / "ledgerly_v1", work, ignore=shutil.ignore_patterns("__pycache__"))
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@e", "commit", "-qm", "base"]):
        subprocess.run(["git", *cmd], cwd=work, check=True)
    monkeypatch.setattr(mcp_server, "HOME", tmp_path / "home")
    monkeypatch.setattr(mcp_server, "VERIFY_CMD", f"{sys.executable} -m pytest -q -p no:cacheprovider")
    return work


def _change(repo, body):
    with open(repo / "ledgerly" / "invoice.py", "a") as f:
        f.write(body)


def test_learn_recall_and_human_retract(repo):
    _change(repo, "\n\ndef average_price(total, qty):\n    return round_money(total / qty)\n")
    out = mcp_server.learn(str(repo), "Add average_price", REVIEW, candidates=[NOTE])
    assert out["verified"] and out["admitted"] == ["at-0001"]
    shown = mcp_server.recall(str(repo), "Compute the average invoice price")
    assert shown["repository"] == "ledgerly" and shown["note_ids"] == ["at-0001"]
    mcp_server.retract(str(repo), "at-0001", "policy changed")
    assert mcp_server.recall(str(repo), "average price")["note_ids"] == []
    assert mcp_server.list_notes(str(repo), include_inactive=True)[0]["status"] == "retired"


def test_failing_verification_learns_nothing(repo):
    _change(repo, "\n\ndef average_price(total, qty):\n    return round_money(total / qty)\n\nraise SystemExit('broken')\n")
    out = mcp_server.learn(str(repo), "Add average_price", REVIEW, candidates=[NOTE])
    assert not out["verified"] and out["admitted"] == []


def test_said_but_not_done_is_rejected(repo):
    _change(repo, "\n\ndef average_price(total, qty):\n    return total / qty\n")
    out = mcp_server.learn(str(repo), "Add average_price", REVIEW, candidates=[NOTE])
    assert out["verified"] and out["admitted"] == [] and "not applied" in out["rejected"][0]["reason"]


def test_server_exposes_tools_but_not_retract():
    names = {t.name for t in asyncio.run(mcp_server.build_server().list_tools())}
    assert names == {"recall", "learn", "report_outcome", "list_notes"}


def _clone_with_remote(repo, tmp_path, name, remote):
    other = tmp_path / name / "ledgerly"
    shutil.copytree(repo, other)
    subprocess.run(["git", "remote", "set-url", "origin", remote], cwd=other, check=True)
    return other


def test_spoofed_remote_cannot_read_another_repositorys_memory(repo, tmp_path, monkeypatch):
    """D43: memory used to be keyed by the remote's basename, so evil/ledgerly read acme/ledgerly's notes."""
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/ledgerly.git"], cwd=repo, check=True)
    _change(repo, "\n\ndef average_price(total, qty):\n    return round_money(total / qty)\n")
    assert mcp_server.learn(str(repo), "Add average_price", REVIEW, candidates=[NOTE])["admitted"] == ["at-0001"]
    same = _clone_with_remote(repo, tmp_path, "same", "git@github.com:acme/ledgerly.git")
    assert mcp_server.recall(str(same), "average price")["note_ids"] == ["at-0001"]  # same origin over ssh
    evil = _clone_with_remote(repo, tmp_path, "evil", "https://github.com/evil/ledgerly.git")
    assert mcp_server.recall(str(evil), "average price")["note_ids"] == []
    assert mcp_server.list_notes(str(evil), include_inactive=True) == []
    monkeypatch.setenv("ATTEST_ALLOWED_REPOS", "github.com/acme/ledgerly")
    assert mcp_server.recall(str(same), "average price")["note_ids"] == ["at-0001"]
    with pytest.raises(PermissionError):
        mcp_server.recall(str(evil), "average price")
