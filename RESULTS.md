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

### Sensitivity of forgetting to its parameters (offline) / 遗忘参数敏感度（离线）

The half-lives and the threshold were fixed in advance, not tuned. A sweep
(`scripts/forgetting_sweep.py`, `runs/forgetting_sweep`, 45 configurations × 3
repetitions, no model calls) shows which conclusions depend on them:

| Policy | Range swept | Clean memory? | Policy rules wrongly archived |
|---|---|---|---|
| uniform age decay | half-life 25–800 tasks | only at ≤ 100 tasks | **3** at every half-life short enough to clean (≤ 100); none above, but then nothing is archived |
| exposure decay | half-life 5–40 unused injections | partly | 3 except at 40 (which archives almost nothing) |
| type-aware decay | half-lives × 0.25–4 | yes at × 0.25–0.5 | **0** everywhere |

- **Revised:** "forgetting cannot repair crowding" holds for the default parameters,
  not in general. Aggressive type-aware decay (half-lives × 0.25, threshold 0.2–0.3)
  raised the share of needed rules injected from 44% to 68–69% without archiving a
  policy rule, but wrongly archived 2–5 other learned rules. Tiered admission reached 82%
  with none archived. 修正：默认参数下遗忘解决不了挤占；激进的按类型遗忘能部分缓解，但会误删 2–5 条普通规则。
- **Robust:** uniform and exposure decay archive policy rules whenever they are strong
  enough to clean; type-aware decay never does.
- The selection rule fixed before the sweep (no policy rule archived, at most one other
  learned note, then most needed rules injected) chose type-aware × 1 at threshold 0.1;
  on a second stream it gave 44% injected, 0 archived: safe, but no cleaner than no
  forgetting.
- **Why the curves flatten:** the formula R = E × max(D, U) gives every note that was used
  once in a passing task R ≥ 0.25 (E ≥ 0.5, U ≥ 0.5), above the 0.2 threshold, whatever its
  age. 21 of 26 learned notes are protected this way; only the 5 never reused (k = 0) can be
  archived, so half-lives only ever move those 5. One-off notes are never "used" in this
  simulation, so the floor did not protect them here; with a looser notion of use it
  would make them permanent (see V1.1 below). 公式里的效用下限让"用过一次"的笔记永远不会被归档。

## Trust-tiered admission against memory pollution (exploratory) / 可信度分级写入（探索性）

The forgetting experiment pointed to admission, not forgetting, as the place to stop
pollution. Admission tiers (`attest/memory/admission.py`, explainable rules): a note
citing a policy or incident (**policy**), a review comment that states a team
convention (**convention**) or a note verified in at least 2 independent tasks
(**repeated**) may be injected anywhere in its repository; anything else is a
**candidate**, stored but injected only in tasks that name a file it was learned in,
and promoted when a second task verifies it. Rules rank before candidates. Same stream
as the forgetting experiment, except that every one-off note is tied to the real module
its topic belongs to, so details still reach tasks touching that file (harder than
before). `scripts/admission_eval.py`, `runs/admission`, 132 runs, 0 crashed.

| Arm | Needed rule injected | One-off notes injected / task | Active notes | Held-out pass@1 | C6 violated (H04, H07, H11) |
|---|---|---|---|---|---|
| main experiment, clean memory (reference) | – | 0 | 8–9 | 70% | – |
| none | 44% | 4.1 | 208 | 36% | 4 of 9 |
| type-aware forgetting only | 48% | 4.0 | 99 | 33% | 3 of 9 |
| **tiered admission** | 82% | 1.7 | 208 | **67%** | 1 of 9 |
| **tiered admission + type-aware forgetting** | 82% | 1.7 | 99 | **76%** | **0 of 9** |

