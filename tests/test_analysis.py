from attest import analysis


def r(task, cond, group, first, final=None, rep=1, shown=(), leaks=(), missed=(), events=()):
    return {
        "task_id": task, "condition": cond, "group": group, "rep": rep,
        "first_pass": first, "final_pass": first if final is None else final,
        "steps": 10, "cost_usd": 0.01, "shown_notes": list(shown), "cited_notes": [],
        "leaks": list(leaks), "attempts": [{"conv_failed": list(missed)}], "memory_events": list(events),
    }


RESULTS = [
    r("H01", "no_memory", "heldout", False, missed=["C1"]), r("H01", "no_memory", "heldout", True, rep=2),
    r("H01", "attest", "heldout", True, shown=["at-0001"]), r("H01", "attest", "heldout", True, rep=2),
    r("H02", "no_memory", "heldout", True), r("H02", "ace", "heldout", False, missed=["C2"]),
    r("B01", "ace", "control", False, shown=["ace-0001", "ace-0002"]), r("B01", "attest", "control", True),
    r("H03", "attest", "heldout", True, leaks=["hidden_test"]),
]


def test_headline_and_spread():
    kept, excluded = analysis.usable(RESULTS)
    assert len(excluded) == 1
    rows = {(x["condition"], x["group"]): x for x in analysis.headline(kept)}
    nm = rows[("no_memory", "heldout")]
    assert nm["runs"] == 3 and round(nm["pass1"], 3) == round(2 / 3, 3)
    assert nm["pass1_min"] == 0.5 and nm["pass1_max"] == 1.0  # rep 1: 1/2, rep 2: 1/1
    assert rows[("attest", "heldout")]["pass1"] == 1.0


def test_per_task_regressions_contamination():
    kept, _ = analysis.usable(RESULTS)
    assert analysis.per_task(kept)["H01"]["no_memory"] == {"pass1": 1, "runs": 2, "missed": {"C1": 1}}
    assert analysis.regressions(kept) == [{"task_id": "H02", "condition": "ace", "memory": "0/1", "baseline": "1/1"}]
    cont = {c["condition"]: c for c in analysis.contamination(kept)}
    assert cont["ace"]["foreign_notes_shown"] == 2 and cont["attest"]["foreign_notes_shown"] == 0
