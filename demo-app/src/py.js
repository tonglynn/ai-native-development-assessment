// Loads Pyodide and the real Attest package into the page, once, on first use.
let ready = null;
export function engine(onStatus) {
  if (!ready) ready = (async () => {
    const base = new URL("./", location.href);
    onStatus?.("正在加载 Python 运行环境（约 13 MB，只在第一次）…");
    const { loadPyodide } = await import(/* @vite-ignore */ new URL("pyodide/pyodide.mjs", base).href);
    const py = await loadPyodide({ indexURL: new URL("pyodide/", base).href });
    onStatus?.("正在载入 Attest 源代码…");
    const src = await (await fetch(new URL("data/attest_src.json", base))).json();
    for (const [p, c] of Object.entries(src)) { const f = "/app/" + p; py.FS.mkdirTree(f.slice(0, f.lastIndexOf("/"))); py.FS.writeFile(f, c); }
    py.runPython("import sys; sys.path.insert(0, '/app'); import web_engine");
    onStatus?.("");
    return py;
  })();
  return ready;
}
// Call a Python expression with named arguments passed safely through globals; returns parsed JSON.
export async function call(expr, args = {}, onStatus) {
  const py = await engine(onStatus);
  for (const [k, v] of Object.entries(args)) py.globals.set(k, v);
  const t = performance.now();
  const out = py.runPython(expr);
  return { result: JSON.parse(out), ms: Math.round(performance.now() - t) };
}
export const fetchJson = async name => (await fetch(new URL(`data/${name}`, new URL("./", location.href)))).json();
