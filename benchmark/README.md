# Benchmark / 基准任务集

> **Status: DRAFT — not yet frozen.** It becomes frozen when `PREREGISTRATION.md`
> is committed. Changes after that are recorded as deviations.
>
> **状态：草案，尚未冻结。** 提交 `PREREGISTRATION.md` 时冻结，之后的任何修改都记为偏差。

## What it simulates / 模拟什么

A coding agent works on a team's private Python codebase whose rules are
**tribal knowledge**: they are not written in any issue or contributing guide,
are only partly visible in existing code, and are enforced in code review.

编码 Agent 在团队私有代码库里工作。这个库的规矩是**口口相传的经验**：issue 里不写、
没有贡献指南，只能从已有代码里部分看出来，靠代码评审把关。

| Repo / 仓库 | Description / 说明 |
|---|---|
| `ledgerly_v1` | Billing library (invoices, payments, subscriptions) / 计费库 |
| `ledgerly_v2` | Same library after finance policy FIN-2026-07: rounding switches to banker's rounding (see its CHANGELOG) / 财务政策变更后，舍入改为银行家舍入 |
| `simkit` | Control repo with the **opposite** conventions: plain floats, `ValueError`, float seconds / 对照仓库，规矩与 ledgerly 相反 |

ledgerly also contains six **legacy modules** "moved over from the old billing
monolith" (`pricing`, `promotions`, `importers`, `reporting`, `adjustments`,
`renewals`). They predate the conventions: floats, `ValueError`, naive
datetimes, no audit entries. Seven tasks add a function to one of them, where
copying the surrounding code is exactly the wrong move. This mirrors real
codebases, where the nearest example is often older than the current rules.

ledgerly 还包含六个从旧单体系统迁过来的**遗留模块**，它们早于现行规范：用 float、
`ValueError`、不带时区的时间、不写审计记录。有 7 个任务要在这些模块里新增函数，此时照抄周围
代码恰恰是错的。真实代码库也是这样：离你最近的示例往往比现行规矩更老。

### ledgerly conventions / ledgerly 的隐性规范

| ID | Convention / 规范 | Where it is (partly) visible / 哪里能部分看出 |
|---|---|---|
| C1 | Money is `Decimal` with exactly 2 decimals, rounded only via `money.round_money` (v1: half-up; v2: half-even) / 金额用两位小数的 `Decimal`，只用 `round_money` 舍入 | `money.py`, `invoice.py` |
| C2 | Invalid input raises `BillingError(code)`, never `ValueError` / 非法输入抛 `BillingError` | `errors.py`, `payments.py` |
| C3 | Datetimes are aware UTC; incoming datetimes go through `clock.ensure_utc` / 时间一律是带时区的 UTC | `clock.py`, `subscriptions.py` |
| C4 | Money-moving operations write `audit.record("<event>", <entity>_id=..., amount=...)` / 动钱的操作必须写审计记录 | `invoice.py`, `payments.py` |
| C5 | Money-moving operations take a keyword-only `idempotency_key` and do nothing if an audit entry with that key exists / 动钱的操作必须支持幂等键 | **nowhere — review only** / 代码中没有，只靠评审 |
| C6 | Support refunds and credits above 500.00 need `approved_by`, else `BillingError("approval_required")` (v2: 1000.00) / 超过阈值的退款和抵扣需要审批 | **nowhere — review only** / 代码中没有，只靠评审 |

The conventions come in two tiers. **C1–C4 are discoverable**: a careful agent
can infer them by reading the modern modules, so memory can at best save effort.
**C5–C6 are tribal**: they exist only in reviewers' heads, so without memory the
agent cannot know them. This split came out of the pilots (see Known risks).

规范分两层。**C1–C4 可发现**：仔细读新模块就能推断出来，记忆最多帮着省事。**C5–C6 是口口相传的**：
只存在于评审者的脑子里，没有记忆就无从得知。这个分层来自基线校准的发现（见"已知风险"）。

simkit conventions: **K1** float-only (no `Decimal`, no `datetime`), **K2** built-in `ValueError`.

## Tasks / 任务

Tasks placed in legacy modules / 放在遗留模块中的任务: E03 (`renewals`), E04 (`adjustments`),
E05 (`pricing`), H01 (`promotions`), H02 (`importers`), H03 (`reporting`), H04 (`adjustments`).

| Group / 组 | Tasks | Repo | Purpose / 用途 |
|---|---|---|---|
| experience / 经验生成 | E01–E06 | ledgerly_v1 | The only tasks memory may be written from / 只有这组可以写入记忆 |
| heldout / 留出 | H01–H10 | ledgerly_v1 | Same conventions, different functions; never used to write memory / 同样的规范，不同的函数；从不用来写记忆 |
| stale / 过期 | S01–S04 | ledgerly_v2 | Rounding policy (S01–S03) and approval threshold (S04) changed; v1 memories about them are now wrong / 舍入政策和审批阈值已变，v1 的相关经验失效 |
| control / 对照 | B01–B03 | simkit | ledgerly memories must **not** transfer here / ledgerly 的经验不应迁移到这里 |

