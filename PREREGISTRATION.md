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
| Tasks | `benchmark/` at the freeze commit: 6 experience (E), 6 held-out (H), 3 control (B, simkit), 4 stale (S, ledgerly 2.0.0) |
| Conditions | `no_memory`, `reasoningbank`, `ace`, `attest` (same prompt; only the notes section differs) |
| Repetitions | 3 per condition, each starting from an empty memory store |

**Protocol** (identical for every condition and repetition, `attest/experiment.py`):

1. *learn* — E01–E06 in order; memory may be written.
2. *heldout* — H01–H06; memory frozen (read-only).
3. *control* — B01–B03; memory frozen.
4. *stale* — S01–S03 in order; memory may be updated.

## 3. Pilot disclosure / 基线校准说明

Before freezing, every task was run **without memory only** (`runs/pilot_nomem`)
to check difficulty. The pilot is used for exactly one decision: whether
held-out tasks leave room for improvement (no-memory pass@1 on H clearly below
100%). If tasks were changed because of the pilot, the changes are listed here:

- *(to be filled in after the pilot)*

## 4. Hypotheses / 假设

| | Hypothesis | Supported if |
|---|---|---|
| H1 | Attest improves held-out tasks | pass@1 on H: `attest` > `no_memory` (pooled over 3 repetitions) |
| H2 | Attest does not leak across repositories | on B, `attest` shows 0 ledgerly notes and its pass@1 ≥ `no_memory` |
| H3 | Outdated experience does not make Attest worse than having none | pass@1 on S: `attest` ≥ `no_memory`. Mechanism check (reported, not a hypothesis): every note cited in an S task that failed a related review check ends S04 as suspect, retired or superseded |
| H4 | Attest is at least as good as published designs on H, with fewer regressions | pass@1 on H: `attest` ≥ `reasoningbank` and ≥ `ace`; number of H/B regressions: `attest` ≤ each baseline |

Exploratory, no prediction: steps and cost per task; which conventions are learned; whether baselines leak ledgerly habits into simkit.

## 5. Measures and analysis / 指标与分析

All numbers are computed by `attest/analysis.py` from `runs/<experiment>/**/result.json`.

- **Primary:** pass@1 = first attempt passes public and hidden tests.
- **Secondary:** pass@2 (after one simulated review), steps, estimated cost, notes shown and cited.
- **Regression:** a task whose pass@1 under a memory condition is lower than under `no_memory` (all repetitions pooled). Every regression is listed, not only counted.
- **Contamination:** notes learned on ledgerly that are shown on simkit tasks.
- **Spread:** min and max pass@1 across the 3 repetitions is reported next to every pooled rate.
- With 6 held-out tasks × 3 repetitions the sample is small. Results are reported as counts and per-task tables; no significance tests are claimed.

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
