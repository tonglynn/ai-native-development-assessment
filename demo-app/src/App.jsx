import { lazy, Suspense, useEffect, useState } from "react";
import { cn } from "./ui";
import Opening from "./views/Opening";
import Background from "./views/Background";
import How from "./views/How";
const Growth = lazy(() => import("./views/Growth"));
const Security = lazy(() => import("./views/Security"));
const Governance = lazy(() => import("./views/Governance"));
const Evidence = lazy(() => import("./views/Evidence"));
const Results = lazy(() => import("./views/Results"));

const VIEWS = [
  ["opening", "开场", "这个项目解决什么问题", Opening],
  ["background", "业务背景", "计费系统和三条规矩", Background],
  ["how", "它怎么工作", "经验的写入流程", How],
  ["growth", "场景一：成长", "开记忆 vs 不开记忆的运行过程", Growth],
  ["security", "场景二：防学坏", "毒药建议进来会怎样", Security],
  ["governance", "场景三：人来管", "审批、政策变更、审计", Governance],
  ["evidence", "证据详情", "为什么相信一条经验", Evidence],
  ["results", "表现如何", "三个结论和局限", Results],
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
          <div className="grid gap-0.5"><span className="text-[22px] font-black tracking-tight">Attest</span><span className="text-xs text-soft">AI 编程助手的团队记忆</span></div>
          <nav aria-label="演示步骤" className="flex gap-1 overflow-x-auto lg:grid lg:overflow-visible">
            {VIEWS.map(([k, t, d]) => (
              <button key={k} onClick={() => go(k)} aria-current={view === k ? "page" : undefined} className={cn("grid shrink-0 rounded-md px-3 py-2 text-left", view === k ? "bg-sheet shadow-[inset_3px_0_0_var(--pen)]" : "hover:bg-sheet")}>
                <span className="text-sm font-bold">{t}</span><span className="hidden text-xs text-soft lg:block">{d}</span></button>))}
          </nav>
          <div className="hidden gap-1.5 border-t border-rule pt-4 text-xs text-soft lg:grid">
            <div><b className="text-ink">真实回放</b>：已提交的运行记录</div><div><b className="text-ink">现场运行</b>：在你的浏览器里执行 Attest 的真实代码</div><div><b className="text-ink">模拟 / 合成</b>：评审意见、负责人决定、代码仓库与毒药</div>
          </div>
        </aside>
        <main id="main" className="grid min-w-0 content-start gap-8" data-view={view}>
          <Suspense fallback={<p className="text-soft">正在载入…</p>}><V go={go} /></Suspense>
          {i < VIEWS.length - 1 && <div className="border-t border-rule pt-4"><button onClick={() => go(VIEWS[i + 1][0])} className="text-sm font-medium text-pen">下一步：{VIEWS[i + 1][1]}</button></div>}
        </main>
      </div>
    </div>
    </>
  );
}