Convention coverage / 规范覆盖：

| | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---|---|---|---|---|---|
| experience | E01 E05 | E02 E04 E05 E06 | E03 E06 | E04 E06 | E04 E06 | E04 |
| heldout | H01 H02 H05 H08 | H02 H04 H06–H10 | H03 H05 H08 H09 H10 | H04 H06 H07 H08 H10 | H04 H06 H07 H08 H10 | H04 H07 |

## Task layout / 单个任务的结构

```
tasks/<ID>/
  task.json        issue text shown to the agent + metadata / 给 Agent 的 issue 与元数据
  setup/           public tests added to the workspace / 公开测试
  stub/            code overlay the agent starts from / Agent 拿到的初始代码
  naive/           plausible solution WITHOUT team knowledge / 不了解团队规范时的"合理"写法
  reference/       correct solution / 正确解
  hidden_test.py   hidden tests; each docstring is the simulated review comment / 隐藏测试，docstring 即模拟评审意见
```

Files ending in `.append` are appended to the base file instead of replacing it.
以 `.append` 结尾的文件会追加到原文件末尾，而不是替换。

Hidden test names encode what they check: `test_func_*` = behaviour,
`test_conv_<ID>_*` = a team convention. **Review comments are simulated**: they
are the docstrings of failing hidden tests, not written by a person.

隐藏测试的命名说明了它检查什么：`test_func_*` 是功能，`test_conv_<ID>_*` 是团队规范。
**评审意见是模拟的**：它们来自失败隐藏测试的 docstring，不是真人写的。

## Validation / 自检

`python scripts/validate_benchmark.py` checks every task: the stub fails, the
naive solution passes public and behaviour tests but misses at least one
convention, and the reference solution passes everything. Latest result:
`validation.json` (23/23 valid).

`python scripts/validate_benchmark.py` 会逐个检查：初始代码会失败；naive 解能通过公开测试和功能测试，
但至少违反一条规范；参考解全部通过。最新结果见 `validation.json`（23/23 有效）。

## Known risks / 已知风险

- **Calibration history.** In the first no-memory pilot (`runs/pilot_nomem`)
  the agent read almost the whole 9-module repository and passed 5/6 held-out
  tasks on the first attempt: no headroom. The legacy modules were added and
  seven tasks moved into them *before* any memory condition was run (see
  `PREREGISTRATION.md`, section 3).
  **校准记录。** 第一次无记忆基线中，Agent 几乎读完了整个 9 个模块的仓库，留出任务首次通过
  5/6，记忆没有提升空间。因此在运行任何有记忆的实验之前，加入了遗留模块并把 7 个任务移入其中。
- The second pilot (`runs/pilot2_nomem`) still passed 5/6 held-out tasks: the
  agent explicitly searched for conventions (`grep -rn round_money`) instead of
  copying the legacy code next to it. Conclusion: conventions visible anywhere
  in the code are discovered by a capable agent. Two review-only conventions
  (C5, C6) and stale task S04 were added, again before any memory condition ran.
  第二次基线留出任务仍通过 5/6：Agent 会主动搜索规范，而不是照抄旁边的遗留代码。结论：代码中
  任何地方可见的规范，强 Agent 都能找到。因此加入了两条只靠评审传承的规范（C5、C6）和过期任务 S04，
  同样是在运行任何有记忆的实验之前。
- After pilot 3 reached the target, four held-out tasks (H07–H10) were added to
  reduce the small-sample problem (6 → 10 held-out tasks); a fourth no-memory
  pilot on the held-out group checks they keep the difficulty in range.
  第三次基线达标后，为缓解样本量过小的问题，新增 4 个留出任务（6 → 10），并对留出组再做一次无记忆基线，
  确认难度仍在目标区间。
- Conventions C1–C4 are still visible in the modern modules, so a careful agent can
  infer them without memory. That is intended: memory should save effort and
  mistakes, not be the only way to succeed.
  规范在新模块中仍然可见，仔细的 Agent 不靠记忆也能做对。这是有意的：记忆应该减少犯错和工作量，
  而不是成功的唯一途径。
- The tasks and conventions were designed by the author, so they are not a
  neutral sample of real-world work. Mitigations: held-out tasks, the control
  repo, preregistration, and reporting every regression.
  任务和规范由作者设计，不是真实工作的中立样本。对策：留出任务、对照仓库、预注册、逐条报告回归。
