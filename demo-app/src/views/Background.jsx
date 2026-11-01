import { useState } from "react";
import { Panel, Code, Tag } from "../ui";
const RULES = [
  { k: "幂等", title: "同一个退款请求只能执行一次", story: "客户网络抖动，退款按钮点了两次，系统退了两次钱。", rule: "每笔动钱的操作都带一个唯一的请求编号（idempotency_key）；同一个编号再来一次，直接返回第一次的结果，不再退钱。",
    code: `def refund(payment, amount, at, *, idempotency_key=None, approved_by=None):\n    if idempotency_key is not None:\n        for entry in audit.events("refunded"):\n            if entry.get("idempotency_key") == idempotency_key:\n                return entry  # 重复请求：返回第一次的结果`, tag: "C5" },
  { k: "审批", title: "超过 500 元的退款要第二个人批准", story: "有客服给熟人退了一大笔钱，没人复核。", rule: "客服发起的退款超过 500.00，必须带上第二位审批人（approved_by），否则拒绝并报 approval_required。政策编号 FIN-2026-03，后来 FIN-2026-11 把阈值提到 1000.00。",
    code: `APPROVAL_THRESHOLD = round_money("500.00")\nif amount > APPROVAL_THRESHOLD and not approved_by:\n    raise BillingError("approval_required")`, tag: "C6" },
  { k: "审计", title: "每笔动钱的操作都要记审计日志", story: "月底财务对账，有几笔钱找不到记录。", rule: "退款、扣款、调账都要调用 ledgerly.audit.record(...) 写一条审计记录，金额保持精确的 Decimal 类型。",
    code: `audit.record("refunded", payment_id=payment.id, amount=amount)  # amount 是 Decimal，不能转成 float`, tag: "C4" },
];
export default function Background() {
  const [open, setOpen] = useState(0);
  return (
    <div className="grid gap-6">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">业务背景：一家 SaaS 公司的计费系统</h2>
        <p className="m-0 max-w-[68ch] text-soft">这家公司把老的计费系统迁移到新代码库 ledgerly，客服在里面处理退款、调账。AI 编程助手负责写这些功能，团队工程师做代码评审。公司、代码库和下面的事故都是为实验<b className="text-ink">合成</b>的业务情境，不是真实事故。</p>
      </div>
      <div className="grid gap-3 lg:grid-cols-3">
        {RULES.map((r, i) => (
          <button key={r.k} onClick={() => setOpen(i)} className={`grid content-start gap-2 rounded-lg border p-4 text-left ${open === i ? "border-pen bg-sheet" : "border-rule bg-sheet hover:border-pen"}`}>
            <span className="text-xs text-soft">团队规矩：{r.k} <Tag tone="soft">{r.tag}</Tag></span>
            <span className="text-[17px] font-bold">{r.title}</span>
            <span className="text-sm text-soft">起因：{r.story}</span>
          </button>))}
      </div>
      <Panel title={`在代码里长什么样：${RULES[open].title}`}>
        <p className="m-0 mb-3 text-sm">{RULES[open].rule}</p><Code>{RULES[open].code}</Code>
        <p className="m-0 mt-2 text-xs text-soft">代码为示意，根据演示运行中 AI 写出的最终代码简化。C4、C5、C6 是实验给这几条规矩的编号，隐藏测试会逐条检查。</p>
      </Panel>
      <Panel title="问题出在哪">
        <p className="m-0 max-w-[70ch]">这些业务规则可能分散在代码、测试、历史评审和团队规范中。每次遇到新任务，AI 不一定能找到并正确复用过去的经验，评审只好一遍遍重复。Attest 要解决的，是把<b>经过验证的</b>经验沉淀下来，并在<b>合适的</b>任务中重新使用；同时不让未经验证或有害的"经验"混进来。</p>
      </Panel>
    </div>
  );
}
