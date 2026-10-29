# Scenario: Ledgerly / 业务场景：Ledgerly

> Everything in this scenario (the company, the incidents, the finance decisions)
> is **synthetic**, written for this project. It is not taken from a real company.
> The real-world evidence in this project comes only from public open-source
> review history (see *Two layers of evidence*).
>
> 本场景中的公司、事故和财务决策均为**合成设定**，为本项目编写，并非来自真实企业。
> 本项目的真实数据仅来自公开开源项目的评审历史（见"两层证据"）。

## The business / 业务背景

A B2B SaaS company is migrating its billing monolith to a modular platform.
**ledgerly** is the extracted billing library: subscription renewals, invoices,
payments, refunds and the account adjustments that the support team makes for
customers. Finance policy changes several times a year, and old and new code live
side by side (the "moved over from the old billing monolith" modules).

一家 B2B SaaS 企业正在把历史单体计费系统迁移为模块化平台。**ledgerly** 是拆出来的计费库，负责订阅续费、
账单、支付、退款，以及客服为客户做的账务调整。财务政策一年会变好几次，新旧代码并存。

**The problem.** Over the years the team learned, through code review, incident
postmortems and finance decisions, how money must be handled here. Much of it
never made it into code or documentation. A new AI coding agent repeats mistakes
the team already paid for.

**问题。** 团队多年来通过代码评审、事故复盘和财务决策积累了"这里的钱该怎么处理"的经验，但很多没有沉淀进
代码或文档。新来的 AI 编码 Agent 会重犯团队早已付过代价的错误。

**Research question.** Can a coding agent learn from this history so that later
work repeats fewer of those mistakes, without carrying rules into the wrong
repository, without clinging to outdated policy, and without trusting unverified
memory?

**研究问题。** 编码 Agent 能否从这些历史中学习，让后续工作少犯同样的错误，同时不把规则带到错误的仓库、
不死守过期政策、也不相信未经验证的记忆？

## The refund and adjustment flow / 退款与账务调整流程

| Step / 步骤 | What happens / 内容 | Where team experience matters / 需要团队经验的地方 |
|---|---|---|
| 1 Request / 接收请求 | A customer or support agent asks to refund or credit an amount, citing a payment or invoice | Amounts arrive as text or numbers (C1) |
| 2 Duplicate check / 重复请求校验 | Requests are retried after timeouts | **C5 idempotency** — learned from incident INC-204 |
| 3 Approval / 审批 | Large support-initiated operations need a second approver | **C6 approval threshold** — finance decisions FIN-2026-03, FIN-2026-09 |
| 4 Money operation / 资金操作 | Amounts are computed and the refund or credit is applied | **C1 money precision and rounding** — FIN-2026-07 changed the rounding policy |
| 5 Ledger and audit / 账务与审计 | State is updated and the movement is recorded | **C4 audit entries**, **C3 UTC timestamps** |
| 6 Failures / 异常处理 | Invalid requests are rejected so callers can tell business failures from system faults | **C2 BillingError** |

## Team experience / 团队经验

| | Experience / 经验 | Why the team insists / 业务后果 | Where it lives / 经验在哪里 | Business risk measured / 衡量的业务风险 |
|---|---|---|---|---|
| C1 | Money is `Decimal`, rounded only with `round_money` | Rounding drift makes invoices disagree with the general ledger | Modern code (discoverable) | Amount-precision violations |
| C2 | Invalid input raises `BillingError(code)` | The API maps only `BillingError` to 4xx; anything else pages on-call as a system fault | Modern code (discoverable) | Misclassified failures |
| C3 | Datetimes are timezone-aware UTC | Renewals and billing periods shift across time zones | Modern code (discoverable) | Ambiguous timestamps |
| C4 | Money movements write an audit entry | Finance reconciles refunds and credits from the audit trail | Modern code (discoverable) | Unaudited money movements |
| C5 | Money operations take an `idempotency_key` and never apply twice | **INC-204**: retried support refunds were paid twice | **Review comments only** | **Duplicate money operations** |
| C6 | Support refunds and credits above the threshold need `approved_by` | **FIN-2026-03**: unapproved large refunds; **FIN-2026-09** raised the threshold | **Review comments only** | **Unauthorised operations** and **wrongly blocked legitimate operations** |

C1–C4 can be inferred by reading the modern modules; the pilots showed a capable
agent does exactly that. C5–C6 exist only in reviewers' heads and in the
documents below, which the agent never sees. That split is the core of the
research question: memory should matter most for knowledge that is not in the code.

