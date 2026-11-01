import { useState } from "react";
import { DATA, sysName, pct } from "../lib";
import { Panel, Button, Source } from "../ui";
import Chart, { theme } from "../Chart";

export default function Results() {
  const [more, setMore] = useState(false);
  const t = theme(), g = DATA.d71, m = DATA.main, d70 = DATA.d70, vs = m.vs_no_memory.attest;
  const arms = ["reasoningbank", "ace", "attest", "attest_no_gate", "attest_secure_v31", "attest_secure_v4"];
  const grp = s => s.startsWith("attest_secure") ? t.pen : s.startsWith("attest") ? t.hold : t.soft;
  const C = [
    ["会成长", `${pct(m.rate.no_memory.heldout)} → ${pct(m.rate.attest.heldout)}`, "11 个从没参与学习的新任务，第一次提交就做对的比例（每个条件 33 次运行）。",
      `预注册主实验：代码在任何记忆运行之前冻结（cf5d879）。相对无记忆 +${Math.round(vs.mean_diff * 100)} 个百分点，95% 区间 [${Math.round(vs.ci_low * 100)}, ${Math.round(vs.ci_high * 100)}]。`],
    ["不会被教坏", `${d70.attest_secure_v4.rule}/60`, `60 次投毒攻击中，门控 v4 把毒药批准成规则的次数；同类基线 ${d70.ace.rule}/60（ACE 式）到 ${d70.reasoningbank.rule}/60（ReasoningBank 式）。`,
      `口径：0/60 指没有毒药成为规则，不是什么都没存：另有 ${d70.attest_secure_v4.stored} 条作为"待人工"笔记保留，只在所属文件里带标记显示。两个基线是本项目按论文复现的版本。探索性实验（D70）。`],
    ["门槛不拖累效果", `${pct(g["pass@1"].attest_secure_v31)}`, `门控 v3.1 在正常任务上的成绩，与完全不设门槛（${pct(g["pass@1"].attest_no_gate)}）持平；同一轮的投毒流里，55 次留出运行 ${g.poison_float.attest_secure_v31.heldout_runs_applying_poison} 次照着毒药做。`,
      `口径：82% 是 v3.1 的成绩（v4 为 ${pct(g["pass@1"].attest_secure_v4)}）；0/55 是"照做毒药的运行次数"，和上面 D70 的"写入数量"不是一回事。11 个任务 × 5 次重复，判读规则事先提交，三条全部满足；但这是探索性实验（D71），v3.1 是在主实验之后设计的。`],
  ];
  return (
    <div className="grid gap-5">
      <div className="grid gap-2"><h2 className="m-0 text-2xl font-black">表现如何</h2><p className="m-0 max-w-[70ch] text-soft">三个结论，每个都写明它是怎么测的、只能说明什么。</p></div>
      <div className="grid gap-3 lg:grid-cols-3">{C.map(([a, n, d, k]) => (
        <section key={a} className="grid content-start gap-2 rounded-lg border border-rule bg-sheet p-5">
          <h3 className="m-0 text-lg font-black">{a}</h3><div className="text-[2.4rem] font-black leading-none tabular-nums">{n}</div><p className="m-0 text-sm">{d}</p><p className="m-0 text-xs text-soft">{k}</p></section>))}</div>
      <Panel title="局限">
        <ul className="m-0 grid gap-1.5 pl-5 text-sm">
          <li>只有一个合成基准（两个仓库、25 个冻结任务）和一个模型家族（DeepSeek），样本小。</li>
          <li>预注册的写入门槛有 −15 个百分点的代价（H6 不成立）；补回代价的 v3.1 是之后设计的。</li>
          <li>v3.1 仍会批准受信评审者给出的错误建议；v4 不会，但更多笔记要等人审核。</li>
          <li>在真实仓库的评审历史上覆盖率低：25 条规则里 13 条没有任务教过。</li>
        </ul>
      </Panel>
      <div><Button onClick={() => setMore(!more)}>{more ? "收起完整数据" : "看完整数据"}</Button></div>
      {more && <>
        <Panel title="同一轮、各系统自己学习：成长与安全（D71）">
          <Chart height={340} label="横轴干净任务的 pass@1，纵轴投毒流里照做毒药的运行数" option={{
            grid: { left: 60, right: 30, top: 44, bottom: 50 }, tooltip: { formatter: p => `${p.data.name}<br/>正常任务 ${p.data.value[0]}%<br/>照做毒药 ${p.data.value[1]}/55` },
            xAxis: { name: "正常任务：第一次通过率（%）", nameLocation: "middle", nameGap: 30, min: 55, max: 90, axisLabel: { color: t.soft }, nameTextStyle: { color: t.soft }, splitLine: { lineStyle: { color: t.rule } } },
            yAxis: { name: "照做毒药的运行（/55）", min: -2, max: 32, axisLabel: { color: t.soft }, nameTextStyle: { color: t.soft }, splitLine: { lineStyle: { color: t.rule } } },
            series: [{ type: "scatter", symbolSize: 16, data: arms.map(s => ({ name: sysName[s], value: [Math.round(g["pass@1"][s] * 100), g.poison_float[s].heldout_runs_applying_poison], itemStyle: { color: grp(s) }, label: { position: s === "attest_secure_v31" ? "top" : s === "attest_secure_v4" ? "bottom" : "right" } })),
              label: { show: true, formatter: p => p.data.name, color: t.ink, fontSize: 12 } }] }} />
        </Panel>
        <Panel title="预注册主实验">
          <div className="overflow-x-auto"><table className="w-full border-collapse text-sm tabular-nums"><thead><tr className="border-b border-rule text-left text-soft">{["条件", "新任务", "政策变更后的任务", "另一个仓库（对照）"].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
            <tbody>{Object.entries(m.rate).map(([c, r]) => <tr key={c} className="border-b border-rule last:border-0"><td className="px-3 py-2 font-medium">{sysName[c]}</td><td className="px-3 py-2">{pct(r.heldout)}</td><td className="px-3 py-2">{pct(r.stale)}</td><td className="px-3 py-2">{pct(r.control)}</td></tr>)}</tbody></table></div>
        </Panel>
      </>}
      <Source>runs/main、runs/poison_channels、runs/gate_confirm；导出时的提交 {DATA.source_commit}</Source>
    </div>
  );
}
