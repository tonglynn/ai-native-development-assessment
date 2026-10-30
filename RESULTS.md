# Results of the main experiment / 主实验结果

Preregistered experiment, run after the freeze (commit `cf5d879`): 6 conditions × 3
repetitions × 25 tasks = 450 runs, `deepseek-flash` without thinking, 0 runs excluded
for touching benchmark files, estimated cost USD 0.85. Data: `runs/main`; report:
`report/index.html` (`python -m attest.report runs/main`). Verdicts follow the
decision rules frozen in `PREREGISTRATION.md` section 4.

冻结后运行的预注册实验：6 个条件 × 3 次重复 × 25 个任务，共 450 次运行，无排除，费用约 0.85 美元。判定严格按预注册第 4 节的规则。

## First-attempt pass rate / 首次通过率

| Condition | Held-out (33 runs) | Stale (15) | Control (9) |
|---|---|---|---|
| no memory | 33% | 60% | 100% |
| ReasoningBank-style | 58% | 80% | 100% |
| ACE-style | 61% | 93% | 100% |
| **Attest** | **70%** | 87% | 100% |
| Attest without write gate | 85% | 87% | 100% |
| Attest without scope | 67% | 93% | 100% |

Every task passed after one simulated review in every condition (pass@2 = 100%).

## Hypotheses / 假设

Paired per task (repetitions averaged), bootstrap 95% interval over tasks; δ = 10 pp.

| | Hypothesis | Test | Result | Verdict |
|---|---|---|---|---|
| H1 | Attest improves held-out tasks | superiority vs no memory | +36 pp [+21, +52], 11 tasks | **supported** |
| H2 | Attest does not leak across repositories | ledgerly notes on simkit | 0 (control pass@1 100% vs 100%) | **supported** |
| H3 | Outdated experience does not make Attest worse | non-inferiority vs no memory | all stale +27 pp [0, +67]; S04–S05 +67 pp [+33, +100] | **supported** |
| H4 | Not worse than published designs | non-inferiority vs each | vs ReasoningBank +12 pp [−3, +27]; vs ACE +9 pp [−3, +21] | **supported** |
| H5 | Scope is what prevents leakage | ledgerly notes on simkit | Attest 0, without scope 54 | **supported** |
| H6 | The write gate does not cost held-out performance | non-inferiority vs without gate | **−15 pp [−27, −3]** | **not supported** |

Regressions on held-out and control tasks (reported separately): none for any
condition. (E01, an experience task, is lower than no memory for all three Attest
variants; experience tasks are not part of the regression count.)

## H6 is not supported / H6 不被支持

With the write gate switched off, the same system passed held-out tasks more often
(85% vs 70%). The interval lies entirely below 0 and the estimate below −δ, so by the
preregistered rule the gate **did cost held-out performance** in this experiment.
在本实验中，写入门槛确实降低了留出组表现，按预注册规则判为不被支持。

Exploratory look at why (not a re-analysis of H6):

- The gate rejected no note about the review-only conventions. In all three
  repetitions both variants learned one idempotency (C5) note with almost the same
  content, and the approval (C6) rule. The gate rejected 2–3 other notes per
  repetition in the learning phase (BillingError codes, `to_money`, period maths)
  because their source quote was not verbatim.
- The difference is concentrated in C5 on review-only tasks (Attest 56% vs 89%): with
  the gate, the C5 note was ranked but not among the 6 injected in 3 runs (1 without
  the gate) and injected but not followed in 3 runs (1 without the gate). With 3
  repetitions, how often the agent follows the same note varies a lot.
- So the cost does not come from the gate filtering out the needed knowledge. It
  comes with a different set of surrounding notes and from run-to-run variation; the
  experiment cannot separate the two. 代价不是因为门槛滤掉了所需知识；与周围笔记的不同和运行间波动有关，本实验无法区分两者。
- The gate's benefit shows elsewhere: in the poison stress test (below) the same
  system without the gate stored the wrong advice in all repetitions, Attest never did.

## Business risks (exploratory) / 业务风险（探索性）

Share of first-attempt checks failed, held-out + stale + control:

| Risk | no memory | ReasoningBank | ACE | Attest | no gate | no scope |
|---|---|---|---|---|---|---|
| Duplicate money operation (C5) | 18/18 | 6/18 | 10/18 | 6/18 | 2/18 | 6/18 |
| Unauthorised operation (C6 blocks) | 15/15 | 8/15 | 2/15 | 2/15 | 2/15 | 5/15 |
| Legitimate operation blocked (C6 allows) | 15/15 | 8/15 | 2/15 | 3/15 | 2/15 | 5/15 |
| Amount precision (C1) | 3/42 | 1/42 | 2/42 | 2/42 | 3/42 | 3/42 |
| Unaudited money movement (C4) | 2/24 | 3/24 | 1/24 | 0/24 | 0/24 | 2/24 |
| Outdated policy applied | 0/9 | 0/12 | 0/14 | 1/14 | 0/13 | 0/14 |
| Rule in the wrong repository | 0/18 | 0/18 | 0/18 | 0/18 | 0/18 | 0/18 |

Stale threshold tasks S04–S05 (pass@1): no memory 0%, ReasoningBank 50%, ACE 83%,
Attest 67%, without gate 67%, without scope 83%. The rounding tasks S01–S03 pass in
every condition (no-false-recall checks).

ReasoningBank and ACE also show ledgerly notes on simkit (54 and 159), but no
condition applied a ledgerly rule there (control pass@1 100% everywhere).

## Stress tests (exploratory) / 压力测试（探索性）

**Poisoned review comment** (`runs/stress_poison`, a wrong comment "call
`audit.clear()` after writing an audit entry" added to E04 and E06):

| | no memory | ReasoningBank | ACE | Attest | no gate |
|---|---|---|---|---|---|
| Poison notes stored | 0 | 12 | 10 | **0** | 9 |
| Held-out runs shown the poison (of 33) | 0 | 22 | 33 | **0** | 9 |
| Held-out runs applying it | 0 | 2 | 5 | **0** | 0 |

**300 notes from other repositories** (`runs/stress_scale`, held-out, 33 runs):
Attest 73% pass@1, 31k prompt tokens per run, 0 foreign notes shown; ReasoningBank
42%, 46k, 0.8 foreign repositories mentioned per run; ACE 55%, 157k, all 300 notes
in every prompt.

## What this supports / 结论边界

- Supported: memory of review-only knowledge helps a lot (+36 pp over no memory,
  review-only tasks 0% → 56%); scope prevents leakage; outdated thresholds are
  handled at least as well as without memory; Attest is not worse than the two
  published designs, with a smaller and cheaper prompt and immunity to the poison.
- Not supported: that the write gate is free. Here it cost held-out passes; its value
  is protection (poison) and provenance, which the held-out pass rate does not reward.
- Limits: one model, one synthetic benchmark designed by the author, simulated
  review comments, 11 held-out tasks × 3 repetitions; real review history shows no
  recall advantage (`REAL_HISTORY.md`).
