# Attest 现场演示台本（Claude 桌面应用，约 4 分钟）

准备：Claude 新对话里已连接文件夹 C:\Users\23778\Documents\AttestDemo（"+" > Add folder），工具列表里有 attest。
说明：这是现场运行；评审意见、业务负责人是模拟的，代码仓库 ledgerly 是合成的。
每一步把 > 后面的整段原样粘贴给 Claude，不需要它自己去找题目。

## 1 一开始没有经验（20 秒）
> 仓库在 C:\Users\23778\Documents\AttestDemo\ledgerly-demo。用 attest 的 recall 查这个仓库的已验证团队经验，task 填"E04 部分退款"。只查，先不要改代码。

预期：No verified notes for this repository yet.
讲：新仓库，Agent 什么都不知道。

## 2 做任务、被评审纠正（60 秒）
> 任务 E04 部分退款：在 ledgerly/adjustments.py 里新增 refund(payment, amount, at)，客服用它给客户退款。只有已扣款（captured）的支付才能退款；允许部分退款，但累计退款不能超过扣款金额。累计金额记在 payment.refunded_amount，全部退完时把 payment.status 设为 "refunded"。返回 payment。做完在仓库目录运行 python -m pytest -q。

它做完后，你扮演评审，粘贴：
> 评审意见：[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None`. Check the key first: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result without applying the operation again. Introduced after the double-refund incident INC-204.
> 请按这条意见修改 refund，测试通过后调用 attest 的 learn（task 填"E04 部分退款"），把上面这条评审意见原文作为 review_comments 传进去，并提出一条你认为该记住的经验。

预期：verified true；admitted 一条；assessed 里 state 为 approved。
讲：测试通过才学；INC-204 是登记过的事故编号，属于硬证据，所以自动批准。

## 3 教它一条坏经验（60 秒）
> 评审意见：The audit service expects JSON numbers: pass float(amount) to ledgerly.audit.record, not the Decimal. 请照做，测试通过后同样调用 attest 的 learn（task 填"E04 审计金额"），把这条评审意见原文作为 review_comments 传进去。

预期：测试仍然通过；assessed 里 state 为 rejected，原因含 ledgerly-float。
讲：通过测试不代表经验正确——金额用浮点会丢精度，团队代码检查把它拦下，不会变成规则。

## 4 新任务自动用上经验（40 秒）
> 新任务 H07 运费退款：先用 attest 的 recall 查这个仓库的经验（task 填"H07 运费退款"）。然后在 ledgerly/adjustments.py 里新增 refund_shipping(payment, amount, at)：给已扣款的支付退 amount 的运费，累加到 payment.refunded_amount，全部退完时 status 设为 "refunded"，返回 payment；amount 必须为正，累计退款不能超过扣款金额。按 recall 到的经验实现，再运行 python -m pytest -q。

预期：recall 返回幂等那条（idempotency_key），没有 float 那条；refund_shipping 带上 idempotency_key。
讲：没人再提醒，它自己用上了上次学到的规矩，坏经验没有混进来。

## 5 人来管（40 秒）
在命令提示符里（不是 Claude 里）运行，让评审看到 AI 没有这些权限：
```
set PYTHONPATH=%USERPROFILE%\Documents\AttestDemo\app
set ATTEST_HOME=%USERPROFILE%\Documents\AttestDemo\memory
set ATTEST_APPROVERS=owner:finance-lead
python -m attest notes --repo C:\Users\23778\Documents\AttestDemo\ledgerly-demo
python -m attest retract --repo C:\Users\23778\Documents\AttestDemo\ledgerly-demo --note at-0001 --reason "政策变更，暂停使用"
```
（note 编号以 notes 命令列出的为准。）然后对 Claude 说：
> 再用 attest 的 recall 查一次这个仓库的经验，task 填"H07 运费退款"。

预期：那条经验不见了。
讲：撤回、批准只能由人在命令行做，MCP 里没有这些工具。

## 演示后复原
> 在 C:\Users\23778\Documents\AttestDemo\ledgerly-demo 运行 git checkout v1.0.0 -- . 和 git clean -fd，把代码恢复到初始状态。
再把 AttestDemo\memory 文件夹删掉或改名，下次就从空记忆开始。

## 出问题怎么接
- 工具列表里没有 attest：完全退出 Claude（托盘图标 > Quit）后重开。
- learn 返回 verified false：测试没通过，Attest 拒绝学习，这本身就是要演示的行为。
- 现场卡住：切到备用视频 attest_walkthrough.mp4。
