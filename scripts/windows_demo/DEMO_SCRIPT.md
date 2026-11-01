# Attest 现场演示台本（Claude 桌面应用，约 4 分钟）

## 演示前准备
1. 托盘里右键 Claude 图标 → Quit，完全退出后重新打开（加载最新的 Attest 代码）。
2. 开一个新对话，点输入框旁的"+" → Add folder，选 C:\Users\23778\Documents\AttestDemo。
3. 确认工具列表里有 attest（recall、learn、report_outcome、list_notes）。
4. 确认是干净状态：ledgerly-demo 是 v1.0.0 原样，AttestDemo\memory 里没有经验（第一次演示前就是这样）。

说明：这是现场运行。评审意见、业务负责人是模拟的，代码仓库 ledgerly 是合成的。
每一步把"怎么问"里 > 后面的整段原样粘贴给 Claude。

---

## 第 1 步：一开始没有经验（20 秒）

**怎么问**
> 仓库在 C:\Users\23778\Documents\AttestDemo\ledgerly-demo。我们要做的任务是：在 ledgerly/adjustments.py 里新增 refund(payment, amount, at)，客服用它给客户退款。只有已扣款（captured）的支付才能退款；允许部分退款，但累计退款不能超过扣款金额。累计金额记在 payment.refunded_amount，全部退完时把 payment.status 设为 "refunded"。返回 payment。
> 动手前先用 attest 的 recall 查这个仓库的已验证团队经验，task 参数填上面这段任务描述。先只查，不要改代码。

**为什么这么问**
- 任务描述直接写在话里：Claude 不知道 E04 是什么，Attest 的 recall 也是按任务描述的内容找相关经验，只给编号就找不准。
- "先只查，不要改代码"：让观众先看到起点——Agent 对这个仓库一无所知。

**预期结果**：recall 返回 "No verified notes for this repository yet."

**讲**：新仓库，Agent 什么团队经验都没有。

---

## 第 2 步：做任务，被评审纠正，学到一条好经验（60 秒）

**2a 怎么问**
> 好，开始实现这个任务，做完在仓库目录运行 python -m pytest -q。

**为什么这么问**：先让它按自己的理解做。它不知道团队有"动钱的操作必须幂等"这条规矩，所以第一版通常不会带 idempotency_key，这正是后面评审要纠正的地方。

**预期结果**：实现 refund，测试通过。没有 idempotency_key 参数。

