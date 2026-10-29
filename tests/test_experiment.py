"""The experiment protocol: phase order, frozen phases and snapshots (run_task is faked)."""

import json

from attest import experiment


def test_protocol_order_frozen_phases_and_resume(tmp_path, monkeypatch):
    calls = []

    def fake_run_task(task, memory, out, settings=None, update_memory=True):
        calls.append((task.id, update_memory, memory.name))
        result = {"task_id": task.id, "first_pass": True, "final_pass": True, "shown_notes": [], "cited_notes": []}
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(json.dumps(result))
        return result

    monkeypatch.setattr(experiment, "run_task", fake_run_task)
    experiment.run_sequence("attest", 1, tmp_path, settings=None, log=lambda m: None)

    order = [c[0] for c in calls]
    assert order == ["E01", "E02", "E03", "E04", "E05", "E06", "H01", "H02", "H03", "H04", "H05", "H06",
                     "B01", "B02", "B03", "S01", "S02", "S03"]
    frozen = {c[0] for c in calls if not c[1]}
    assert frozen == {"H01", "H02", "H03", "H04", "H05", "H06", "B01", "B02", "B03"}
    for phase in ("learn", "heldout", "control", "stale"):
        assert (tmp_path / "attest" / "r1" / "memory" / f"after_{phase}.json").exists()

    # a second invocation resumes from saved results instead of rerunning
    calls.clear()
    experiment.run_sequence("attest", 1, tmp_path, settings=None, log=lambda m: None)
    assert calls == []
