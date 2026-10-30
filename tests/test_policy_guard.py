"""Optional business-policy guard (D38): money written to the audit trail must be Decimal."""

import re

import pytest

from attest.benchmark import load_task, load_tasks, materialize
from attest.verify import verify


def test_every_reference_passes_with_the_guard(tmp_path):
    for task in load_tasks():
        assert verify(materialize(task, tmp_path / task.id, "reference"), task, policy_guard=True)["passed"], task.id


@pytest.mark.parametrize("task_id", ["E04", "H11"])
def test_float_amounts_in_the_audit_trail_fail_c1(task_id, tmp_path):
    task = load_task(task_id)
    ws = materialize(task, tmp_path / "w", "reference")
    for f in (ws / "ledgerly").rglob("*.py"):
        f.write_text(re.sub(r"(audit\.record\([^)]*?\bamount=)([\w.]+)", r"\1float(\2)", f.read_text(), flags=re.S))
    assert verify(ws, task)["passed"]  # the frozen tests do not notice
    r = verify(ws, task, policy_guard=True)
    assert not r["passed"] and r["conv_failed"] == ["C1"] and "Decimal end-to-end" in r["review_comments"][0]
