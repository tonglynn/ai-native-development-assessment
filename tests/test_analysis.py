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


def test_paired_tier_and_attribution():
    base = [r(t, "no_memory", "heldout", ok) for t, ok in [("H01", True), ("H04", False), ("H06", False)]]
    mem = [r(t, "attest", "heldout", ok) for t, ok in [("H01", True), ("H04", True), ("H06", False)]]
    for x in base + mem:
        x["conventions"] = ["C1"] if x["task_id"] == "H01" else ["C2", "C5"]
        x["attempts"][0]["tokens"] = {"prompt": 100, "completion": 10}
    mem[1]["notes_context"] = "- [at-0001] Idempotency: accept idempotency_key\n- [at-0002] Use BillingError"
    mem[1]["cited_notes"] = ["at-0001"]
    p = {row["condition"]: row for row in analysis.paired(base + mem, resamples=200)}["attest"]
    assert (p["wins"], p["losses"], p["ties"]) == (1, 0, 2) and round(p["mean_diff"], 3) == 0.333
    tiers = {(x["condition"], x["tier"]): x for x in analysis.tier_split(base + mem)}
    assert tiers[("attest", "review_only")]["pass1"] == 0.5 and tiers[("no_memory", "discoverable")]["tokens"] == 110
    att = {(x["condition"], x["convention"]): x for x in analysis.attribution(base + mem)}
    c5 = att[("attest", "C5")]
    assert c5["shown"] == 1 and c5["cited"] == 1 and c5["cited_ok"] == 1 and c5["not_shown"] == 1


def test_business_risks_from_failed_test_names():
    rs = [r("H04", "no_memory", "heldout", False), r("H04", "attest", "heldout", True)]
    rs[0]["attempts"][0]["tests_failed"] = ["test_conv_c5_idempotent", "test_conv_c6_approval"]
    rows = {(x["condition"], x["risk"]): x for x in analysis.business_risks(rs)}
    assert rows[("no_memory", "duplicate_money_operation")]["failed"] == 1
    assert rows[("no_memory", "unauthorised_operation")]["rate"] == 1.0
    assert rows[("attest", "duplicate_money_operation")]["failed"] == 0


def test_funnel_locates_where_the_note_was_lost():
    from attest.analysis import funnel

    def run(cond, trace, conv_failed):
        return {"condition": cond, "group": "heldout", "task_id": "H04", "conventions": ["C5", "C6", "C4"],
                "attempts": [{"crashed": False, "conv_failed": conv_failed}], "retrieval_debug": {"trace": trace}}

    texts = {"at-1": "Accept idempotency_key and skip retried requests", "at-2": "Refunds above 500 need approved_by",
             "at-3": "Round money with round_money"}
    trace = {"texts": texts, "excluded": {"at-2": "superseded by at-9 from 2.0.0"}, "retrieved": ["at-1", "at-3"], "injected": ["at-3"]}
    rows = {r["convention"]: r for r in funnel([run("attest", trace, ["C5", "C6", "C4"])])}
    assert rows["C5"]["retrieved_not_injected_fail"] == 1      # found, but cut before the prompt
    assert rows["C6"]["excluded_fail"] == 1 and rows["C6"]["excluded_reasons"] == {"superseded": 1}
    assert rows["C4"]["not_in_memory_fail"] == 1               # memory never had it
    trace2 = dict(trace, injected=["at-1"])
    rows = {r["convention"]: r for r in funnel([run("attest", trace2, [])])}
    assert rows["C5"]["injected_ok"] == 1 and rows["C5"]["followed_when_injected"] == 1.0
