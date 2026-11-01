import { useState } from "react";
import { allNotes } from "../lib";
import { Stamp, Tag, Source, cn } from "../ui";
import NoteDrawer from "./NoteDrawer";
export default function Evidence() {
  const [f, setF] = useState("all"), [note, setNote] = useState(null);
  const notes = allNotes(), shown = notes.filter(n => f === "all" || n.state === f);
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <h2 className="m-0 text-2xl font-black">证据详情：为什么相信一条经验</h2>
        <p className="m-0 max-w-[70ch] text-soft">Attest 记住的不只是经验本身，还有它为什么值得相信、在哪里适用、后来产生了什么影响。下面是演示运行学到的全部笔记，点一条展开 8 项证据。</p>
      </div>
      <div className="flex flex-wrap gap-2">{[["all", "全部"], ["approved", "已批准"], ["uncertain", "待人工"]].map(([k, l]) => <button key={k} onClick={() => setF(k)} className={cn("rounded-full border px-3 py-1 text-sm", f === k ? "border-pen bg-penwash text-pen" : "border-rule bg-sheet")}>{l} {k === "all" ? notes.length : notes.filter(n => n.state === k).length}</button>)}</div>
      <ul className="ruled m-0 list-none rounded-lg border border-rule bg-sheet p-0">{shown.map(n => (
        <li key={n.id}><button onClick={() => setNote(n)} className="flex w-full flex-wrap items-center gap-3 px-4 py-3 text-left hover:bg-penwash">
          <Tag tone="soft">{n.id}</Tag><span className="min-w-0 flex-1 font-medium">{n.title}</span><span className="text-xs text-soft">学自 {n.learned_in}</span><Stamp kind={n.state || "none"} /></button></li>))}</ul>
      <Source>runs/demo（真实运行回放）、runs/demo/memory/events.jsonl、runs/demo/govern_offline.json</Source>
      <NoteDrawer note={note} onClose={() => setNote(null)} />
    </div>
  );
}
