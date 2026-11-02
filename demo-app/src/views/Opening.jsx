import { Button, CapMap, Term } from "../ui";
const Q = [
  ["为什么 AI 编程助手需要长期记忆？", "background"],
  ["经验从哪里来？", "how"],
  ["为什么不能直接相信 AI 学到的东西？", "security"],
  ["怎么判断一条经验值得保留？", "how"],
  ["为什么有些经验必须交给人审核？", "governance"],
  ["这些机制是怎么实现的、证据在哪？", "evidence"],
];
export default function Opening({ go }) {
  return (
    <div className="grid gap-7">
      <div className="grid gap-4">
        <h1 className="m-0 max-w-[20ch] text-[2.5rem] font-black leading-[1.1] tracking-tight">AI 编程助手不记得评审教过它什么。</h1>
        <p className="m-0 max-w-[62ch] text-lg text-soft">今天评审指出"重复的退款请求会退两次钱"，它改好了；下一个任务，它又犯同样的错。Attest 给 <Term id="agent">AI 编程助手</Term>一份团队的<Term id="memory">长期记忆</Term>：评审教过一次的经验，经过验证后记下来，下次自动用上；没有证据的、可能有害的，不让它记；拿不准的，交给人决定。</p>
      </div>
      <CapMap go={go} compact />
      <video className="w-full max-w-[920px] rounded-lg border border-rule bg-black" src="attest_mcp_live.mp4" controls playsInline preload="metadata" aria-label="Attest × Claude 桌面应用：一次真实运行（5 分钟，中英双语）">
        <track kind="subtitles" src="attest_mcp_live.vtt" srcLang="zh" label="中文 / English" />
      </video>
      <p className="m-0 -mt-4 text-xs text-soft">真实运行录屏：Claude 桌面应用通过 MCP 使用 Attest，两次会话共用一份团队记忆；等待部分已加速并标出倍速。仓库是合成的，评审意见和审批人是模拟的。</p>
      <p className="m-0 -mt-4 text-sm">答辩幻灯片：<a className="text-pen underline" href="../slides/attest_defense_slides.pdf" target="_blank" rel="noopener">PDF</a> · <a className="text-pen underline" href="../slides/attest_defense_slides.pptx">PowerPoint</a>（正文 14 页 + 证据索引与附录；幻灯片中的演示视频即上方录屏）</p>
      <section className="grid gap-2">
        <h2 className="m-0 text-lg font-black">这个演示依次回答六个问题</h2>
        <ol className="m-0 grid gap-1 pl-5 text-sm">{Q.map(([q, v]) => <li key={q}><button onClick={() => go(v)} className="text-left hover:text-pen">{q}</button></li>)}</ol>
        <p className="m-0 text-sm text-soft">每处都标着它是<b className="text-ink">浏览器现场运行</b>、<b className="text-ink">真实实验回放</b>、<b className="text-ink">预先计算</b>、<b className="text-ink">演示身份</b>还是<b className="text-ink">模拟</b>；带下划虚线的词可以点开，看一句话解释、为什么需要和具体实现。</p>
      </section>
      <div className="flex flex-wrap gap-3"><Button tone="primary" onClick={() => go("background")}>先看业务背景</Button><Button onClick={() => go("how")}>直接看工作原理</Button></div>
    </div>
  );
}
