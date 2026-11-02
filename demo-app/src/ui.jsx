import * as Dialog from "@radix-ui/react-dialog";
import { useEffect, useState } from "react";
import { cva } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...a) => twMerge(clsx(a));

const button = cva("inline-flex items-center gap-2 rounded-md text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed", {
  variants: {
    tone: { primary: "bg-pen text-white hover:opacity-90", plain: "border border-rule bg-sheet hover:border-pen", quiet: "hover:bg-penwash" },
    size: { md: "px-3.5 py-2", sm: "px-2.5 py-1 text-xs" },
  },
  defaultVariants: { tone: "plain", size: "md" },
});
export const Button = ({ tone, size, className, ...p }) => <button className={cn(button({ tone, size }), className)} {...p} />;

const STAMP = { approved: ["text-ok", "批准"], uncertain: ["text-hold", "待人工"], rejected: ["text-bad", "拒绝"], rule: ["text-bad", "存为规则"],
  none: ["text-ok", "未写入"], pass: ["text-ok", "通过"], fail: ["text-bad", "未通过"], refused: ["text-bad", "拒绝"], done: ["text-ok", "完成"],
  superseded: ["text-soft", "已取代"], retired: ["text-soft", "已撤回"] };
export function Stamp({ kind, label, className }) {
  const [c, t] = STAMP[kind] || ["text-soft", kind];
  const icon = { approved: "✓", pass: "✓", none: "✓", done: "✓", rejected: "✕", fail: "✕", refused: "✕", rule: "!", uncertain: "‖", superseded: "↻", retired: "–" }[kind] || "•";
  return <span className={cn("stamp text-xs", c, className)}><span aria-hidden="true" className="stamp-i">{icon}</span>{label || t}</span>;
}
export const Tag = ({ tone = "pen", children, className }) => {
  const m = { pen: "bg-penwash text-pen", ok: "bg-okwash text-ok", hold: "bg-holdwash text-hold", bad: "bg-badwash text-bad", soft: "bg-code text-soft" };
  return <span className={cn("rounded px-1.5 py-0.5 text-xs font-medium font-mono", m[tone], className)}>{children}</span>;
};
export const Panel = ({ title, aside, children, className }) => (
  <section className={cn("rounded-lg border border-rule bg-sheet", className)}>
    {title && <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-rule px-4 py-2.5"><h3 className="m-0 text-[15px] font-bold">{title}</h3>{aside}</header>}
    <div className="min-w-0 p-4">{children}</div>
  </section>
);
export const Code = ({ children, className }) => <pre className={cn("out m-0 rounded-md bg-code px-3 py-2 font-mono text-[12.5px] leading-relaxed", className)}>{children}</pre>;
export const Source = ({ children }) => <p className="m-0 text-xs text-soft">来源：{children}</p>;

export function Drawer({ open, onOpenChange, title, children }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content className="fixed bottom-0 right-0 top-0 flex w-[min(640px,100vw)] flex-col border-l border-rule bg-sheet shadow-xl" style={{ paddingTop: "env(safe-area-inset-top,0px)" }}>
          <div className="flex items-start justify-between gap-3 border-b border-rule px-5 py-3">
            <Dialog.Title className="m-0 text-lg font-bold">{title}</Dialog.Title>
            <Dialog.Close asChild><Button size="sm" aria-label="关闭">关闭</Button></Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">证据详情</Dialog.Description>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const STATUS = { replay: ["真实实验回放", "bg-penwash text-pen"], record: ["真实实验记录", "bg-penwash text-pen"], live: ["浏览器现场运行", "bg-okwash text-ok"],
  notrun: ["未现场执行 · 依据不足", "bg-holdwash text-hold"], demo: ["演示身份", "bg-holdwash text-hold"], sim: ["模拟 / 合成", "bg-code text-soft"], baseline: ["对照基线", "bg-code text-soft"],
  pre: ["预先计算", "bg-code text-ink"], notimpl: ["尚未实现", "bg-badwash text-bad"] };
export const Status = ({ kind }) => { const [t, c] = STATUS[kind]; return <span className={cn("whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-medium", c)}>{t}</span>; };
export const Statuses = ({ kinds }) => <span className="flex flex-wrap gap-1">{kinds.map(k => <Status key={k} kind={k} />)}</span>;

// ---- plain-language layers (glossary.js): a term opens a drawer with what / why / how-it-is-built
import { TERMS, FEATURES, CAPS } from "./glossary";
export const openTerm = id => dispatchEvent(new CustomEvent("glossary", { detail: id }));
export function Term({ id, children }) {
  const t = TERMS[id] || FEATURES[id];
  if (!t) return children;
  return (
    <span className="group relative inline">
      <button type="button" onClick={() => openTerm(id)} aria-describedby={`tip-${id}`}
        className="cursor-help border-b border-dotted border-pen text-inherit [font:inherit] hover:text-pen focus-visible:text-pen">{children || t.zh}</button>
      <span id={`tip-${id}`} role="tooltip" className="pointer-events-none absolute left-0 top-full z-40 mt-1 hidden w-[min(320px,80vw)] rounded-md border border-rule bg-sheet px-3 py-2 text-left text-xs font-normal leading-relaxed text-ink shadow-lg group-hover:block group-focus-within:block">
        <b className="block text-[13px]">{t.zh} <span className="font-normal text-soft">{t.en}</span></b>{t.l1}<span className="mt-1 block text-soft">点击看为什么需要、怎么实现</span></span>
    </span>);
}
// Layer 1 always visible, layer 2 a short line, layer 3 behind an expander for technical reviewers.
export function Layers({ l1, l2, l3, className }) {
  return (
    <div className={cn("grid gap-1.5", className)}>
      {l1 && <p className="m-0 text-[15px]">{l1}</p>}
      {l2 && <p className="m-0 text-sm text-soft"><b className="font-medium text-ink">为什么需要：</b>{l2}</p>}
      {l3 && <details className="text-sm"><summary className="cursor-pointer text-xs font-medium text-pen">实现细节（技术评审）</summary><p className="m-0 mt-1 rounded-md bg-code px-3 py-2 font-mono text-[12px] leading-relaxed">{l3}</p></details>}
    </div>);
}
export function GlossaryDrawer() {
  const [id, setId] = useState(null);
  useEffect(() => { const f = e => setId(e.detail); addEventListener("glossary", f); return () => removeEventListener("glossary", f); }, []);
  const all = [...Object.entries(FEATURES).map(([k, v]) => [k, v, "功能"]), ...Object.entries(TERMS).map(([k, v]) => [k, v, "术语"])];
  const cur = id && id !== "*" ? (TERMS[id] || FEATURES[id]) : null;
  return (
    <Drawer open={!!id} onOpenChange={o => !o && setId(null)} title={cur ? `${cur.zh}` : "术语与功能表"}>
      {cur ? <div className="grid gap-4">
        <p className="m-0 text-sm text-soft">{cur.en}{cur.cap ? ` · 属于「${CAPS.find(c => c.id === cur.cap).zh}」` : ""}</p>
        <section className="grid gap-1"><h4 className="m-0 text-xs font-bold text-soft">一句话</h4><p className="m-0 text-[15px]">{cur.l1}</p></section>
        <section className="grid gap-1"><h4 className="m-0 text-xs font-bold text-soft">为什么需要</h4><p className="m-0 text-sm">{cur.l2}</p></section>
        <section className="grid gap-1"><h4 className="m-0 text-xs font-bold text-soft">Attest 怎么实现（代码与数据）</h4><p className="m-0 rounded-md bg-code px-3 py-2 font-mono text-[12.5px] leading-relaxed">{cur.l3}</p></section>
        <Button size="sm" onClick={() => setId("*")}>看全部术语</Button>
      </div> : <ul className="ruled m-0 list-none p-0">{all.map(([k, v, kind]) => (
        <li key={k}><button onClick={() => setId(k)} className="grid w-full gap-0.5 py-2.5 text-left hover:bg-penwash">
          <span className="text-sm font-bold">{v.zh} <span className="text-xs font-normal text-soft">{v.en} · {kind}</span></span><span className="text-xs text-soft">{v.l1}</span></button></li>))}</ul>}
    </Drawer>);
}
export function CapMap({ go, compact }) {
  return (
    <div className="grid gap-3 lg:grid-cols-3">{CAPS.map(c => (
      <section key={c.id} className="grid content-start gap-2 rounded-lg border border-rule bg-sheet p-4">
        <div className="flex items-baseline justify-between gap-2"><span className="font-mono text-xs text-soft">能力 {c.n}</span>{go && <button onClick={() => go(c.view)} className="text-xs font-medium text-pen">看演示</button>}</div>
        <h3 className="m-0 text-[17px] font-black leading-snug">{c.zh}<span className="block text-xs font-medium text-soft">{c.en}</span></h3>
        <p className="m-0 text-sm">{c.l1}</p>
        {!compact && <>
          <p className="m-0 text-xs text-soft"><b className="font-medium text-ink">传统做法的问题：</b>{c.why}</p>
          <p className="m-0 text-xs text-soft"><b className="font-medium text-ink">数据从哪来：</b>{c.data}</p>
          <details className="text-xs"><summary className="cursor-pointer font-medium text-pen">Attest 怎么做</summary><p className="m-0 mt-1 text-ink">{c.how}</p></details>
        </>}
        <div className="mt-1 flex flex-wrap gap-1.5">{c.subs.map(s => <Term key={s} id={s}><span className="rounded bg-penwash px-1.5 py-0.5 text-xs font-medium text-pen">{FEATURES[s].zh}</span></Term>)}</div>
      </section>))}</div>);
}
export function CapIntro({ id, scene }) {
  const c = CAPS.find(x => x.id === id);
  return (
    <div className="grid gap-2">
      <span className="font-mono text-xs text-soft">能力 {c.n} · {c.en}</span>
      <h2 className="m-0 text-2xl font-black">{c.zh}</h2>
      <p className="m-0 max-w-[70ch] text-[15px]">{c.l1}</p>
      <div className="grid max-w-[900px] gap-2 rounded-lg border border-rule bg-sheet p-3 text-sm sm:grid-cols-3">
        <div><b className="block text-xs text-soft">传统做法的问题</b>{c.why}</div>
        <div><b className="block text-xs text-soft">数据和依据从哪来</b>{c.data}</div>
        <div><b className="block text-xs text-soft">Attest 怎么实现</b>{c.how}<span className="mt-1 flex flex-wrap gap-1">{c.subs.map(s => <Term key={s} id={s}><span className="text-xs text-pen">{FEATURES[s].zh}</span></Term>)}</span></div>
      </div>
      {scene && <p className="m-0 max-w-[70ch] text-soft">{scene}</p>}
    </div>);
}
