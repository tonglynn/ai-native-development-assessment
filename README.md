# Attest: verified, scoped, retractable memory for coding agents

**English** · [中文说明](#中文说明)

Coding agents forget what code review taught them, and the memory systems that try
to fix this store whatever the agent concluded, apply it everywhere and never take
it back. **Attest** keeps only experience that a verified change actually applied,
ties each note to the repository and version it came from, and demotes, supersedes
or retracts it when it stops being true. A preregistered experiment measures what
that buys and what it costs.

## Results at a glance

Preregistered (frozen at commit `cf5d879` before any memory run), 6 conditions ×
3 repetitions × 25 tasks = 450 agent runs, `deepseek-flash`, 0 runs excluded,
USD 0.85. Full write-up: [`RESULTS.md`](RESULTS.md); interactive report:
[`report/index.html`](report/index.html).

| Condition | Held-out pass@1 | Stale (policy changed) | Control (other repo) |
|---|---|---|---|
| no memory | 33% | 60% | 100% |
| ReasoningBank-style | 58% | 80% | 100% |
| ACE-style | 61% | 93% | 100% |
| **Attest** | **70%** | 87% | 100% |
| Attest without write gate | 85% | 87% | 100% |
| Attest without scope | 67% | 93% | 100% |

| | Hypothesis (decision rule fixed in advance) | Result | Verdict |
|---|---|---|---|
| H1 | Attest beats no memory on unseen tasks (CI > 0) | +36 pp [+21, +52] | supported |
| H2 | No ledgerly notes leak into the other repository | 0 shown | supported |
| H3 | Outdated experience is not worse than none (non-inferiority, δ = 10 pp) | S04–S05 +67 pp [+33, +100] | supported |
| H4 | Not worse than ReasoningBank / ACE (non-inferiority) | +12 pp [−3, +27] / +9 pp [−3, +21] | supported |
| H5 | Scope is what prevents leakage | 0 vs 54 notes | supported |
| H6 | The write gate costs nothing on held-out tasks | **−15 pp [−27, −3]** | **not supported** |

Stress tests and risks (exploratory):

- **Poisoned review advice** ("clear the audit log after writing an entry"):
  Attest stored it 0 times; without the gate 9 times; ReasoningBank 12, ACE 10.
  ReasoningBank and ACE agents then cleared the audit log in 2 and 5 held-out runs.
  But the poisoned tasks failed verification in every condition, so Attest kept the
  poison out with its simplest rule (learn nothing from an unverified task). It also
  learned nothing else from those tasks: held-out pass@1 under poison was 36%, against
  67% without the gate. The finer evidence checks were not tested by this poison.
- **300 notes from other repositories** in memory: Attest 73% pass@1 with 31k
  prompt tokens per run and 0 foreign notes shown; ReasoningBank 42% / 46k; ACE 55% /
  157k (every note in every prompt). This tests scope and retrieval; there was no
  no-gate arm.
- **Business risks** on held-out, stale and control tasks, no memory → Attest:
  duplicate money operations 18/18 → 6/18, unauthorised operations 15/15 → 2/15,
  legitimate operations blocked 15/15 → 3/15. This is what memory buys, not the gate:
  without the gate the rates are equal or better (2/18, 2/15, 2/15).
- **Near and far transfer** (preregistered split, reported late): Attest vs no memory
  +58 pp on the 4 held-out tasks that mirror an experience task, +24 pp [+10, +43] on
  the other 7.

Later extensions (exploratory, `RESULTS.md`): a **context manager**, designed after seeing results, kept the
session's review rule under a 6k-token budget (S05 2 of 3, 0 approval violations;
sliding window 0/3, full history 3/3 at 4× the tokens; the plain-summary baseline was
broken and is not compared); **dynamic
forgetting** showed that 200 one-off notes cut held-out pass@1 from 70% to 42% and
that no forgetting policy repaired it with its default parameters, while uniform decay wrongly archived the
approval rule and type-aware decay did not. **Trust-tiered admission** (a detail seen once is
injected only in its own files), on a harder polluted stream where memory without tiers
scored 36%, brought held-out pass@1 to 67%, 76% together with type-aware
forgetting, with 0 approval violations (exploratory; the separating signal exists by
construction). **Forgetting V1.1** (offline): counting adoption as
contribution let 34 one-off notes become permanent; reinforcing only verified use removed
that, but V1.1 wrongly archived more correct rules (4 → 10–11 of 52), mostly rules no test
checks, so V1 stays the default. The hard part is reliable evidence of value, not the decay
rate.

