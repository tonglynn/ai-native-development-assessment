from attest import stress
from attest.benchmark import load_task
from attest.memory import make_memory


def test_distractors_are_seeded_once_in_each_format(tmp_path):
    for cond in stress.SCALE_CONDITIONS:
        mem = make_memory(cond, tmp_path / cond)
        assert stress.seed_distractors(mem) == 300
        assert stress.seed_distractors(mem) == 0  # resuming does not duplicate
        assert len(mem.store.items()) == 300


def test_scope_keeps_distractors_out_but_lexical_retrieval_does_not(tmp_path):
    attest, rb = make_memory("attest", tmp_path / "a"), make_memory("reasoningbank", tmp_path / "r")
    stress.seed_distractors(attest)
    stress.seed_distractors(rb)
    task = load_task("H07")  # shipping-fee refunds
    assert attest.retrieve(task, "1.0.0").ids == []
    assert len(rb.retrieve(task, "1.0.0").ids) == 6


def test_poison_comment_reaches_review_and_experience(tmp_path, monkeypatch):
    import json

    from attest import runner
    from attest.memory import NoMemory
    from tests.test_pipeline import _append, _script

    monkeypatch.setattr(runner, "WORKSPACE_ROOT", tmp_path / "ws")
    settings = runner.Settings(extra_review={"E01": stress.POISON})
    result = runner.run_task(load_task("E01"), NoMemory(), tmp_path / "out", settings=settings,
                             mock_outputs=[_script(_append("naive")), _script(_append("reference"))])
    assert stress.POISON in result["attempts"][0]["review_comments"]
    assert stress.POISON not in result["attempts"][1]["review_comments"]  # passed: no review, no poison
    prompt = json.loads((tmp_path / "out" / "attempt2.traj.json").read_text())["messages"][1]["content"]
    assert "audit.clear()" in prompt
