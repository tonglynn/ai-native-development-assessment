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

What the gate buys instead (exploratory stress tests):

- **Poisoned review advice** ("clear the audit log after writing an entry"):
  Attest stored it 0 times; without the gate 9 times; ReasoningBank 12, ACE 10.
  ReasoningBank and ACE agents then cleared the audit log in 2 and 5 held-out runs.
- **300 notes from other repositories** in memory: Attest 73% pass@1 with 31k
  prompt tokens per run and 0 foreign notes shown; ReasoningBank 42% / 46k; ACE 55% /
  157k (every note in every prompt).
- **Business risks** on held-out, stale and control tasks, no memory → Attest:
  duplicate money operations 18/18 → 6/18, unauthorised operations 15/15 → 2/15,
  legitimate operations blocked 15/15 → 3/15.

Later extensions (exploratory, `RESULTS.md`): a **context manager** kept the
session's review rule under a 6k-token budget (S05 2 of 3, 0 approval violations;
window 0/3, plain summary 1/3, full history 3/3 at 4× the tokens); **dynamic
forgetting** showed that 200 one-off notes cut held-out pass@1 from 70% to 42% and
that no forgetting policy repaired it, while uniform decay wrongly archived the
approval rule and type-aware decay did not. **Trust-tiered admission** (a detail seen once is
injected only in its own files) brought that back to 67%, 76% together with type-aware
forgetting, with 0 approval violations (exploratory; the separating signal exists by
construction). **Forgetting V1.1** (offline): counting adoption as
contribution let 34 one-off notes become permanent; reinforcing only verified use removed
that, but V1.1 wrongly archived more correct rules (4 → 10–11 of 52), mostly rules no test
checks, so V1 stays the default. The hard part is reliable evidence of value, not the decay
rate.

What it does **not** show: on real review history (Flask, Saleor) Attest has no
recall advantage ([`REAL_HISTORY.md`](REAL_HISTORY.md)); embedding retrieval finds
more relevant notes but did not improve coding results (retrieval ablation in
`RESULTS.md`).

## The problem

A team's rules about money live partly in code and partly only in reviewers' heads:
an idempotency key after a double-refund incident, a second approver above a
threshold set by finance. An agent that does not know them repeats mistakes the team
already paid for. Memory can help, but naive memory adds new failure modes:

1. it learns from unverified attempts and from wrong advice,
2. it applies one repository's rules to another,
3. it keeps applying a rule after the policy changed.

The benchmark is a synthetic billing library, `ledgerly`, migrating from a monolith,
with a 2.0 release that changes the rounding policy and raises the approval threshold
from 500.00 to 1000.00, and a control library, `simkit`, with opposite conventions.
The business context, roles and the incident and policy history are in
[`SCENARIO.md`](SCENARIO.md) (clearly marked synthetic).

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
python -m pytest -q                         # 66 offline tests, scripted model, no API calls
python scripts/validate_benchmark.py        # 25/25 tasks measure what they claim
python -m attest summary runs/main          # recompute the tables from committed results
python -m attest.report runs/main report/index.html

# new runs need DEEPSEEK_API_KEY (a GitHub secret; never in the repository)
python -m attest experiment --name main --reps 3 --parallel 6
python -m attest stress --kind poison --name stress_poison
python -m attest ablation --source main --name retrieval_ablation
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
| `PREREGISTRATION.md`, `DECISIONS.md`, `AI_LOG.md`, `INCIDENTS.md` | Method, decisions D1–D28, AI collaboration log, incidents |
| `SCENARIO.md`, `scenario/history/` | Business scenario (synthetic) |
| `ROADMAP.md`, `PROCESS_MEMORY.md` | Next steps (Attest 2.0), deliberately not added |

---

## 中文说明

编码 Agent 记不住代码评审教过它的东西；而现有的记忆方案往往是"Agent 总结了什么就存什么、到哪都用、从不收回"。**Attest** 只保留被验证通过的改动真正落实过的经验，每条经验绑定来源仓库和适用版本，规则失效时降级、替换或撤回。一个预注册实验衡量了它带来的收益和代价。

### 结果概览

预注册实验（任何记忆实验运行前在提交 `cf5d879` 冻结）：6 个条件 × 3 次重复 × 25 个任务，共 450 次运行，模型 `deepseek-flash`，无排除，费用约 0.85 美元。详见 [`RESULTS.md`](RESULTS.md) 与 [`report/index.html`](report/index.html)。

- **留出组首次通过率**：无记忆 33%，ReasoningBank 58%，ACE 61%，**Attest 70%**；关掉写入门槛 85%，关掉作用域 67%。
- **H1–H5 得到支持**：比无记忆高 36 个百分点（区间 [+21, +52]）；不泄漏到其他仓库；过期政策场景不比无记忆差；不差于两种已发表的设计；作用域是防泄漏的关键。
- **H6 不被支持**：写入门槛让留出组降低 15 个百分点（[−27, −3]）。门槛换来的是安全：投毒实验中 Attest 0 次写入错误建议，关掉门槛 9 次，ReasoningBank 12 次、ACE 10 次，后两者的 Agent 在后续任务中确实清空了审计日志。
- **业务风险**（无记忆 → Attest）：重复资金操作 18/18 → 6/18，未授权操作 15/15 → 2/15，误拦合法操作 15/15 → 3/15。
- **后续扩展（探索性）**：上下文管理器在 6k token 预算下保住了会话中的评审规则（S05 通过 2/3，0 次审批违规；滑动窗口 0/3，普通摘要 1/3）；动态遗忘实验显示 200 条一次性笔记把留出组从 70% 降到 42%，没有一种遗忘策略能修复，统一衰减误删了审批规则，按类型衰减没有；**可信度分级写入**（只出现一次的细节只在所属文件中注入）把它拉回到 67%，与按类型遗忘结合为 76%，审批违规为 0（探索性，区分信号为构造所得）。**遗忘 V1.1**（离线）：把"被采用"当成贡献，会让 34 条一次性笔记永久保留；只按验证强化能消除这一点，但 V1.1 误归档的正确规则从 4/52 增加到 10–11/52，多为没有测试覆盖的规则，因此 V1 仍为默认。难点在于拿到可靠的价值反馈，而不是遗忘速度。
- **没有证明的**：在真实评审历史（Flask、Saleor）上 Attest 没有召回优势；语义检索找到更多相关笔记，但没有改善编码结果。

### 问题

团队关于"钱怎么处理"的规矩，一部分写在代码里，一部分只在评审者脑子里：重复退款事故后引入的幂等键、财务规定的审批阈值。不知道这些的 Agent 会重犯团队已经付过代价的错误。记忆能帮忙，但朴素的记忆会带来新问题：从没验证过的尝试和错误建议中学习；把一个仓库的规矩用到另一个仓库；政策变了还继续用旧规则。基准是一个从单体迁出的合成计费库 `ledgerly`（2.0 版改了舍入政策、把审批阈值从 500 提到 1000）和一个规矩相反的对照库 `simkit`。业务背景、角色、事故与政策历史见 [`SCENARIO.md`](SCENARIO.md)（明确标注为合成材料）。

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

单一模型、作者自建的合成基准、模拟的评审意见、11 个留出任务 × 3 次重复；三个留出任务与经验任务结构相近。写入门槛只检查证据行是真实的已验证改动，不检查它是否与规则相关。真实评审中漏掉的多是流程类意见（rebase、backport），diff 无法体现（见 `PROCESS_MEMORY.md`）。下一阶段（Attest 2.0：上下文管理、类型化记忆、动态遗忘）见 [`ROADMAP.md`](ROADMAP.md)。
