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
