import { useState } from "react";
import { D, allNotes } from "../lib";
import { Stamp, Tag, Source, cn } from "../ui";
import NoteDrawer from "./NoteDrawer";
const kindOf = n => n.review ? "human" : n.state || "none";
export default function Evidence() {
  const [f, setF] = useState("all");
  const [note, setNote] = useState(null);
  const notes = allNotes();
  const rejected = D.learn.flatMap(l => l.rejected.map(r => ({ ...r, task: l.task })));
  const shown = notes.filter(n => f === "all" || (f === "approved" ? n.state === "approved" : n.state === "uncertain"));
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">每条记忆从哪来、凭什么成立</h2>
        <p className="m-0 max-w-[68ch] text-soft">这是演示运行学到的全部笔记。点一条，查看它引用的评审、落实的代码行、门控的证据、适用范围、人工决定，以及日志里关于它的每一条记录。</p>
      </div>
      <div className="flex flex-wrap gap-2">{[["all", "全部"], ["approved", "已批准"], ["uncertain", "待人工"]].map(([k, l]) => (
        <button key={k} onClick={() => setF(k)} className={cn("rounded-full border px-3 py-1 text-sm", f === k ? "border-pen bg-penwash text-pen" : "border-rule bg-sheet")}>{l} {k === "all" ? notes.length : notes.filter(n => n.state === k).length}</button>))}</div>
      <div className="overflow-x-auto rounded-lg border border-rule bg-sheet">
        <table className="w-full border-collapse text-sm">
          <thead><tr className="border-b border-rule text-left text-soft"><th className="px-4 py-2 font-medium">笔记</th><th className="px-3 py-2 font-medium">学自</th><th className="px-3 py-2 font-medium">证据</th><th className="px-3 py-2 font-medium">状态</th></tr></thead>
          <tbody>{shown.map(n => (
            <tr key={n.id} onClick={() => setNote(n)} className="cursor-pointer border-b border-rule last:border-0 hover:bg-penwash">
              <td className="px-4 py-2.5"><div className="flex items-center gap-2"><Tag tone="soft">{n.id}</Tag><span className="font-medium">{n.title}</span></div></td>
              <td className="px-3 py-2.5">{n.learned_in}</td>
              <td className="px-3 py-2.5 text-xs text-soft">{[...(n.hard || []).map(h => `硬：${h}`), ...(n.soft || []).map(h => `软：${h}`), ...(n.counter || []).map(h => `反证：${h}`)].join("；") || "无独立证据"}</td>
              <td className="px-3 py-2.5"><Stamp kind={kindOf(n) === "human" ? "approved" : n.state || "none"} label={kindOf(n) === "human" ? "人工批准" : undefined} /></td>
            </tr>))}</tbody>
        </table>
      </div>
      {rejected.length > 0 && <div className="grid gap-1 text-sm"><b>写入时就被拒绝的候选</b>{rejected.map((r, i) => <div key={i} className="text-soft">{r.task}：{r.title} · {r.reason}</div>)}</div>}
      <Source>runs/demo/demo.json、runs/demo/memory/events.jsonl</Source>
      <NoteDrawer note={note} onClose={() => setNote(null)} />
    </div>
  );
}
