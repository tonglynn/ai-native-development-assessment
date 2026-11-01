import { useState } from "react";
import { ReactFlow, Background as Grid, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { D } from "../lib";
import { Panel, Code, Stamp, Tag, cn } from "../ui";

const E04 = D.learn.find(l => l.task === "E04");
const N = E04.new_notes[0];
const STEPS = [
  ["run", "1 AI 做任务", "AI 在代码库里改代码，第一次提交"],
  ["collect", "2 收集证据", "评审原话、改动的代码、隐藏测试结果"],
  ["gate", "3 写入门槛", "原话是否出自评审、是否落实在通过测试的改动里；独立证据；反事实检查"],
  ["judge", "4 三态判定", "批准、待人工或拒绝"],
  ["use", "5 检索与注入", "新任务开始前，只在适用的仓库和版本里取出相关规则"],
];
function Node({ data }) {
  return <div className={cn("w-[190px] rounded-md border bg-sheet px-3 py-2", data.on ? "border-pen ring-2 ring-penwash" : "border-rule")}>
    <Handle type="target" position={Position.Left} style={{ opacity: 0 }} /><div className="text-[13px] font-bold">{data.t}</div><div className="text-xs text-soft">{data.d}</div><Handle type="source" position={Position.Right} style={{ opacity: 0 }} /></div>;
}
export default function How() {
  const [sel, setSel] = useState("collect");
  const nodes = STEPS.map(([id, t, d], i) => ({ id, type: "n", position: { x: i * 215, y: 0 }, data: { t, d, on: sel === id }, draggable: false }));
  const edges = STEPS.slice(1).map(([id], i) => ({ id, source: STEPS[i][0], target: id, animated: true }));
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">它怎么工作：一条经验的写入流程</h2>
        <p className="m-0 max-w-[68ch] text-soft">普通的 AI 记忆，是让模型自己总结"学到了什么"，然后直接存下来。Attest 多了一道关：只有能拿出证据的经验才进得去。点下面每一步，看演示运行（任务 E04，部分退款）里这一步的真实数据。</p>
      </div>
      <Panel title="写入流程" aside={<span className="text-xs text-soft">点击节点</span>}>
        <div className="h-[120px]"><ReactFlow nodes={nodes} edges={edges} nodeTypes={{ n: Node }} fitView proOptions={{ hideAttribution: true }} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} nodesConnectable={false} onNodeClick={(_, n) => setSel(n.id)}><Grid gap={18} size={1} color="var(--rule)" /></ReactFlow></div>
        <div className="mt-4 grid gap-3 border-t border-rule pt-4 text-sm">
          {sel === "run" && <><p className="m-0">任务 E04 要求实现部分退款。AI 第一次提交后，隐藏测试发现两条规矩没做对：</p><div className="flex gap-2">{E04.attempts[0].conv_failed.map(c => <Tag key={c} tone="bad">{c} 未通过</Tag>)}</div><p className="m-0 text-xs text-soft">真实回放：runs/demo/learn/E04</p></>}
          {sel === "collect" && <><p className="m-0">评审给出的原话（评审意见是为实验编写的模拟内容）：</p>{E04.attempts[0].review_comments.map((c, i) => <Code key={i}>{c}</Code>)}<p className="m-0">AI 按评审修改后，第二次提交通过了全部隐藏测试。Attest 从这次任务里提炼出一条经验候选，并记下它落实在哪一行代码：</p><Code>{N.applied}</Code></>}
          {sel === "gate" && <><p className="m-0">写入门槛逐项检查这条候选：</p><ul className="m-0 grid gap-1 pl-5"><li>它引用的话，是不是评审的原话：是</li><li>它有没有落实在一次通过隐藏测试的改动里：是，见上一步那行代码</li><li>有没有独立证据：评审引用了登记过的政策编号，评审者在可信名单上</li><li>反事实检查：把那行改动撤掉，相关的隐藏测试会失败，说明这条经验确实是测试通过的原因</li></ul><p className="m-0 text-xs text-soft">硬证据：{(N.hard || []).join("、")}；软证据：{(N.soft || []).join("、")}（真实回放）</p></>}
          {sel === "judge" && <><div className="flex flex-wrap items-center gap-3"><b>{N.title}</b><Stamp kind={N.state} /></div>
            <p className="m-0">三态判定的规则：有反证且没有硬证据 → 拒绝；没有反证，并且有硬证据（登记的政策、反事实测试、团队代码检查）或两种软证据 → 批准；其余 → 待人工，交给业务负责人决定。</p>
            <p className="m-0 text-xs text-soft">批准表示满足系统设定的证据要求，不等于这条经验永远正确；政策变了，它会被取代或退回审核。</p></>}
          {sel === "use" && <><p className="m-0">新任务开始前，Attest 只在同一个仓库、版本范围内、相关的文件里检索，按相关度挑出规则交给 AI。待人工的笔记不当作规则。场景一会展示一个从没参与学习的新任务，开记忆和不开记忆的完整运行过程。</p></>}
        </div>
      </Panel>
    </div>
  );
}