Paired per task against none (bootstrap 95% over the 11 tasks): tiered +30 pp
[+9, +52], 5 better / 0 worse; tiered + type-aware forgetting +39 pp [+12, +64], 6 / 1.
Adding forgetting to tiering: +9 pp [−6, +27], not distinguishable; forgetting alone:
−3 pp [−12, +6]. 分级写入把被污染的记忆拉回到接近干净记忆的水平；遗忘主要负责把活跃笔记减半，且不误删政策规则。

Division of labour that the experiments support: **admission tiers stop pollution,
version ranges stop outdated rules, type-aware forgetting keeps memory small without
removing policy rules, reactivation brings archived notes back.** 写入分级防污染，版本管理防过期，按类型遗忘控规模且不误删政策，重新激活负责恢复。

Limits, stated as they are: the one-off notes have, by construction, no policy reference
and no convention marker, and the benchmark's review comments mark team rules
explicitly ("[team convention]"), which real reviewers rarely do (`REAL_HISTORY.md`). The
claim is that the mechanism works when the signal exists; where the signal comes from
in real repositories (policy references and repetition over time) is the next question.
Tiering also has a cost: a real rule seen once with diff-only evidence (the audit rule in
repetition 2) becomes a candidate and is not injected outside its file.

## Forgetting V1.1: what counts as evidence of value (offline, exploratory) / 遗忘 V1.1：什么才算价值反馈（离线，探索性）

A review of V1 raised three problems: one verified use protected a note for ever (the U
floor above); "the task passed" was counted as "the note contributed"; and a reactivated
note kept its old age, so the next maintenance could archive it again. V1.1 is opt-in and
changes three things, each switchable:

- **verified-only reinforcement**: a note is reinforced only when the task's hidden tests
  check its convention. A note adopted in a passing task but unchecked is counted, not
  reinforced, and a self-reported citation counts only under the same condition (D10).
- **utility decay**: U decays too, 4 times slower than D. The 4 is an experimental setting.
- **citation protection**: a note citing FIN-/POL-/SEC-/INC- never decays, whatever its type
  label. This is added to the `business_policy` type protection, not a replacement for it.

Noise: 30% of injected one-off notes are "adopted" though the task does not need them,
and the task passes anyway. The stream is the same as before, with 2 stream seeds × 3
repetitions and no model calls (`scripts/forgetting_v11.py`, `runs/forgetting_v11`).
"Verified" here is a proxy signal, not attribution.

| Configuration | Variant | Noise | Needed rule injected | Active notes | One-off notes never archivable | Useful rules wrongly archived | Policy rules archived |
|---|---|---|---|---|---|---|---|
| no forgetting | – | 0.3 | 45% | 208 | 200 | 0/52 | 0 |
| type-aware ×1 | V1 | 0 | 46% | 100 | 0 | 4/52 | 0 |
| type-aware ×1 | V1 | 0.3 | 45% | **126** | **34** | 4/52 | 0 |
| type-aware ×1 | V1.1 | 0.3 | 46% | 99 | 0 | **10/52** | 0 |
| type-aware ×0.25 | V1 | 0 | 67% | 32 | 0 | 4/52 | 0 |
| type-aware ×0.25 | V1 | 0.3 | **54%** | **65** | **34** | 4/52 | 0 |
| type-aware ×0.25 | V1.1 | 0.3 | 68% | 31 | 0 | **11/52** | 0 |
| tiered + type-aware ×1 | V1 | 0.3 | 79% | 106 | 6 | 4/52 | 0 |
| tiered + type-aware ×1 | V1.1 | 0.3 | 82% | 99 | 0 | **10/52** | 0 |