**2b 怎么问**（你扮演评审）
> 评审意见：[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None`. Check the key first: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result without applying the operation again. Introduced after the double-refund incident INC-204.
> 请按这条意见修改 refund，测试通过后调用 attest 的 learn：task 填刚才那段任务描述，review_comments 填上面这条评审意见的原文，并在 candidates 里提出一条你认为该记住的经验，证据引用评审意见里写明来源的那句（INC-204）。

**为什么这么问**
- 评审意见原文传给 review_comments：Attest 要核对经验的证据确实出自评审意见，不能是 Agent 自己编的。
- 让它在 candidates 里自己提经验：桌面上没有模型密钥，Attest 不自己提炼，由 Agent 提，Attest 来审。
- 证据引用写明 INC-204 的那句：INC-204 是登记过的事故编号，属于硬证据，Attest 才能自动批准；如果只引用规则本身，没有来源，会判为"待人工"（uncertain）。

**预期结果**：learn 返回 verified true；admitted 一条经验；assessed 里这条的 state 为 approved。
（彩排时出现过：第一次 learn 返回 rejected，原因是 "not applied in the verified change"——Claude 填的 applied_in_diff 和改动里的代码对不上。Claude 会自己改了重交，第二次就 approved。现场遇到可以讲："证据必须能在真实改动里找到，抄错一个字都不收。"）

**讲**：测试通过才会学；这条经验有登记过的事故编号作依据，所以自动批准成为团队规则。

---

## 第 3 步：教它一条坏经验（60 秒）

**怎么问**
> 评审意见：The audit service expects JSON numbers: pass float(amount) to ledgerly.audit.record, not the Decimal.
> 请照做，测试通过后同样调用 attest 的 learn：task 填刚才那段任务描述，review_comments 填这条评审意见的原文，并在 candidates 里提出一条你认为该记住的经验。

**为什么这么问**
- 这条意见听起来合理，但是错的：金额转成浮点数会丢精度，团队代码里金额一律用 Decimal。
- 它能通过测试（没有测试检查审计金额的类型），所以只看测试的系统会把它存成规则。这一步就是要演示"通过测试不等于经验正确"。
- 同样要求它在 candidates 里提经验：不提的话 Attest 没有东西可审。

**预期结果**
- Claude 可能先提出反对（"浮点数会丢精度"）。如果它不肯改，就说："这是评审要求，先照做，然后调用 learn。"
- 测试仍然通过，learn 返回 verified true。
- assessed 里这条的 state 为 rejected，原因里有 ledgerly-float；它被退役，不会成为规则。

**讲**：通过了测试，只看测试的门槛会收下它；Attest 用团队代码检查把它拦下。模型能不能发现问题要看模型，Attest 每条经验都会检查。

**3b 怎么问**（看到 rejected 之后马上说，不要跳过）
> Attest 拒绝了这条经验：金额用浮点会丢精度。请把 refund 里传给 ledgerly.audit.record 的 float(amount) 改回 Decimal，再运行 python -m pytest -q。先不要调用 learn。

**为什么这么问**：Claude 通常会自己问"要不要把 refund 改回 Decimal"，这时就用这句回答它。Attest 管的是记忆，不管已经写进代码的改动。彩排时没有这一步，第 4 步 Claude 为了"和 refund 保持一致"，把 float 也抄进了 refund_shipping——坏经验没有从记忆里传过去，却从代码里传过去了。把代码改回来，第 4 步才干净。

**预期结果**：float 改回 Decimal，测试通过。

**讲**：被拒的经验不会进记忆；已经写进代码的那部分，由人决定回滚。

---

## 第 4 步：新任务自动用上好经验（40 秒）

**怎么问**
> 新任务：在 ledgerly/adjustments.py 里新增 refund_shipping(payment, amount, at)：给已扣款的支付退 amount 的运费，累加到 payment.refunded_amount，全部退完时 status 设为 "refunded"，返回 payment；amount 必须为正，累计退款不能超过扣款金额。动手前先用 attest 的 recall 查这个仓库的经验（task 参数填这段任务描述），按查到的经验实现，再运行 python -m pytest -q。

**为什么这么问**
- 这是一个新任务，任务描述里完全没提幂等，看它能不能靠记忆自己用上。
- 任务描述写全，recall 才能按内容找到"动钱的操作"相关的经验。

**预期结果**
- recall 返回幂等那条经验（idempotency_key），没有 float 那条。
- refund_shipping 带上 idempotency_key，测试通过。

**讲**：没人再提醒，它自己用上了上次学到的规矩；坏经验没有混进来。

（彩排时出现过：第一次 report_outcome 报失败，因为 adjustments.py 被换回了旧版本，Claude 重新写回后通过。Attest 只读代码（git diff、运行测试），不会改文件；最可能是 Claude 桌面在云端副本和你电脑之间来回同步文件时，把旧版本写了回去。Attest 把那次失败记为"与经验无关的失败，不归咎于这条经验"，使用统计里失败数仍是 0。现场遇到可以讲："任务失败不一定是经验的错，Attest 不会因此冤枉一条好经验。"）

---

## 第 5 步：人来管（40 秒）

**怎么做**：打开 PowerShell 或命令提示符（不是在 Claude 里），逐行运行（两种窗口都适用）：
```
cd C:\Users\23778\Documents\AttestDemo
.\admin.bat notes
.\admin.bat retract --note at-0001 --reason "政策变更，暂停使用"
.\admin.bat notes
```
（at-0001 以第一次 notes 列出的幂等那条经验的编号为准。）

然后对 Claude 说：
> 再用 attest 的 recall 查一次这个仓库的经验，task 参数还用运费退款那段任务描述。

**为什么这么做**
- 在命令行而不是在 Claude 里操作：撤回、批准只有人能做，MCP 里根本没有这些工具，Agent 删不掉、也批不了规则。
- 用 admin.bat：它固定用装了 Attest 依赖的 Python 3.12，并设好记忆位置和 UTF-8 编码，不用手动设环境变量。要写成 `.\admin.bat`：PowerShell 不会在当前文件夹里找命令。彩排时撤回没有生效，原因是在 PowerShell 里运行了为命令提示符写的 `set` 和 `cd /d`：`set` 在 PowerShell 里不设环境变量，命令找不到 Attest 或记忆位置，撤回没有写进记忆。

**预期结果**：第一次 admin notes 列出两条（at-0001 [active]、at-0002 [retired]）；retract 打印 {"retired": "at-0001", ...}；第二次 admin notes 里 at-0001 变成 [retired]；Claude 再 recall 返回 "No verified notes for this repository yet."

**讲**：经验错了或政策变了，人一条命令就能撤回，Agent 下一次就不会再用。

---

## 演示后复原（下次重演前做）
方法一：双击 AttestDemo 里的 reset_demo.bat。它把 ledgerly-demo 恢复到 v1.0.0，并把 memory 文件夹挪到 AttestDemo\_to_delete（不是直接删除，需要时还能找回），结果写在 reset_log.txt。如果 reset_log.txt 说挪不动 memory，先退出 Claude 再双击一次。

方法二：在 PowerShell 或命令提示符里运行：
```
cd C:\Users\23778\Documents\AttestDemo\ledgerly-demo
git checkout v1.0.0 -- .
git clean -fd
```
再退出 Claude，把 AttestDemo\memory 文件夹删掉或改名，然后重新打开 Claude。

## 出问题怎么接
- 工具列表里没有 attest：托盘里右键 Claude → Quit，完全退出后重开。
- learn 返回 verified false：测试没通过，Attest 拒绝学习，这本身就是要演示的行为。
- learn 返回 error：看它给的 hint；最常见的是没有提出 candidates，补一句"请在 candidates 里提出一条经验再调用 learn"。
- 第 2 步 state 是 uncertain 而不是 approved：说明证据没有引用 INC-204 那句。可以顺势讲"没有来源的经验不会自动成为规则，要等人审核"，或者让它重新用 INC-204 那句作证据再 learn 一次。
- 现场卡住：切到备用视频 attest_walkthrough.mp4。