What it does **not** show: on real review history Attest anticipated the fewest
convention comments (Saleor 1/25, against ReasoningBank 4/25 and ACE 8/25) ([`REAL_HISTORY.md`](REAL_HISTORY.md)); embedding retrieval finds
more relevant notes but did not improve coding results (retrieval ablation in
`RESULTS.md`).

## The problem

**Why it is a real problem.** Coding agents repeat mistakes a team has already paid
for, because the lessons live in code review and incident write-ups, not in the code.
Products now ship memory for this: GitHub Copilot Memory (memories with code
citations, re-checked before use; in an A/B test the coding agent's PR merge rate rose
from 83% to 90%), CodeRabbit Learnings (preferences from review comments, optionally
approved by an admin) and Qodo's auto best practices (rules mined from accepted
suggestions). Research on real repositories is less encouraging. In VibeMemBench,
11 of 12 pairings of existing memory systems and agents did not beat no memory.
MemDev-Bench finds that memory makes agents fail tasks they could otherwise solve,
because they reuse it without checking that it applies. What none of these publish
is a controlled measure of the governance questions: wrong advice, rules leaking to
the wrong place, rules that changed. That is the question here.

**The scenario: Ledgerly** (synthetic, [`SCENARIO.md`](SCENARIO.md)). A B2B SaaS
company is moving its billing from a monolith to modules, while finance policy keeps
changing. The lessons came from review, an incident review and finance decisions.
The main thread is: a problem happens → review or an incident review turns it into
experience → the agent learns it → reuses it on new work → corrects it when the policy
changes. The business flow the tasks exercise is a support-initiated refund or credit:

| Step | Requirement | Experience | Covered by the benchmark |
|---|---|---|---|
| 1 Receive the request | the amount the agent typed, the payment, who asked | C1 money precision | yes (H11 parses "49.99" to two-decimal `Decimal`) |
| 2 Check, deduplicate | a retried request must not refund twice | C5 idempotency (incident A, double refund) | yes (E04, H04, H06–H08, H10, H11) |
| 3 Approval | support refunds above a threshold need a second approver | C6 approval (policy B: 500.00, later 1000.00) | yes, including the change (S04, S05 on 2.0) |
| 4 Compute and move money | current rounding rule (half-up in 1.0, half-even in 2.0) | C1 rounding | partly: **no real payment provider is called** |
| 5 Update and audit | every money movement is recorded | C4 audit | yes |
| 6 Errors and retries | business failures vs system faults; retries | C2 errors, C5, C7 | partly: provider timeouts and retries only in the exploratory extension task X01 (`RESULTS.md`); **no partial failures or recovery** |

C1–C4 can be discovered in the code; C5 and C6 pass only through review. The incident
and the policy change are synthetic, not taken from a real company. Only H11 runs the
whole flow in one task; the other tasks each cover part of it.

**Two-layer study design.**

1. **Controlled experiment (done).** The Ledgerly benchmark, with experience,
   held-out, stale and control tasks, compares no memory, ReasoningBank-style and
   ACE-style memory, and Attest with ablations. Preregistered; results above.
2. **Real history (partly done).** A retrospective on real pull requests and review
   comments from Flask and Saleor ([`REAL_HISTORY.md`](REAL_HISTORY.md)): Attest
   showed no recall advantage there, because real reviewers rarely state rules and
   many missed comments are about process. Not done: an agent completing later tasks of
   a real repository with memory learned from its history (as in MemDev-Bench); that
   is the most important next step ([`ROADMAP.md`](ROADMAP.md)).

## How Attest works

