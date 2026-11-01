import { DATA } from "../lib";
import { Drawer, Stamp, Tag, Code } from "../ui";

const evName = { add: "写入", update: "更新", reject: "拒绝写入" };
export default function NoteDrawer({ note, onClose }) {
  const events = note ? DATA.note_events[note.id] || [] : [];
  return (
    <Drawer open={!!note} onOpenChange={o => !o && onClose()} title={note ? `${note.id}  ${note.title}` : ""}>
      {note && (
        <div className="grid gap-5">
          <div className="flex flex-wrap items-center gap-3"><Stamp kind={note.state || "none"} /><Tag tone="soft">{note.type}</Tag><span className="text-sm text-soft">学自任务 {note.learned_in}</span></div>
          <p className="m-0">{note.content}</p>
          <div className="grid gap-3">
            <h4 className="m-0 text-sm font-bold">证据链</h4>
            <div className="grid gap-1"><span className="text-xs text-soft">1 引用的评审或改动</span><Code>{note.quote}</Code></div>
            <div className="grid gap-1"><span className="text-xs text-soft">2 落实在通过隐藏测试的改动里的这一行</span><Code>{note.applied}</Code></div>
            <div className="grid gap-1"><span className="text-xs text-soft">3 门控的判断</span>
              <div className="flex flex-wrap gap-1.5 text-sm">
                {(note.hard || []).map(h => <Tag key={h} tone="ok">硬证据 · {h}</Tag>)}
                {(note.soft || []).map(h => <Tag key={h} tone="pen">软证据 · {h}</Tag>)}
                {(note.counter || []).map(h => <Tag key={h} tone="bad">反证 · {h}</Tag>)}
                {!(note.hard || []).length && !(note.soft || []).length && <span className="text-soft">没有独立证据，所以不当作规则，等人决定</span>}
              </div></div>
            <div className="grid gap-1"><span className="text-xs text-soft">4 适用范围（检索只在范围内注入）</span>
              <div className="text-sm">仓库 <b>{note.scope.repo}</b>，版本 ≥ {note.scope.valid_from}{note.scope.valid_until ? `，< ${note.scope.valid_until}` : ""}，文件 {(note.scope.files || []).join("、")}</div></div>
            {note.review && <div className="grid gap-1"><span className="text-xs text-soft">5 人工决定</span><div className="text-sm"><code>{note.review.by}</code> {note.review.decision === "approved" ? "批准" : note.review.decision}，依据：{(note.review.evidence || []).join("、")}</div></div>}
          </div>
          <div className="grid gap-2">
            <h4 className="m-0 text-sm font-bold">日志里关于它的每一条记录</h4>
            <ol className="ruled m-0 list-none p-0 text-sm">
              {events.map(e => <li key={e.seq} className="flex gap-3 py-1.5"><span className="w-10 shrink-0 font-mono text-xs text-soft">#{e.seq}</span><span className="w-16 shrink-0">{evName[e.type] || e.type}</span><span className="min-w-0 text-soft">{e.reason}</span></li>)}
            </ol>
            <p className="m-0 text-xs text-soft">来源：runs/demo/memory/events.jsonl（只追加的事件日志）</p>
          </div>
        </div>
      )}
    </Drawer>
  );
}
