# Preregistration / 预注册

> **Status: FROZEN** on 2026-10-30, by the commit that replaced the draft notice with
> this line (tag `prereg-frozen`), after the no-memory pilots, the independent audit and
> its two re-checks, and before any memory condition was run. Any later change is
> listed under *Deviations*.
>
> **状态：已冻结**（2026-10-30，标签 `prereg-frozen`）。在无记忆基线、独立审计及两次复核之后、任何有记忆的实验运行之前冻结。之后的任何修改都列在"偏差"一节。

## 1. Question / 研究问题

Does experience that is **verified, scoped to its repository and version, and
retractable** (Attest) help a coding agent on tasks it has never seen, without
leaking into other repositories, and does it recover when the experience goes
out of date — compared with no memory and with two published memory designs?

## 2. Setup / 实验设置

| | |
|---|---|
| Agent | mini-swe-agent 2.4.6 `DefaultAgent`, unmodified; prompt `attest/config/agent.yaml` |
| Model | `deepseek/deepseek-flash`, thinking disabled, temperature 0 |
| Limits | 30 steps and 600 s per attempt; at most 2 attempts per task (2nd after simulated review) |
| Tasks | `benchmark/` at the freeze commit: 6 experience (E), 11 held-out (H), 3 control (B, simkit), 5 stale (S, ledgerly 2.0.0) |
| Conditions | `no_memory`, `reasoningbank`, `ace`, `attest`, and two Attest ablations: `attest_no_gate` (write gate off) and `attest_no_scope` (repository scope and version warnings off). Same prompt; only the notes section differs |
| Repetitions | 3 per condition, each starting from an empty memory store |

**Protocol** (identical for every condition and repetition, `attest/experiment.py`):

1. *learn* — E01–E06 in order; memory may be written.
2. *heldout* — H01–H11; memory frozen (read-only).
3. *control* — B01–B03; memory frozen.
4. *stale* — S01–S05 in order; memory may be updated.

## 3. Pilot disclosure / 基线校准说明

Before freezing, tasks were run **without memory only** to check difficulty.
Pilots are used for exactly one decision: whether held-out tasks leave room for
improvement (no-memory pass@1 on H clearly below 100%). No memory condition was
run before the freeze. Changes made because of the pilots:

| Pilot | No-memory pass@1 on H | What it showed | Change before the next pilot |
|---|---|---|---|
| `runs/pilot_nomem` | 5/6 | The 9-module repository was small enough to read whole; the agent copied conventions from neighbouring code | Added six legacy modules that predate the conventions; moved E03–E05 and H01–H04 into them |
| `runs/pilot2_nomem` | 5/6 | The agent searched for conventions (`grep -rn round_money`) rather than copying legacy code: conventions visible anywhere in the code are discovered | Added review-only conventions C5 (idempotency) and C6 (approval threshold) to E04, E06, H04, H06; added stale task S04 |
| `runs/pilot3_nomem` | **3/6** | Target reached. Discoverable conventions C1–C4 satisfied in 23/27 first-attempt checks; review-only C5–C6 in 0/7. H06 failed even after review because the agent read "must accept a keyword-only `idempotency_key`" as *required* | Reworded the C5 review comment to "optional keyword-only `idempotency_key=None`" (affects attempt 2 only). Added held-out tasks H07–H10 (6 → 10) to reduce the small-sample problem |
| `runs/pilot4_nomem` (held-out only) | **4/10** | Still in range. Discoverable C1–C4 satisfied in 20/21 first-attempt checks, review-only C5–C6 in 0/7; every failure was fixed after one review | None at the time. Then an independent audit (below) led to the changes in the next row |
| `runs/pilot5_nomem` (all 25 tasks, after the audit) | **4/11** | In range. Discoverable C1–C4 satisfied in 39/43 first-attempt checks, review-only C5–C6 in **0/14**; every task passed after one review (no task impossible); no crashes, no leaks. Stale: S01–S03 pass, S04–S05 fail C6 without memory; control 3/3 | Only hidden-test and analysis changes after the independent re-check (below), none visible to the agent on its first attempt, so no further pilot. Benchmark frozen as is |

