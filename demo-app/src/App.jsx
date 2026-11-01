import { useEffect, useState } from "react";
import { LABELS, DATA } from "./lib";
import { cn } from "./ui";
import Opening from "./views/Opening";
import Playground from "./views/Playground";
import Security from "./views/Security";
import Evidence from "./views/Evidence";
import Governance from "./views/Governance";
import Research from "./views/Research";

const VIEWS = [
  ["opening", "开场", "这次演示看什么", Opening],
  ["playground", "成长实验场", "开记忆 vs 不开记忆", Playground],
  ["security", "安全实验室", "同一条毒评论", Security],
  ["evidence", "证据浏览器", "每条记忆的来历", Evidence],
  ["governance", "治理中心", "人来决定规则", Governance],
  ["research", "实验结果", "数据与局限", Research],
];
const fromHash = () => VIEWS.find(v => v[0] === location.hash.slice(1))?.[0] || "opening";

export default function App() {
  const [view, setView] = useState(fromHash());
  useEffect(() => { const f = () => setView(fromHash()); addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const go = k => { location.hash = k; setView(k); scrollTo(0, 0); };
  const V = VIEWS.find(v => v[0] === view)[3];
  return (
    <div className="min-h-full" style={{ paddingLeft: "max(16px, env(safe-area-inset-left, 0px))", paddingRight: "max(16px, env(safe-area-inset-right, 0px))" }}>
      <div className="mx-auto grid max-w-[1280px] gap-6 py-5 lg:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="grid content-start gap-5 lg:sticky lg:top-5 lg:self-start">
          <div className="grid gap-0.5"><span className="text-[22px] font-black tracking-tight">Attest</span><span className="text-xs text-soft">编码智能体的团队记忆</span></div>
          <nav aria-label="视图" className="flex gap-1 overflow-x-auto lg:grid lg:overflow-visible">
            {VIEWS.map(([k, t, d]) => (
              <button key={k} onClick={() => go(k)} aria-current={view === k ? "page" : undefined}
                className={cn("grid shrink-0 rounded-md px-3 py-2 text-left", view === k ? "bg-sheet shadow-[inset_3px_0_0_var(--pen)]" : "hover:bg-sheet")}>
                <span className="text-sm font-bold">{t}</span><span className="hidden text-xs text-soft lg:block">{d}</span></button>))}
          </nav>
          <div className="hidden gap-1.5 border-t border-rule pt-4 text-xs text-soft lg:grid">
            {LABELS.map(([a, b]) => <div key={a}><b className="text-ink">{a}</b>：{b}</div>)}
            <div>回放已提交的运行记录（{DATA.source_commit}），不是现场调用模型。</div>
          </div>
        </aside>
        <main className="min-w-0" data-view={view}><V go={go} /></main>
      </div>
    </div>
  );
}
