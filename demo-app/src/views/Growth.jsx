import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../py";
import { Panel, Code, Stamp, Tag, Source, cn } from "../ui";

const COND = { attest: "开记忆（Attest）", no_memory: "不开记忆" };
const CONV = { C1: "金额精确舍入", C2: "错误码规范", C3: "时间统一为 UTC", C4: "记审计日志", C5: "幂等（重复请求只执行一次）", C6: "超额需审批" };
const fmtMs = ms => ms == null ? "—" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
function kindLabel(s) { return { retrieve: "记忆", llm: "模型", tool: "命令", tests: "测试", review: "评审" }[s.kind]; }
function SpanDetail({ s }) {
  if (!s) return null;
  if (s.kind === "retrieve") return <div className="grid gap-2"><p className="m-0 text-sm">任务开始前，Attest 按仓库、版本和相关度检索，把 {s.injected.length} 条笔记（约 {s.memory_tokens} token）加进 AI 收到的提示里：</p><Code className="max-h-[420px] overflow-auto">{s.context}</Code></div>;
  if (s.kind === "llm") return <div className="grid gap-3 text-sm">
    <div className="flex flex-wrap gap-2"><Tag tone="soft">输入 {s.prompt_tokens ?? "—"} token</Tag><Tag tone="soft">其中缓存 {s.cached_tokens ?? 0}</Tag><Tag tone="soft">输出 {s.completion_tokens ?? "—"} token</Tag><Tag tone="soft">${(s.cost ?? 0).toFixed(5)}</Tag><Tag tone="soft">{fmtMs(s.ms)}</Tag></div>
    {s.input.length > 0 && <div className="grid gap-1"><span className="text-xs text-soft">这次调用新收到的内容（上一条命令的输出或评审意见；更早的对话省略）</span>{s.input.map((x, i) => <Code key={i} className="max-h-48 overflow-auto">{x}</Code>)}</div>}
    {s.output && <div className="grid gap-1"><span className="text-xs text-soft">模型输出的文字</span><Code className="max-h-48 overflow-auto">{s.output}</Code></div>}
    {s.tool_calls.map((c, i) => <div key={i} className="grid gap-1"><span className="text-xs text-soft">模型决定执行的命令</span><Code className="max-h-60 overflow-auto">{c}</Code></div>)}
  </div>;
  if (s.kind === "tool") return <div className="grid gap-2 text-sm"><div className="flex gap-2"><Tag tone={s.rc === 0 ? "ok" : "bad"}>退出码 {s.rc}</Tag><Tag tone="soft">{fmtMs(s.ms)}</Tag></div><span className="text-xs text-soft">命令</span><Code className="max-h-40 overflow-auto">{s.command}</Code><span className="text-xs text-soft">输出</span><Code className="max-h-[360px] overflow-auto">{s.output || "（无输出）"}</Code></div>;
  if (s.kind === "review") return <div className="grid gap-2 text-sm"><p className="m-0">第一次没通过，模拟的评审给出意见，AI 再试一次：</p>{s.comments.map((c, i) => <Code key={i}>{c}</Code>)}</div>;
  if (s.kind === "tests") return <div className="grid gap-2 text-sm">{s.passed ? <p className="m-0 text-ok">全部隐藏测试通过。</p> : <><p className="m-0 text-bad">没通过。没做对的团队规矩：</p><ul className="m-0 pl-5">{s.conv_failed.map(c => <li key={c}>{c}：{CONV[c] || ""}</li>)}</ul><span className="text-xs text-soft">失败的测试</span>{s.tests_failed.map(t => <code key={t}>{t}</code>)}</>}</div>;
  return null;
}
export default function Growth() {
  const [all, setAll] = useState(null);
  const [task, setTask] = useState("H04"), [cond, setCond] = useState("attest"), [rep, setRep] = useState(1), [sel, setSel] = useState(0);
  useEffect(() => { fetchJson("traces.json").then(setAll); }, []);
  useEffect(() => setSel(0), [task, cond, rep]);
  const tasks = useMemo(() => all ? [...new Map(all.map(r => [r.task, r.title])).entries()] : [], [all]);
  if (!all) return <p className="text-soft">正在载入 66 次运行的轨迹…</p>;
  const run = all.find(r => r.task === task && r.condition === cond && r.rep === rep);
  const sib = c => all.filter(r => r.task === task && r.condition === c);
  const tot = run.spans.filter(s => s.kind === "llm").reduce((a, s) => ({ p: a.p + (s.prompt_tokens || 0), c: a.c + (s.completion_tokens || 0) }), { p: 0, c: 0 });
  const overall = c => { const rs = all.filter(r => r.condition === c); return `${rs.filter(r => r.first_pass).length}/${rs.length}`; };
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">场景一：AI 如何成长</h2>
        <p className="m-0 max-w-[70ch] text-soft">11 个"留出任务"都没参与过经验学习。同一个任务，开记忆和不开记忆各跑 3 次，看 AI 每一步做了什么。全部是预注册主实验的<b className="text-ink">真实运行回放</b>；只展示模型可见的输入、输出和它执行的命令，不展示也没有开启思考过程。</p>
      </div>
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-rule bg-sheet px-4 py-3">
        <label className="grid gap-1 text-xs text-soft" htmlFor="task">任务
          <select id="task" value={task} onChange={e => setTask(e.target.value)} className="rounded border border-rule bg-sheet px-2 py-1.5 text-sm text-ink">{tasks.map(([id, t]) => <option key={id} value={id}>{id}：{t}</option>)}</select></label>
        <div className="grid gap-1 text-xs text-soft">条件<div className="flex gap-1">{Object.entries(COND).map(([k, l]) => <button key={k} onClick={() => setCond(k)} className={cn("rounded border px-2.5 py-1.5 text-sm", cond === k ? "border-pen bg-penwash text-pen" : "border-rule")}>{l}</button>)}</div></div>
        <div className="grid gap-1 text-xs text-soft">第几次<div className="flex gap-1">{[1, 2, 3].map(k => { const r = all.find(x => x.task === task && x.condition === cond && x.rep === k); return <button key={k} onClick={() => setRep(k)} className={cn("flex items-center gap-1 rounded border px-2.5 py-1.5 text-sm", rep === k ? "border-pen bg-penwash" : "border-rule")}>{k}<span className={r.first_pass ? "text-ok" : "text-bad"}>{r.first_pass ? "✓" : "✗"}</span></button>; })}</div></div>
        <div className="ml-auto grid gap-0.5 text-sm"><span>这个任务：开记忆 <b className="text-ok">{sib("attest").filter(r => r.first_pass).length}/3</b>，不开 <b className="text-bad">{sib("no_memory").filter(r => r.first_pass).length}/3</b> 第一次通过</span><span className="text-xs text-soft">全部 11 个任务：开记忆 {overall("attest")}，不开 {overall("no_memory")}</span></div>
      </div>
      <Panel title={`${run.task}：${run.title}`} aside={<span className="font-mono text-xs text-soft">{run.path} · 结果提交 {run.commit} · 代码冻结于 {run.frozen_at}</span>}>
        <details className="mb-3"><summary className="cursor-pointer text-sm text-soft">任务原文（AI 收到的题目）</summary><Code className="mt-2">{run.issue}</Code></details>
        <div className="mb-3 flex flex-wrap items-center gap-3 text-sm"><Stamp kind={run.first_pass ? "pass" : "fail"} label={run.first_pass ? "第一次就通过" : run.final_pass ? "评审后通过" : "未通过"} /><span className="text-soft">{run.attempts} 次提交 · {run.steps} 步 · {Math.round(run.seconds)} 秒 · 输入 {tot.p.toLocaleString()} / 输出 {tot.c.toLocaleString()} token · ${run.cost?.toFixed(4)}</span></div>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
          <ol className="m-0 max-h-[560px] list-none overflow-y-auto rounded-md border border-rule p-0" aria-label="执行轨迹">
            {run.spans.map((s, i) => (
              <li key={i}><button onClick={() => setSel(i)} className={cn("flex w-full items-center gap-2 border-b border-rule px-3 py-2 text-left text-sm last:border-0", sel === i ? "bg-penwash" : "hover:bg-code", s.kind === "tool" && "pl-7")}>
                <Tag tone={s.kind === "tests" ? (s.passed ? "ok" : "bad") : s.kind === "retrieve" ? "pen" : s.kind === "review" ? "hold" : "soft"}>{kindLabel(s)}</Tag>
                <span className="min-w-0 flex-1 truncate">{s.kind === "tool" ? s.command.split("\n")[0] : s.name}</span>
                <span className="shrink-0 font-mono text-xs text-soft">{s.kind === "llm" ? `${s.prompt_tokens ?? ""}t` : s.ms != null ? fmtMs(s.ms) : ""}</span></button></li>))}
          </ol>
          <div className="min-w-0"><SpanDetail s={run.spans[sel]} /></div>
        </div>
      </Panel>
      <Panel title="最终改动（这次运行提交的 diff）"><Code className="max-h-[420px] overflow-auto">{run.diff}</Code></Panel>
      <Source>runs/main（预注册主实验，代码冻结于 cf5d879）；每一行都来自轨迹文件 attempt*.traj.json 与 result.json。</Source>
    </div>
  );
}
