import { useEffect, useState } from "react";
import { call, fetchJson } from "../py";
import { Panel, Stamp, Button, Code, Source, Tag, cn, CapIntro, Term } from "../ui";
import { Status, Statuses } from "../ui";

const WHO = [["agent:coder", "AI 智能体"], ["agent:distiller", "提出这条经验的提炼程序"], ["dev:alice", "未登记的员工"], ["owner:finance-lead", "业务负责人（登记的审批人）"]];
const explain = m => /agents and the note's proposer/.test(m) ? "智能体和提出这条经验的一方，都不能批准它。" : /not a registered approver/.test(m) ? "只有登记在审批人名单上的人能做决定。"
  : /say which evidence/.test(m) ? "批准必须写明依据。" : /not waiting for review/.test(m) ? "这条笔记不在待审状态，不能重复决定。" : /not an approved rule/.test(m) ? "只有已经批准的规则，才能取代旧规则。"
  : /agents cannot change/.test(m) ? "智能体不能改变什么算规则。" : /^approved/.test(m) ? "批准成功，这条笔记成为规则。" : /^rejected/.test(m) ? "驳回，这条笔记退役，记录保留在日志里。" : /superseded/.test(m) ? "取代成功：旧规则不再注入，记录保留。" : "";
export default function Governance() {
  const [ready, setReady] = useState(false), [status, setStatus] = useState(""), [who, setWho] = useState("agent:coder");
  const [queue, setQueue] = useState([]), [ret, setRet] = useState(null), [log, setLog] = useState([]), [audit, setAudit] = useState(null), [msgs, setMsgs] = useState([]);
  const [reason, setReason] = useState("matches the team rule"), [evidence, setEvidence] = useState("FIN-2026-09");
  const refresh = async () => { setQueue((await call("G.queue()")).result); setRet((await call("G.retrieve()")).result); setLog((await call("G.log(10)")).result); };
  useEffect(() => { (async () => { const ev = await fetchJson("demo_events.json");
    await call("(globals().__setitem__('G', web_engine.Governance(EV)), 'null')[1]", { EV: JSON.stringify(ev) }, setStatus); setReady(true); await refresh(); })(); }, []);
  const act = async (label, expr, args) => { const { result, ms } = await call(expr, args); setMsgs(m => [{ label, who, ...result, ms }, ...m].slice(0, 8)); await refresh(); return result; };
  const runAudit = async () => setAudit((await call("G.audit()")).result);
  if (!ready) return <div className="grid gap-2"><CapIntro id="govern" /><p className="text-soft">{status || "正在准备"}…</p></div>;
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <CapIntro id="govern" />
        <p className="m-0 max-w-[70ch] text-soft">待人工的经验不作为规则使用，而是进入<Term id="queue">待审队列</Term>，由业务负责人决定。以下操作均在浏览器中<b className="text-ink">现场调用</b> Attest 的真实审批代码（attest/memory/review.py），作用于演示运行写入的记忆。</p>
        <p className="m-0 max-w-[70ch] rounded-md bg-holdwash px-3 py-2 text-sm text-hold">身份是演示用的：切换身份只能演示"给定这个身份，规则会怎么判"。真正的身份认证、授权和持久化审计必须由可信的后端完成，这里不演示。</p>
      </div>
      <div className="flex flex-wrap items-center gap-2"><span className="text-sm text-soft">我现在是</span>{WHO.map(([k, l]) => <button key={k} onClick={() => setWho(k)} className={cn("rounded-full border px-3 py-1 text-sm", who === k ? "border-pen bg-pen text-white" : "border-rule bg-sheet")}>{l}</button>)}</div>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,380px)]">
        <div className="grid content-start gap-5">
          <Panel title={`待审队列（${queue.length}）`} aside={<Statuses kinds={["live", "demo"]} />}>
            <div className="mb-3 grid gap-2 sm:grid-cols-2">
              <label className="grid gap-1 text-xs text-soft" htmlFor="rs">理由<input id="rs" name="reason" autoComplete="off" value={reason} onChange={e => setReason(e.target.value)} className="rounded border border-rule bg-sheet px-2 py-1 text-sm text-ink" /></label>
              <label className="grid gap-1 text-xs text-soft" htmlFor="evd">依据（分号分隔，可留空试试）<input id="evd" name="evidence" spellCheck={false} autoComplete="off" value={evidence} onChange={e => setEvidence(e.target.value)} className="rounded border border-rule bg-sheet px-2 py-1 text-sm text-ink" /></label>
            </div>
            {queue.length === 0 && <p className="m-0 text-sm text-soft">队列是空的。点右边"新政策生效"，会有一条新的笔记进来。</p>}
            <ul className="ruled m-0 list-none p-0">{queue.map(q => (
              <li key={q.id} className="grid gap-2 py-3">
                <div className="flex flex-wrap items-center gap-2"><Tag tone="soft">{q.id}</Tag><b className="text-sm">{q.title}</b><Stamp kind="uncertain" /></div>
                <div className="text-xs text-soft">为什么待审：{q.hard?.length ? `硬证据 ${q.hard.join("、")}` : "没有硬证据"}{q.soft?.length ? `，软证据 ${q.soft.join("、")}` : ""}{q.counter?.length ? `，反证 ${q.counter.join("、")}` : ""}；学自 {q.learned_in}</div>
                <div className="flex gap-2"><Button size="sm" tone="primary" onClick={() => act(`批准 ${q.id}`, "G.approve(I, W, R, E)", { I: q.id, W: who, R: reason, E: evidence })}>批准</Button>
                  <Button size="sm" onClick={() => act(`驳回 ${q.id}`, "G.reject(I, W, R)", { I: q.id, W: who, R: reason })}>驳回</Button></div>
              </li>))}</ul>
          </Panel>
          <Panel title="新任务 H04 的检索与注入结果" aside={<Status kind="live" />}>
            {ret && <div className="grid gap-2 text-sm"><div>注入：{ret.injected.map(i => <Tag key={i} tone={i === "at-0008" ? "ok" : "soft"} className="mr-1">{i}</Tag>)}</div>
              {Object.entries(ret.excluded).map(([k, v]) => <div key={k}><Tag tone="bad">{k}</Tag> 不注入：<span className="text-soft">{v}</span></div>)}</div>}
            <p className="m-0 mt-2 text-xs text-soft">每次操作后都重新调用真实的检索代码。</p>
          </Panel>
          <Panel title="审计日志：记忆版本管理与来源追溯（只追加，最新 10 条）" aside={<Status kind="live" />}>
            <ol className="ruled m-0 list-none p-0 text-sm">{log.slice().reverse().map(e => <li key={e.seq} className="flex gap-3 py-1.5"><span className="w-10 shrink-0 font-mono text-xs text-soft">#{e.seq}</span><span className="w-12 shrink-0">{e.type}</span><span className="w-16 shrink-0 font-mono text-xs">{e.id || e.item}</span><span className="min-w-0 text-soft">{e.reason}</span></li>)}</ol>
          </Panel>
        </div>
        <div className="grid content-start gap-5">
          <Panel title="人工审核与政策变更" aside={<Statuses kinds={["live", "sim"]} />}>
            <p className="m-0 text-sm">FIN-2026-11 把超额退款的审批阈值从 500.00 提到 1000.00。</p>
            <div className="mt-3 grid gap-2">
              <Button size="sm" onClick={() => act("新政策生效：新阈值笔记进入队列（模拟）", "G.new_threshold_note()", {})}>1 新政策生效，新阈值笔记进入队列</Button>
              <Button size="sm" onClick={() => act("用 at-0008 取代 at-0005", "G.supersede(N, O, W, R)", { N: "at-0008", O: "at-0005", W: who, R: "FIN-2026-11 replaces FIN-2026-03" })}>2 记录：at-0008 取代旧阈值 at-0005</Button>
              <Button size="sm" onClick={() => act("通知：政策 FIN-2026-03 已变更", "G.policy_changed(P, W, R)", { P: "FIN-2026-03", W: who, R: "threshold raised" })}>通知：依赖 FIN-2026-03 的批准退回审核</Button>
            </div>
            <p className="m-0 mt-2 text-xs text-soft">先以业务负责人身份批准 at-0008，再做第 2 步；换个身份试试会怎样。新阈值笔记是模拟的。</p>
          </Panel>
          <Panel title="伪造批准测试" aside={<Statuses kinds={["live", "demo"]} />}>
            <p className="m-0 text-sm">假设有人绕过审批接口，直接往日志里写一条"已批准"。</p>
            <div className="mt-3 flex flex-wrap gap-2"><Button size="sm" onClick={() => act("伪造：以当前身份直接写入批准 at-0003", "G.forge(I, W)", { I: "at-0003", W: who })}>伪造一条批准</Button><Button size="sm" tone="primary" onClick={runAudit}>运行审计</Button></div>
            {audit && (audit.length ? <div className="mt-3 grid gap-2 text-sm"><div><Stamp kind="refused" label="查出问题" /></div>{audit.map((a, i) => <div key={i} className="text-soft">日志第 {a.seq} 条：{a.id}，决定人 <code>{String(a.by)}</code>，问题：{a.problems.join("、")}</div>)}</div>
              : <div className="mt-3 flex items-center gap-2 text-sm"><Stamp kind="pass" label="0 处问题" /><span className="text-soft">每个决定都由登记的审批人、带依据做出</span></div>)}
          </Panel>
          <div aria-live="polite"><Panel title="操作结果">
            {msgs.length === 0 && <p className="m-0 text-sm text-soft">还没有操作。</p>}
            <ol className="ruled m-0 list-none p-0">{msgs.map((m, i) => <li key={i} className="grid gap-1 py-2 text-sm"><div className="flex flex-wrap items-center gap-2"><Stamp kind={m.ok ? "done" : "refused"} /><b>{m.label}</b></div><div className="text-xs text-soft">身份 <code>{m.who}</code> · 代码返回：<code>{m.message}</code></div>{explain(m.message) && <div className="text-xs">{explain(m.message)}</div>}</li>)}</ol>
          </Panel></div>
        </div>
      </div>
      <Source>演示运行的记忆：runs/demo/memory/events.jsonl（真实）；操作由 scripts/web_engine.py 调用 attest/memory/review.py，在浏览器里现场执行；刷新页面即恢复原状。</Source>
    </div>
  );
}
