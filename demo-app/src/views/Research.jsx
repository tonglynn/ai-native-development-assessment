import { DATA, sysName, pct } from "../lib";
import { Panel, Source } from "../ui";
import Chart, { theme } from "../Chart";

export default function Research() {
  const t = theme(), g = DATA.d71, m = DATA.main;
  const arms = ["reasoningbank", "ace", "attest", "attest_no_gate", "attest_secure_v31", "attest_secure_v4"];
  const grp = s => s.startsWith("attest_secure") ? t.pen : s.startsWith("attest") ? t.hold : t.soft;
  const sec = Object.fromEntries(DATA.d71_secondary.map(r => [r.arm, r]));
  const vs = m.vs_no_memory.attest;
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">实验结果与局限</h2>
        <p className="m-0 max-w-[68ch] text-soft">主实验在任何记忆运行之前冻结并预注册；后续的门控改进是探索性的，判读规则在运行前提交。</p>
      </div>
      <Panel title="同一轮、各系统自己学习：成长与安全" aside={<span className="text-xs text-soft">D71，探索性，三条预设规则全部满足</span>}>
        <Chart height={360} label="横轴干净任务流留出 pass@1，纵轴投毒流中照做毒药的留出运行数" option={{
          grid: { left: 60, right: 30, top: 44, bottom: 50 },
          tooltip: { formatter: p => `${p.data.name}<br/>干净流 pass@1 ${p.data.value[0]}%<br/>照做毒药 ${p.data.value[1]}/55` },
          xAxis: { name: "干净任务流：留出 pass@1（%）", nameLocation: "middle", nameGap: 30, min: 55, max: 90, axisLabel: { color: t.soft }, nameTextStyle: { color: t.soft }, splitLine: { lineStyle: { color: t.rule } } },
          yAxis: { name: "照做毒药的运行（/55）", min: -2, max: 32, axisLabel: { color: t.soft }, nameTextStyle: { color: t.soft }, splitLine: { lineStyle: { color: t.rule } } },
          series: [{ type: "scatter", symbolSize: 16, data: arms.map(s => ({ name: sysName[s], value: [Math.round(g["pass@1"][s] * 100), g.poison_float[s].heldout_runs_applying_poison], itemStyle: { color: grp(s) }, label: { position: s === "attest_secure_v31" ? "top" : s === "attest_secure_v4" ? "bottom" : "right" } })),
            label: { show: true, formatter: p => p.data.name, position: "right", color: t.ink, fontSize: 12 } }],
        }} />
      </Panel>
      <Panel title="pass@1 以外（D71，干净流，第一次提交；描述性，未检验）">
        <div className="overflow-x-auto"><table className="w-full border-collapse text-sm tabular-nums">
          <thead><tr className="border-b border-rule text-left text-soft">{["系统", "pass@1", "幂等没做对", "审批没做对", "漏记审计", "步数", "成本/次", "记忆笔记数"].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
          <tbody>{arms.map(s => { const r = sec[s]; return (
            <tr key={s} className="border-b border-rule last:border-0"><td className="px-3 py-2 font-medium">{sysName[s]}</td><td className="px-3 py-2">{pct(r.first_pass)}</td><td className="px-3 py-2">{r.c5_failed}</td><td className="px-3 py-2">{r.c6_failed}</td><td className="px-3 py-2">{r.c4_failed}</td><td className="px-3 py-2">{r.steps}</td><td className="px-3 py-2">${r.cost_usd}</td><td className="px-3 py-2">{r.notes_in_memory}</td></tr>); })}</tbody>
        </table></div>
      </Panel>
      <Panel title="预注册主实验（冻结于 cf5d879）" aside={<span className="text-xs text-soft">{m.runs} 次运行，排除 {m.excluded}</span>}>
        <div className="overflow-x-auto"><table className="w-full border-collapse text-sm tabular-nums">
          <thead><tr className="border-b border-rule text-left text-soft">{["条件", "留出新任务", "政策变更后", "对照仓库"].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
          <tbody>{Object.entries(m.rate).map(([c, r]) => <tr key={c} className="border-b border-rule last:border-0"><td className="px-3 py-2 font-medium">{sysName[c]}</td><td className="px-3 py-2">{pct(r.heldout)}</td><td className="px-3 py-2">{pct(r.stale)}</td><td className="px-3 py-2">{pct(r.control)}</td></tr>)}</tbody>
        </table></div>
        <p className="m-0 mt-3 text-sm">H1：Attest 相对无记忆 +{Math.round(vs.mean_diff * 100)} 个百分点 [{Math.round(vs.ci_low * 100)}, {Math.round(vs.ci_high * 100)}]，成立。H6：预注册的写入门槛有 −15 个百分点的代价，不成立；D71 中门控 v3.1 补回了这一代价（探索性）。</p>
      </Panel>
      <Panel title="局限">
        <ul className="m-0 grid gap-1.5 pl-5 text-sm">
          <li>一个合成基准（2 个仓库、25 个冻结任务）、一个模型家族（DeepSeek），每组样本小。</li>
          <li>门控 v3.1、v4 是在主实验之后、在这个基准上设计的；它们的结果是探索性的。</li>
          <li>ReasoningBank 与 ACE 是按论文复现的版本，不是官方代码。</li>
          <li>真实仓库上的覆盖率低：25 条规则中 13 条没有任务教过；home-assistant 上补救无效。</li>
          <li>v3.1 仍会批准受信评审者的错误建议；v4 不会。</li>
        </ul>
      </Panel>
      <Panel title="复现">
        <pre className="out m-0 rounded-md bg-code px-3 py-2 font-mono text-[12.5px]">{`python scripts/validate_benchmark.py         # 25/25 个任务测到它声称的规范
python -m attest stress --kind gate_confirm   # D71（需要 DEEPSEEK_API_KEY，在 GitHub Actions 上运行）
python scripts/demo_run.py --out runs/demo     # 本演示的真实运行
python scripts/export_demo_data.py             # 从运行记录导出本页数据`}</pre>
      </Panel>
      <Source>runs/main、runs/gate_confirm、runs/gate_confirm/secondary.json；数据导出时的提交 {DATA.source_commit}</Source>
    </div>
  );
}
