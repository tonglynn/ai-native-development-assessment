"""Pipeline of scripts/rule_checks.py, without the model: ground truth, sandbox, scoring."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import rule_checks  # noqa: E402

BILLING_ERROR_CHECK = '''
import ast
def check(path, source):
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            name = getattr(node.exc.func, "id", getattr(node.exc.func, "attr", ""))
            if name != "BillingError":
                out.append(f"raises {name}, not BillingError")
    return out
'''
NOTE = {"key": "t/1", "title": "Raise BillingError", "content": "Reject invalid input with BillingError.", "conventions": ["C2"]}


def test_cases_cover_17_tasks_with_reference_and_naive():
    cs = rule_checks.cases()
    assert {c["task"] for c in cs} == set(rule_checks.TASKS) and len(rule_checks.TASKS) == 17
    assert {c["kind"] for c in cs} == {"reference", "naive"}
    assert all(c["broken"] == [] for c in cs if c["kind"] == "reference")


def test_a_correct_check_is_useful():
    row = rule_checks.evaluate(NOTE, {"checkable": True, "code": BILLING_ERROR_CHECK, "why": ""}, rule_checks.cases())
    assert row["usable"] and row["detection"] == 1.0 and row["false_alarms"] == [] and row["useful"]


def test_a_check_that_flags_everything_is_not_useful():
    code = "def check(path, source):\n    return ['always']\n"
    row = rule_checks.evaluate(NOTE, {"checkable": True, "code": code, "why": ""}, rule_checks.cases())
    assert row["detection"] == 1.0 and row["false_alarm_rate"] == 1.0 and not row["useful"]


def test_the_sandbox_has_no_environment_and_stops_runaway_code(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-for-test")
    leak = "import os\ndef check(path, source):\n    return [k for k in os.environ]\n"
    seen = rule_checks.run_check(leak, [{"path": "p", "source": ""}])[0]["violations"]
    assert set(seen) <= {"LC_CTYPE"}  # only what Python itself sets for the C locale; nothing inherited
    loop = "def check(path, source):\n    while True:\n        pass\n"
    assert rule_checks.run_check(loop, [{"path": "p", "source": ""}], timeout=2) == [{"error": "timeout"}]
    broken = "def check(path, source) return []"
    assert "compile" in rule_checks.run_check(broken, [{"path": "p", "source": ""}])[0]["error"]


def test_notes_are_the_25_active_learned_notes():
    ns = rule_checks.notes()  # 26 learned notes in total; r3 at-0001 was retired during learning
    assert len(ns) == 25 and len({n["key"] for n in ns}) == 25
