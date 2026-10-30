# Process Memory (next-phase extension, design) / 流程记忆（下一阶段扩展，设计稿）

Status: **design only**. Not part of the preregistered main experiment, which is
not changed by it. To be evaluated as a separate extension experiment.
状态：仅设计；不改变主实验，作为独立扩展实验评估。

## Why / 动机

On real review history, most convention comments Attest missed are about *how the
team works*, not what the code says (`REAL_HISTORY.md`): rebase before merging,
backport migrations, resolve every review thread, CI must pass before release.
A diff cannot show these, so the code-evidence gate can never admit them. They need
evidence from the workflow itself.

## Memory types / 记忆类型

```
memory_types = ["code", "documentation", "configuration", "process"]
```

`code`, `documentation`, `configuration` keep today's gate (a changed line of the
verified diff of that file kind). `process` notes use process evidence:

| Team practice / 团队经验 | Process evidence / 流程证据 | Source |
|---|---|---|
| Rebase before merge | Merge commit absent / linear history; "rebase" requests followed by a force-push before merge | Git history, PR timeline events |
| Backport migrations | Linked backport PR to a release branch containing the same migration file | PR links, branches, file paths |
| Resolve all review threads before merge | All review threads resolved at merge time | GraphQL `reviewThreads.isResolved` |
| CI must pass before release | Successful required check runs on the release commit | Checks / Actions API |
| Changelog entry for user-visible changes | CHANGES file touched in PRs labelled as features/fixes | Diff + labels |

The evidence check stays deterministic: the model may propose "this PR shows the
team requires X", but code checks the metadata (for example, that every thread was
resolved before the merge timestamp).

## Not every remark is a rule / 一次意见不等于团队规范

A reviewer saying "please rebase" once is not a team policy. Three levels:

| Level / 等级 | Condition / 条件 | Use / 用法 |
|---|---|---|
| `policy` | Stated in a project document (CONTRIBUTING, PR template, branch protection, release checklist), quoted verbatim | Direct evidence; injected |
| `repeated` | The same requirement in ≥ 2 PRs from ≥ 2 different reviewers, each time followed (process evidence present) | Injected, with counts |
| `candidate` | Seen once, or never followed, or a single reviewer | Stored, **not injected**; promoted when it repeats or a policy is found |

Candidates are visible in the ledger and to people (who can promote or retract
them), so a one-off preference never reaches the agent as a team rule.
Lifecycle fields (`valid_from`, `superseded_by`, `last_verification`, D21) apply
unchanged; a process rule also expires when the policy document that backs it
changes.

## Evaluation (separate experiment) / 评估方案（独立实验）

- Data: the same retrospective protocol (train on older PRs, test on newer),
  Saleor and Flask, plus process metadata fetched with the PRs.
- Measure, split by memory type: coverage of process-type review comments,
  precision of injected notes, and the share of candidates later confirmed
  (repeated or backed by policy) versus never confirmed.
- Arms: Attest (code evidence only) vs Attest + process memory; the same judge
  and anonymisation as `scripts/retro_eval.py`.
- Risk to report: process metadata is partly missing in history (squash merges
  hide rebases; deleted branches), so absence of evidence is not evidence of
  absence; such PRs are counted separately.

## Scope for this assessment / 本次考核范围

Design and evaluation plan only. If time allows after the main experiment, a
prototype could start with the cheapest signal (review threads resolved at merge,
policy documents), since both are available from one GraphQL query.
