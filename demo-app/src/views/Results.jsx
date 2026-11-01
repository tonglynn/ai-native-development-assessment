import { useState } from "react";
import { DATA, sysName, pct } from "../lib";
import { Panel, Button, Source } from "../ui";
import { Status, Statuses } from "../ui";
import Chart, { theme } from "../Chart";

const SHORT = { no_memory: "不开记忆", reasoningbank: "ReasoningBank 式", ace: "ACE 式", attest: "Attest 预注册门槛", attest_no_gate: "Attest 无门槛", attest_no_scope: "Attest 无作用域", attest_secure_v31: "Attest + v3.1", attest_secure_v4: "Attest + v4" };
function Perf() {
  const t = theme(), m = DATA.main, g = DATA.d71, sec = Object.fromEntries(DATA.d71_secondary.map(r => [r.arm, r]));
  const arms = ["reasoningbank", "ace", "attest", "attest_no_gate", "attest_secure_v31", "attest_secure_v4"];
  const col = s => s.startsWith("attest_secure") ? t.pen : s.startsWith("attest") ? t.hold : t.soft;
  const axis = { axisLabel: { color: t.soft }, axisLine: { lineStyle: { color: t.rule } }, splitLine: { lineStyle: { color: t.rule } } };
  const bars = (names, values, fmt, colors) => ({ grid: { left: 130, right: 56, top: 8, bottom: 24 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", ...axis }, yAxis: { type: "category", data: names, inverse: true, ...axis, axisLabel: { color: t.ink } },
    series: [{ type: "bar", barWidth: 13, data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] } })), label: { show: true, position: "right", color: t.ink, formatter: p => fmt(p.value) } }] });
  const pre = ["no_memory", "reasoningbank", "ace", "attest", "attest_no_gate", "attest_no_scope"];
  const rate = v => { const [a, b] = v.split("/").map(Number); return Math.round((a / b) * 100); };
  const grouped = (cats, series) => ({ grid: { left: 130, right: 40, top: 30, bottom: 24 }, legend: { top: 0, textStyle: { color: t.soft }, itemWidth: 12, itemHeight: 8 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    xAxis: { type: "value", max: 100, ...axis, axisLabel: { color: t.soft, formatter: "{value}%" } }, yAxis: { type: "category", data: cats.map(s => SHORT[s]), inverse: true, ...axis, axisLabel: { color: t.ink } },
    series: series.map(([name, color, fn]) => ({ name, type: "bar", barWidth: 9, barGap: "30%", itemStyle: { color, borderRadius: [0, 3, 3, 0] }, data: cats.map(fn), label: { show: true, position: "right", color: t.soft, fontSize: 10, formatter: "{c}%" } })) });
  return (
    <div className="grid gap-4">
      <h3 className="m-0 text-lg font-black">性能比较</h3>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="新任务第一次通过率（预注册主实验）" aside={<Statuses kinds={["record", "baseline"]} />}>
          <Chart height={230} label="各条件的留出任务 pass@1" option={bars(pre.map(s => SHORT[s]), pre.map(s => Math.round(m.rate[s].heldout * 100)), v => `${v}%`, pre.map(col))} />
          <p className="m-0 text-xs text-soft">11 个任务 × 3 次重复。Attest 相对不开记忆的差值有 95% 区间（+21 到 +52 个百分点）；相对两个复现基线只证明"不更差"。</p>
        </Panel>
        <Panel title="同一轮：正常任务 vs 受投毒时（D71）" aside={<Statuses kinds={["record", "baseline"]} />}>
          <Chart height={260} label="正常流与投毒流的留出 pass@1" option={grouped(arms, [["正常任务", t.pen, s => Math.round(g["pass@1"][s] * 100)], ["受投毒时", t.bad, s => Math.round(g.poison_float[s]["heldout_pass@1"] * 100)]])} />
          <p className="m-0 text-xs text-soft">探索性；每组 55 次运行。投毒流里注入的是能通过测试的毒评论。</p>
        </Panel>
        <Panel title="业务风险：第一次提交就犯规的比例（D71 正常流）" aside={<Statuses kinds={["record", "baseline"]} />}>
          <Chart height={260} label="幂等、审批、审计规矩的失败率" option={grouped(arms, [["重复扣款（幂等 C5）", t.bad, s => rate(sec[s].c5_failed)], ["越权退款（审批 C6）", t.hold, s => rate(sec[s].c6_failed)], ["漏记审计（C4）", t.soft, s => rate(sec[s].c4_failed)]])} />
          <p className="m-0 text-xs text-soft">越低越好。描述性比较，未做显著性检验；每格的分母是需要这条规矩的运行数（15–30）。</p>
        </Panel>
        <Panel title="成本与记忆体积（D71 正常流）" aside={<Statuses kinds={["record", "baseline"]} />}>
          <div className="grid grid-cols-2 gap-2">
            {[["每个任务的步数", s => sec[s].steps, v => v], ["每次运行成本（美元）", s => sec[s].cost_usd, v => `$${v}`], ["记忆里的笔记数", s => sec[s].notes_in_memory, v => v], ["每次注入的记忆 token", s => sec[s].memory_tokens, v => v]].map(([title, fn, fmt]) => (
              <div key={title}><div className="text-xs text-soft">{title}</div><Chart height={170} label={title} option={(o => ({ ...o, grid: { left: 118, right: 58, top: 4, bottom: 6 }, xAxis: { ...o.xAxis, axisLabel: { show: false }, splitLine: { show: false } } }))(bars(arms.map(s => SHORT[s]), arms.map(fn), fmt, arms.map(col)))} /></div>))}
          </div>
          <p className="m-0 text-xs text-soft">越低越省。墙钟时间不比较：各组共用一台运行器。</p>
        </Panel>
      </div>
    </div>
  );
}

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
    ["探索性对照：效果与无门槛组持平", `${pct(g["pass@1"].attest_secure_v31)}`, `门控 v3.1 在正常任务上的成绩，与完全不设门槛（${pct(g["pass@1"].attest_no_gate)}）持平；同一轮的投毒流里，55 次留出运行 ${g.poison_float.attest_secure_v31.heldout_runs_applying_poison} 次照着毒药做。`,
      `口径：82% 是 v3.1 的成绩（v4 为 ${pct(g["pass@1"].attest_secure_v4)}）；0/55 是"照做毒药的运行次数"，和上面 D70 的"写入数量"不是一回事。11 个任务 × 5 次重复，判读规则事先提交，三条全部满足；但这是探索性实验（D71），v3.1 是在主实验之后设计的。`],
  ];
  return (
    <div className="grid gap-5">
      <div className="grid gap-2"><h2 className="m-0 text-2xl font-black">表现如何</h2><p className="m-0 max-w-[70ch] text-soft">三个结论，每个都写明它是怎么测的、只能说明什么。</p></div>
      <div className="grid gap-3 lg:grid-cols-3">{C.map(([a, n, d, k]) => (
        <section key={a} className="grid content-start gap-2 rounded-lg border border-rule bg-sheet p-5">
          <h3 className="m-0 text-lg font-black">{a}</h3><div className="text-[2.4rem] font-black leading-none tabular-nums">{n}</div><p className="m-0 text-sm">{d}</p><p className="m-0 text-xs text-soft">{k}</p></section>))}</div>
      <Perf />
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
