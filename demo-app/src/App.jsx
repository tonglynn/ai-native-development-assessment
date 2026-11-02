import { lazy, Suspense, useEffect, useState } from "react";
import { cn, GlossaryDrawer, openTerm, Status } from "./ui";
import { HONESTY } from "./glossary";
import Opening from "./views/Opening";
import Background from "./views/Background";
import How from "./views/How";
const Growth = lazy(() => import("./views/Growth"));
const Security = lazy(() => import("./views/Security"));
const Governance = lazy(() => import("./views/Governance"));
const Evidence = lazy(() => import("./views/Evidence"));
const Results = lazy(() => import("./views/Results"));

const VIEWS = [
  ["opening", "开场", "为什么 AI 需要长期记忆", Opening],
  ["background", "业务背景", "计费系统和三条团队规矩", Background],
  ["how", "工作原理", "三项能力与一条经验的生命周期", How],
  ["growth", "能力 01 持续经验学习", "开记忆 vs 不开记忆的真实运行", Growth],
  ["security", "能力 02 可信记忆与安全准入", "能通过测试的坏建议进来会怎样", Security],
  ["governance", "能力 03 人工治理与全生命周期", "审批、政策变更、审计", Governance],
  ["evidence", "来源追溯", "每条经验的 8 项证据", Evidence],
  ["results", "实验结果", "效果、安全、局限与尚未实现", Results],
];
const fromHash = () => VIEWS.find(v => v[0] === location.hash.slice(1))?.[0] || "opening";
export default function App() {
  const [view, setView] = useState(fromHash());
  useEffect(() => { const f = () => setView(fromHash()); addEventListener("hashchange", f); return () => removeEventListener("hashchange", f); }, []);
  const go = k => { location.hash = k; setView(k); scrollTo(0, 0); };
  const i = VIEWS.findIndex(v => v[0] === view), V = VIEWS[i][3];
  return (
    <>
    <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-pen focus:px-3 focus:py-2 focus:text-white">跳到正文</a>
    <div className="min-h-full" style={{ paddingLeft: "max(16px, env(safe-area-inset-left, 0px))", paddingRight: "max(16px, env(safe-area-inset-right, 0px))" }}>
      <div className="mx-auto grid max-w-[1320px] gap-6 py-5 lg:grid-cols-[230px_minmax(0,1fr)]">
        <aside className="grid content-start gap-5 lg:sticky lg:top-5 lg:self-start">
          <div className="grid gap-0.5"><span className="text-[22px] font-black tracking-tight">Attest</span><span className="text-xs text-soft">MCP Agent 的统一记忆治理</span></div>
          <nav aria-label="演示步骤" className="flex gap-1 overflow-x-auto lg:grid lg:overflow-visible">
            {VIEWS.map(([k, t, d]) => (
              <button key={k} onClick={() => go(k)} aria-current={view === k ? "page" : undefined} className={cn("grid shrink-0 rounded-md px-3 py-2 text-left", view === k ? "bg-sheet shadow-[inset_3px_0_0_var(--pen)]" : "hover:bg-sheet")}>
                <span className="text-sm font-bold">{t}</span><span className="hidden text-xs text-soft lg:block">{d}</span></button>))}
          </nav>
          <div className="hidden gap-2 border-t border-rule pt-4 text-xs text-soft lg:grid">
            <b className="text-ink">每处内容都标明它是什么</b>
            {HONESTY.map(([k, , d]) => <div key={k} className="grid gap-0.5"><Status kind={k} /><span>{d}</span></div>)}
          </div>
          <button onClick={() => openTerm("*")} className="hidden rounded-md border border-rule bg-sheet px-3 py-2 text-left text-sm font-medium text-pen hover:border-pen lg:block">术语与功能表<span className="block text-xs font-normal text-soft">带下划虚线的词都可以点开</span></button>
        </aside>
        <main id="main" className="grid min-w-0 content-start gap-8" data-view={view}>
          <div className="flex justify-end lg:hidden"><button onClick={() => openTerm("*")} className="text-sm font-medium text-pen">术语与功能表</button></div>
          <Suspense fallback={<p className="text-soft">正在载入…</p>}><V go={go} /></Suspense>
          {i < VIEWS.length - 1 && <div className="border-t border-rule pt-4"><button onClick={() => go(VIEWS[i + 1][0])} className="text-sm font-medium text-pen">下一步：{VIEWS[i + 1][1]}</button></div>}
        </main>
      </div>
    </div>
    <GlossaryDrawer />
    </>
  );
}
