import { DiffEditor, loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker&inline";
import { useEffect, useState } from "react";

self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco }); // bundled locally: no CDN, works offline

const dark = () => document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);

export default function CodeDiff({ original, modified, height = 420, leftLabel, rightLabel }) {
  const [theme, setTheme] = useState(dark() ? "vs-dark" : "vs");
  useEffect(() => { const q = matchMedia("(prefers-color-scheme: dark)"); const f = () => setTheme(dark() ? "vs-dark" : "vs"); q.addEventListener("change", f); return () => q.removeEventListener("change", f); }, []);
  return (
    <div className="overflow-hidden rounded-md border border-rule">
      <div className="grid grid-cols-2 border-b border-rule bg-code text-xs text-soft"><div className="px-3 py-1.5">{leftLabel}</div><div className="border-l border-rule px-3 py-1.5">{rightLabel}</div></div>
      <DiffEditor key={`${original.length}-${modified.length}`} keepCurrentOriginalModel keepCurrentModifiedModel height={height} language="python" original={original} modified={modified} theme={theme}
        options={{ readOnly: true, renderSideBySide: true, minimap: { enabled: false }, fontSize: 12.5, scrollBeyondLastLine: false, renderOverviewRuler: false, originalEditable: false, wordWrap: "off", ignoreTrimWhitespace: false }} />
    </div>
  );
}
