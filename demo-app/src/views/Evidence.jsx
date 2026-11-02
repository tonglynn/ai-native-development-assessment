import { useState } from "react";
import { allNotes } from "../lib";
import { Stamp, Tag, Source, cn, Status, Layers } from "../ui";
import { FEATURES } from "../glossary";
import NoteDrawer from "./NoteDrawer";
export default function Evidence() {
  const [f, setF] = useState("all"), [note, setNote] = useState(null);
  const notes = allNotes(), shown = notes.filter(n => f === "all" || n.state === f);
  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <div className="flex flex-wrap items-center gap-3"><h2 className="m-0 text-2xl font-black">来源追溯：为什么相信一条经验</h2><Status kind="replay" /></div>
        <Layers l1={FEATURES.version.l1} l2={FEATURES.version.l2} l3={FEATURES.version.l3} className="max-w-[80ch]" />
        <p className="m-0 max-w-[70ch] text-soft">Attest 不仅记录经验本身，还记录其可信依据、适用范围与后续影响。下列为演示运行写入的全部笔记，展开任一条可查看 8 项证据。</p>
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
