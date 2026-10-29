# Preregistration / 预注册

> **Status: DRAFT.** This file is frozen by the commit that removes this line,
> after the no-memory pilot and before any memory condition is run. The commit
> hash and time of that commit are the evidence that the tasks, hypotheses and
> analysis were fixed before results with memory existed. Any later change is
> listed under *Deviations*.
>
> **状态：草案。** 无记忆基线跑完、任何有记忆的实验开始之前，删除本段的那次提交即为冻结。
> 该提交的哈希和时间证明：任务、假设和分析方法都在看到有记忆的结果之前就已确定。之后的任何修改都列在"偏差"一节。

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
| Tasks | `benchmark/` at the freeze commit: 6 experience (E), 10 held-out (H), 3 control (B, simkit), 4 stale (S, ledgerly 2.0.0) |
| Conditions | `no_memory`, `reasoningbank`, `ace`, `attest`, and two Attest ablations: `attest_no_gate` (write gate off) and `attest_no_scope` (repository scope and version warnings off). Same prompt; only the notes section differs |
| Repetitions | 3 per condition, each starting from an empty memory store |

**Protocol** (identical for every condition and repetition, `attest/experiment.py`):

1. *learn* — E01–E06 in order; memory may be written.
2. *heldout* — H01–H10; memory frozen (read-only).
3. *control* — B01–B03; memory frozen.
4. *stale* — S01–S04 in order; memory may be updated.

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
| `runs/pilot4_nomem` (held-out only) | **4/10** | Still in range. Discoverable C1–C4 satisfied in 20/21 first-attempt checks, review-only C5–C6 in 0/7; every failure was fixed after one review | None. Benchmark frozen as is |

**Write-path check.** Before freezing, the no-memory trajectories of E01–E06
from pilot 3 were fed through each memory system's `learn()` step with the real
model (`scripts/distill_check.py`); no agent ran with memory. Check 1
(`runs/distill_check1`) found notes describing code that existed only in an
earlier task's unmerged diff. The shared experience packet now says the diff is
not kept; this applies to all three systems equally. Check 2
(`runs/distill_check2`) no longer shows the problem. A third gate condition was
then added to Attest before the freeze (decision D17): every note must point to
the added line of the verified diff that applies it. Check 3
(`runs/distill_check3`) shows what this costs.

写入环节检查：冻结前，把第三次基线中 E01–E06 的无记忆轨迹交给三种记忆系统的学习步骤（真实模型），
没有任何 Agent 带记忆运行。第一次检查发现有经验描述了只存在于未合并改动中的代码；修复方式是在三种
系统共用的输入中说明"改动不会保留"，第二次检查确认问题消失。

## 4. Hypotheses / 假设

| | Hypothesis | Supported if |
|---|---|---|
| H1 | Attest improves held-out tasks | pass@1 on H: `attest` > `no_memory` (pooled over 3 repetitions) |
| H2 | Attest does not leak across repositories | on B, `attest` shows 0 ledgerly notes and its pass@1 ≥ `no_memory` |
| H3 | Outdated experience does not make Attest worse than having none | pass@1 on S: `attest` ≥ `no_memory`. Mechanism check (reported, not a hypothesis): every note cited in an S task that failed a related review check ends S04 as suspect, retired or superseded |
| H4 | Attest is at least as good as published designs on H, with fewer regressions | pass@1 on H: `attest` ≥ `reasoningbank` and ≥ `ace`; number of H/B regressions: `attest` ≤ each baseline |
| H5 | Scope is what prevents leakage | on B, `attest_no_scope` shows ledgerly notes (> 0) while `attest` shows none, and pass@1 on B: `attest` ≥ `attest_no_scope` |
| H6 | The write gate does not cost held-out performance | pass@1 on H: `attest` ≥ `attest_no_gate`, and H/B regressions: `attest` ≤ `attest_no_gate` |

Exploratory, no prediction: steps and cost per task; which conventions are learned; whether baselines leak ledgerly habits into simkit; how many notes each Attest variant stores and how many candidates the gate rejects.

## 4b. Exploratory follow-ups (not hypotheses) / 探索性研究（不属于假设）

Run after the main experiment and reported separately: (1) **poison**, a wrong
review comment added to E04 and E06; is it learned, shown and applied on
held-out tasks; (2) **scale**, 300 notes from twenty other repositories in
memory before learning; (3) a case study on review comments from a real
open-source repository, used by a real agent through an MCP server. No
decision rule is fixed for these.

## 5. Measures and analysis / 指标与分析

All numbers are computed by `attest/analysis.py` from `runs/<experiment>/**/result.json`.

- **Primary:** pass@1 = first attempt passes public and hidden tests.
- **Secondary:** pass@2 (after one simulated review), steps, estimated cost, notes shown and cited.
- **Regression:** a task whose pass@1 under a memory condition is lower than under `no_memory` (all repetitions pooled). Every regression is listed, not only counted.
- **Contamination:** notes learned on ledgerly that are shown on simkit tasks.
- **Paired comparison:** per held-out task, pass@1 under each memory condition minus no memory (repetitions averaged), with wins / losses / ties and a bootstrap 95% interval over tasks.
- **Tier split:** pass@1, steps and tokens on held-out tasks that need review-only knowledge (C5–C6) versus tasks that do not.
- **Behavioural attribution:** whether a note about a convention was shown or cited, against whether the first attempt actually satisfied that convention (hidden test), instead of trusting the agent's own citation.
- **Convention hit rate:** for each convention, the share of first attempts that satisfy it, reported separately for discoverable (C1–C4) and review-only (C5–C6) conventions. Exploratory.
- **Spread:** min and max pass@1 across the 3 repetitions is reported next to every pooled rate.
- With 10 held-out tasks × 3 repetitions the sample is still small. Results are reported as counts and per-task tables; no significance tests are claimed.

## 6. Exclusions / 排除规则

- A run whose commands or outputs touch benchmark files (`hidden_test`, `benchmark/tasks`, reference solutions) is **excluded and listed**.
- A run that crashes, hits a limit or produces no submission counts as a **failure**, not an exclusion.
- No other runs are removed. Failed repetitions are not re-run.

## 7. Threats to validity / 局限

- The author designed the conventions and tasks. Mitigated by held-out tasks, a control repository with opposite conventions, this preregistration and full regression lists — not eliminated.
- Review comments are simulated from hidden-test docstrings, not written by people.
- Baselines are simplified reproductions (lexical retrieval; no official code); they receive the same verified outcome as Attest, which favours them.
- One model, one small benchmark; results may not transfer to larger repositories or stronger models.

## 8. Deviations / 偏差记录

*(none yet)*
