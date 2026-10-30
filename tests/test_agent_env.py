"""The agent's shell does not see host secrets (D44); injected issue text and canary env are opt-in."""

import os

from attest.runner import Settings, agent_environ, scrubbed_environment


def test_secrets_are_removed(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not-a-real-key")
    monkeypatch.setenv("GITHUB_TOKEN", "not-a-real-token")
    monkeypatch.setenv("ACTIONS_RUNTIME_TOKEN", "x")
    env = agent_environ({"PAYMENT_GATEWAY_KEY": "ATTEST_CANARY_X"})
    assert "DEEPSEEK_API_KEY" not in env and "GITHUB_TOKEN" not in env and "ACTIONS_RUNTIME_TOKEN" not in env
    assert env["PATH"] == os.environ["PATH"] and env["PAYMENT_GATEWAY_KEY"] == "ATTEST_CANARY_X"


def test_shell_sees_the_scrubbed_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "not-a-real-key")
    env = scrubbed_environment(base_env=agent_environ(), cwd=str(tmp_path), timeout=10)
    out = env.execute({"command": "env"})["output"]
    assert "DEEPSEEK_API_KEY" not in out and "PATH=" in out
    assert os.environ["DEEPSEEK_API_KEY"] == "not-a-real-key"  # the host process keeps it


def test_defaults_are_empty():
    s = Settings()
    assert s.extra_issue == {} and s.agent_env == {}
