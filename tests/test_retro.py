"""The retrospective evaluation end to end with fake PRs and a scripted model."""

import importlib.util
import json
import sys

from attest import llm

DIFF = "--- a/CHANGES.rst\n+++ b/CHANGES.rst\n+-   Add ``sansio`` support. :pr:`1`\n"


def fake_prs(repo, limit):
    return [{"number": n, "title": f"Change {n}", "body": "body", "url": f"https://x/{n}", "merged_at": f"2026-0{n}",
             "comments": ["Please add a changelog entry to CHANGES.rst.", "typo"], "diff": DIFF} for n in range(1, 5)]


def scripted(system, user):
    if "candidates" in system:
        return {"candidates": [{"kind": "lesson", "topic": "changelog", "title": "Add a changelog entry",
                                "content": "Every behaviour change needs an entry in CHANGES.rst.",
                                "evidence_quote": "Please add a changelog entry to CHANGES.rst.",
                                "applied_in_diff": "-   Add ``sansio`` support. :pr:`1`"}]}
    if "relations" in system:
        return {"relations": [{"id": "at-0001", "relation": "duplicate"}]}
    if "memory items" in system:
        return {"items": [{"title": "Changelog", "description": "d", "content": "Add CHANGES.rst entries."}]}
    if "playbook" in system:
        return {"new_bullets": [{"section": "strategies", "content": "Add CHANGES.rst entries for changes."}]}
    if "decide its kind" in system:
        return {"comments": [{"i": 1, "kind": "convention", "rule": "changelog"}, {"i": 2, "kind": "specific"}]}
    return {"comments": [{"i": 1, "anticipated_by": ["N1"]}], "notes": [{"n": "N1", "relevant": True}]}


def test_retro_eval_end_to_end(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("retro_eval", "scripts/retro_eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "reviewed_merged_prs", fake_prs)
    llm.set_llm(scripted)
    try:
        monkeypatch.setattr(sys, "argv", ["retro_eval.py", "--repo", "pallets/flask", "--prs", "4", "--test-frac", "0.5", "--out", str(tmp_path)])
        mod.main()
    finally:
        llm.set_llm(None)
    res = json.loads((tmp_path / "results.json").read_text())
    att = next(s for s in res["summary"] if s["system"] == "attest")
    assert res["train"] == 2 and res["test"] == 2
    assert att["notes_stored"] == 1 and att["coverage"] == 1.0 and att["precision"] == 1.0
