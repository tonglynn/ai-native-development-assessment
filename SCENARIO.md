# Scenario: Ledgerly / 业务场景：Ledgerly

> Everything in this scenario (the company, the incidents, the finance decisions)
> is **synthetic**, written for this project. It is not taken from a real company.
> The real-world evidence in this project comes only from public open-source
> review history (see *Two layers of evidence*).
>
> 本场景中的公司、事故和财务决策均为**合成设定**，为本项目编写，并非来自真实企业。
> 本项目的真实数据仅来自公开开源项目的评审历史（见"两层证据"）。

## The business / 业务背景

**Research scope.** Payments, refunds and account adjustments (credits, write-offs) in the migration of a B2B
SaaS subscription-billing system. Subscriptions and invoicing are business context: some tasks touch them (renewal,
cancellation, proration, discounts, tax), but the benchmark does not cover the whole billing system.

**研究范围。** B2B SaaS 订阅计费系统迁移中的支付、退款与账务调整（抵扣、核销）业务。订阅与账单是业务背景，部分任务
涉及（续费、取消、按比例退款、折扣、税），但本基准不覆盖完整的计费系统。

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

### Business chain and scope / 业务链路与研究范围

| # | Stage / 环节 | What happens / 内容 | In this benchmark / 本研究 |
|---|---|---|---|
| 01 | Subscriptions / 订阅管理 | sign-up, renewal, cancellation, plan change | background (E03, H05) |
| 02 | Invoicing / 账单生成 | amounts, discounts, tax, period settlement | background (E01, E05, H01, H02) |
| 03 | Payments / 支付处理 | capture, void, timeout retries, duplicate callbacks | **core** (E06, H06, H08) |
| 04 | Refunds and credits / 退款与抵扣 | request, approval, idempotency, money back | **core** (E04, H04, H07, H10, H11, S04, S05) |
| 05 | Finance audit / 财务审计 | operation records, money trail, anomaly tracing | **core** (C4 in every money-moving task) |
| 06 | Policy and versions / 政策与版本管理 | rounding rules, approval thresholds, rule history | **core** (stale group, ledgerly 2.0.0) |

Stages 01–02 give the business context; payments, refunds, amounts and audit are
the core of the tasks. 前两个环节作为业务背景，支付、退款、金额与审计是任务的核心范围。

### Roles / 业务角色

| Role / 角色 | Responsibility / 职责 | Cares about / 关心的问题 | Convention that serves it / 对应规范 |
|---|---|---|---|
| Customer / 用户 | subscribes, pays, asks for refunds | money is right | C1 amounts, C5 no double refunds |
| Support / 客服 | handles refund and credit requests | operations go through without friction | C6 *allows*: legitimate operations are not blocked |
| Finance / 财务 | sets approval and billing policy | money risk is under control | C6 *blocks*, policy versions (FIN-2026-03, FIN-2026-09) |
| Engineering / 研发 | maintains billing and payments | code follows the team's rules | C2 errors, C3 time zones, the agent's memory |
| Auditor / 审计 | checks money operations | every movement can be traced | C4 audit entries, C5 keys in the trail |

Each technical rule has a business reason: idempotency prevents paying a refund
twice, approval controls money risk, audit entries trace every movement, and
version management makes each release apply the policy in force.
幂等是为了避免重复退款，审批是为了控制资金风险，审计记录是为了追踪每笔资金操作，版本管理是为了让每个版本执行当时有效的财务政策。

### Core objective: safety without blocking / 核心目标：保证资金安全，同时少误拦合法操作

| Option / 方案 | Benefit / 好处 | Risk / 风险 |
|---|---|---|
| Every refund needs approval / 所有退款都审批 | low money risk | legitimate refunds blocked, support queue grows |
| Every refund goes through / 所有退款直接放行 | smooth for customers | unauthorised money movement |
| By amount and approval, per policy version / 按金额、审批状态和政策版本判断 | balances both | the threshold must be kept current (FIN-2026-09) |

So the business metrics point in two directions, and both are reported:
业务指标因此有两个方向，同时报告：

- **Risk control / 风险控制:** unauthorised-operation rate (C6 *blocks* failed), duplicate-money-operation rate (C5 failed), unaudited movements (C4 failed).
- **Efficiency / 业务效率:** legitimate-operation-blocked rate (C6 *allows* failed, including a stale 500.00 threshold on 2.0.0). Processing time of a real request is not simulated; the agent's steps and tokens per task are reported as engineering cost, not as business processing time.

### Who initiates, approves, executes and audits / 谁发起、谁审批、谁执行、谁审计

| Operation / 操作 | Initiates / 发起 | Approves / 审批 | Executes / 执行 | Audits / 审计 | Checked by the benchmark / 基准是否检查 |
|---|---|---|---|---|---|
| Capture a payment / 扣款 | billing system (renewal, invoice) | – | billing code (ledgerly) | finance reconciles from audit entries | C3, C4, C5 (E06, H08) |
| Void an authorization / 作废授权 | billing system or support | – | billing code | finance | C4, C5 (H06) |
| Refund (money back) / 退款 | customer request via support | finance lead, above the threshold | billing code, through the payment provider (X01) | finance, auditor | C1, C4, C5, C6 (E04, H07, H11, S05, X01) |
| Credit (balance adjustment) / 抵扣 | support | finance lead, above the threshold | billing code | finance | C4, C5, C6 (H04, S04) |
| Write-off / 核销 | finance | finance (policy) | billing code | auditor | C4, C5 (H10) |
| Change a policy / 政策变更 | finance | finance leadership (FIN-…) | engineering releases a version | auditor | stale group on 2.0.0 (S01–S05) |
| Change team memory / 团队记忆变更 | the agent proposes | a registered approver (D62) | Attest stores it | the event log (D42) | judgement sets (D58–D60) |

