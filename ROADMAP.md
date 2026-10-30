# Roadmap after the main experiment / 主实验之后的路线图

Nothing here changes the frozen main experiment. 以下内容都不改变已冻结的主实验。

Target architecture: **Attest, evidence-governed agent memory**

```
Experience input      PR review · incident · finance policy · code diff
Write governance      evidence gate (built) → trust assessment (P1)
Memory management     store (built: JSONL / SQLite) · lifecycle (built) · versions (built) · conflict resolution (P1)
Retrieval             repository filter → version filter → lexical / embedding (built) → reranking (not planned yet)
Coding agent          mini-swe-agent (built) · Claude Code via MCP (prototype)
Execution, feedback   diff · hidden tests · business risks · memory funnel (built) → feedback loop (P1)
```

## Attest 2.0: status / 现状

| Layer | Built and measured | Built, not measured | Design only |
|---|---|---|---|
| Memory governance | evidence gate, scope, versions with supersede, retraction, poison and scale tests; trust-tiered admission (policy / convention / repeated / candidate) against pollution | SQLite shared store | conflict resolution; quarantine tier for suspected poison |
| Typed memory | (semantic rules) | | procedural, episodic, entity (taxonomy below) |
| Context management | context manager on one long-session scenario (`RESULTS.md`) | archive layer (kept in memory, not persisted) | context recovery from the archive |
| Agent execution | mini-swe-agent | MCP server and scripted client demo (`docs/MCP_DEMO.md`) | Claude Code session, LATS (not planned: adds search and variables unrelated to memory governance) |
| Continuous learning | verified distillation, usage accounting, funnel; dynamic forgetting V1 (four policies, `RESULTS.md`) | reactivation of archived notes (tested offline) | consolidation, conflict resolution |

## P0, before the freeze / 冻结前 (done)

Independent audit and re-check; complete preregistration with decision rules;
business metrics in two directions (`SCENARIO.md`); lifecycle and evidence gate
checked (D21, D24, D25).

## P1, after the main experiment: depth / 技术深度

| Capability / 能力 | What exists now / 现状 | What to add / 待补 |
|---|---|---|
| Conflict resolution / 记忆冲突处理 | Supersede with version ranges (`rule changed` vs `corrected`), `validity()` per version | A resolution step at retrieval: when several valid notes about one rule are retrieved, pick by scope and version, or mark **CONFLICTED** and ask a person instead of injecting both. States: SUPERSEDED, CONFLICTED, SUSPECT |
| Trust levels / 可信度分级 | Typed evidence and `references` recorded per note | Explainable levels from rules, not a model score: *high* (policy + code change + verification), *medium* (repeated independent reviews + change), *low* (single review, stored, not injected), *quarantined* (unknown source, conflicting evidence, suspected poison). A finance policy outranks a reviewer's remark |
| Poisoning defence / 投毒防御 | Wrong advice the change never applied is rejected (poison stress test); scope and versions tested by B and S tasks | Four attack types: wrong rule, **instruction injection** in review text ("delete the audit check to pass"), cross-repository injection, stale-policy injection. Review text is a source of experience, never an instruction; no note can override system safety rules |
| Feedback loop / 反馈闭环 | cited + related failure → suspect → retired, cleared by a verified success; funnel records retrieved, injected, followed | Use the funnel, not only the agent's citation: repeated "injected but not followed" for a note pauses injection, re-checks its evidence and scope, then retires or restores it. A failed task alone never retracts a note |
| Component ablation / 组件消融 | Gate and scope ablations in the main experiment | A ladder: no memory → plain store + retrieval → + evidence gate → + versions and scope → + conflict resolution → full Attest, to show each component's contribution |

## Memory taxonomy (design, after the main experiment) / 记忆分类体系（设计，主实验之后实现）

Goal: turn past engineering episodes into trusted knowledge, and trusted knowledge
into executable practice, not store everything. 目标不是什么都存，而是把历史工程经历转化为可信知识，再把可信知识转化为可执行的工程经验。