**Independent audit before the freeze** (`benchmark/AUDIT.md`). A separate agent
that had not built the benchmark audited it after pilot 4 (validator, regeneration,
19 deliberately broken solutions, fairness and leakage review). It found one
blocker and six majors, all fixed before pilot 5, without running any memory
condition: (B1) the C6 checks are split into "blocks unapproved" and "allows at or
below the threshold or approved", so the business risks *unauthorised operation*
and *legitimate operation blocked* are measured separately and a stale 500.00
threshold counts as the latter; (M1) the C6 review comment says `approved_by` is
optional and amounts at or below the threshold need no approval, as its source
policy does; (M2) audit entries are found by entity id, not by event name; (M3)
S01–S03 cannot detect stale memory (v2's `round_money` already rounds
half-even), so a second threshold task **S05** was added and H3 is also reported
for S04–S05 alone; (M4) boundary amounts vary per task and held-out tasks are
tagged near/far transfer; (M5) S04's issue states the rule its C2 test relied on;
(M6) this disclosure. Nine of the ten minor findings were fixed before pilot 5
(wording of C4/C5, issue texts, H05 drops a C3 check that could not discriminate);
minor 9 (C6 tests coupled to C5 behaviour) was completed after the re-check. The
planned end-to-end task **H11** (a support refund request needing C1–C6) was
revised per the audit and added.

**Independent re-check after the fixes** (`benchmark/AUDIT.md`, "Re-check after
fixes"). A second independent agent verified the fixes (validator, regeneration
diff, 33 broken variants). No blocker; one major and nine minors, fixed before the
freeze without any memory run: (R1) a condition that never learned C6 is no longer
counted as "outdated policy applied" (an S-task *allows* failure counts as outdated
only if the same attempt blocked the unapproved amount); (r1) C6 tests clear the
audit log before every call, and the C5 tests of E04, H04 and H07 check that
keyless callers keep working, so a key-less de-duplication bug shows up as C5, not
as a blocked legitimate operation; (r2) the H04 and S04 *blocks* tests check that
nothing was credited; (r3) H11's half-up check uses 1.005, which also catches a
detour through `float`; (r4) H08 is tagged near transfer (mirrors E06); (r5)
`validation.json` refreshed (25/25); (r6–r7) this disclosure and wording below;
(r8) comparison and arithmetic operators count as tokens in evidence matching.
Not changed (r9, optional): S04 and S05 do not test exactly 1000.00, so a
`>=` threshold is not detected; the v2 comment names the CHANGELOG, not FIN-2026-09.

**Write-path checks after the gate changes.** `runs/distill_check5` (after D21)
reproduced check 4 exactly (7 notes, 2 rejected for the source quote).
`runs/distill_check6` (after D25) rejected two sound E06 notes whose multi-line
snippets also contained punctuation-only lines (`*,`, `)`) and an unchanged
docstring line; the old verbatim gate (D17) would have rejected them too. Fixed
by D27 (punctuation-only lines skipped; unchanged context lines may surround but
never be the evidence; every line must still be a real line of the diff).
`runs/distill_check7` checked D27: 7 notes, one genuine rejection (a source quote not
in the review comments). An independent re-check of D27 (`benchmark/AUDIT.md`) then
found one major: an unchanged context line such as the existing `audit.clear()` in
`conftest.py`, next to a trivial change, could carry a rule nobody applied. Fixed by
D28 (above, 5b); `runs/distill_check8` is the check on the final gate.