```
task ──► recall ──► mini-swe-agent (unmodified) ──► hidden tests ──► review comments
           ▲                                              │
           │                                              ▼
     scope + version filter                      write gate (deterministic)
     (repository, valid_from..valid_until,        · task verified
      status) → rank → inject top 6               · source quote verbatim
           ▲                                       · applied line = a real changed line
           │                                              │
     append-only event log ◄── lifecycle: active · suspect · retired · superseded
     (JSONL or SQLite)          supersede keeps the old rule valid for older versions
```

- **Write gate** (`attest/memory/earned.py`, `evidence.py`): a note needs a verbatim
  source quote, a changed line of the verified diff that applies it (code, test, doc
  or config; added or removed) and a passing verification, recorded separately. Format
  differences are tolerated, paraphrase is not (D25, D28).
- **Scope and versions**: notes carry repository, files and a version range. When a
  rule changes in a newer version the old note stays valid for older versions
  (`valid_until`), so maintaining v1 still recalls the 500.00 rule.
- **Accounting**: a note cited by a task that fails a related check becomes suspect,
  then retired; a verified success clears it. People can retract notes; agents cannot.
- **Observability**: every run records excluded notes with reasons, retrieved vs
  injected notes and memory tokens, so the analysis can tell "never learned" from
  "filtered", "not ranked", "cut" and "injected but not followed".
- **Baselines** are simplified reproductions of ReasoningBank (append, retrieve
  top-k) and ACE (playbook with helpful/harmful counters), fed the same verified
  outcomes as Attest.
- **Reused, not rebuilt**: the agent is mini-swe-agent 2.4.6 unmodified; memory and
  review comments enter only through its prompt template.

## How it was evaluated

- 25 tasks: 6 experience tasks (memory is written), 11 held-out, 5 stale on
  ledgerly 2.0.0, 3 control on simkit. Review comments are simulated from the
  docstrings of failing hidden tests. Conventions come in two tiers: C1–C4 can be
  discovered in the code, C5 (idempotency) and C6 (approval threshold) only through
  review. Without memory, the review-only conventions were met in 0 of 14 first
  attempts.
- [`PREREGISTRATION.md`](PREREGISTRATION.md): hypotheses, decision rules (task-level
  paired bootstrap; superiority for H1, non-inferiority for H3, H4, H6), exclusions,
  every pilot and every change before the freeze.
- [`benchmark/AUDIT.md`](benchmark/AUDIT.md): an independent agent audited the task
  set, then re-checked the fixes and the final gate; blockers and majors were fixed
  before the freeze.
- Exploratory, reported separately: poison and scale stress tests, a retrieval
  ablation (lexical vs embedding), retrieval at 100–10,000 notes, and a
  retrospective on real pull requests judged by a different model.

## Reproduce

```bash
pip install -r requirements.txt
python -m pytest -q                         # offline tests, scripted model, no API calls
python scripts/validate_benchmark.py        # 25/25 tasks measure what they claim
python -m attest summary runs/main          # recompute the tables from committed results
python -m attest.report runs/main report/index.html

# new runs need DEEPSEEK_API_KEY (a GitHub secret; never in the repository)
python -m attest experiment --name main --reps 3 --parallel 6
python -m attest stress --kind poison --name stress_poison
python -m attest ablation --source main --name retrieval_ablation

# exploratory extensions, offline (no API key, deterministic)
python scripts/forgetting_sweep.py --out runs/forgetting_sweep
python scripts/forgetting_v11.py --out runs/forgetting_v11
python scripts/forgetting_v2.py --out runs/forgetting_v2
python scripts/liveness_check.py --out runs/liveness
python scripts/failure_attribution.py --out runs/failure_attribution
python scripts/rule_checks.py --out runs/rule_checks --evaluate-only
# exploratory extensions with agent runs (Actions commands: context_eval, forgetting_eval,
# admission_eval, rule_checks, verify_eval, x01_eval)
```

Long runs execute on GitHub Actions (`.github/workflows/experiment.yml`): push
`.github/run-request.json`, results are committed back to `runs/<name>/`.

