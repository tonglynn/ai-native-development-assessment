import { useRef } from "react";
import { CapMap, Term } from "../ui";
const CH = [["能力 01 · 经验学习与准入", 10], ["能力 02 · 风险拦截", 70], ["待人工判定", 134], ["新任务复用经验", 150], ["能力 03 · 人工治理", 165], ["会话二 · 跨会话复用", 215], ["结果小结", 295]];
const Q = [
  ["业务场景与长期记忆的需求", "background"],
  ["经验采集与写入路径", "how"],
  ["风险识别：可通过测试的错误建议", "security"],
  ["证据验证与三态判定", "how"],
  ["人工审核与职责分离", "governance"],
  ["实现依据与证据来源", "evidence"],
];
export default function Opening({ go }) {
  const vid = useRef(null);
  const jump = (t) => { const v = vid.current; if (!v) return; const go2 = () => { v.currentTime = t; v.play().catch(() => {}); }; if (v.readyState >= 1) go2(); else { v.addEventListener("loadedmetadata", go2, { once: true }); v.load(); } };
  return (
    <div className="grid gap-7">
      <div className="grid gap-4">
        <h1 className="m-0 max-w-[40ch] text-[2rem] font-black leading-[1.25] tracking-tight">Attest：AI 编码 Agent 的统一记忆治理——<br className="hidden md:block" />从评审反馈中学习可验证的经验</h1>
        <p className="m-0 max-w-[62ch] text-sm text-soft">通过标准 MCP 接口提供经验学习、证据验证、记忆检索与生命周期管理，与具体模型解耦。已验证：Claude Desktop（MCP，真实运行）与 mini-swe-agent（基准实验）；其他 MCP 客户端可接入，尚未测试。</p>
      </div>
      <CapMap go={go} compact />
      <video ref={vid} className="w-full max-w-[920px] rounded-lg border border-rule bg-black" src="attest_mcp_live.mp4" controls playsInline preload="metadata" aria-label="Attest × Claude 桌面应用：一次真实运行（5 分钟，中英双语）">
        <track kind="subtitles" src="attest_mcp_live.vtt" srcLang="zh" label="中文 / English" />
      </video>
      <div className="-mt-4 flex flex-wrap gap-2" aria-label="视频章节">{CH.map(([n, t]) => <button key={n} onClick={() => jump(t)} className="rounded-md border border-rule px-2.5 py-1 text-xs hover:border-pen hover:text-pen">{n} · {Math.floor(t / 60)}:{String(t % 60).padStart(2, "0")}</button>)}</div>
      <p className="m-0 text-xs text-soft">真实运行录屏：Claude 桌面应用通过 MCP 使用 Attest，两次会话共用一份团队记忆；等待部分已加速并标出倍速。仓库是合成的，评审意见和审批人是模拟的。</p>
      <p className="m-0 -mt-4 text-sm">答辩幻灯片：<a className="text-pen underline" href="../slides/attest_defense_slides.pdf" target="_blank" rel="noopener">PDF</a> · <a className="text-pen underline" href="../slides/attest_defense_slides.pptx">PowerPoint</a>（正文 14 页 + 证据索引与附录；幻灯片中的演示视频即上方录屏）</p>
      <section className="grid gap-2">
        <h2 className="m-0 text-lg font-black">演示结构</h2>
        <ol className="m-0 grid gap-1 pl-5 text-sm">{Q.map(([q, v]) => <li key={q}><button onClick={() => go(v)} className="text-left hover:text-pen">{q}</button></li>)}</ol>
        <p className="m-0 text-sm text-soft">各部分均标注材料类型：<b className="text-ink">浏览器现场运行</b>、<b className="text-ink">真实实验回放</b>、<b className="text-ink">预先计算</b>、<b className="text-ink">演示身份</b>或<b className="text-ink">模拟</b>。带下划虚线的术语可展开，查看定义、业务动机与具体实现。</p>
      </section>
    </div>
  );
}