V1.1 gives the same numbers with and without noise. *Useful rules* are the learned notes
about C1–C6 (44), plus learned rules outside C1–C6 that I checked against the benchmark's
own sources and found correct but untested (8: "reject bool as an integer", "use to_money
and ZERO"; labelled by hand after the run). "Not verified" is not "verification failed",
so these count on the risk side. The direction is the same on both stream seeds.

- **The U floor is real.** When adoption counts as contribution (V1 with noise), 34 one-off
  notes became permanent. Active notes went from 100 to 126 (×1) and from 32 to 65 (×0.25),
  and under aggressive decay the needed rules injected fell from 67% to 54%. 一次"被采用"就能让细节笔记永久保留。
- **V1.1 removes it.** No one-off note becomes permanent, and memory is the same with or
  without noise.
- **But V1.1 wrongly archives more correct rules: 4 → 10–11 of 52 (8% → 19–21%).** Most are
  rules whose use the proxy cannot see (all 8 known-correct rules outside C1–C6, against 2
  under V1). Once it is a C1–C6 rule: the audit rule (C4) in one repetition under ×0.25. No
  arm archived a policy rule. 省了空间，但丢了更多正确规则。
- **Ablation** (×0.25, noise, seed 0, 3 repetitions):
  - Verified-only reinforcement alone gives all of the space saving (31 active notes, 0
    permanent, 68%) and wrongly archives 3 of 26 (V1: 2 of 26).
  - Utility decay alone is the worst arm (49 active notes, 61%, 8 of 26 wrongly archived),
    and it archived the `ensure_utc` rule (C3) in all 3 repetitions. That is consistent with
    reinforced one-off notes keeping the rule out of the injected six, so it is never
    reinforced while its utility decays. I did not trace the injections to confirm it.
  - Citation protection alone changes nothing here: the cited rules were either typed
    `business_policy` or reinforced by the stream.
  - The parts interact: utility decay is only safe together with verified-only reinforcement.
- **utility_factor 2 / 4 / 8** (V1.1, ×1, noise, seed 0) wrongly archives 6 / 5 / 3 of 26.
  Active notes and needed rules injected hardly change (98–99 notes, 47–48%). In this simulation utility decay
  saves no space, because verified-only reinforcement already does, so the factor only
  sets how much is lost. Utility decay is meant for one case: a detail genuinely verified
  once and never needed again. The stream never produces that case, so it shows no benefit
  here. That is a limit of this test, not evidence against utility decay.
- **Decision** (the rule was set by the user before the results were read): V1.1 saves
  space but wrongly archives more correct rules, so **V1 stays the default and V1.1 stays an
  experimental option**. The two fixes are judged separately, and both are kept:
  - Reactivation now always resets the decay clock and requires the current task clock.
    Before, a restored note could be archived again at the next maintenance. No published
    run reactivated a note.
  - Policy references are now an explicit list. ADR-, RFC- and CVE- references had counted
    as policy. The run data contain only FIN- and INC-, so no result changes.
- **What it says about memory governance:** all of the space saving came from what counts
  as feedback (verified-only reinforcement), and the losses came from rules that the feedback
  cannot see. The hard part is not the decay rate but getting reliable evidence of value: a
  rule nobody tests looks the same as a rule nobody needs. 难点不是遗忘速度，而是拿到可靠的价值反馈：没有测试覆盖的规则，和没人需要的规则，在反馈里看起来一样。

Regression scenarios (`tests/test_governance_regressions.py`) pin four cases:

- A policy rule nobody needed for 1,000 tasks is kept and injected for H04.
- A team-convention rule learned in one file reaches another file.
- A superseded rule is neither archived nor revived, and still serves 1.0.0.
- A reactivated note is not archived at the next maintenance.

One unresolved limitation is kept as a strict xfail: a real rule seen once, with diff-only
evidence, does not reach other files. These tests pin behaviour; they do not show that a
retention policy works overall.

Limits: the stream, the adoption noise and the verification proxy are all simulated, and
verification is detected by pattern matching. I labelled the known-correct rules myself,
after the run. Each repetition starts from one learned memory.

## Forgetting V2: six ways to get better evidence of value (exploratory) / 遗忘 V2：六种获得价值反馈的办法（探索性）

V1.1 showed that the hard part is evidence, not the decay rate. Six ideas were tested, at
different depths. Points 5 and 6 are checked against the benchmark's real code. Points 1–4 are
tested in the simulated stream, with cases constructed for them. V1 stays the default
throughout.

### 1–4. Formula and feedback, in the simulated stream / 公式与反馈（模拟任务流）

`scripts/forgetting_v2.py`, `runs/forgetting_v2`, no model calls; 11 arms, each run on 2
stream seeds × 3 repetitions. The setup is the admission experiment's stream (tiered
admission, 200 one-off notes, no task needs the approval rule) with 30% adoption noise, plus
three constructed cases:

