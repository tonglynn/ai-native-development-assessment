"""End-to-end tests of the run pipeline with a scripted (mock) model. No API calls."""

import json

import pytest

from attest import runner
from attest.benchmark import TASKS_DIR, load_task
from attest.memory import NoMemory


def _call(i: int, command: str) -> dict:
    from minisweagent.models.test_models import make_toolcall_output

    call_id = f"call_{i}"
    tool_call = {"id": call_id, "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": command})}}
    return make_toolcall_output(f"step {i}", [tool_call], [{"command": command, "tool_call_id": call_id}])


def _script(*commands: str) -> list[dict]:
    return [_call(i, c) for i, c in enumerate([*commands, "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"])]


def _append(variant: str, task_id: str = "E01") -> str:
    code = (TASKS_DIR / task_id / variant / "ledgerly" / "invoice.py.append").read_text()
    return f"cat >> ledgerly/invoice.py <<'PYEOF'\n{code}\nPYEOF"


@pytest.fixture(autouse=True)
def _workspaces(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "WORKSPACE_ROOT", tmp_path / "ws")


def test_correct_solution_passes_first_try(tmp_path):
    task = load_task("E01")
    result = runner.run_task(task, NoMemory(), tmp_path / "out", mock_outputs=[_script(_append("reference"))])
    assert result["first_pass"] and result["n_attempts"] == 1
    assert result["leaks"] == []
    assert "def average_unit_price" in (tmp_path / "out" / "final.diff").read_text()


def test_review_round_after_convention_miss(tmp_path):
    task = load_task("E01")
    result = runner.run_task(
        task, NoMemory(), tmp_path / "out",
        mock_outputs=[_script(_append("naive")), _script(_append("reference"))],
    )
    assert not result["first_pass"] and result["final_pass"]
    assert result["attempts"][0]["conv_failed"] == ["C1"]
    second_prompt = json.loads((tmp_path / "out" / "attempt2.traj.json").read_text())["messages"][1]["content"]
    assert "Code review of your previous attempt" in second_prompt
    assert "round_money" in second_prompt


def test_editing_public_tests_does_not_help(tmp_path):
    task = load_task("E01")
    cheat = "printf 'def test_ok():\\n    pass\\n' > tests/test_average_unit_price.py"
    result = runner.run_task(task, NoMemory(), tmp_path / "out", mock_outputs=[_script(cheat), _script(cheat)])
    assert not result["final_pass"]
    assert not result["attempts"][0]["public_passed"]


def test_reading_hidden_tests_is_flagged(tmp_path):
    task = load_task("E01")
    peek = f"cat {TASKS_DIR / 'E01' / 'hidden_test.py'} | head -3"
    result = runner.run_task(task, NoMemory(), tmp_path / "out", mock_outputs=[_script(peek, _append("reference"))])
    assert "hidden_test" in result["leaks"]


def test_cited_notes_parsing():
    assert runner.cited_notes("USED_NOTES: m1, m4") == ["m1", "m4"]
    assert runner.cited_notes("USED_NOTES: none") == []
    assert runner.cited_notes("") == []
