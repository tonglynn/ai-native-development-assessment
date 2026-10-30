# Real review history: results / 真实评审历史：结果

Exploratory, outside the preregistered main experiment (PREREGISTRATION 4b).
Method: `scripts/retro_eval.py`. Merged, reviewed PRs of a public repository are
ordered by merge date. Each memory system learns from the oldest 29 PRs (the
reviewers' comments and the merged diff); for each of the 16 newest PRs it recalls
6 notes from the title and description, and an independent judge
(`deepseek-v4-pro`; memory is written by `deepseek-flash`) decides, with notes
anonymised and shuffled, which reviewer comments of a reusable "convention" kind
the notes would have anticipated (coverage) and which notes were relevant to the PR
(precision).

探索性研究，不属于预注册主实验。按合并时间排序，用较早的 29 个 PR 学习，在最新的 16 个 PR 上评估；评审模型与写记忆的模型不同，笔记匿名并打乱。

## Results / 结果

| Repository | Role | System | Convention comments anticipated (coverage) | Recalled notes relevant (precision) |
|---|---|---|---|---|
| saleor/saleor | **test** (not looked at before) | Attest | 1 / 25 (4%) | 11 / 96 (11%) |
| | | ReasoningBank-style | 4 / 25 (16%) | 12 / 96 (12%) |
| | | ACE-style (whole playbook) | 8 / 25 (32%) | 32 / 1328 (2%) |
| pallets/flask | development (gate changed after run 1) | Attest, run 1 | 1 / 21 (5%) | 13 / 96 (14%) |
| | | Attest, run 2 (new gate, D21) | 1 / 24 (4%) | 21 / 96 (22%) |
| | | ReasoningBank-style, run 1 / run 2 | 4 / 21 (19%), 2 / 24 (8%) | 17 / 96, 17 / 96 (18%) |
| | | ACE-style, run 1 / run 2 | 2 / 21 (10%), 1 / 24 (4%) | 76 / 1328 (6%), 52 / 1344 (4%) |

Gate version: both Saleor and Flask run 2 used the D21 gate (80% word overlap); the gate was then bounded by D25 (format tolerance only) and D27 (multi-line snippets). Their numbers are not re-run with the final gate. 两次运行使用的是 D21 版本的门槛，之后由 D25、D27 收紧/修正，数字未用最终门槛重跑。

Run folders: `runs/retro_saleor`, `runs/retro_flask` (run 1), `runs/retro_flask_gate2`
(run 2); `runs/retro_flask_cancelled` is an earlier run cancelled by hand and not used.

## What we conclude / 结论

1. **Attest shows no recall advantage on real review history.** On the test
   repository it anticipated 1 of 25 convention comments, fewer than both
   baselines. We report this as it is. 在真实仓库上，Attest 没有表现出召回优势。
2. **The differences are within the noise of this sample.** ReasoningBank's code
   did not change between the two Flask runs, yet its coverage went from 4/21 to
   2/24. With about 25 convention comments per repository, one versus four hits
   cannot separate the systems. No significance is claimed.
3. **Precision is similar or slightly better for Attest**, ACE's coverage comes
   from injecting the whole playbook (about 1,300 notes over 16 PRs, 2–6% relevant).
4. **Coverage limit of the evidence gate (D17/D21).** Most missed "convention"
   comments are not rules a diff can show: *rebase before merging*, *backport the
   migration source*, *resolve all review conversations*, *changes only to
   docstrings need no changelog entry*. Attest's gate requires a changed line that
   applies the rule, so these can never be learned. This is a deliberate trade
   (no rule without proof it was done) and a real limitation. We do not lower the
   gate to raise recall; process knowledge needs its own kind of evidence
   (see `PROCESS_MEMORY.md`). 证据门槛要求改动里有落实规则的那一行，因此流程类经验（rebase、backport、解决所有评论）永远学不到。这是有意的取舍，也是真实的局限；不会为了召回率降低门槛。
5. **What the gate change (D21) did.** On Saleor, 24 of 61 notes Attest kept are
   backed by documentation, test or configuration changes, which the old gate
   (added lines only, verbatim) would mostly have rejected; coverage did not
   change. Flask is development data for this change and is reported as such.

## Where Attest's claims rest instead / Attest 的主张依据在哪里

Scoping, versioned rules, retraction and resistance to poisoned advice: the
synthetic benchmark (held-out, control and stale tasks), the poison and scale stress
tests, and the retrieval scale test (`runs/retrieval_scale`). On real history the
claim is limited to: grounded notes with provenance, similar precision, no recall
advantage.