**Write-path check.** Before freezing, the no-memory trajectories of E01–E06
from pilot 3 were fed through each memory system's `learn()` step with the real
model (`scripts/distill_check.py`); no agent ran with memory. Check 1
(`runs/distill_check1`) found notes describing code that existed only in an
earlier task's unmerged diff. The shared experience packet now says the diff is
not kept; this applies to all three systems equally. Check 2
(`runs/distill_check2`) no longer shows the problem. A third gate condition was
then added to Attest before the freeze (decision D17): every note must point to
the added line of the verified diff that applies it. Check 3
(`runs/distill_check3`) exposed a format bug in the new check (the model copies the
diff's `+` markers into its snippet); after the fix, check 4 (`runs/distill_check4`)
shows what the stricter gate costs.

写入环节检查：冻结前，把第三次基线中 E01–E06 的无记忆轨迹交给三种记忆系统的学习步骤（真实模型），
没有任何 Agent 带记忆运行。第一次检查发现有经验描述了只存在于未合并改动中的代码；修复方式是在三种
系统共用的输入中说明"改动不会保留"，第二次检查确认问题消失。

## 4. Hypotheses / 假设

| | Hypothesis | Type | Supported if |
|---|---|---|---|
| H1 | Attest improves held-out tasks | superiority | paired difference of pass@1 on H, `attest` − `no_memory`: 95% CI lower bound **> 0** |
| H2 | Attest does not leak across repositories | exact count | on B, `attest` shows **0** ledgerly notes; pass@1 on B vs `no_memory` reported descriptively (3 tasks are too few for an interval) |
| H3 | Outdated experience does not make Attest worse than having none | non-inferiority | `attest` − `no_memory` on S: 95% CI lower bound **> −δ**, both over S01–S05 **and** over the threshold tasks S04–S05 (S01–S03 are no-false-recall checks, audit M3). Mechanism check (reported, not a hypothesis): every note cited in an S task that failed a related review check ends the stale phase as suspect, retired or superseded |
| H4 | Attest is not worse than published designs | non-inferiority | `attest` − `reasoningbank` **and** `attest` − `ace` on H, each: 95% CI lower bound **> −δ**. Regressions (defined in section 5) are reported separately per condition and are not part of the verdict |
| H5 | Scope is what prevents leakage | exact counts | on B, `attest_no_scope` shows ledgerly notes (> 0) while `attest` shows none; pass@1 on B vs `attest_no_scope` reported descriptively |
| H6 | The write gate does not cost held-out performance | non-inferiority | `attest` − `attest_no_gate` on H: 95% CI lower bound **> −δ**. `attest_no_gate` is the same system with only the write gate switched off, so the comparison isolates the gate. Regressions reported separately |

**Decision rules / 判定规则.** Fixed before any memory condition is run.

- *Unit of analysis:* the task. For each task, pass@1 is averaged over the 3 repetitions, then the paired difference to the comparison condition is taken; the bootstrap (10,000 resamples, seed 0) resamples tasks, never the 33 individual held-out runs (`analysis.compare`).
- *Superiority (H1):* supported if the 95% interval lies above 0. If the estimate is positive but the interval reaches 0: **direction consistent, insufficient evidence**. If the estimate is ≤ 0: not supported.
- *Non-inferiority (H3, H4, H6):* margin **δ = 10 percentage points**, about one of the 11 held-out tasks lost entirely (1/11 ≈ 9 pp), the smallest difference this task set can resolve. Supported if the 95% interval lies above −δ. If the interval crosses −δ while the estimate is above it: **direction consistent, insufficient evidence**. If the estimate is ≤ −δ: not supported.
- *Combining two comparisons* (H3: all stale tasks and S04–S05; H4: vs ReasoningBank and vs ACE): supported only if both are supported; not supported if either is not supported; otherwise direction consistent, insufficient evidence (`analysis._all`).
- Where an interval crosses a decision boundary while the estimate lies on the favourable side, the result is reported as "direction consistent, insufficient evidence", never as success; it is "not supported" only when the estimate itself is on the wrong side of the boundary. With 11 held-out tasks (5 stale, 2 of them threshold tasks) intervals will be wide; this is expected and stated, not a reason to change δ after seeing results.
- 判定：H1 为优效性（区间下界 > 0）；H3、H4、H6 为非劣效性（区间下界 > −δ，δ = 10 个百分点，约等于 11 个留出任务中完全输掉 1 个）；区间跨过边界时统一写"方向一致，但证据不足"；以任务为重抽样单位。

Exploratory, no prediction: steps and cost per task; which conventions are learned; whether baselines leak ledgerly habits into simkit; how many notes each Attest variant stores and how many candidates the gate rejects.

## 4b. Exploratory follow-ups (not hypotheses) / 探索性研究（不属于假设）

Run after the main experiment and reported separately: (1) **poison**, a wrong
review comment added to E04 and E06; is it learned, shown and applied on
held-out tasks; (2) **scale**, 300 notes from twenty other repositories in
memory before learning; (3) a case study on review comments from a real
open-source repository, used by a real agent through an MCP server. No
decision rule is fixed for these.

## 4c. Retrieval ablation (exploratory, reported separately) / 检索机制消融（探索性，单独报告）

**Question / 问题.** How much of each system's result is due to *what* it
remembers and how much to *how* it retrieves? The ReasoningBank-style baseline
ranks lexically, while the original method uses embeddings; this ablation also
closes that gap. 记忆内容与检索方式各贡献多少；同时补上 ReasoningBank 简化实现与原方法在检索方式上的差异。

**Arms / 条件.** Attest + lexical, Attest + embedding, ReasoningBank-style +
lexical, ReasoningBank-style + embedding (`attest`, `attest_emb`,
`reasoningbank`, `reasoningbank_emb`).

**Held constant / 控制变量.** Memory content: no arm learns its own experience;
every arm starts from the main experiment's memory snapshot after the learning
phase (`runs/main/<system>/r<rep>/memory/after_learn.json`, built with lexical
retrieval), so lexical and embedding arms of a system see identical notes.
Candidate set (status; repository scope for Attest), number of notes shown (6),
prompt, agent, model and settings, tasks, phase order (held-out → control →
stale), repetitions (3). Only the ranking function differs. The write path
(distillation, gate, de-duplication) is unchanged in both arms.

**Embedding model / 嵌入模型.** `BAAI/bge-small-en-v1.5` (fastembed 0.9.1,
onnxruntime 1.31.1, ONNX on CPU, revision `aa8f8b06…`), cosine similarity, ties
broken by id as in the lexical ranker. Local, so no API cost and no network at
query time.

**No leakage / 防泄漏.** The retrieval query is the task title and issue text
only, never review comments or fixes of the task being solved. Memory comes
only from experience tasks (checked automatically: a note learned from a query
task aborts the evaluation).

**Measures / 指标.**

1. *Retrieval quality (offline, same memory, no agent).* For every held-out,
   control and stale task as a query: Recall@5, Precision@5 (over the notes
   returned, at most 5) and MRR over the full ranking. A note is *relevant* to
   a task if it states a convention the task's hidden tests check
   (`task.json → conventions`). Each note is labelled once, by
   `deepseek-v4-pro`, without seeing the queries, the system or the retriever;
   the labels are committed (`labels.json`). Relevance is topical: an outdated
   note about the right rule still counts as relevant (whether it is correct is
   what the stale tasks measure). Queries with no relevant note are left out of
   recall and MRR; for control tasks we report irrelevant notes in the top 5.
   Also: ranking latency (median, p95, warm model).
2. *Effect on the work (end to end).* First-attempt pass rate on held-out,
   control and stale tasks; business-risk check failure rates (section 5);
   tokens per task; retrieval latency in the agent loop.

**Analysis / 分析.** Within each system, embedding vs lexical: paired per query
(retrieval metrics) or per task averaged over repetitions (pass@1), mean
difference with a bootstrap 95% interval (10,000 resamples, seed 0) and
better/worse/same counts. Two-sided: we do not assume embedding retrieval is
better. A gain in retrieval metrics is not taken as a gain in coding quality;
both are reported side by side, and an improvement is attributed to retrieval
only if it shows in the end-to-end measures. 不预设语义检索更好，也不把检索指标的提升等同于编码质量的提升。

**Run / 运行.** After the main experiment:
`python -m attest ablation --source main --name retrieval_ablation`
(`--part quality` for the offline part only).

## 5. Measures and analysis / 指标与分析

All numbers are computed by `attest/analysis.py` from `runs/<experiment>/**/result.json`.

- **Primary:** pass@1 = first attempt passes public and hidden tests.
- **Secondary:** pass@2 (after one simulated review), steps, estimated cost, notes shown and cited.
- **Regression:** a held-out or control task whose pass@1 under a memory condition (3 repetitions pooled) is lower than under `no_memory`. Every regression is listed with its task and rates, not only counted; regression counts are reported per condition next to H4 and H6 but do not decide them.
- **Contamination:** notes learned on ledgerly that are shown on simkit tasks.
- **Paired comparison:** per held-out task, pass@1 under each memory condition minus no memory (repetitions averaged), with wins / losses / ties and a bootstrap 95% interval over tasks.
- **Tier split:** pass@1, steps and tokens on held-out tasks that need review-only knowledge (C5–C6) versus tasks that do not.
- **Behavioural attribution:** whether a note about a convention was shown or cited, against whether the first attempt actually satisfied that convention (hidden test), instead of trusting the agent's own citation.
- **Memory funnel:** for every convention a held-out or stale task needs, how far a note about it got: not in memory → filtered out (scope, version, status, with the reason) → not ranked into the top 10 (retrieved) → ranked but not among the 6 injected → injected; and whether the first attempt then satisfied the convention. Separates "never learned", "learned but filtered", "not found", "cut", and "injected but not followed". Notes are matched to conventions by the same regular expressions for every system (approximate).
- **Convention hit rate:** for each convention, the share of first attempts that satisfy it, reported separately for discoverable (C1–C4) and review-only (C5–C6) conventions. Exploratory.
- **Business risks** (`SCENARIO.md`, `analysis.business_risks`): per condition, the share of first-attempt checks failed for each risk, mapped from hidden-test names: duplicate money operation (C5), unauthorised operation (C6 *blocks*), legitimate operation blocked (C6 *allows*), amount-precision violation (C1), unaudited money movement (C4), outdated policy applied (S-group rounding-policy tests and C6 *allows* failures of attempts that did block the unapproved amount), rule in the wrong repository (B-group K tests). Exploratory; reported for held-out, stale and control tasks.
- **Spread:** min and max pass@1 across the 3 repetitions is reported next to every pooled rate.
- With 11 held-out tasks × 3 repetitions the sample is still small. Verdicts follow the decision rules in section 4 (bootstrap intervals over tasks); no p-values are computed. Results are also reported as counts and per-task tables.

## 5b. Attest design changes before the freeze / 冻结前对 Attest 的设计修改

Made on 10/30, before any main-experiment run, and disclosed here because two of
them were informed by data (DECISIONS D21):

1. **Lifecycle and versions.** Every note records its source references
   (e.g. `FIN-2026-03`, `INC-204`, extracted from the quoted review comment), the
   files it was observed in, the version range it is valid for
   (`valid_from`..`valid_until`), its supersede relation and its last
   verification. A rule that *changed* in a newer version keeps the old note
   valid for older versions (`valid_until`) instead of only warning; a rule
   shown to be *wrong* is invalid everywhere.
2. **Typed evidence.** The gate records source (verbatim quote), applied line
   (typed code / test / doc / config, added or removed) and verification
   separately, and an optional independent review (off in all preregistered
   runs). Matching of the applied line became line-based and tolerates format
   differences only (D25): every claimed line must match one changed line, as a
   verbatim substring of ≥ 10 characters after removing diff markers and
   normalising whitespace and case, or with all of its words (≥ 3) occurring in
   that line in the same order, so a claim may omit words but never add, replace
   or reorder them (no paraphrase); quotes are matched
   against the before and after text of the diff, so diff markers no longer break
   multi-line quotes. In multi-line snippets, punctuation-only lines are skipped and
   unchanged context lines may surround the evidence, but at least one line must be
   a changed line and every line a real line of the diff (D27). After an independent
   re-check of D27 (D28): the evidence line must pass on its own (3+ tokens or 10+
   characters); changed lines must be at least half of the snippet; context lines are
   accepted only in the same file and hunk as an evidence line; snippet lines must
   follow the diff's order; a line is skipped only if it has no token at all, and a
   line too short for the word rule must equal a diff line exactly and is never the
   evidence; only the first evidence line is recorded, always as the real diff line. Comparison and
   arithmetic operators count as tokens, so a swapped operator does not match; an
   omitted token (including `not`) is still tolerated, and the recorded evidence is
   always the real diff line, not the claim. **Informed by data:** the Flask retrospective
   (`runs/retro_flask`) showed 8 of 49 candidates rejected, at least 5 of them
   sound rules lost to brittle string matching (a changelog line quoted
   imprecisely, a rule applied by deleting code, quotes spanning diff markers).
   Flask is therefore **development data** for the gate from now on; a second
   repository not looked at before is used as the real-history test.
3. **Retrieval trace.** Every run records excluded notes with reasons, the
   10 retrieved and the 6 injected notes, and the approximate tokens of the memory
   block, for the funnel above. The prompt shown to the agent is unchanged except
   that Attest notes now name their source references and validity range.

The synthetic experience tasks only produce code diffs, so change 2 matters
mostly for real repositories; the poison check (a rule nobody applied is
rejected) is kept and tested.

## 6. Exclusions / 排除规则

- A run whose commands or outputs touch benchmark files (`hidden_test`, `benchmark/tasks`, reference solutions) is **excluded and listed**.
- A run that crashes, hits a limit or produces no submission counts as a **failure**, not an exclusion.
- No other runs are removed. Failed repetitions are not re-run.

## 7. Threats to validity / 局限

- The author designed the conventions and tasks. Mitigated by held-out tasks, a control repository with opposite conventions, this preregistration and full regression lists — not eliminated.
- Review comments are simulated from hidden-test docstrings, not written by people.
- Baselines are simplified reproductions (lexical retrieval; no official code); they receive the same verified outcome as Attest, which favours them.
- One model, one small benchmark; results may not transfer to larger repositories or stronger models.
- Three held-out tasks (H06, H07, H11) closely mirror an experience task (same module and shape), so part of the held-out gain measures near transfer; held-out results are also reported split into near and far transfer (exploratory, audit M4).
- The stale group has two tasks that can detect outdated memory (S04, S05); H3 rests mostly on them.
- Attest's write gate checks that a rule's evidence line is a real, verified change, not that the line is *about* the rule (relevance is not verified). For example, a rounding note was confirmed by a task whose evidence line was `at = ensure_utc(at)` (`runs/distill_check7`).

## 8. Deviations / 偏差记录

*(none yet)*
