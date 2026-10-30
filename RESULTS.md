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

## Retrieval ablation (exploratory, PREREGISTRATION 4c) / 检索机制消融（探索性）

Both arms start from the main experiment's memory after learning; only the ranking
differs (lexical vs `bge-small-en-v1.5`). `runs/retrieval_ablation`, 228 runs.

**Retrieval quality** (offline, 57 queries, relevance labelled blind by `deepseek-v4-pro`):

| System | Retriever | Recall@5 | Precision@5 | MRR | Review-only rule in top 5 | ms median |
|---|---|---|---|---|---|---|
| Attest | lexical | 76% | 55% | 0.83 | 88% | 0.3 |
| Attest | embedding | 88% | 63% | 0.85 | 76% | 22 |
| ReasoningBank | lexical | 39% | 44% | 0.79 | 73% | 1.0 |
| ReasoningBank | embedding | 49% | 53% | 0.86 | 67% | 26 |

Embedding − lexical, paired per query: recall +11 pp [+6, +17] (Attest), +10 pp
[+4, +15] (ReasoningBank); precision +7 pp and +9 pp, both intervals above 0.

**Effect on the work** (first-attempt pass rate, paired per task):

| System | Held-out lexical → embedding | Stale lexical → embedding |
|---|---|---|
| Attest | 70% → 70%, 0 pp [−18, +15] | 93% → 80%, −13 pp [−40, 0] |
| ReasoningBank | 58% → 45%, −12 pp [−27, +3] | 73% → 73% |

Embedding retrieval finds more of the relevant notes but **did not improve the coding
results**; it put the review-only rules (C5, C6) into the top 5 less often, which is
where memory matters, and costs about 25 ms per query instead of under 1 ms. The
lexical arms reproduce the main experiment's held-out rates exactly (Attest 70%,
ReasoningBank 58%), a check on run-to-run stability. The ReasoningBank baseline's
lexical retrieval is therefore not what held it back. 语义检索召回了更多相关笔记，但没有改善编码结果；只靠评审传承的规则进入前 5 的比例反而下降。检索指标提升不等于编码质量提升。

## Context management on a long session (exploratory, after the main experiment) / 长会话的上下文管理（探索性）

Scenario: one agent session in which the agent first worked on four ledgerly 2.0.0
tasks (real trajectories of S04, S01, S02, S03: 70 messages, about 19k tokens; in S04
the reviewer stated the approval rule) and then, in the same session, gets S05, which
needs exactly that rule. No long-term memory; the rule exists only in the session.
Budget 6,000 tokens for the managed arms. `scripts/context_eval.py`, `runs/context_eval`.

| Arm | S05 pass@1 (3 runs) | C6 failures | Prompt tokens / run |
|---|---|---|---|
| no earlier session | 0% | 3 of 3 runs | 44k |
| full session, no budget (ceiling) | 100% | 0 | 195k |
| sliding window | 0% | 3 | 43k |
| window + plain model summary | 33% | 2 | 41k |
| **Attest Context Manager** | **67%** | **0** | 46k |

