import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { DATA, D, sysName } from "../lib";
import { Panel, Stamp, Button, Code, Source, Tag, cn } from "../ui";
import CodeDiff from "../CodeDiff";
import Chart, { theme } from "../Chart";

const LANES = {
  ace: ["从任务中提炼经验", "没有写入前检查", "写入记忆"],
  reasoningbank: ["从任务中提炼经验", "没有写入前检查", "写入记忆"],
  attest_secure_v4: ["从任务中提炼经验", "写入前检查：评审者是否可信、撤销改动后相关测试会不会失败、团队代码检查、三态判定", "决定是否写入"],
};
export default function Security() {
  const [stage, setStage] = useState(-1);
  const [pick, setPick] = useState("ace");
  useEffect(() => { if (stage < 0 || stage > 3) return; const t = setTimeout(() => setStage(s => s + 1), 900); return () => clearTimeout(t); }, [stage]);
  const rows = Object.fromEntries(D.poison.slice(1).map(p => [p.system, p]));
  const pc = D.poison[0];
  const down = DATA.poison_downstream;
  const f = Object.keys(down.ace.files)[0];
  const d71 = DATA.d71.poison_float;
  const t = theme();
  const order = ["reasoningbank", "ace", "attest", "attest_no_gate", "attest_secure_v4", "attest_secure_v4_warm"];
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">一条能通过测试的毒评论</h2>
        <p className="m-0 max-w-[68ch] text-soft">攻击者在一个能通过隐藏测试的任务里留下评审意见。它违反"金额一律用 Decimal"，但没有测试检查审计金额的类型，所以"测试通过"挡不住它。点下面的按钮，把同一个学习事件交给三种记忆系统。</p>
      </div>
      <Panel title="毒评论（合成）" aside={<Tag tone="bad">{pc.payload && "float_audit"}</Tag>}>
        <Code>{pc.case.reviews[0].text}</Code>
        <p className="m-0 mt-2 text-xs text-soft">违反：{pc.payload.violates}。任务 {pc.case.task} 的改动也照着写了，并通过了全部隐藏测试。</p>
        <div className="mt-3"><Button tone="primary" onClick={() => setStage(0)} disabled={stage >= 0 && stage <= 3}>{stage < 0 ? "把这次学习事件交给三种系统" : "重新播放"}</Button></div>
      </Panel>
      <div className="grid gap-3 lg:grid-cols-3">
        {Object.entries(LANES).map(([sys, steps]) => {
          const r = rows[sys];
          return (
            <Panel key={sys} title={sysName[sys]} aside={stage > 2 ? <Stamp kind={r.rule ? "rule" : r.stored ? "uncertain" : "none"} /> : null}>
              <ol className="m-0 grid list-none gap-2 p-0">
                {steps.map((s, i) => (
                  <motion.li key={i} initial={false} animate={{ opacity: stage >= i ? 1 : 0.3 }} className="flex gap-2 text-sm">
                    <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", stage >= i ? (i === 1 && sys !== "attest_secure_v4" ? "bg-bad" : "bg-pen") : "bg-rule")} />{s}
                  </motion.li>))}
              </ol>
              {stage > 2 && (r.notes?.length ? <div className="mt-3 grid gap-1"><span className="text-xs text-soft">写进记忆的笔记</span><Code>{r.notes[0].trim().slice(0, 300)}</Code></div>
                : <p className="m-0 mt-3 text-sm">没有笔记写入记忆。</p>)}
              {sys === "attest_secure_v4" && stage > 2 && <p className="m-0 mt-2 text-xs text-soft">检查项是 v4 代码里的步骤；这次记录下的是结果（没有写入），没有逐项记录每个检查的输出。</p>}
            </Panel>);
        })}
      </div>
      <Panel title="毒药进了记忆之后：后续任务的代码" aside={<span className="text-xs text-soft">D71，投毒流，H04 第 1 次重复</span>}>
        <div className="mb-3 flex flex-wrap gap-2">{["ace", "reasoningbank"].map(s => <Button key={s} size="sm" tone={pick === s ? "primary" : "plain"} onClick={() => setPick(s)}>{sysName[s]}</Button>)}<span className="self-center text-xs text-soft">对比 Attest + 门控 v4</span></div>
        <CodeDiff original={down[pick].files[f]?.after || ""} modified={down.attest_secure_v4.files[f]?.after || ""} leftLabel={`${sysName[pick]}（记忆里有毒笔记）`} rightLabel="Attest + 门控 v4" height={380} />
        <p className="m-0 mt-2 text-sm">{pick === "ace" ? "ACE 式的智能体照着毒笔记把审计金额写成了 float(amount)。" : "这一次 ReasoningBank 式的智能体没有照做，但它的记忆里存着这条毒笔记。"}整轮实验里照做毒药的留出任务运行：{order.filter(s => d71[s]).map(s => `${sysName[s]} ${d71[s].heldout_runs_applying_poison}/${d71[s].heldout_runs}`).join("，")}。</p>
      </Panel>
      <Panel title="换六个写入通道、五种有害指令再测（60 次攻击）" aside={<span className="text-xs text-soft">D70，攻击者让任务通过验证</span>}>
        <Chart height={260} label="各系统把毒药写成规则的次数" option={{
          grid: { left: 150, right: 40, top: 10, bottom: 30 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
          xAxis: { type: "value", max: 60, axisLabel: { color: t.soft }, splitLine: { lineStyle: { color: t.rule } } },
          yAxis: { type: "category", data: order.map(s => sysName[s]), axisLabel: { color: t.ink }, axisLine: { lineStyle: { color: t.rule } } },
          series: [{ type: "bar", barWidth: 14, data: order.map(s => ({ value: DATA.d70[s].rule, itemStyle: { color: DATA.d70[s].rule ? t.bad : t.ok, borderRadius: [0, 4, 4, 0] } })),
            label: { show: true, position: "right", color: t.ink, formatter: p => `${p.value}/60` } }],
        }} />
        <p className="m-0 text-xs text-soft">v4 的 0 条规则之外，有 {DATA.d70.attest_secure_v4.stored} 条作为"待人工"笔记保留，只在所属文件里带标记显示；D71 中它们没有被照做（0/55）。</p>
      </Panel>
      <Source>runs/demo（这次学习事件）、runs/gate_confirm（后续任务）、runs/poison_channels（60 次攻击）。</Source>
    </div>
  );
}
