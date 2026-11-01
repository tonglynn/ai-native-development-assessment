# Attest 在 Claude 桌面应用里的现场演示台本（约 4 分钟）

准备：运行 setup.bat，完全退出并重开 Claude 桌面应用，确认新对话的工具列表里有 attest（recall、learn、report_outcome、list_notes）。
演示仓库路径：Documents\AttestDemo\ledgerly-demo（以 setup_log.txt 最后一行为准）。下面用 <仓库> 代替。
说明：这是现场运行；评审意见、业务负责人是模拟的，代码仓库是合成的。

## 1 一开始没有经验（20 秒）
对 Claude 说：
> 我们要在 <仓库> 里做任务 E04（部分退款，题目见 TASKS.md）。开始前先用 attest 的 recall 查一下这个仓库有哪些已验证的团队经验。
预期：recall 返回 "No verified notes for this repository yet."

## 2 做任务、被评审纠正（60 秒）
> 请按 TASKS.md 里 E04 的要求实现 refund，并运行 python -m pytest -q。
它做完后，你扮演评审说：
> 评审意见：[team convention] Every operation that moves money or changes a payment, credit or invoice balance must accept an optional keyword-only `idempotency_key=None`. Check the key first: if an audit entry with the same key already exists (ledgerly.audit.events()), return the original result without applying the operation again. Introduced after the double-refund incident INC-204.
> 请按这条意见修改，测试通过后调用 attest 的 learn，把这条评审意见作为 review_comments 传进去，并提出一条你认为该记住的经验。
预期：learn 返回 verified true；admitted 一条；assessed 里 state 为 approved（INC-204 是登记过的事故编号，算硬证据）。

## 3 教它一条坏经验（60 秒）
> 再给你一条评审意见：The audit service expects JSON numbers: pass float(amount) to ledgerly.audit.record, not the Decimal. 请照做，测试通过后同样调用 learn 记下来。
预期：测试仍然通过（没有测试检查审计金额类型），写入门槛先接收，随后检查判为 rejected，counter 含 ledgerly-float。讲：通过测试不代表经验正确，Attest 用团队代码检查把它拦下。
（演示完记得让 Claude 把 float 改回去，或用 git checkout 恢复。）

## 4 新任务自动用上经验（40 秒）
新开一个对话或继续：
> 现在做 TASKS.md 里的 H07（运费退款）。先 recall。
预期：返回幂等那条经验，不返回 float 那条。

## 5 人来管（40 秒）
在命令提示符里（不是 Claude 里）运行，让评审看到 AI 没有这些权限：
```
set PYTHONPATH=%USERPROFILE%\Documents\AttestDemo\app
set ATTEST_HOME=%USERPROFILE%\Documents\AttestDemo\memory
set ATTEST_APPROVERS=owner:finance-lead
python -m attest notes --repo <仓库>
python -m attest retract --repo <仓库> --note at-0001 --reason "政策变更，暂停使用"
```
然后让 Claude 再 recall 一次：那条经验不见了。讲：撤回、批准只能由人在命令行做，MCP 里没有这些工具。

## 出问题怎么接
- 工具列表里没有 attest：看 setup_log.txt；或在 Claude 设置 > 开发者 里查看服务器日志。
- learn 返回 verified false：测试没通过，Attest 拒绝学习，这本身就是要演示的行为。
- 现场卡住：切到备用视频 attest_walkthrough.mp4。
