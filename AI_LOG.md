# AI collaboration log / AI 协作日志

**English** · [中文说明](#中文说明)

Claude wrote most of the code and documents in this project. This log keeps only the decisions that shaped the
work, following `DECISIONS.md` (the D numbers there give the full reasoning, the alternatives and the evidence). Each
row says what the AI proposed or produced, what I judged or corrected, and what came of it. When a correction came
from the AI checking its own work, the row says so. Routine steps (scheduling, reruns, wording) are left out.

| Date | Decision | AI proposed or produced | My judgement / correction | Outcome |
|---|---|---|---|---|
| 10/29 | D2 | Reuse my earlier project tiny-agent-harness as the agent | It was written by AI and I do not understand it; I could not defend reused code I cannot explain | Not reused; an understanding check added to the plan |
| 10/29 | D3 | A small agent core written from scratch | Questioned whether it was too simple; asked for mature open-source agents to build on | mini-swe-agent as the agent, compared with ReasoningBank-style and ACE-style memory, two published designs |
| 10/29 | D4, D14 | — | I pasted an API key into the chat; the AI refused to use it and advised revoking it. Later, Codespaces kept disconnecting, so I asked the AI to run the experiments itself | The key lives only in a repository secret; experiments run on GitHub Actions, started by a request file, so the AI never handles the key |
| 10/30 | D10 | Treat the agent's self-reported citations as evidence that a note was used | Only as a trigger for demotion; whether a note worked is judged by hidden tests, behaviour and injection records | D10 made conditional |
| 10/30 | Preregistration | A statistical plan | Set H1 as superiority and H3, H4, H6 as non-inferiority (δ = 10 pp); an interval crossing the margin is reported as "same direction, not enough evidence" | Written into `PREREGISTRATION.md` before any memory run |
| 10/30 | D15 | Baselines showed a strong agent finds every convention visible in the code; proposed splitting conventions into discoverable and review-only, adding C5, C6 and stale task S04 | Agreed: do not weaken the model; memory's value should be knowledge the code does not show | Task set grew to 25 tasks |
| 10/30 | D23 | Options for the low recall on the real Saleor reviews | Keep the evidence gate; do not lower it to raise recall; report Saleor as an independent real-repository result; rerun an independent benchmark audit first | Saleor reported as is (no recall advantage); audit fixes before the freeze |
| 10/30 | Freeze | Freeze the main experiment | Required an independent review of 8 items first; freeze only with no blocker or major, fixing only what is necessary and revalidating 25/25 | Frozen at `cf5d879` |
| 10/30 | D31 | Forgetting V1.1 | Questioned how the parameters were chosen and found four flaws in the formula; fixed the adoption rule before seeing results (saves space but loses more correct rules → V1 stays default) | Parameter sweep; V1.1 optional; result matched the rule |
| 10/30 | Commit 21ec78d | — | Found four problems in review: "not verified" treated as "verification failed"; "4×" was an assumption; policy protection should add, not replace; `reactivate()` without a clock | All fixed and disclosed |
| 10/31 | D32, D33 | Six ways to get value feedback for forgetting | Asked for all six to be tested | Negative results reported as found (model-made checks useful for 1 of 25 rules) |
| 10/31 | D34 | — | Questioned whether the business scenario was realistic; asked to study better implementations on GitHub | Studied Copilot Memory and others; README rewritten; use-time verification added (no gain, reported) |
| 10/31 | Audit | — | Asked for an independent audit of the whole repository | 7 blockers found (including how the poison test really worked and an empty summary baseline), each checked and fixed |
| 10/31 | D41–D45 | — | Proposed moving from memory governance to memory security: six attack kinds, red-team cases, metrics; fake keys, simulated tools and isolated repositories only | Trust boundary, sealed log, MCP identity and secret scanning, a real injection run, quarantine |
| 10/31 | D43, D44 | While building D43 and D44 the AI found two real vulnerabilities: MCP memory keyed by the repository's last name segment, and the agent's shell inheriting the model key | — | Both fixed; committed runs scanned, no leak |
| 10/31 | D46 | Reported low coverage of real review comments | Asked whether and how to improve it, in the order the AI proposed | Coverage funnel; the remedy did not help on home-assistant, reported as a negative result |
| 10/31 | D50, D51 | Explained H6 (no gate scored higher) | Asked whether this meant trading performance for safety, and what happens when the gate cannot judge right from wrong | Code-cited review; all safeguards together, which cost 21 points (reported) |
| 10/31 | D52–D56 | — | Brought an external review: the gate "proves itself", correct notes held by mistake, guards only at task level, quarantine does not reach code | Two-layer evidence, graded handling, rule-level checks, impact tracing, gateway v2 |
| 10/31 | D57 | v2 still held 8 correct notes | Said the real bottleneck was why they were held, and asked for them to be split into three causes | All were false conflicts cited from legacy code; v3 holds 0 |
| 10/31 | D58 | — | Asked for proof that v3 tells trusted, wrong and undecidable advice apart, not just that it passes tests | Frozen judgement set; found the hole: from an empty memory, 5 of 10 wrong cases became rules via R2 |
| 11/01 | D60 | Counterfactual check (D59) | Pointed out that automatic reverts were not enough, that business rules and code conventions need different checks, that a trusted reviewer's mistakes were unsolved; asked to keep "uncertain" | Gateway v4 with three states: 0 critical errors on every frozen set |
| 11/01 | D61–D63 | — | Asked for human review in the lifecycle, independence of soft evidence, and the measured benefit and cost of review | Independence by origin (attacks counted 4/6 → 0/6); review queue; replay showed review cost 79% → 70% |
| 11/01 | D64 | — | Proposed value scores, tiers, dynamic top-k and a crowding ablation | AI advised not fitting weights and adding a displacement measure; criticality-first removed displacement |
| 11/01 | D65 | The AI wrote that I had agreed to stop | Corrected it: I had not; asked how C compares with v3.1 | Same-session comparison: v3.1 better than Attest |
| 11/01 | D67 | Two-layer number audit (deterministic script + a model that wrote nothing) | Asked for it to run locally or on GitHub first | 0 wrong numbers; the one number without a source was rerun and saved |
| 11/01 | D68 | Explained the Context Manager | Asked whether it was just a sliding window and whether that was too naive | Reading the code found two ways to exceed the budget; fixed; contexts byte-identical on recorded scenarios |
| 11/01 | D69, D70 | A competitive review, then a security benchmark ("strategy b") | Stopped the run and asked, against the assessment brief, whether the direction had drifted | AI agreed the weight had shifted to security; the dose experiment was dropped; the README front page was rebuilt around what reviewers look for, with growth as the main line |
| 11/01 | D71 | Proposed confirming "a gate without a performance cost"; then found its own premise wrong (the main memories hold 9 notes, so the cost was not crowding) | Agreed to go ahead | Redesigned to compare the gates themselves, rules committed first; all three met: v3.1 not worse than no gate, better than the preregistered gate, 0 poison applied |
| 11/01 | README | A list of modules and features | Every module must answer: what real problem it solves for a coding agent, why existing approaches fall short, and which data shows it works | The "Each module" table, with what did not work listed separately |

<a id="中文说明"></a>
## 中文说明

本项目的大部分代码和文档由 Claude 编写。这里只保留影响方向的决定，与 `DECISIONS.md` 的 D 编号对应（完整理由、替代方案和证据见该文件）。每一行写明 AI 提出或产出了什么、我做了什么判断或纠正、结果如何；纠正来自 AI 自查时会注明。排期、重跑、措辞等日常事项不记录。

关键的几次纠正：不复用自己看不懂的 AI 代码（D2）；要求站在成熟开源项目上，并与已发表的方案对比（D3）；密钥只放在仓库 secret，AI 不接触（D4、D14）；坚持证据门槛，不为提高召回而降低（D23）；冻结前必须独立复核（cf5d879）；看结果前先定判读规则（D31、预注册）；把"为什么还挂起正确笔记"作为真正的瓶颈（D57）；要求证明门控能区分可信、错误与无法判断的建议（D58、D60）；纠正 AI 声称"已经说好停止"（D65）；中断"策略 b"，对照题目判断方向偏了，主线改回"成长"（D69、D70）；要求每个模块回答"解决什么问题、现有方案为何不行、用什么数据证明"。AI 自查发现的问题：两个真实漏洞（D43、D44）、确认实验的前提错误（D71）。