The manager's one failure was the audit entry (C4, discoverable in the code), not the
rule from the session. Offline, at budgets of 4k, 6k and 8k tokens, only the manager
kept all three facts S05 needs (`1000.00`, `approved_by`, `approval_required`) in the
context; the model summary kept 0 of 6 pinned tokens at every budget ("large refunds
need approval").

**How the design got here (disclosed):** design 1 (`runs/context_eval_inc2`) crashed
on unanswered tool calls in the stitched session (INCIDENTS INC-2); design 1 re-run
(`runs/context_eval_design1`) had a ceiling of 0: even with the whole session in
context the agent did not apply an earlier review rule to a new task, so the new task
now says "apply the review guidance you received earlier in this session" (all arms).
With that, manager v1 (`runs/context_eval_design2_manager_v1`) scored 0/3 although
the facts were in its context: the rule was split into sentences among code lines and
not marked as review. Manager v2 keeps review comments whole and first, and drops code
lines from tool output. These changes were made after seeing results, on one scenario;
the 67% may not transfer. Two findings hold regardless: a fact in the context is not a
fact the agent uses, and an unchecked model summary drops exactly the numbers that
matter. 信息在上下文里不等于 Agent 会用；未经检查的模型摘要恰好丢掉关键数字。

## Dynamic forgetting V1 (exploratory, after the main experiment) / 动态遗忘 V1（探索性）

Setup (`scripts/forgetting_eval.py`, `runs/forgetting`): Attest's memories after the
learning phase of the main experiment, then a simulated stream of 400 later tasks in
which Attest's real retrieval injects notes, a note is "used" when it is about a
convention the task needs, and 200 verified one-off notes accumulate ("the refund
export uses semicolons"). In the `rare` scenario no task in the stream needs the
approval rule (C6). Forgetting runs every 50 tasks; eligibility (scope, versions,
status) is checked first and never overridden; notes are archived, not deleted.
Then the 11 held-out tasks run with each final memory (132 runs, 0 crashed).

| Policy | Held-out pass@1 | C6 violated on H04/H07/H11 | Learned notes wrongly archived (3 reps) | One-off notes archived |
|---|---|---|---|---|
| main experiment, no one-off notes (reference) | 70% | – | – | – |
| none | 42% | 4 of 9 runs | 0 | 0% |
| uniform age decay (half-life 50 tasks) | 45% | **9 of 9** | 5, incl. the approval rule in 2 reps | 77% |
| type-aware age decay (policies never decay) | 39% | **3 of 9** | 2 (code conventions), approval rule kept | 54% |
| exposure decay + retention-weighted ranking | 39% | 7 of 9 | 4, incl. the approval rule in 2 reps | 13% |

What it shows:

- **Memory pollution is the bigger problem.** 200 verified but one-off notes in scope
  cut held-out pass@1 from 70% to 42%: they share the tasks' words and take 4 of the 6
  injected slots. 被验证过、但只用过一次的细节笔记把留出组从 70% 拉到 42%。
- **No forgetting policy repaired it** (39–45%, within noise): age-based forgetting
  removes old notes, but the recent one-off notes keep crowding the top 6.
- **False forgetting has a business cost.** Uniform decay archived the approval rule
  that nobody had needed for 400 tasks, and every later run of a task that needed it
  violated the approval check (9 of 9). Type-aware decay, which never decays policy
  rules, kept it (3 of 9, fewer than without forgetting). 统一衰减误删了审批规则，之后需要它的任务全部违规；按类型衰减保住了它。
- **My exposure-based variant failed**: lexical retrieval injects a rule into
  unrelated tasks, each unused injection counts against it, and the approval rule was
  archived anyway.
- Implication: the fix belongs at admission and ranking (a detail seen once is stored
  but not injected, the trust levels in `ROADMAP.md`), not in forgetting alone; and
  any decay must exempt policy rules. 应在写入与排序环节分级（只出现一次的细节只存不注入），而不是只靠遗忘；任何衰减都必须豁免政策规则。

Limits: simulated stream and "use" by pattern matching, one clutter generator, one
threshold and half-lives chosen in advance and not tuned; 3 repetitions.

## What this supports / 结论边界

- Supported: memory of review-only knowledge helps a lot (+36 pp over no memory,
  review-only tasks 0% → 56%); scope prevents leakage; outdated thresholds are
  handled at least as well as without memory; Attest is not worse than the two
  published designs, with a smaller and cheaper prompt and immunity to the poison.
- Retrieval: better recall from embeddings did not translate into better coding results; lexical retrieval is kept.
- Context: under a 6k-token budget the context manager kept the session's review rule (2 of 3 S05 runs passed, 0 C6 failures) where a sliding window (0/3) and a plain summary (1/3) lost it; full history passes 3/3 at four times the tokens. Exploratory, one scenario, tuned after seeing results.
- Forgetting: 200 one-off notes cut held-out pass@1 from 70% to 42%; no forgetting policy repaired it; uniform decay wrongly archived the approval rule (9 of 9 later C6 runs violated it), type-aware decay did not. Exploratory.
- Not supported: that the write gate is free. Here it cost held-out passes; its value
  is protection (poison) and provenance, which the held-out pass rate does not reward.
- Limits: one model, one synthetic benchmark designed by the author, simulated
  review comments, 11 held-out tasks × 3 repetitions; real review history shows no
  recall advantage (`REAL_HISTORY.md`).