- **verified-once details:** every 5th one-off note is genuinely verified once, then never
  needed again;
- **wrong rules:** 12 wrong rules about C1–C3, worded like the correct ones and admitted as
  team conventions. The agent follows one half the time, and that convention then fails;
- **convention outcomes:** a convention passes if a correct note about it was used; without
  one, it passes half the time for C1–C4 and never for C5–C6.

The cases are what the mechanisms are built for, so this shows whether each mechanism does
its job and what it costs, not how often the cases occur.

| Arm | Needed rule injected | Injectable notes | Useful rules archived | Policy rules archived | Stale verified-once still active | Wrong-note injections in the stream | Wrong notes left at the end |
|---|---|---|---|---|---|---|---|
| V1 | 57% | 132 | 4/52 | 0 | 114/115 | 609 | 9 |
| V1.1 | 64% | 122 | 12/52 | 0 | 68/115 | 656 | 9 |
| base = verified-only reinforcement | 57% | 130 | 6/52 | 0 | 114/115 | 646 | 9 |
| base + 1 stability growth | 64% | 122 | **8/52** | 0 | **70/115** | 647 | 9 |
| base + 3 three evidence states | 63% | 125 (+87 dormant) | **0/52** (6 dormant) | 0 | 115/115 | **82** | 4 |
| base + 4 demand signal | 57% | 130 | **4/52** | 0 | 114/115 | 646 | 9 |
| all four | 66% | 118 (+94 dormant) | 0/52 (4 dormant) | 0 | 70/115 | 82 | 4 |
| exposure decay (V1) | 52% | 211 | 6/52 | **6** | 115/115 | 289 | 4 |
| exposure decay + 2 scoped counting | 61% | 216 | **0/52** | **0** | 115/115 | 455 | 8 |
| V1, type half-lives × 0.25 | 66% | 54 | 4/52 | 0 | 76/115 | 243 | 0 |
| all four, × 0.25 | **71%** | **44** (+168 dormant) | **0/52** (8 dormant) | 0 | **11/115** | 82 | 4 |

Read against the rules fixed before the run:

- **1 Stability growth: it does its job but costs rules, so it does not pass.** It replaces the
  utility floor with a half-life that doubles at each independent verification. Stale details
  fade (114 → 70 of 115 still active), and no one-off note is permanent (34 → 0). But it
  archived the audit rule (C4) in 2 runs: 6 → 8 of 52 useful rules archived.
- **2 Scoped counting passes, but exposure decay as a family still fails.** Counting a note as
  unused only in tasks that touch its files stopped exposure decay from archiving the approval
  rule (6 → 0) and any useful rule (6 → 0). But exposure decay barely cleans memory (211–216
  notes stay injectable). Scoping also shields wrong notes, which are counted unused less
  often: 4 → 8 of them are left at the end.
- **3 Three evidence states pass, and they are the strongest single mechanism.** A note is
  archived only on negative evidence; low retention without it makes the note dormant (kept
  in its own files). Useful rules archived fell from 6 to 0, with 6 dormant and still reachable
  in their files. Injections of wrong rules fell by 87% (646 → 82), and the needed rules
  injected rose from 57% to 63%. The caveat: here a failure is attributed to the wrong note
  perfectly, by construction. In real work, finding which note caused a failure is the hard
  part, and point 6 showed that generated checks cannot yet supply that reliably.
