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
| Continuous learning | verified distillation, usage accounting, funnel; dynamic forgetting V1 (four policies, `RESULTS.md`); forgetting V1.1 offline (verified-only reinforcement, utility decay; an option, V1 stays the module's default); reactivation resets the decay clock (regression-tested); forgetting V2 mechanisms (stability, scoped exposure, three evidence states, demand), liveness check, rule-to-check generation, measured offline or on the benchmark's code; just-in-time verification at retrieval (no harm on stale tasks, no improvement shown). All opt-in and used only by evaluation scripts, not by the evaluated Attest or the MCP server | | consolidation, conflict resolution; failure attribution (which note caused a failure): validating generated checks against their own evidence was tested and does not work (D33); next, attribute by matching the review comment that names the failed convention |

## P0, before the freeze / 冻结前 (done)

Independent audit and re-check; complete preregistration with decision rules;
business metrics in two directions (`SCENARIO.md`); lifecycle and evidence gate
checked (D21, D24, D25).

## P1, after the main experiment: depth / 技术深度

| Capability / 能力 | What exists now / 现状 | What to add / 待补 |
|---|---|---|
| Conflict resolution / 记忆冲突处理 | Supersede with version ranges (`rule changed` vs `corrected`), `validity()` per version | A resolution step at retrieval: when several valid notes about one rule are retrieved, pick by scope and version, or mark **CONFLICTED** and ask a person instead of injecting both. States: SUPERSEDED, CONFLICTED, SUSPECT |
| Trust levels / 可信度分级 | Typed evidence and `references` recorded per note; trust-tiered admission (policy / convention / repeated / candidate, a candidate is stored but injected only in its own files) built and measured (`RESULTS.md`, D30) | Explainable levels from rules, not a model score: *high* (policy + code change + verification), *medium* (repeated independent reviews + change), *low* (single review, stored, not injected), *quarantined* (unknown source, conflicting evidence, suspected poison). A finance policy outranks a reviewer's remark |
| Poisoning defence / 投毒防御 | Nothing is learned from an unverified task (first poison: the poisoned tasks failed verification). Advice that passes the tests and is followed is stored with a complete evidence chain (second poison). Built and measured, opt-in: a business-policy guard (D38) stops it where the rule is written as a check; semantic review with cited conflicts (D39) holds it where a contradicting rule or changelog entry exists, but cannot tell new-and-right from new-and-wrong rules (8 of 25 correct notes held); scope and versions tested by B and S tasks | Four attack types: wrong rule, **instruction injection** in review text ("delete the audit check to pass"), cross-repository injection, stale-policy injection. Review text is a source of experience, never an instruction; no note can override system safety rules |
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

## Agent memory security: designed, not built / 智能体记忆安全：只有设计，未实现

Built and measured (exploratory, RESULTS.md "Agent memory security"): trust boundary for admission
(D41), sealed event log (D42), MCP repository identity and secret scanning (D43), a scrubbed agent
shell and a real prompt-injection run (D44), quarantine with a propagation trace (D45). The three
items below were left as designs, because each needs infrastructure this prototype does not have
(a real tool registry, real credentials, a real deployment), and a simulation of them would mostly
test the simulation. References: OWASP Top 10 for Agentic Applications
(https://genai.owasp.org/2025/12/09/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security/),
OWASP MCP Top 10 (https://owasp.org/projects/mcp-top-10), OWASP AI Agent Security Cheat Sheet
(https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).

| Risk | What could go wrong here | Design | Why not built now |
|---|---|---|---|
| MCP tool poisoning | the agent reads Attest's tool descriptions; a modified server (or a second server with a look-alike tool name) could tell it to send code or notes elsewhere, or to call `learn` with crafted candidates | pin the tool list and descriptions by hash at install and refuse a changed server; the notes returned by `recall` are data, labelled as such and never instructions to call tools; `learn` accepts only candidates that pass the same gate, and `retract`/quarantine stay off MCP (already so) | needs a client that verifies server manifests; one local server here |
| Privilege escalation | memory decides what the agent sees; a note that says "you may skip review" or "run with the deploy token" would turn memory into permissions | memory can never grant a capability: notes are injected as advice under the task; permissions come from the runner (scrubbed shell, D44; no network beyond the model), never from note text; flag notes that mention credentials, permissions or disabling checks for review | the agent here has no privileges to escalate to |
| Agent goal hijacking via memory | a stored note re-states the task ("instead of X, do Y") and is injected into every later task in the repository | the D41 trust boundary limits who can make a note a repository-wide rule; governance (D39) can hold notes that conflict with a cited rule; the D44 run measures how often an injected instruction is obeyed and stored | partly covered by D41/D39/D44; a dedicated "goal conflict" check would need a task model |
| Security gateway | one place that applies every check before a note is stored or injected | order: secret scan (D43) → write gate → trust tier (D41) → governance (D39) → sealed append (D42); at injection: scope → liveness (D34) → quarantine status (D45) | the pieces exist as options; wiring them as one default changes the evaluated system and needs its own run |

## Memory value and injection: next stage (design, after D63–D65) / 记忆价值与注入：下一阶段（设计）

What is measured so far: putting business-critical rules first removed displacement on Ledgerly (D64, arm C:
idempotency rule injected 18 of 18 times; 77% vs 70%, not shown better); a hard cap on core notes (arm D, 3 at most)
saved 36% of memory tokens but dropped core rules on tasks needing four; v3.1 already injects 118 of 120 needed core
rules, and its remaining failures are rules injected but not followed (D65). Scope kept every Ledgerly note out of
simkit in every run. Three things are not built:

| Item | Design | Why not yet / what it needs |
|---|---|---|
| Criticality by task type, not by a fixed list (a keyword version built as arm E, D66: better than A, 83% vs 70%; a team-written taxonomy and held-out task types are still missing) | criticality = importance of the rule for the operation the task performs (moving money → idempotency, audit, approval; amount calculation → Decimal, rounding; refactoring → error and interface conventions), from the task text and the note's scope; no rule is permanently first | needs a task-type taxonomy written by the team and a held-out set of task types; arm C uses a fixed core list that fits Ledgerly only |
| Soft budget instead of a core cap (built as arm D2, D66: better than A, 85% vs 70%; regular notes compressed to titles, the Context Manager is not yet used) | keep every relevant core rule; order regular rules by relevance and criticality; candidates never injected globally; when over the token budget, compress regular rules first (the Context Manager's extractive summary, D49), never drop a core rule | arm D's cap of 3 was the failure; the compression path exists in `attest/context/manager.py` but is not wired to injection |
| Cross-domain check | does criticality-first injection help in another domain, does one domain's core rules crowd out another's within one repository | simkit has 3 control tasks and no business rules of its own; this needs new tasks with their own critical rules (e.g. a second business module in Ledgerly, or a simkit module with safety limits), i.e. benchmark work, not only a run |
| Rules injected but not followed | the remaining failures of the best pipelines (C1 precision, C5 idempotency) happen with the rule in the prompt | a pre-submit code check or the team's code checks (D60) run as feedback before the agent submits, measured against injection alone |

## Business coverage: not in the benchmark (from the scenario's coverage map) / 业务覆盖缺口

New tasks with their own hidden tests, outside the frozen task set: plan upgrade and downgrade with proration;
failed-renewal retries; refund to the original method, and refund failure with reprocessing; compensation when the
provider succeeded but the ledger update failed; late or out-of-order provider callbacks; segregation of duties
(the approver must differ from the requester); audit entries with operator, state before and after, and request id.
Each would add a business rule that is only in review or policy, which is where memory is meant to matter.

## Deliberately not added / 刻意不加

| Technology | Why not |
|---|---|
| PostgreSQL | the event log and SQLite cover the current scale (D19) |
| FAISS / vector database | no retrieval bottleneck at 10,000 notes (D22) |
| GraphRAG | more complexity without a hypothesis it would test |
| LangGraph | the agent loop needs no orchestration framework |
| Multi-agent collaboration | adds experimental variables |
| Fine-tuning | the research is about governing memory, not training models |
