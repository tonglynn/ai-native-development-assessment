import { useState } from "react";
import { DATA, D } from "../lib";
import { Panel, Stamp, Button, Tag, Source, cn } from "../ui";

const WHO = { "agent:coder": "智能体 agent:coder", "owner:finance-lead": "业务负责人 owner:finance-lead（模拟）" };
export default function Governance() {
  const [who, setWho] = useState("agent:coder");
  const [done, setDone] = useState({});
  const [g, setG] = useState(0);
  const rec = (id, actor) => D.review.find(s => s.id === id && s.who === actor);
  const act = id => { const r = rec(id, who); if (r) setDone(d => ({ ...d, [`${who}/${id}`]: r })); };
  const gov = DATA.govern_offline;
  const steps = gov.filter(s => s.who);
  const after = gov.find(s => s.step.startsWith("retrieval"));
  const audit = gov.find(s => s.step.startsWith("audit"));
  const forged = D.govern.find(s => s.step === "forged approval in the log");
  const tools = D.govern.find(s => s.tools).tools;
  const stepName = ["智能体尝试批准新阈值笔记", "智能体尝试用它取代旧规则", "负责人批准（依据 FIN-2026-11），并记录它取代 at-0005"];
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">什么能成为团队规则，由人决定</h2>
        <p className="m-0 max-w-[68ch] text-soft">待人工的笔记不会当作规则注入。你可以切换身份，亲手操作：每个按钮显示的都是这次运行里真实代码给出的结果；运行中没有记录的组合不能点。</p>
      </div>
      <Panel title="待审队列" aside={
        <div className="flex gap-1 rounded-md border border-rule p-0.5">{Object.entries(WHO).map(([k, l]) => <button key={k} onClick={() => setWho(k)} className={cn("rounded px-2.5 py-1 text-xs", who === k ? "bg-pen text-white" : "")}>{l}</button>)}</div>}>
        <ul className="ruled m-0 list-none p-0">{D.queue.map(q => {
          const r = rec(q.id, who), res = done[`${who}/${q.id}`];
          return (
            <li key={q.id} className="grid gap-2 py-3 sm:grid-cols-[1fr_auto] sm:items-center">
              <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><Tag tone="soft">{q.id}</Tag><b className="text-sm">{q.title}</b></div>
                <div className="mt-1 text-xs text-soft">为什么待人工：{q.hard?.length ? "" : "没有硬证据"}{q.counter?.length ? `，有反证：${q.counter.join("、")}` : ""}；学自 {q.learned_in}</div>
                {res && <div className="mt-2 flex flex-wrap items-center gap-2 text-sm"><Stamp kind={res.result.startsWith("refused") ? "refused" : res.result === "approved" ? "approved" : "uncertain"} label={res.result.startsWith("refused") ? "拒绝" : res.result === "approved" ? "批准" : "留在队列"} />
                  <span className="text-soft">{res.result.startsWith("refused") ? res.result.replace(/^refused: /, "") : res.result === "approved" ? `依据：${(res.evidence || []).join("、")}` : res.result}</span></div>}
              </div>
              <Button size="sm" tone={r ? "primary" : "plain"} disabled={!r || !!res} onClick={() => act(q.id)} title={r ? "" : "这次运行没有记录这个组合"}>{r?.action === "leave in queue" ? "留在队列" : "批准"}</Button>
            </li>);
        })}</ul>
      </Panel>
      <Panel title="政策变了：新阈值取代旧阈值" aside={<span className="text-xs text-soft">新笔记为模拟；检查与拒绝来自真实代码</span>}>
        <p className="m-0 text-sm text-soft">FIN-2026-11 把超额退款的审批阈值从 500.00 提到 1000.00。一条新的阈值笔记进入队列。</p>
        <ol className="ruled m-0 mt-3 list-none p-0">{steps.map((s, i) => (
          <li key={i} className="flex flex-wrap items-center gap-3 py-2.5">
            <Button size="sm" tone={i === g ? "primary" : "plain"} disabled={i !== g} onClick={() => setG(g + 1)}>{stepName[i]}</Button>
            {i < g && <><Stamp kind={s.result.startsWith("refused") ? "refused" : "done"} /><span className="min-w-0 text-sm text-soft">{s.result.replace(/^refused: /, "")}</span></>}
          </li>))}</ol>
        {g >= steps.length && (
          <div className="mt-3 grid gap-2 rounded-md bg-code p-3 text-sm">
            <b>现在给 H04 检索</b>
            <div>注入：{after.injected.map(i => <Tag key={i} tone={i === "at-0008" ? "ok" : "soft"} className="mr-1">{i}</Tag>)}</div>
            {Object.entries(after.excluded).map(([k, v]) => <div key={k}><Tag tone="bad">{k}</Tag> 不再注入：{v}</div>)}
            <div className="text-soft">旧规则仍在只追加的日志里：{after.old_still_in_log ? "是" : "否"}，随时可以追溯。</div>
          </div>)}
      </Panel>
      <Panel title="审计：每个决定都对得上">
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <div className="grid gap-1"><div className="flex items-center gap-2"><b>有人绕过接口，直接往日志里写了一条"智能体批准"</b><Stamp kind="refused" label="查出" /></div>
            {forged.audit.map((a, i) => <div key={i} className="text-soft">日志第 {a.seq} 条：{a.id} 由 <code>{a.by}</code> 决定，问题：{a.problems.join("、")}</div>)}</div>
          <div className="grid gap-1"><div className="flex items-center gap-2"><b>这次运行的全部决定</b><Stamp kind={audit.audit.length ? "refused" : "pass"} label={audit.audit.length ? `${audit.audit.length} 处问题` : "0 处问题"} /></div>
            <div className="text-soft">智能体通过 MCP 只能用：{tools.map(t => <code key={t} className="mr-1">{t}</code>)}，没有任何批准、撤回或取代工具。</div></div>
        </div>
      </Panel>
      <Source>runs/demo/demo.json（审核与伪造检查）、runs/demo/govern_offline.json（取代，scripts/demo_govern.py 在记录下的记忆上离线运行）</Source>
    </div>
  );
}