- **4 The demand signal passes, with a modest effect and a clear limit.** A convention that fails
  for lack of a note credits the notes about it, so 6 → 4 of 52 useful rules were archived. The
  4 still lost are the "reject bool" rules: no test or review names them, so demand cannot reach
  them. It reactivated no note in any arm: all of its effect is credit given before a note is
  archived. Its cost is that it also credits wrong rules about the failing convention, 220 times
  per run on its own and 122 with three evidence states, where negative evidence blocks the
  credit. In "all four",
  the 4 wrong notes left at the end are wrong C3 rules that were never followed, so they had no
  negative evidence, and one demand credit each kept them alive.
- **Aggressive decay becomes safe with the four mechanisms.** With half-lives × 0.25, V1
  archives 4 useful rules, while "all four × 0.25" archives none (8 dormant). It also has the
  best needed-rule injection (71% against V1's 57%) and the smallest injectable memory (44 notes
  against 132). Its cost: 4 wrong rules survive, against 0 under V1 × 0.25.
- **Decision:** V1 stays the default. "All four × 0.25" is the most promising configuration and
  passes the user's rule here: it saves space and loses fewer correct rules. But it rests on
  constructed cases, and on attribution of negative evidence that is perfect here and does not
  yet exist in practice. 三态证据最有效，但它依赖"能准确知道是哪条笔记导致了失败"，这在模拟里是构造出来的，现实中还做不到。

Disclosed:

- **Two changes after a smoke run of two arms, before the experiment.** The wrong rules were
  first single-task candidates, which were never injected (the rules fill the six slots first),
  so they were made admitted team conventions. The coverage measure briefly counted only a
  note's primary convention, and was restored to the earlier experiments' definition.
- **A fix made in that smoke run.** Demand must never revive a note with negative evidence.
- **Counters corrected after the first full run.** The demand-reactivation and wrong-credit
  counters had counted the demand list before `observe` applied its rules. They were
  corrected, and the experiment rerun with the same seeds; the other numbers are identical
  (`report_first_run.md` kept).

### 5. Liveness: check a rule against the code it describes / 存活检查

`scripts/liveness_check.py`, `runs/liveness`, 25 active learned notes. A note's *anchors* are
the project names it mentions (functions, classes, constants, modules, file paths) and domain
terms found in the code ("half-up" in `ROUND_HALF_UP`). Python builtins are not anchors,
because they never disappear. The verdicts are:

- **drifted**: an anchor is missing from the code;
- **review**: a newer changelog entry names the note's names, terms or amounts;
- **alive**: neither of the above, and the note has anchors;
- **not checkable**: the note has no anchors at all.

Ground truth comes from the benchmark design.

| Version | Stale notes flagged | Valid notes wrongly flagged | Not checkable |
|---|---|---|---|
| 1.0.0 (all 25 valid) | – | 0 of 25 | 3 |
| 2.0.0 (half-even rounding, approval at 1000.00; both in CHANGELOG) | **5 of 5** (2 by code drift, 3 by the changelog) | 4 of 20 for review, 0 drifted | 3 |
| 1.0.0 with 3 APIs silently renamed, no changelog | **12 of 12** (code drift) | 0 of 13 | 3 |

- As positive evidence, "alive" never contradicted a valid rule (0 false "dead" on 1.0.0), and
  it covers 22 of 25 notes. It catches code drift and silent renames. The 4 valid notes sent for
  review on 2.0.0 rely on `round_money`, whose change the changelog does name. A person can
  confirm them in a minute.
- But **"alive" means the names exist, not that the rule holds.** The approval rule (C6) is
  "alive" on 1.0.0 only because it mentions `BillingError`. Its change on 2.0.0 was caught only
  because the changelog names the amount. The three "reject bool" rules mention only builtins,
  so they cannot be checked, and those are exactly the untested rules V1.1 lost. 存活检查能证明"它提到的东西还在"，不能证明"规则还成立"。
