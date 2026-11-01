import { DATA, D } from "../lib";
import { Drawer, Stamp, Tag, Code } from "../ui";

const Sec = ({ n, t, children }) => <section className="grid gap-1.5"><h4 className="m-0 text-sm font-bold">{n} {t}</h4><div className="text-sm">{children}</div></section>;
export default function NoteDrawer({ note, onClose }) {
  if (!note) return <Drawer open={false} onOpenChange={() => {}} title="" />;
  const events = DATA.note_events[note.id] || [];
  const src = D.learn.find(l => l.task === note.learned_in);
  const uses = D.reuse.runs.filter(r => (r.injected || []).includes(note.id));
  const gov = DATA.govern_offline.find(s => s.step.startsWith("retrieval"))?.excluded?.[note.id];
  const cf = (note.hard || []).includes("test");
  return (
    <Drawer open onOpenChange={o => !o && onClose()} title={`${note.id}  ${note.title}`}>
      <div className="grid gap-5">
        <p className="m-0">{note.content}</p>
        <Sec n="1" t="来源：哪条评审意见提出的">{src?.attempts[0]?.review_comments?.length ? src.attempts[0].review_comments.filter(c => (note.quote || "").slice(0, 30) && c.includes((note.quote || "").slice(0, 30))).concat([]).slice(0, 1).map((c, i) => <Code key={i}>{c}</Code>) : null}<div className="mt-1 text-xs text-soft">引用的原话：</div><Code>{note.quote}</Code></Sec>
        <Sec n="2" t="证据：落实在哪一行代码"><Code>{note.applied}</Code><div className="mt-1 text-xs text-soft">这一行出现在任务 {note.learned_in} 最终通过隐藏测试的改动里。</div></Sec>
        <Sec n="3" t="验证：哪些测试支持它">任务 {note.learned_in}（{src?.title}）{src?.first_pass ? "第一次提交就通过" : "评审后第二次提交通过"}全部隐藏测试，检查的规矩：{(src?.conventions || []).join("、")}。</Sec>
        <Sec n="4" t="反事实：撤销对应改动，测试会失败吗">{cf ? <span>会。撤销这行改动后相关的隐藏测试失败，所以测试确实在为这条经验作证（计为硬证据）。</span> : <span className="text-soft">没有作为证据：要么撤销后测试仍通过，要么这类规范由团队代码检查而不是测试来验证。</span>}</Sec>
        <Sec n="5" t="适用范围">仓库 <b>{note.scope.repo}</b>，版本 ≥ {note.scope.valid_from}{note.scope.valid_until ? `，< ${note.scope.valid_until}` : "，没有上限"}；学自文件 {(note.scope.files || []).join("、")}。检索只在这个范围内注入它。</Sec>
        <Sec n="6" t="审核状态"><div className="flex flex-wrap items-center gap-2"><Stamp kind={note.state || "none"} />{(note.hard || []).map(h => <Tag key={h} tone="ok">硬证据 {h}</Tag>)}{(note.soft || []).map(h => <Tag key={h} tone="pen">软证据 {h}</Tag>)}{(note.counter || []).map(h => <Tag key={h} tone="bad">反证 {h}</Tag>)}</div>
          {note.review && <div className="mt-1">人工决定：<code>{note.review.by}</code> 批准，依据 {(note.review.evidence || []).join("、")}</div>}</Sec>
        <Sec n="7" t="使用记录：哪些任务用过它">{uses.length ? <ul className="m-0 pl-5">{uses.map(u => <li key={u.run}>新任务 H04 第 {u.run} 次运行：{u.first_pass ? "第一次就通过" : "未通过"}</li>)}</ul> : <span className="text-soft">演示运行中没有被注入过（不相关或不是规则）。</span>}</Sec>
        <Sec n="8" t="生命周期"><ol className="m-0 list-none p-0">{events.map(e => <li key={e.seq} className="flex gap-3 py-0.5"><span className="w-10 shrink-0 font-mono text-xs text-soft">#{e.seq}</span><span className="min-w-0 text-soft">{e.reason}</span></li>)}</ol>
          {gov && <div className="mt-1">之后：{gov}（场景三的政策变更）</div>}</Sec>
      </div>
    </Drawer>
  );
}