Use Attest with a real agent through MCP (`attest/mcp_server.py`, demo in
[`docs/MCP_DEMO.md`](docs/MCP_DEMO.md)):
`claude mcp add attest -- python -m attest.mcp_server`. The server computes the diff
and runs the verification command itself; retraction is not exposed to agents.

## Limits

One model, one synthetic benchmark designed by the author, simulated review
comments, 11 held-out tasks × 3 repetitions. Three held-out tasks closely mirror an
experience task. The gate checks that the evidence line is a real verified change,
not that it is about the rule. On real review history most missed comments are about
process (rebase, backport), which a diff cannot show (see `PROCESS_MEMORY.md`).
Unsolved: **failure attribution**. Forgetting works best when a failure can be pinned on the
note that caused it, and this project has no reliable way to do that yet. Model-generated
checks were useful for 1 of 25 rules. Validating them against the review that created each
rule did not help: real agent mistakes are often omissions, which the checks miss, and even
validated checks were right about half the time (`RESULTS.md`, D33). Rules that no test or
review names stay out of reach of every feedback signal tried.

Sources for the industry and research context: [GitHub Copilot agentic memory](https://github.blog/2026-01-09-building-an-agentic-memory-system-for-github-copilot), [CodeRabbit Learnings](https://docs.coderabbit.ai/guides/learnings), [Qodo auto best practices](https://docs.qodo.ai/qodo-documentation/qodo-merge/pr-agent/core-abilities/auto_best_practices), [VibeMemBench](https://arxiv.org/abs/2609.23570), [MemDev-Bench](https://arxiv.org/abs/2610.27524v1).

## Repository map

| Path | What it is |
|---|---|
| `attest/` | Runner, verifier, analysis, report, CLI (`python -m attest`) |
| `attest/memory/` | Attest (`earned.py`, `evidence.py`), baselines, stores (JSONL, SQLite), retrieval (lexical, embedding) |
| `attest/mcp_server.py` | Attest as an MCP server for real coding agents |
| `benchmark/` | Repositories, 25 tasks, authoring script, validator output, audit |
| `runs/` | Every run: trajectories, diffs, `result.json`, memory event logs |
| `report/index.html` | Interactive report of the main experiment |
| `RESULTS.md`, `REAL_HISTORY.md` | Results |
| `PREREGISTRATION.md`, `DECISIONS.md`, `AI_LOG.md`, `INCIDENTS.md` | Method, decisions D1–D35, AI collaboration log, incidents |
| `SCENARIO.md`, `scenario/history/` | Business scenario (synthetic) |
| `ROADMAP.md`, `PROCESS_MEMORY.md` | Next steps (Attest 2.0), deliberately not added |

---

## 中文说明

编码 Agent 记不住代码评审教过它的东西；而现有的记忆方案往往是"Agent 总结了什么就存什么、到哪都用、从不收回"。**Attest** 只保留被验证通过的改动真正落实过的经验，每条经验绑定来源仓库和适用版本，规则失效时降级、替换或撤回。一个预注册实验衡量了它带来的收益和代价。

### 结果概览

预注册实验（任何记忆实验运行前在提交 `cf5d879` 冻结）：6 个条件 × 3 次重复 × 25 个任务，共 450 次运行，模型 `deepseek-flash`，无排除，费用约 0.85 美元。详见 [`RESULTS.md`](RESULTS.md) 与 [`report/index.html`](report/index.html)。

- **留出组首次通过率**：无记忆 33%，ReasoningBank 58%，ACE 61%，**Attest 70%**；关掉写入门槛 85%，关掉作用域 67%。
- **H1–H5 得到支持**：比无记忆高 36 个百分点（区间 [+21, +52]）；不泄漏到其他仓库；过期政策场景不比无记忆差；不差于两种已发表的设计；作用域是防泄漏的关键。
- **H6 不被支持**：写入门槛让留出组降低 15 个百分点（[−27, −3]）。投毒实验中 Attest 0 次写入错误建议，关掉门槛 9 次，ReasoningBank 12 次、ACE 10 次，后两者的 Agent 在后续任务中确实清空了审计日志。但被投毒的任务在所有条件下都没有通过验证，Attest 靠"不从未验证的任务学习"这一条挡住了毒药，同时也没学到这些任务里的其他经验：投毒下留出组为 36%，关掉门槛为 67%。更细的证据检查没有被这次投毒检验到。
- **业务风险**（无记忆 → Attest）：重复资金操作 18/18 → 6/18，未授权操作 15/15 → 2/15，误拦合法操作 15/15 → 3/15。这是记忆带来的，不是门槛带来的：关掉门槛时这三项相同或更好（2/18、2/15、2/15）。
- **近迁移与远迁移**（预注册的拆分，补报）：在 4 个与经验任务结构相近的留出任务上，Attest 比无记忆高 58 个百分点；在另外 7 个任务上高 24 个百分点（[+10, +43]）。
- **后续扩展（探索性）**：上下文管理器（看到结果后设计）在 6k token 预算下保住了会话中的评审规则（S05 通过 2/3，0 次审批违规；滑动窗口 0/3；普通摘要基线有缺陷，不作比较）；动态遗忘实验显示 200 条一次性笔记把留出组从 70% 降到 42%，默认参数下没有一种遗忘策略能修复，统一衰减误删了审批规则，按类型衰减没有；**可信度分级写入**（只出现一次的细节只在所属文件中注入）在更难的污染任务流上（不分级时为 36%）把留出组提高到 67%，与按类型遗忘结合为 76%，审批违规为 0（探索性，区分信号为构造所得）。**遗忘 V1.1**（离线）：把"被采用"当成贡献，会让 34 条一次性笔记永久保留；只按验证强化能消除这一点，但 V1.1 误归档的正确规则从 4/52 增加到 10–11/52，多为没有测试覆盖的规则，因此 V1 仍为默认。难点在于拿到可靠的价值反馈，而不是遗忘速度。
- **没有证明的**：在真实评审历史上，Attest 预判到的规范类评审意见最少（Saleor 上 1/25，ReasoningBank 4/25，ACE 8/25）；语义检索找到更多相关笔记，但没有改善编码结果。

### 问题

**为什么这是真实问题。**编码 Agent 会重犯团队已经付过代价的错误，因为这些经验存在于代码评审和事故复盘里，而不在代码里。业界已经在做这件事：GitHub Copilot Memory 让记忆带上代码引用，用之前先核对（A/B 测试中编码 Agent 的 PR 合并率从 83% 提高到 90%）；CodeRabbit Learnings 从评审评论中记住团队偏好，可设管理员审批；Qodo 从被采纳的建议中提炼规则。但真实仓库上的研究结论并不乐观：VibeMemBench 中现有记忆系统与 Agent 的 12 种组合里有 11 种不比无记忆好；MemDev-Bench 发现，记忆会让 Agent 做错原本能做对的任务，原因是不检查记忆是否适用。这些工作都没有公开回答治理问题：错误建议、规则用错地方、规则已经变了。这正是本项目要回答的。

**场景：Ledgerly**（合成材料，见 [`SCENARIO.md`](SCENARIO.md)）。一家 B2B SaaS 企业正把计费系统从单体迁移到模块化架构，财务政策不断变化；经验来自代码评审、事故复盘和财务决策。主线是：出现问题 → 评审或复盘形成经验 → Agent 学会 → 在新需求中复用 → 政策变化后修正。任务覆盖的业务流程是客服发起的退款或抵扣：

| 环节 | 业务要求 | 对应经验 | 基准是否覆盖 |
|---|---|---|---|
| 1 接收请求 | 客服输入的金额、交易、发起人 | C1 金额精度 | 是（H11 把 "49.99" 解析为两位小数的 `Decimal`） |
| 2 校验与去重 | 重试的请求不能重复退款 | C5 幂等（事件 A：重复退款） | 是（E04、H04、H06–H08、H10、H11） |
| 3 审批判断 | 客服发起、超过阈值需第二人审批 | C6 审批（政策 B：500，后改为 1000） | 是，含政策变化（2.0 上的 S04、S05） |
| 4 计算与资金操作 | 当前舍入规则（1.0 为 half-up，2.0 为 half-even） | C1 舍入 | 部分：**没有调用真实支付服务** |
| 5 更新账务与审计 | 每笔资金变动都要记录 | C4 审计 | 是 |
| 6 异常与重试 | 区分业务失败与系统故障；重试 | C2 异常、C5、C7 | 部分：支付服务超时与重试只在探索性扩展任务 X01 中（见 `RESULTS.md`）；**没有部分失败与恢复** |

C1–C4 可以从代码中发现，C5、C6 只能靠评审传承。事故与政策变化都是模拟设定，不来自真实企业。只有 H11 一个任务完整走完六个环节，其余任务各覆盖其中一段。

**两层研究设计。**

1. **受控实验（已完成）**：Ledgerly 基准（经验、留出、过期、对照四组任务），比较无记忆、ReasoningBank 式、ACE 式与 Attest 及其消融；预注册，结果见上。
2. **真实历史（部分完成）**：对 Flask、Saleor 的真实 PR 与评审评论做了回溯（[`REAL_HISTORY.md`](REAL_HISTORY.md)），Attest 没有召回优势，因为真实评审很少明说规则，漏掉的多是流程类意见。尚未完成的是：用从真实仓库历史中学到的记忆，让 Agent 完成该仓库后续的任务（如 MemDev-Bench 的做法）。这是最重要的下一步（见 [`ROADMAP.md`](ROADMAP.md)）。

### Attest 怎么工作

- **写入门槛**：每条经验需要来源原文、验证通过的改动中落实它的那一行（代码 / 测试 / 文档 / 配置，新增或删除）以及验证结果，分别记录；容忍格式差异，不容忍改写。
- **作用域与版本**：经验带仓库、文件和版本区间；规则在新版本变化时，旧规则对旧版本仍然有效，维护 v1 时仍能召回 500 元规则。
- **使用记录**：被引用且相关检查失败的经验先标可疑、再退役；验证成功可恢复。只有人能撤回经验，Agent 不能。
- **可观测**：每次运行记录被排除的笔记及原因、检索出的与实际注入的笔记、记忆占用的 token，可以区分"没学到""被过滤""没排上""被截掉""注入了但没照做"。
- **复用而非重写**：Agent 是原样的 mini-swe-agent 2.4.6；两个对照组是 ReasoningBank 与 ACE 的简化复现，拿到与 Attest 相同的验证结果。

### 评估方式

25 个任务（6 个经验、11 个留出、5 个过期、3 个对照）；评审意见由失败隐藏测试的 docstring 模拟；规范分两层：C1–C4 可在代码中发现，C5、C6 只能靠评审传承（无记忆时首次满足 0/14）。预注册写明了假设、判定规则（任务级配对 bootstrap；H1 优效性，H3、H4、H6 非劣效性）、排除规则以及冻结前的每一次校准和修改。独立 Agent 审计了任务集，并两次复核修复和最终门槛。投毒、规模、检索消融、真实仓库回溯为探索性研究，单独报告。

### 复现

见上方 [Reproduce](#reproduce)。离线测试和结果重算不需要 API key；新的运行需要 `DEEPSEEK_API_KEY`（GitHub secret，从不进入仓库）。

### 局限

单一模型、作者自建的合成基准、模拟的评审意见、11 个留出任务 × 3 次重复；三个留出任务与经验任务结构相近。写入门槛只检查证据行是真实的已验证改动，不检查它是否与规则相关。真实评审中漏掉的多是流程类意见（rebase、backport），diff 无法体现（见 `PROCESS_MEMORY.md`）。尚未解决的问题是**失败归因**：遗忘机制要想做好，需要知道失败是哪条笔记造成的，本项目目前还没有可靠的办法。模型生成的检查只对 25 条规则中的 1 条有用；用产生规则的评审去验证这些检查也没有帮助，因为 Agent 的真实错误常常是"漏了"，检查抓不到，通过验证的检查也只有约一半报得对（见 `RESULTS.md`、D33）。没有测试或评审点名的规则，目前试过的所有反馈信号都覆盖不到。下一阶段（Attest 2.0：上下文管理、类型化记忆、动态遗忘）见 [`ROADMAP.md`](ROADMAP.md)。