- Disclosed: the first run matched any word of 4+ letters in newer changelog entries and
  flagged 7 valid notes. Generic words caused 3 of those flags: "code", and the module name
  "money". The matching was changed after that run, and the first report is kept
  (`runs/liveness/report_first_run.md`).

### 6. Turn a verified rule into an executable check / 把规则变成检查

`scripts/rule_checks.py`, `runs/rule_checks`, one Actions run. The setup:

- **Checks:** deepseek-flash wrote `check(path, source)` for each of the 25 notes, from the
  note alone, with one prompt fixed before the run.
- **Ground truth:** the reference solutions of the 17 ledgerly 1.0.0 tasks follow every
  convention, and the naive solutions break each task's conventions.
- **Useful, fixed before the run:** a check is useful if it detects at least half of the
  labelled violations, with at most 1 false alarm in 17.
- **Sandbox:** the generated code ran in an isolated Python with an empty environment.

| | Count |
|---|---|
| Checks written / usable (ran without error) | 25 / 23; 2 declared not checkable (approval, idempotency: they need the module's context) |
| **Useful** (pre-stated scoring) | **1 of 25** (`round_money`: 71% detection, 0 false alarms) |
| Useful when scored against the note's primary convention only (added after the run) | 2 of 25 (adds an approval check: 100%, 1 false alarm) |
| Checks with 0 false alarms / of those detecting at least half | 13 / 1 |
| Checks detecting at least half / of those with 2+ false alarms (up to 9 of 17) | 6 / 5 |

- The trade-off is sharp. A precise check implements the letter of the note: "BillingError
  codes are snake_case" does not flag `raise ValueError`. A check that catches violations
  over-applies: it demands `idempotency_key` from `add_line`, which moves no money, or demands
  one exact form of the audit call.
- For the memory this cuts both ways. A narrow check gives false confidence. An over-broad
  check produces *false negative evidence* against code that follows the rule, which under
  three-state forgetting would archive correct rules. 生成的检查要么太窄（漏报），要么太宽（误报）；误报会变成冤枉正确规则的负面证据。
- One encouraging case, but only one: the three "reject bool" checks raise no false alarm,
  and two of them flag the only naive solution that accepts a bool (E02, not a labelled
  violation, n = 1). That is the kind of rule no test checks.
- Implication: a generated check must itself be validated before its verdicts count. The
  cheapest validation is the evidence that created the rule: the check should flag the attempt
  the reviewer rejected and pass the accepted diff. That is not tested here. Also not tested:
  whether a rule enforced by a check can leave the prompt.

### Failure attribution, step 1: validate a check against its own evidence / 失败归因第一步

Three evidence states only pay off if a failure can be pinned on the note that caused it.
The cheapest safeguard for a generated check: before its verdicts count, it must reproduce
the review that created its rule. It must flag the attempt the reviewer rejected, and pass
the accepted change.

`scripts/failure_attribution.py`, `runs/failure_attribution`, no model calls. Only the
accepted diff had been stored, so I rebuilt the rejected first attempt by replaying the
agent's recorded commands in a fresh workspace. All **14 of 14** replays reproduced
`final.diff` exactly. 13 of the 25 notes come from a task whose first attempt was rejected,
so they can be fully validated; 12 come from first-pass tasks and can only be validated
against the accepted version. Each check was scored on the 16 tasks other than its source
task.

| Validation | Result | Checks | Mean false-alarm rate on references | Useful | Share of flags on a really broken convention |
|---|---|---|---|---|---|
| full (rejected and accepted) | pass | 4 | 19% | 1 | 52% |
| full | fail | 7 | 20% | 1 | 35% |
| accepted version only | pass | 10 | 1% | 0 | 29% |
| accepted version only | fail | 2 | 16% | 0 | 17% |

- **By the rule fixed before the run, validation is not a useful filter.** Checks that pass have
  the same false-alarm rate as checks that fail (19% vs 20%). And validation **rejected the one
  check that had been useful** (rounding, r1).
- **Why it rejected that check, and why it matters:** the agent's real mistake in E01 was not
  rounding at all (`return weighted_total / total_quantity`). The check looks for the wrong
  rounding call (`round()`, bare `quantize()`), which is what the benchmark's hand-written naive
  solutions do. A generated check catches a wrong call much more easily than a missing one, and
  real agent mistakes are often omissions. The benchmark's naive solutions overstate what
  generated checks can catch. 真实的错误常常是"漏了"，生成的检查擅长抓"用错了"；作者写的朴素解高估了检查的能力。
- **Validation against the accepted version alone selects narrow checks.** They pass everything
  (1% false alarms) and detect almost nothing (0 useful). That gives false confidence.
- **Even the checks that pass full validation attribute only about half of their flags to a
  solution that really breaks the convention (52%).** Used as negative evidence under three
  evidence states, roughly every other flag would blame a correct rule.
- Conclusion: generated checks are not yet a reliable source of failure attribution, even when
  validated against the rule's own evidence. In this project, the reliable attribution signal is
  the reviewer's or the test's own statement of which convention failed. Simulated reviews here
  name it explicitly; real reviews often do not (`REAL_HISTORY.md`). The next step would be to
  attribute a failure to the note whose evidence quote matches the review comment that names it.
  That is not tested here.
- Limits: 25 checks, 11 of them fully validated; one prompt; replay reproduces the recorded
  commands, not the agent's reasoning.

## What this supports / 结论边界

- Supported: memory of review-only knowledge helps a lot (+36 pp over no memory,
  review-only tasks 0% → 56%); scope prevents leakage; outdated thresholds are
  handled at least as well as without memory; Attest is not worse than the two
  published designs, with a smaller and cheaper prompt and immunity to the poison.
- Retrieval: better recall from embeddings did not translate into better coding results; lexical retrieval is kept.
- Context: under a 6k-token budget the context manager kept the session's review rule (2 of 3 S05 runs passed, 0 C6 failures) where a sliding window (0/3) and a plain summary (1/3) lost it; full history passes 3/3 at four times the tokens. Exploratory, one scenario, tuned after seeing results.
- Forgetting: 200 one-off notes cut held-out pass@1 from 70% to 42%; no forgetting policy repaired it; uniform decay wrongly archived the approval rule (9 of 9 later C6 runs violated it), type-aware decay did not. Exploratory.
- Pollution: trust-tiered admission brought held-out pass@1 under pollution from 36% back to 67% (76% with type-aware forgetting; clean memory 70%), with 0 approval violations in the combined arm. Exploratory; the separating signal exists by construction.
- Forgetting V2 (exploratory): treating "no evidence" as dormant rather than archived, and archiving only on negative evidence, removed every wrongly archived useful rule and made aggressive decay safe (71% needed rules injected, 44 injectable notes) in a simulation whose failure attribution is perfect by construction. Liveness against code caught every stale and renamed rule; one-prompt generated checks were useful for 1 of 25 rules, and validating them against the review that created each rule did not filter out bad checks (it rejected the useful one: the agent's real mistake was an omission the check did not look for). Rules no test or review names stay out of reach of every signal.
- Value feedback (offline): when adoption counts as contribution, one-off notes become permanent (34 under 30% adoption noise). Reinforcing only verified use removes that, but V1.1 also wrongly archived more correct rules (4 → 10–11 of 52), mostly rules no test checks. V1 stays the default and V1.1 is an option. The hard part is reliable evidence of value, not the decay rate.
- Not supported: that the write gate is free. Here it cost held-out passes; its value
  is protection (poison) and provenance, which the held-out pass rate does not reward.
- Limits: one model, one synthetic benchmark designed by the author, simulated
  review comments, 11 held-out tasks × 3 repetitions; real review history shows no
  recall advantage (`REAL_HISTORY.md`).
