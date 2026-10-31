# Number audit (D67)

Sections: 120; citing a run folder: 21.
Run folders cited but missing: 0.
Sections with numbers not found in their cited reports (review; many are derived): 6.


## Numbers not found in the cited reports

- README.md / Reproduce (counterfactual, crowding_soft, failure_attribution, forgetting_sweep, forgetting_v11, forgetting_v2, independence, judgement, liveness, main, pipeline_compare, review_replay, rule_checks, three_state): 25/25
- RESULTS.md / Just-in-time verification at retrieval (after GitHub Copilot's agentic memory) / (verify_eval): 33/33, 9/9
- RESULTS.md / Hybrid retrieval and task-aware reranking (D47, after the user's proposal) / 混合检 (retrieval_hybrid): 13/15
- RESULTS.md / Does Gateway v3 tell trusted, wrong and undecidable experience apart? (D58, froz (crowding, crowding_soft, crowding_soft_rep, independence, judgement, judgement_cold, judgement_cold_v4, judgement_v4, review_replay, stress_gateway, three_state): 0/0, 10/11, 5/10
- RESULTS.md / Closing the "self-proving evidence" gap (exploratory, after an external review)  (evidence_layers, graded_review, impact_trace, rule_level, semantic_review_code): 8/25
- RESULTS.md / Extension task X01: provider timeouts and retries (exploratory) / 扩展任务 X01：支付服务超 (x01): 25/25

## Manual review of the 6 flagged sections (D67)

- README / Reproduce, 25/25; RESULTS / X01, 25/25: the frozen task set validates 25/25 (`python -m attest validate`), not a run number. Correct.
- RESULTS / hybrid retrieval, 13/15 → 15/15: `arms_summary.json` stores stale pass@1 0.867 and 1.0 over 15 runs = 13/15 and 15/15. Correct.
- RESULTS / D58, 10/11, 5/10, 0/0: the reports give the counts as table cells (judgement: trusted 11 → 10 rule; judgement_cold: wrong 10 → 5 rule). Correct.
- RESULTS / evidence layers, 8/25: `graded_review` row "D39: hold every uncertain" retains 17/25, so 8/25 held. Correct.
- RESULTS / just-in-time verification, 33/33 and 9/9: had no committed source (run interactively). Rerun and saved: `runs/verify_offline_identity` gives 18/18, 33/33, 9/9 at every intermediate memory state.

Result: 0 missing run folders, 0 wrong numbers; the one number without a committed source now has one.
