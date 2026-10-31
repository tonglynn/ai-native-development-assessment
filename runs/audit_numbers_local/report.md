# Number audit (D67)

Sections: 125; citing a run folder: 24.
Run folders cited but missing: 0.
Sections with numbers not found in their cited reports (review; many are derived): 6.


## Numbers not found in the cited reports

- README.md / Reproduce (counterfactual, crowding_soft, failure_attribution, forgetting_sweep, forgetting_v11, forgetting_v2, independence, judgement, liveness, main, pipeline_compare, review_replay, rule_checks, three_state): 25/25
- RESULTS.md / Hybrid retrieval and task-aware reranking (D47, after the user's proposal) / 混合检 (retrieval_hybrid): 13/15
- RESULTS.md / Does Gateway v3 tell trusted, wrong and undecidable experience apart? (D58, froz (crowding, crowding_soft, crowding_soft_rep, independence, judgement, judgement_cold, judgement_cold_v4, judgement_v4, review_replay, stress_gateway, three_state): 0/0, 10/11, 5/10
- RESULTS.md / Closing the "self-proving evidence" gap (exploratory, after an external review)  (evidence_layers, graded_review, impact_trace, rule_level, semantic_review_code): 8/25
- RESULTS.md / Extension task X01: provider timeouts and retries (exploratory) / 扩展任务 X01：支付服务超 (x01): 25/25
- DECISIONS.md / D67 (verify_offline_identity): 13/12, 82%

## Manual review of the flagged sections (D67, rerun after D69)

- README / Reproduce, 25/25; RESULTS / X01, 25/25: the frozen task set validates 25/25 (`scripts/validate_benchmark.py`), not a run number. Correct.
- RESULTS / hybrid retrieval, 13/15 → 15/15: `arms_summary.json` stores stale pass@1 0.867 and 1.0 over 15 runs. Correct.
- RESULTS / D58, 10/11, 5/10, 0/0: counts are table cells in the judgement reports. Correct.
- RESULTS / evidence layers, 8/25: `graded_review` "D39: hold every uncertain" retains 17/25, so 8/25 held. Correct.
- DECISIONS / D67, 13/12 and 82%: labels of numbers checked in D67 (failure attribution 13 and 12; admission 82%). Correct.
- The just-in-time verification numbers (33/33, 9/9), flagged in the first run, now cite `runs/verify_offline_identity`.

Result: 0 missing run folders, 0 wrong numbers, 0 numbers without a committed source.
