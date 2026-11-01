import { D, LABELS } from "../lib";
import { Button } from "../ui";
const pass = c => D.reuse.runs.filter(r => r.condition === c && r.first_pass).length;
export default function Opening({ go }) {
  const poison = Object.fromEntries(D.poison.slice(1).map(p => [p.system, p]));
  return (
    <div className="grid gap-8">
      <div className="grid gap-4">
        <h1 className="m-0 max-w-[22ch] text-[2.6rem] font-black leading-[1.08] tracking-tight">编码智能体总在重犯评审已经纠正过的错误。</h1>
        <p className="m-0 max-w-[62ch] text-lg text-soft">Attest 让它只从验证过的经验中成长：经验要有可执行的证据才能成为规则，拿不准的交给人，每一次决定都能追溯。这里回放的是一次真实运行，你可以逐步查看智能体做了什么、门控为什么这样判。</p>
      </div>
      <video className="w-full max-w-[960px] rounded-lg border border-rule bg-black" src="attest_film.mp4" controls muted playsInline preload="metadata" aria-label="Attest 机制动画" />
      <div className="grid gap-3 sm:grid-cols-3">
        {[["playground", "看它怎样成长", `新任务 H04：开记忆 ${pass("attest_v4")}/3 通过，不开记忆 ${pass("no_memory")}/3。`],
          ["security", "看它怎样拒绝学坏", `同一条毒评论：ACE 式${poison.ace?.rule ? "写成了规则" : "未写入"}，ReasoningBank 式${poison.reasoningbank?.rule ? "写成了规则" : "未写入"}，Attest ${poison.attest_secure_v4?.stored ? "写入了" : "一条也没写"}。`],
          ["governance", "看人怎样管它", "智能体不能自己批准规则；政策变了由人取代旧规则；每个决定都能审计。"]].map(([k, t, d]) => (
          <button key={k} onClick={() => go(k)} className="grid gap-1.5 rounded-lg border border-rule bg-sheet p-4 text-left hover:border-pen">
            <span className="text-[17px] font-bold">{t}</span><span className="text-sm text-soft">{d}</span><span className="text-sm font-medium text-pen">打开</span>
          </button>))}
      </div>
      <div className="grid gap-1.5 text-sm">
        {LABELS.map(([a, b]) => <div key={a}><b>{a}：</b><span className="text-soft">{b}</span></div>)}
        <div className="text-soft">本页所有数值都由 <code>scripts/export_demo_data.py</code> 从已提交的运行记录导出，不是现场调用模型。</div>
      </div>
      <div><Button tone="primary" onClick={() => go("playground")}>从第一个场景开始</Button></div>
    </div>
  );
}