A **refund** returns money to the customer through the payment provider and changes `payment.refunded_amount`;
a **credit** adjusts what the customer owes on an invoice and moves no money. Both need approval above the
threshold and an audit entry; only a refund can fail at the provider.
**退款**是通过支付服务商把钱退回客户，改变 `payment.refunded_amount`；**抵扣**是调整客户在账单上的应付金额，不发生资金
流动。两者超过阈值都需要审批、都要写审计记录；只有退款可能在支付服务商一侧失败。

**Segregation of duties / 职责分离.** Whoever requests an operation may not approve it, and the approver is not
the code that executes it. In the benchmark, C6 checks that an approver is present above the threshold, **not** that
the approver differs from the requester (H11 passes `requested_by` and `approved_by`, but no test sets them equal):
that rule is stated here, not measured. The same principle is enforced for the team's memory: an agent cannot
approve its own candidate experience (D62).
申请人不能审批自己的操作，审批人也不是执行操作的代码。基准中 C6 只检查超过阈值时是否有审批人，**不检查**审批人与申请人
是否不同（H11 同时传入 `requested_by` 与 `approved_by`，但没有测试让两者相同），这一规则在此说明，未被测量。同一原则
在团队记忆上是强制的：Agent 不能批准自己提出的经验（D62）。

### What every money operation records / 每笔资金操作记录什么

| Field / 字段 | Required by the benchmark (C4) / 基准要求 | Stated here, not checked / 仅在此说明 |
|---|---|---|
| event name (past tense) | yes | |
| payment or invoice id | yes | |
| amount | yes | |
| idempotency key | yes, in tasks with C5 | |
| approver | where the operation needed approval (E04 reference) | |
| operator (requested_by) | | yes |
| state before and after | | yes |
| related business request id | | yes |

Example (synthetic, not a real transaction / 模拟数据，不代表真实交易):
`audit.record("payment_refunded", payment_id="pay_2026_001", amount=Decimal("800.00"), idempotency_key="req_7f3", approved_by="usr_finance_lead")`

### Failures at each step and what the agent must learn / 各环节的异常与 Agent 应学会的处理

| Failure / 异常 | Business risk / 业务风险 | What handles it / 处理方式 | In the benchmark / 基准 |
|---|---|---|---|
| Invalid request (zero, negative, over-refund, wrong state) | money moved that should not move | reject with `BillingError(code)` (C2) | every task |
| Provider timeout, retried request | refund paid twice | idempotency key checked first (C5); retry with the same key (C7) | E04, H04, H06–H08, H10, H11; X01 |
| Duplicate request with the same key | double money operation | return the original result (C5) | C5 tests |
| Large operation without approval | unauthorised money movement | `approval_required` (C6) | C6 *blocks* tests |
| Legitimate operation refused | support blocked, customer harmed | threshold of the current policy version (FIN-2026-09) | C6 *allows* tests, S04, S05 |
| Provider succeeded, ledger update failed | books disagree with the bank | compensation or reconciliation | **not covered** (ROADMAP) |
| Callback late or out of order | wrong payment state | state checks and event handling | **not covered** (ROADMAP) |
| Refund failed at the provider, reprocessing | customer not refunded | retry or manual handling | **not covered** (X01 tests success and timeout only) |

### Coverage map / 覆盖地图

| Area / 领域 | Covered / 已覆盖 | Partly / 部分 | Not covered / 未覆盖 |
|---|---|---|---|
| Subscriptions and invoicing | renewal (E03), cancellation (H09), proration (H05), discounts, tax, amounts (E01, E05, H01, H02) | billing periods | plan upgrade and downgrade; failed-renewal retries |
| Payments and refunds | partial refund (E04), void (H06), partial capture (H08), duplicate refunds (C5), provider timeout (X01) | refund vs credit (both present, distinguished in this document only) | refund to the original method; refund failure and reprocessing |
| Approval and permissions | second approver above the threshold (C6), policy versions (FIN-2026-03, FIN-2026-09) | segregation of duties in the business operation (stated, not tested); in the memory lifecycle tested 16/16 (D69) | a full role and permission model |
| Ledger and audit | event, entity id, amount, idempotency key, approver (C4) | | operator, state before and after, request id |
| Failure recovery | timeouts, duplicate requests | | compensation after a ledger failure; late or out-of-order callbacks |

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
| 2 Retries and approvals / 重复请求与审批 | E04, E06, H04, H06–H08, H10, H11 (end-to-end support refund request) | Inheriting C5–C6 from earlier review |
| 3 Policy upgrade / 政策升级 | S01–S05 on ledgerly 2.0.0 | Noticing that remembered policy (rounding, threshold) is out of date |

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
| Unauthorised operation (risk control) | Share of C6 checks where an over-threshold operation went through without approval | C6 "blocks" tests |
| Legitimate operation blocked (efficiency) | Share of C6 checks where an operation at or below the threshold, or an approved one, was refused | C6 "allows" tests, incl. 700.00 and 800.00 under the 2.0.0 threshold (S04, S05) |
| Amount-precision violation | Share of C1 checks failed | C1 tests |
| Unaudited money movement | Share of C4 checks failed | C4 tests |
| Outdated policy applied | Failures of the checks an outdated v1 rule can fail on ledgerly 2.0.0 | S-group rounding-policy tests and C6 *allows* tests |
| Rule carried into the wrong repository | Share of simkit checks failed, and ledgerly notes shown on simkit | B-group K1, K2; retrieval logs |

These are risks in a simulated business. They show which mistakes memory
prevents; they do not estimate losses at a real company.

以上是模拟业务中的风险指标，说明记忆避免了哪类错误，不代表真实企业的损失估计。
