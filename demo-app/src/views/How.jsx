import { useState } from "react";
import { ReactFlow, Background as Grid, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { D, DATA } from "../lib";
import { Panel, Code, Stamp, Tag, cn, Term, Layers, CapMap } from "../ui";
import { Status, Statuses } from "../ui";
import { FEATURES } from "../glossary";

const E04 = D.learn.find(l => l.task === "E04");
const N = E04.new_notes[0];
const CF = DATA.counterfactual.filter(c => !String(c.status).startsWith("invalid")); // W5 excluded, as in the report
// Five stages of one note's life, each named after the feature it belongs to
const STEPS = [
  ["run", "1 任务与评审", "AI 改代码；评审纠正；隐藏测试判定", null],
  ["collect", "2 经验采集与沉淀", "收集评审原话、改动的代码、测试结果", "capture"],
  ["gate", "3 证据验证与记忆准入", "原话、落实、独立依据、反事实验证", "admit"],
  ["judge", "4 风险识别与分级处置", "批准、待人工或拒绝", "risk"],
  ["use", "5 上下文检索与记忆注入", "只在适用的仓库和版本里取出相关规则", "inject"],
];
function Node({ data }) {
  return <div className={cn("w-[200px] rounded-md border bg-sheet px-3 py-2", data.on ? "border-pen ring-2 ring-penwash" : "border-rule")}>
    <Handle type="target" position={Position.Left} style={{ opacity: 0 }} /><div className="text-[13px] font-bold">{data.t}</div><div className="text-xs text-soft">{data.d}</div><Handle type="source" position={Position.Right} style={{ opacity: 0 }} /></div>;
}
function Counterfactual() {
  const by = k => CF.filter(c => c.class === k);
  const ok = k => by(k).filter(c => c.counterfactual).length;
  const t4 = CF.find(c => c.case === "T4");
  return (
    <div className="grid gap-3 rounded-lg border border-rule bg-sheet p-4">
      <div className="flex flex-wrap items-center gap-2"><b className="text-[15px]"><Term id="counterfactual">反事实验证</Term>（Counterfactual Verification）</b><Status kind="replay" /></div>
      <p className="m-0 text-sm"><b>先回答一个问题：</b>AI 按评审改完代码，测试通过了，能不能说明"这条经验是对的"？不能。测试通过只说明代码整体没出错，那处修改可能根本没被测试检查到，换成别的写法测试也照样通过。</p>
      <p className="m-0 text-sm"><b>反事实验证的做法：</b>把这条经验对应的那处修改撤掉，其他代码保持不变，再运行一次测试。</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-md bg-okwash px-3 py-2 text-sm text-ok"><b>撤掉后测试失败</b><br />说明测试确实依赖这处修改，计为一项硬证据。</div>
        <div className="rounded-md bg-holdwash px-3 py-2 text-sm text-hold"><b>撤掉后测试仍然通过</b><br />测试不能为这条经验作证，不计入证据（不等于它是错的）。</div>
      </div>
      <p className="m-0 text-sm">真实例子：检验案例 T4，任务 E04 里的幂等修改（规矩 {t4.conventions.join("、")}）。把这处修改撤掉后，隐藏测试 <code>{t4.reverted_conv_failures.join("、")}</code> 失败，所以测试确实在为这条经验作证。</p>
      <div className="overflow-x-auto"><table className="w-full border-collapse text-sm tabular-nums"><thead><tr className="border-b border-rule text-left text-xs text-soft"><th className="py-1.5 pr-3 font-medium">冻结的检验案例（事先人工标注）</th><th className="py-1.5 pr-3 font-medium">案例数</th><th className="py-1.5 font-medium">反事实验证通过</th></tr></thead>
        <tbody>{[["trusted", "正确的经验"], ["wrong", "错误的经验"], ["undecidable", "无法判断对错"]].map(([k, l]) => <tr key={k} className="border-b border-rule last:border-0"><td className="py-1.5 pr-3">{l}</td><td className="py-1.5 pr-3">{by(k).length}</td><td className="py-1.5"><b className={k === "trusted" ? "text-ok" : "text-ink"}>{ok(k)}/{by(k).length}</b></td></tr>)}</tbody></table></div>
      <p className="m-0 text-xs text-soft">读法：它从没把错误的、无法判断的经验当作证据，正确的 {by("trusted").length} 条里有 {ok("trusted")} 条拿到了这项证据（另一条的测试不依赖那处修改）。判读规则事先写好（错误 0、无法判断 0、正确至少 6/8），结果满足。另有 1 个案例因建议本身让测试失败而被排除。</p>
      <details className="text-sm"><summary className="cursor-pointer text-xs font-medium text-pen">实现细节（技术评审）</summary><p className="m-0 mt-1 rounded-md bg-code px-3 py-2 font-mono text-[12px] leading-relaxed">{FEATURES.admit && "attest/memory/counterfactual.py：auto_revert 生成撤销后的代码，check / check_all 在任务工作区重新运行隐藏测试，记录 reverted_conv_failures。数据：runs/counterfactual/results.json（15 个案例，真实工作区，冷启动）。只在基准实验中运行；浏览器和桌面演示的 MCP 服务器都不运行它（需要整套测试环境）。"}</p></details>
    </div>);
}
export default function How({ go }) {
  const [sel, setSel] = useState("collect");
  const nodes = STEPS.map(([id, t, d], i) => ({ id, type: "n", position: { x: i * 225, y: 0 }, data: { t, d, on: sel === id }, draggable: false }));
  const edges = STEPS.slice(1).map(([id], i) => ({ id, source: STEPS[i][0], target: id, animated: true }));
  const f = FEATURES[STEPS.find(s => s[0] === sel)[3]];
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">工作原理：三项能力</h2>
        <p className="m-0 max-w-[70ch] text-soft">朴素的 AI 记忆由模型自行总结所学内容并直接写入。Attest 将这一过程拆分为三项能力：持续经验学习、可信记忆与安全准入、人工治理与全生命周期管理。展开"Attest 怎么做"可查看各项能力的机制。</p>
      </div>
      <CapMap go={go} />
      <div className="grid gap-2">
        <h2 className="m-0 text-xl font-black">一条经验的生命周期</h2>
        <p className="m-0 max-w-[70ch] text-soft">以演示运行中的任务 E04（部分退款）为例，依次查看每一步的说明与真实数据。</p>
      </div>
      <Panel title="一条经验从产生到被使用" aside={<Statuses kinds={["replay"]} />}>
        <div className="h-[120px]"><ReactFlow nodes={nodes} edges={edges} nodeTypes={{ n: Node }} fitView proOptions={{ hideAttribution: true }} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} nodesConnectable={false} onNodeClick={(_, n) => setSel(n.id)}><Grid gap={18} size={1} color="var(--rule)" /></ReactFlow></div>
        <div className="mt-4 grid gap-3 border-t border-rule pt-4 text-sm">
          {f && <Layers l1={f.l1} l2={f.l2} l3={f.l3} className="rounded-md bg-penwash/40 p-3" />}
          {sel === "run" && <><Layers l1="AI 先按自己的理解完成任务；评审指出问题，AI 再改；最后由隐藏测试判定是否真的做对。" l2="经验必须来自一个结果已经确认的任务：做错了还没改好的任务里学不到可靠的东西。" />
            <p className="m-0">任务 E04 要求实现部分退款。AI 第一次提交后，<Term id="tests">隐藏测试</Term>发现两条规矩没做对：</p><div className="flex gap-2">{E04.attempts[0].conv_failed.map(c => <Tag key={c} tone="bad">{c} 未通过</Tag>)}</div><p className="m-0 text-xs text-soft">真实回放：runs/demo/learn/E04</p></>}
          {sel === "collect" && <><p className="m-0">评审给出的原话（评审意见是为实验编写的模拟内容）：</p>{E04.attempts[0].review_comments.map((c, i) => <Code key={i}>{c}</Code>)}<p className="m-0">AI 按评审修改后，第二次提交通过了全部隐藏测试。Attest 从这次任务里提炼出一条经验候选，并记下它落实在<Term id="diff">代码改动</Term>的哪一行：</p><Code>{N.applied}</Code></>}
          {sel === "gate" && <><p className="m-0">写入门槛逐项检查这条候选，每一项都是能核对的事实，而不是 AI 的说法：</p><ul className="m-0 grid gap-1 pl-5"><li>它引用的话，是不是评审的原话：是</li><li>它有没有落实在一次通过隐藏测试的改动里：是，见上一步那行代码</li><li>有没有独立依据：评审引用了登记过的政策编号（<Term id="hard">硬证据</Term>），评审者在可信名单上（<Term id="soft">软证据</Term>）</li><li>反事实验证：见下面的说明</li></ul>
            <Counterfactual />
            <p className="m-0 text-xs text-soft">这条笔记的硬证据：{(N.hard || []).join("、")}；软证据：{(N.soft || []).join("、")}（真实回放）。</p></>}
          {sel === "judge" && <><div className="flex flex-wrap items-center gap-3"><b>{N.title}</b><Stamp kind={N.state} /></div>
            <p className="m-0"><Term id="threestate">三态判定</Term>的规则：有反证（例如团队代码检查发现问题）且没有硬证据 → <b className="text-bad">拒绝</b>；没有反证，并且有硬证据（登记的政策、反事实验证、团队代码检查）或两种软证据 → <b className="text-ok">批准</b>；其余 → <b className="text-hold">待人工</b>，交给业务负责人决定。</p>
            <p className="m-0 text-xs text-soft">批准表示满足系统设定的证据要求，不等于这条经验永远正确；政策变了，它会被取代或退回审核。</p></>}
          {sel === "use" && <><p className="m-0">新任务开始前，Attest 只在同一个仓库、<Term id="scope">版本范围</Term>内检索，按和任务的相关度挑出规则交给 AI。待人工的笔记不当作规则。能力 01 的演示展示了一个从没参与学习的新任务，开记忆和不开记忆的完整运行过程。</p></>}
        </div>
      </Panel>
    </div>
  );
}