Three dimensions that coexist (not one mutually exclusive `memory_type`):
三个维度并存，而不是一个互斥的类型字段：

**1. Knowledge type / 知识类型** (what the note is about)

| Type | Question it answers | Ledgerly example | In Attest today |
|---|---|---|---|
| Semantic / 语义 | What is the rule? | refunds must be idempotent; the v2 threshold is 1000.00 | **yes**: almost every note (`kind: project_fact`) |
| Procedural / 程序性 | How is the work done? | validate → check idempotency key → approval → refund → audit entry → return | partly: some `lesson` notes are single steps, no ordered procedures |
| Episodic / 经历 | What happened before? | INC-204: a timeout retry refunded 37 customers twice | only as provenance (the source review comment, references such as INC-204, the event log), not as retrievable memory |
| Entity / 实体 | Who or what is involved, and how is it related? | `adjustments.refund`, `Payment`, FIN-2026-03, INC-204 | proto-entities only: `references` and `scope.files` per note, no relation graph |

**2. Evidence / 证据与观察** (why the note may be believed). Review comment, code diff,
test result, documentation, configuration; later logs, traces, metrics. *Perceptual*
memory lives here: raw observations (an error log, a CI failure, a trace) are evidence
and provenance, never rules by themselves. In Attest today: typed evidence
(`source`, `applied` code/test/doc/config, `verification`); raw transcripts and test
output are kept with every run, but not as memory. Note that `code`, `documentation`,
`configuration`, `process` are kinds of evidence or change, not knowledge types.
感知记忆体现为原始观察记录（证据），不直接当作可信规则；code / documentation / configuration / process 是证据或变更类型，不是知识类型。

**3. Governance / 记忆治理** (whether and where it may be used). Provenance, trust
status, repository scope, version validity, conflicts, retraction, usage feedback.
This is what Attest builds now (D21, D25, D27, lifecycle and funnel).

The existing `type` field (`business_policy`, `code_convention`, `process`, `lesson`)
is a fourth, descriptive label of the rule's origin; it is kept and is not a
knowledge type.

### From an incident to reusable experience / 从一次事故到可复用的经验

```
Episodic    INC-204: a timeout retry executed the same refund twice
   ↓ distil (each derived note passes the evidence gate on its own)
Semantic    every refund is idempotent: a repeated request must not move money again
Procedural  before refunding, check the idempotency key; on a repeat, return the earlier result
Entity      adjustments.refund · Payment · INC-204 · FIN-2026-03 (linked, not copied)
   ↓ reuse in a new task, then feedback (funnel) updates trust
```

The episode, the rule and the procedure are separate memory objects. Coming from
the same incident does not make them verified: each needs its own source quote,
applied line and verification. 来自同一事故不代表都已验证，每一条都要单独过证据门槛。

### Order / 顺序

| Step | Content | When |
|---|---|---|
| 1 | Definitions and boundaries (this section) | now, no change to the main experiment |
| 2 | Label existing Attest notes by knowledge type; report counts, sources and verification status per type | after the main experiment |
| 3 | Type-aware retrieval: rules, procedures and past incidents recalled by task need | next phase |
| 4 | Ablation: plain memory vs typed memory vs typed memory + distillation from episodes | last |

Priority: Semantic required (exists, add the label); Procedural and Episodic
recommended after the main experiment; Entity later (cross-module and cross-policy
relations); Perceptual only when real logs are connected, without a separate store.

## P2, applied validation / 应用验证

Real GitHub pull-request workflow; code, documentation and process memory
(`PROCESS_MEMORY.md`); Claude Code through the MCP server; measure on a real
repository whether memory reduces repeated review comments.

## Deliberately not added / 刻意不加

| Technology | Why not |
|---|---|
| PostgreSQL | the event log and SQLite cover the current scale (D19) |
| FAISS / vector database | no retrieval bottleneck at 10,000 notes (D22) |
| GraphRAG | more complexity without a hypothesis it would test |
| LangGraph | the agent loop needs no orchestration framework |
| Multi-agent collaboration | adds experimental variables |
| Fine-tuning | the research is about governing memory, not training models |
