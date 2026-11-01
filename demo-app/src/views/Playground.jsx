import { useMemo, useState } from "react";
import { ReactFlow, Background, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import * as Switch from "@radix-ui/react-switch";
import { DATA, D, allNotes } from "../lib";
import { Panel, Stamp, Tag, Code, Source, cn } from "../ui";
import CodeDiff from "../CodeDiff";
import NoteDrawer from "./NoteDrawer";

function StepNode({ data }) {
  return (
    <div className={cn("w-[170px] rounded-md border bg-sheet px-3 py-2 text-left shadow-sm", data.selected ? "border-pen ring-2 ring-penwash" : "border-rule")}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="text-[13px] font-bold">{data.title}</div>
      <div className={cn("text-xs", data.tone === "bad" ? "text-bad" : data.tone === "ok" ? "text-ok" : "text-soft")}>{data.sub}</div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}
const nodeTypes = { step: StepNode };

export default function Playground() {
  const [memory, setMemory] = useState(true);
  const [n, setN] = useState(1);
  const [sel, setSel] = useState("recall");
  const [note, setNote] = useState(null);
  const cond = memory ? "attest_v4" : "no_memory";
  const run = D.reuse.runs.find(r => r.condition === cond && r.run === n);
  const files = DATA.reuse_files[`${cond}/${n}`];
  const notes = allNotes();
  const byId = Object.fromEntries(notes.map(x => [x.id, x]));
  const passes = c => D.reuse.runs.filter(r => r.condition === c && r.first_pass).length;
  const nodes = useMemo(() => [
    ["task", "任务 H04", "开具贷项通知单"],
    ["recall", "读取记忆", memory ? `注入 ${run.injected.length} 条笔记` : "记忆关闭"],
    ["agent", "智能体执行", `${files.trace.length} 步 · ${Math.round(files.seconds)} 秒`],
    ["tests", "隐藏测试", run.first_pass ? "全部通过" : `未通过：${(run.conv_failed || []).join("、")}`, run.first_pass ? "ok" : "bad"],
  ].map(([id, title, sub, tone], i) => ({ id, type: "step", position: { x: i * 205, y: 0 }, data: { title, sub, tone, selected: sel === id }, draggable: false })), [memory, n, sel]);
  const edges = ["task-recall", "recall-agent", "agent-tests"].map(e => { const [s, t] = e.split("-"); return { id: e, source: s, target: t, animated: true }; });
  const other = DATA.reuse_files[`${memory ? "no_memory" : "attest_v4"}/${n}`];
  const fname = Object.keys(files.files)[0];
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">同一个新任务，开记忆和不开记忆</h2>
        <p className="m-0 max-w-[68ch] text-soft">H04 没有参与任何经验生成。记忆来自前面 E02、E04、E06 三个任务学到、并经过门控和人工审核的笔记，跑 H04 时记忆冻结。开记忆 <b className="text-ok">{passes("attest_v4")}/3</b> 次第一次就通过，不开记忆 <b className="text-bad">{passes("no_memory")}/3</b>。</p>
      </div>
      <div className="flex flex-wrap items-center gap-5 rounded-lg border border-rule bg-sheet px-4 py-3">
        <label className="flex items-center gap-2.5 text-sm font-medium" htmlFor="mem">
          <Switch.Root id="mem" checked={memory} onCheckedChange={setMemory} className="relative h-6 w-11 rounded-full bg-rule data-[state=checked]:bg-pen">
            <Switch.Thumb className="block h-5 w-5 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[22px]" />
          </Switch.Root>
          记忆 {memory ? "开" : "关"}
        </label>
        <div className="flex items-center gap-1.5 text-sm"><span className="text-soft">第几次运行</span>
          {[1, 2, 3].map(k => <button key={k} onClick={() => setN(k)} className={cn("h-7 w-7 rounded border text-sm", k === n ? "border-pen bg-penwash text-pen" : "border-rule")}>{k}</button>)}</div>
        <div className="flex items-center gap-2"><span className="text-sm text-soft">这次结果</span><Stamp kind={run.first_pass ? "pass" : "fail"} /></div>
      </div>
      <Panel title="执行过程" aside={<span className="text-xs text-soft">点击节点查看当时发生了什么</span>}>
        <div className="h-[110px]"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView proOptions={{ hideAttribution: true }} nodesConnectable={false} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} onNodeClick={(_, nd) => setSel(nd.id)}><Background gap={18} size={1} color="var(--rule)" /></ReactFlow></div>
        <div className="mt-4 border-t border-rule pt-4">
          {sel === "task" && <Code>{D.reuse.task.issue}</Code>}
          {sel === "recall" && (memory ? (
            <div className="grid gap-2">
              <p className="m-0 text-sm text-soft">按仓库 ledgerly、版本 1.0.0 和文件过滤后，按与任务的相关度排序注入。点一条看它的证据链。</p>
              <ul className="ruled m-0 list-none p-0">{run.injected.map(id => byId[id] && (
                <li key={id}><button onClick={() => setNote(byId[id])} className="flex w-full flex-wrap items-center gap-3 py-2 text-left hover:text-pen">
                  <Tag tone="soft">{id}</Tag><span className="min-w-0 flex-1 text-sm">{byId[id].title}</span><Stamp kind={byId[id].review ? "approved" : byId[id].state || "none"} label={byId[id].review ? "人工批准" : undefined} /></button></li>))}</ul>
              {Object.entries(run.excluded || {}).map(([k, v]) => <p key={k} className="m-0 text-xs text-soft">{k} 没有作为规则注入：{v}</p>)}
            </div>) : <p className="m-0 text-sm text-soft">记忆关闭：智能体只拿到题目本身。</p>)}
          {sel === "agent" && (
            <ol className="ruled m-0 grid list-none p-0">{files.trace.map((s, i) => (
              <li key={i} className="grid gap-1.5 py-2.5"><div className="flex items-center gap-2 text-xs text-soft"><span className="font-mono">第 {i + 1} 步</span>{s.rc != null && <Tag tone={s.rc === 0 ? "ok" : "bad"}>exit {s.rc}</Tag>}</div>
                <Code className="max-h-28 overflow-auto">{s.cmd}</Code>
                {s.out && <details><summary className="cursor-pointer text-xs text-soft">输出</summary><Code className="mt-1 max-h-48 overflow-auto">{s.out}</Code></details>}</li>))}</ol>)}
          {sel === "tests" && (run.first_pass ? <p className="m-0 text-sm">第一次提交就通过了全部隐藏测试，包括幂等（C5）和超额审批（C6）。</p> :
            <div className="grid gap-1 text-sm"><p className="m-0">没通过的隐藏测试：</p>{(run.tests_failed || []).map(t => <code key={t}>{t}</code>)}</div>)}
        </div>
      </Panel>
      <Panel title="记忆改变了哪些代码" aside={<span className="text-xs text-soft">{fname}，第 {n} 次运行的最终版本</span>}>
        <CodeDiff original={(memory ? other : files).files[fname]?.after || ""} modified={(memory ? files : other).files[fname]?.after || ""} leftLabel="不开记忆" rightLabel="开记忆" />
      </Panel>
      <Source>runs/demo/reuse（真实运行的轨迹、最终 diff 和隐藏测试结果）；最终文件由记录下的 diff 应用到任务起始代码重建。</Source>
      <NoteDrawer note={note} onClose={() => setNote(null)} />
    </div>
  );
}
