import { useEffect, useMemo, useState } from "react";
import { fetchJson } from "../py";
import { Panel, Code, Stamp, Tag, Source, cn, CapIntro, Term } from "../ui";
import { Status, Statuses } from "../ui";

const COND = { attest: "开记忆（Attest）", no_memory: "不开记忆" };
const CONV = { C1: "金额精确舍入", C2: "错误码规范", C3: "时间统一为 UTC", C4: "记审计日志", C5: "幂等（重复请求只执行一次）", C6: "超额需审批" };
const NOTE_RX = { C1: /round_money|half-up|Decimal/i, C2: /BillingError/i, C3: /ensure_utc|\bUTC\b/i, C4: /audit\.record|audit entr/i, C5: /idempot/i, C6: /approv/i };
const CODE_RX = { C1: /round_money/, C2: /BillingError\(/, C3: /ensure_utc/, C4: /audit\.record\(/, C5: /idempotency_key/, C6: /approved_by/ };
function KeyEvidence({ run }) {
  const ret = run.spans.find(s => s.kind === "retrieve");
  const notes = ret ? ret.context.split("\n").filter(l => /^- \[/.test(l)) : [];
  const added = run.diff.split("\n").filter(l => l.startsWith("+") && !l.startsWith("+++")).join("\n");
  const t1 = run.spans.find(s => s.kind === "tests");
  const rows = (run.conventions || []).map(c => ({ c, note: notes.find(n => NOTE_RX[c]?.test(n)), code: CODE_RX[c]?.test(added), ok: !(t1?.conv_failed || []).includes(c) }));
  return (
    <div className="grid gap-2 rounded-lg border-2 border-pen bg-penwash/40 p-4">
      <div className="flex flex-wrap items-center gap-2"><b className="text-[15px]">这次任务为什么{run.first_pass ? "第一次就成功" : "第一次没成功"}</b><span className="text-xs text-soft">读取记忆 {ret ? `${ret.injected.length} 条经验` : "：记忆关闭"}</span></div>
      <div className="overflow-x-auto"><table className="w-full border-collapse text-sm"><thead><tr className="text-left text-xs text-soft"><th className="py-1 pr-3 font-medium">这个任务要守的规矩</th><th className="py-1 pr-3 font-medium">记忆里有相关经验吗</th><th className="py-1 pr-3 font-medium">代码落实了吗</th><th className="py-1 font-medium">第一次的隐藏测试</th></tr></thead>
        <tbody>{rows.map(r => <tr key={r.c} className="border-t border-rule"><td className="py-1.5 pr-3">{r.c} {CONV[r.c]}</td>
          <td className="py-1.5 pr-3">{r.note ? <span className="text-ok">有：{r.note.replace(/^- \[[\w-]+\] /, "").split(":")[0]}</span> : <span className="text-soft">{ret ? "没有" : "—"}</span>}</td>
          <td className="py-1.5 pr-3">{r.code ? <span className="text-ok">写了</span> : <span className="text-bad">没写</span>}</td>
          <td className="py-1.5">{r.ok ? <span className="text-ok">通过</span> : <span className="text-bad">失败</span>}</td></tr>)}</tbody></table></div>
      <p className="m-0 text-xs text-soft">按关键词从注入的记忆文本和最终 diff 里判断，是辅助阅读，不是模型的自述；测试结果是真实的。"代码落实"只看有没有写出对应的代码，写了也可能写错，以测试为准。</p>
    </div>
  );
}
const fmtMs = ms => ms == null ? "—" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
function kindLabel(s) { return { retrieve: "记忆", llm: "模型", tool: "命令", tests: "测试", review: "评审" }[s.kind]; }
function SpanDetail({ s }) {
  if (!s) return null;
  if (s.kind === "retrieve") return <div className="grid gap-2"><p className="m-0 text-sm"><b>上下文检索与记忆注入：</b>任务开始前，Attest 按仓库、版本和相关度检索，把 {s.injected.length} 条笔记（约 {s.memory_tokens} token）加进 AI 收到的提示里：</p><Code className="max-h-[420px] overflow-auto">{s.context}</Code></div>;
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
      <CapIntro id="learn" />
      <p className="m-0 max-w-[70ch] text-soft">演示：11 个<Term id="heldout">留出任务</Term>都没参与过经验学习。同一个任务，开记忆和不开记忆各跑 3 次，看 AI 每一步做了什么、<Term id="passat1">第一次</Term>有没有做对。全部是预注册主实验的<b className="text-ink">真实实验回放</b>；只展示模型可见的输入、输出和它执行的命令，不展示也没有开启思考过程。</p>
      <div className="flex flex-wrap items-end gap-4 rounded-lg border border-rule bg-sheet px-4 py-3">
        <label className="grid gap-1 text-xs text-soft" htmlFor="task">任务
          <select id="task" value={task} onChange={e => setTask(e.target.value)} className="rounded border border-rule bg-sheet px-2 py-1.5 text-sm text-ink">{tasks.map(([id, t]) => <option key={id} value={id}>{id}：{t}</option>)}</select></label>
        <div className="grid gap-1 text-xs text-soft">条件<div className="flex gap-1">{Object.entries(COND).map(([k, l]) => <button key={k} onClick={() => setCond(k)} className={cn("rounded border px-2.5 py-1.5 text-sm", cond === k ? "border-pen bg-penwash text-pen" : "border-rule")}>{l}</button>)}</div></div>
        <div className="grid gap-1 text-xs text-soft">第几次<div className="flex gap-1">{[1, 2, 3].map(k => { const r = all.find(x => x.task === task && x.condition === cond && x.rep === k); return <button key={k} onClick={() => setRep(k)} className={cn("flex items-center gap-1 rounded border px-2.5 py-1.5 text-sm", rep === k ? "border-pen bg-penwash" : "border-rule")}>{k}<span className={r.first_pass ? "text-ok" : "text-bad"}>{r.first_pass ? "✓" : "✗"}</span></button>; })}</div></div>
        <div className="ml-auto grid gap-0.5 text-sm"><span>这个任务：开记忆 <b className="text-ok">{sib("attest").filter(r => r.first_pass).length}/3</b>，不开 <b className="text-bad">{sib("no_memory").filter(r => r.first_pass).length}/3</b> 第一次通过</span><span className="text-xs text-soft">全部 11 个任务：开记忆 {overall("attest")}，不开 {overall("no_memory")}</span></div>
      </div>
      <Panel title={`${run.task}：${run.title}`} aside={<Status kind="replay" />}>
        <p className="m-0 mb-2 font-mono text-xs text-soft">任务 {run.task} · 运行 {run.path} · 条件 {cond} · 结果提交 {run.commit} · 代码冻结于 {run.frozen_at}</p>
        <details className="mb-3"><summary className="cursor-pointer text-sm text-soft">任务原文（AI 收到的题目）</summary><Code className="mt-2">{run.issue}</Code></details>
        <div className="mb-3 flex flex-wrap items-center gap-3 text-sm"><Stamp kind={run.first_pass ? "pass" : "fail"} label={run.first_pass ? "第一次就通过" : run.final_pass ? "评审后通过" : "未通过"} /><span className="text-soft">{run.attempts} 次提交 · {run.steps} 步 · {Math.round(run.seconds)} 秒 · 输入 {tot.p.toLocaleString()} / 输出 {tot.c.toLocaleString()} token · ${run.cost?.toFixed(4)}</span></div>
        <div className="mb-4"><KeyEvidence run={run} /></div>
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
      <Panel title="最终改动（这次运行提交的 diff）" aside={<Status kind="replay" />}><Code className="max-h-[420px] overflow-auto">{run.diff}</Code></Panel>
      <Source>runs/main（预注册主实验，代码冻结于 cf5d879）；每一行都来自轨迹文件 attempt*.traj.json 与 result.json。</Source>
    </div>
  );
}
