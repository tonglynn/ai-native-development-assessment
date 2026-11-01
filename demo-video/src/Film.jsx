// Attest mechanism film (D73). Every number and every quoted line comes from demo-app/src/data.json, which
// scripts/export_demo_data.py exports from committed runs. The animation is a diagram of what the recorded run did.
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import DATA from "../../demo-app/src/data.json";

const C = { paper: "#eef1ec", sheet: "#fbfcfa", rule: "#d3dad1", ink: "#18221c", soft: "#5b6a60", pen: "#2648b8", ok: "#1d7448", hold: "#9a6a08", bad: "#b23a2e", code: "#f1f4f0" };
const SANS = '"Noto Sans CJK SC","Noto Sans CJK TC",sans-serif', MONO = '"DejaVu Sans Mono",monospace';
const D = DATA.demo;
const E04 = D.learn.find(l => l.task === "E04");
const pass = c => D.reuse.runs.filter(r => r.condition === c && r.first_pass).length;
const pf = DATA.d71.poison_float;
const S = [["open", 300], ["flow", 450], ["memory", 540], ["poison", 480], ["govern", 480], ["end", 270]];
export const FILM_FRAMES = S.reduce((a, [, d]) => a + d, 0);

const fade = (f, a, b) => interpolate(f, [a, a + 12, b - 12, b], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const appear = (f, at, len = 15) => interpolate(f, [at, at + len], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
function Stamp({ text, color, at, size = 40 }) {
  const f = useCurrentFrame(), { fps } = useVideoConfig();
  const s = spring({ frame: f - at, fps, config: { damping: 9, mass: 0.6 } });
  return <span style={{ display: "inline-block", fontFamily: SANS, fontWeight: 900, fontSize: size, color, border: `5px solid ${color}`, borderRadius: 10, padding: "2px 18px",
    transform: `rotate(-5deg) scale(${interpolate(s, [0, 1], [2.2, 1])})`, opacity: f < at ? 0 : 0.92 }}>{text}</span>;
}
const Frame = ({ children, title, sub }) => (
  <AbsoluteFill style={{ background: C.paper, color: C.ink, fontFamily: SANS, padding: "80px 110px", gap: 36 }}>
    {title && <div><div style={{ fontSize: 58, fontWeight: 900, letterSpacing: -1 }}>{title}</div>{sub && <div style={{ fontSize: 28, color: C.soft, marginTop: 10 }}>{sub}</div>}</div>}
    {children}
    <div style={{ position: "absolute", left: 110, bottom: 44, fontSize: 20, color: C.soft }}>回放：真实运行记录 runs/demo、runs/gate_confirm；评审意见与负责人为模拟，仓库与毒评论为合成</div>
  </AbsoluteFill>
);
const Card = ({ children, style }) => <div style={{ background: C.sheet, border: `2px solid ${C.rule}`, borderRadius: 14, padding: "22px 28px", ...style }}>{children}</div>;

function Open() {
  const f = useCurrentFrame();
  return <Frame>
    <div style={{ marginTop: 120, fontSize: 92, fontWeight: 900, lineHeight: 1.1, maxWidth: 1500, opacity: appear(f, 5, 25) }}>编码智能体总在重犯<br />评审已经纠正过的错误。</div>
    <div style={{ fontSize: 40, color: C.soft, opacity: appear(f, 90, 25), maxWidth: 1500 }}>Attest 让它只从验证过的经验中成长：<br />有可执行的证据才能成为规则，拿不准的交给人，每个决定都能追溯。</div>
  </Frame>;
}
function Flow() {
  const f = useCurrentFrame();
  const nodes = ["任务", "读取记忆", "智能体执行", "隐藏测试", "沉淀经验"];
  const lit = Math.floor(interpolate(f, [30, 230], [0, nodes.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return <Frame title="智能体的一次工作" sub="每次任务：读取记忆、执行、由隐藏测试判定；只有通过验证的任务才能沉淀经验">
    <div style={{ display: "flex", alignItems: "center", gap: 18, marginTop: 40 }}>
      {nodes.map((n, i) => <div key={n} style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <Card style={{ width: 250, textAlign: "center", fontSize: 34, fontWeight: 700, borderColor: i < lit ? C.pen : C.rule, color: i < lit ? C.ink : C.soft, boxShadow: i === lit - 1 ? `0 0 0 8px ${C.pen}22` : "none" }}>{n}</Card>
        {i < nodes.length - 1 && <div style={{ width: 50, height: 4, background: i < lit - 1 ? C.pen : C.rule }} />}</div>)}
    </div>
    <div style={{ display: "flex", gap: 40, marginTop: 50, opacity: appear(f, 260, 20) }}>
      <Card style={{ flex: 1 }}><div style={{ fontSize: 30, color: C.soft }}>新任务 H04，开记忆</div><div style={{ fontSize: 120, fontWeight: 900, color: C.ok }}>{pass("attest_v4")}/3</div><div style={{ fontSize: 28 }}>第一次就通过隐藏测试</div></Card>
      <Card style={{ flex: 1 }}><div style={{ fontSize: 30, color: C.soft }}>同一个任务，不开记忆</div><div style={{ fontSize: 120, fontWeight: 900, color: C.bad }}>{pass("no_memory")}/3</div><div style={{ fontSize: 28 }}>每次都错在幂等（C5）和审批（C6）</div></Card>
    </div>
  </Frame>;
}
function Memory() {
  const f = useCurrentFrame();
  const n = E04.new_notes[0];
  const row = (at, label, body, color = C.ink) => <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 24, alignItems: "start", opacity: appear(f, at) }}>
    <div style={{ fontSize: 28, color: C.soft, paddingTop: 6 }}>{label}</div><div style={{ fontFamily: MONO, fontSize: 25, background: C.code, borderRadius: 10, padding: "14px 18px", color, lineHeight: 1.45 }}>{body}</div></div>;
  return <Frame title="一条经验是怎么来的" sub="E04 第一次没通过，评审纠正后通过；经验必须引用评审、落实在通过测试的代码里">
    <div style={{ display: "grid", gap: 22, marginTop: 10, maxWidth: 1600 }}>
      {row(20, "评审意见（模拟）", E04.attempts[0].review_comments[0].slice(0, 150) + "…")}
      {row(110, "落实在这一行", n.applied)}
      {row(200, "隐藏测试", "第二次提交：全部通过", C.ok)}
      {row(290, "门控的证据", `硬证据：${(n.hard || []).join("、")}；软证据：${(n.soft || []).join("、")}`)}
      <div style={{ display: "flex", alignItems: "center", gap: 30, opacity: appear(f, 380) }}><div style={{ fontSize: 36, fontWeight: 700 }}>{n.title}</div><Stamp text="批准" color={C.ok} at={395} /></div>
    </div>
  </Frame>;
}
function Poison() {
  const f = useCurrentFrame();
  const rows = Object.fromEntries(D.poison.slice(1).map(p => [p.system, p]));
  const lanes = [["ace", "ACE 式"], ["reasoningbank", "ReasoningBank 式"], ["attest_secure_v4", "Attest + 门控 v4"]];
  return <Frame title="一条能通过测试的毒评论" sub={`"${D.poison[0].case.reviews[0].text}"（合成）`}>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 30, marginTop: 20 }}>
      {lanes.map(([s, name], i) => { const r = rows[s]; const bad = r.rule; return (
        <Card key={s} style={{ display: "grid", gap: 20, minHeight: 420, opacity: appear(f, 20 + i * 15) }}>
          <div style={{ fontSize: 38, fontWeight: 900 }}>{name}</div>
          <div style={{ fontSize: 26, color: C.soft }}>{s === "attest_secure_v4" ? "写入前检查：评审者、反事实测试、代码检查、三态判定" : "没有写入前检查"}</div>
          <div style={{ marginTop: 10 }}><Stamp text={bad ? "存为规则" : "未写入"} color={bad ? C.bad : C.ok} at={120 + i * 20} size={44} /></div>
          <div style={{ fontSize: 28, opacity: appear(f, 260) }}>后续照做毒药的运行（D71，整轮）<br /><b style={{ fontSize: 64, color: pf[s].heldout_runs_applying_poison ? C.bad : C.ok }}>{pf[s].heldout_runs_applying_poison}/{pf[s].heldout_runs}</b></div>
        </Card>); })}
    </div>
  </Frame>;
}
function Govern() {
  const f = useCurrentFrame();
  const g = DATA.govern_offline, ex = g.find(s => s.step.startsWith("retrieval")).excluded;
  const line = (at, who, what, stamp, color) => <div style={{ display: "flex", alignItems: "center", gap: 28, opacity: appear(f, at) }}>
    <div style={{ fontFamily: MONO, fontSize: 26, width: 330, color: C.soft }}>{who}</div><div style={{ fontSize: 32, flex: 1 }}>{what}</div><Stamp text={stamp} color={color} at={at + 10} size={32} /></div>;
  return <Frame title="什么能成为团队规则，由人决定" sub="政策 FIN-2026-11 把审批阈值从 500.00 提到 1000.00（新阈值笔记为模拟）">
    <Card style={{ display: "grid", gap: 26, marginTop: 10 }}>
      {line(20, "agent:coder", "批准新阈值笔记", "拒绝", C.bad)}
      {line(90, "agent:coder", "用它取代旧阈值规则", "拒绝", C.bad)}
      {line(160, "owner:finance-lead", "批准（依据 FIN-2026-11），并记录取代 at-0005", "完成", C.ok)}
    </Card>
    <div style={{ fontSize: 30, opacity: appear(f, 250), lineHeight: 1.6 }}>
      <div>检索 H04 时，at-0005 不再注入：<span style={{ fontFamily: MONO, fontSize: 24 }}>{ex["at-0005"]}</span></div>
      <div>旧规则仍留在只追加的日志里；伪造的"智能体批准"被审计当场查出。</div></div>
  </Frame>;
}
function End() {
  const f = useCurrentFrame();
  const v31 = DATA.d71["pass@1"].attest_secure_v31, ng = DATA.d71["pass@1"].attest_no_gate;
  return <Frame>
    <div style={{ marginTop: 150, display: "grid", gap: 34 }}>
      {[["会成长", `新任务 H04：开记忆 ${pass("attest_v4")}/3，不开 ${pass("no_memory")}/3`], ["不会被教坏", `门控 v3.1 留出 ${Math.round(v31 * 100)}%，与去掉门槛（${Math.round(ng * 100)}%）持平；毒药 0/55 被照做`], ["说得清为什么", "每条规则都有来源、证据、适用范围和人工决定，日志可审计"]].map(([a, b], i) => (
        <div key={a} style={{ display: "flex", gap: 40, alignItems: "baseline", opacity: appear(f, 10 + i * 30) }}><div style={{ fontSize: 76, fontWeight: 900, width: 520 }}>{a}</div><div style={{ fontSize: 36, color: C.soft }}>{b}</div></div>))}
      <div style={{ fontSize: 26, color: C.soft, opacity: appear(f, 120) }}>探索性结果：一个合成基准、一个模型家族；完整数据与局限见仓库 RESULTS.md</div>
    </div>
  </Frame>;
}
const SCENES = { open: Open, flow: Flow, memory: Memory, poison: Poison, govern: Govern, end: End };
export function AttestFilm() {
  let at = 0;
  return <AbsoluteFill style={{ background: C.paper }}>
    {S.map(([k, d]) => { const from = at; at += d; const Scene = SCENES[k]; return (
      <Sequence key={k} from={from} durationInFrames={d}><Fader d={d}><Scene /></Fader></Sequence>); })}
  </AbsoluteFill>;
}
function Fader({ children, d }) { const f = useCurrentFrame(); return <AbsoluteFill style={{ opacity: fade(f, 0, d) }}>{children}</AbsoluteFill>; }