C1–C4 读新模块就能推断，基线校准表明强 Agent 确实会这么做；C5–C6 只存在于评审者脑中和下列文档里，Agent
看不到。这个区分是研究问题的核心：记忆最该发挥作用的，是代码里没有的知识。

### History behind C5 and C6 / C5 与 C6 的来历

Synthetic source documents (not part of any repository the agent can read):

- [`scenario/history/INC-204-duplicate-refunds.md`](scenario/history/INC-204-duplicate-refunds.md) — postmortem of the duplicate-refund incident → C5
- [`scenario/history/FIN-2026-03-support-refund-approval.md`](scenario/history/FIN-2026-03-support-refund-approval.md) — finance decision introducing the 500.00 approval threshold → C6
- [`scenario/history/FIN-2026-07-rounding.md`](scenario/history/FIN-2026-07-rounding.md) — finance policy switching to banker's rounding → stale C1 in ledgerly 2.0.0
- [`scenario/history/FIN-2026-09-threshold.md`](scenario/history/FIN-2026-09-threshold.md) — finance decision raising the threshold to 1000.00 → stale C6 in ledgerly 2.0.0

In the benchmark, reviewers pass this knowledge on the way real reviewers do: as
review comments on a change that got it wrong (simulated from hidden-test
docstrings that cite INC-204 and FIN-2026-03).

## Three workflows, one maintenance lifecycle / 三条工作流，一个维护周期

| Workflow / 工作流 | Tasks / 任务 | What it tests / 检验什么 |
|---|---|---|
| 1 Refund features / 退款功能 | E01–E05, H01–H03, H05, H09 | Discoverable conventions in everyday feature work |
| 2 Retries and approvals / 重复请求与审批 | E04, E06, H04, H06–H08, H10 (and the end-to-end refund-request task) | Inheriting C5–C6 from earlier review |
| 3 Policy upgrade / 政策升级 | S01–S04 on ledgerly 2.0.0 | Noticing that remembered policy (rounding, threshold) is out of date |

The four task groups follow one system's life: **E** the team's earlier work and
reviews, **H** new work on the same system, **S** the same system after a finance
policy change, **B** a different team's repository with opposite conventions,
where nothing from ledgerly should be applied.

四组任务对应一个系统的维护周期：E 是团队以往的工作与评审，H 是同一系统上的新工作，S 是财务政策变化之后，
B 是规范相反的另一个团队的仓库，ledgerly 的经验不应被套用。

## Two layers of evidence / 两层证据

1. **Controlled benchmark (synthetic)** — the Ledgerly tasks above. Lets us
   isolate each memory mechanism, preregister hypotheses and measure business
   risks with hidden tests. It can only show that the mechanisms work *in this
   simulated business*.
2. **Real review history (real, public)** — merged, reviewed pull requests of
   public projects (a web framework and an e-commerce platform with payments and
   refunds). Memory learns from older PRs; an independent model judges whether
   the notes recalled for newer PRs anticipated the reviewers' real comments, and
   whether they were relevant. This tests learning from real review, not task
   success in those repositories.

1. **受控基准（合成）**：用于隔离各个机制、预注册假设、用隐藏测试衡量业务风险，但只能证明"在这个模拟业务中有效"。
2. **真实评审历史（真实、公开）**：用公开项目已合并 PR 的评审记录，由独立模型判定记忆能否预见后续真实评审意见。
   它检验的是"能否从真实评审中学习"，而不是在这些仓库中完成任务。

## Business risk metrics / 业务风险指标

Computed from hidden-test outcomes on the first attempt (see `attest/analysis.py`):

| Risk / 风险 | Metric / 指标 | From / 来源 |
|---|---|---|
| Duplicate money operation | Share of C5 checks where a retried request was applied again | C5 tests (retry with the same key) |
| Unauthorised operation | Share of C6 checks where an over-threshold operation went through without approval | C6 "blocks" tests |
| Legitimate operation blocked | Share of C6 checks where a below-threshold operation was refused | C6 "allows" tests, incl. 700.00 under the 2.0.0 threshold |
| Amount-precision violation | Share of C1 checks failed | C1 tests |
| Unaudited money movement | Share of C4 checks failed | C4 tests |
| Outdated policy applied | Failures of the policy-dependent checks on ledgerly 2.0.0 | S-group C1 and C6 tests |
| Rule carried into the wrong repository | Share of simkit checks failed, and ledgerly notes shown on simkit | B-group K1, K2; retrieval logs |

These are risks in a simulated business. They show which mistakes memory
prevents; they do not estimate losses at a real company.

以上是模拟业务中的风险指标，说明记忆避免了哪类错误，不代表真实企业的损失估计。
