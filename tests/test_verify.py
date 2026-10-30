"""Just-in-time verification at retrieval (attest/memory/verify.py)."""

from attest.benchmark import load_task
from attest.memory.earned import EarnedMemory
from attest.memory.verify import VerifiedMemory


def note(i, title, content, files=("ledgerly/invoice.py",)):
    return {"id": i, "kind": "project_fact", "type": "code_convention", "title": title, "content": content, "status": "active",
            "supersedes": [], "superseded_by": None,
            "scope": {"repo": "ledgerly", "observed_version": "1.0.0", "valid_from": "1.0.0", "valid_until": None, "files": list(files)},
            "source": {"task_id": "E01", "review_comments": [], "references": []},
            "evidence": [{"task_id": "E01", "version": "1.0.0", "source": {"kind": "review_comment", "quote": "x", "references": []},
                          "applied": {"kind": "code", "change": "added", "file": files[0], "line": "..."}, "verification": {"passed": True}}],
            "usage": {"shown": 0, "cited": 0, "cited_pass": 0, "cited_fail": 0, "fail_streak": 0}}


ROUND = note("at-0001", "Round money only with round_money",
             "Always round monetary results with ledgerly.money.round_money (half-up to the cent).")


def seeded(cls, **kw):
    m = cls(None, **kw)
    m.store.append("add", item=ROUND, reason="seed")
    return m


def test_same_version_context_is_unchanged():
    task = load_task("H01")
    assert seeded(VerifiedMemory).retrieve(task, "1.0.0").context == seeded(EarnedMemory).retrieve(task, "1.0.0").context


def test_drifted_note_is_annotated_on_the_new_version():
    r = seeded(VerifiedMemory).retrieve(load_task("S01"), "2.0.0")
    assert r.debug["verification"] == {"at-0001": "drifted"}
    assert "CHECK BEFORE USE" in r.context and "half-up no longer appears" in r.context


def test_drop_mode_excludes_a_drifted_note():
    r = seeded(VerifiedMemory, mode="drop").retrieve(load_task("S01"), "2.0.0")
    assert "at-0001" not in r.ids and "cited code changed" in r.debug["trace"]["excluded"]["at-0001"]
