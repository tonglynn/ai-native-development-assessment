"""Export the demo app's lazy-loaded data (D74), all from committed files:
  demo-app/public/data/traces.json      66 main-experiment held-out runs (11 tasks x Attest / no memory x 3 repetitions) as
                                 Langfuse-style spans: memory retrieval, each model call (visible input and output,
                                 tokens, cost, duration), each command, hidden tests, review, final diff
  demo-app/public/data/attest_src.json  the attest package and the task definitions, loaded into Pyodide
  demo-app/public/data/presets.json     the D70 attack cases shown as presets, with every system's recorded outcome
Hidden reasoning is not shown (thinking was off in every run); only messages and tool calls the agent produced.
Usage: python scripts/export_demo_traces.py
"""

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys  # noqa: E402
sys.path.insert(0, str(ROOT))
OUT = ROOT / "demo-app/public/data"
WS = re.compile(r"/tmp/attest_workspaces/[^/\s]+/workspace/?")
clip = lambda s, n: (s if len(s) <= n else s[:n] + f"\n… ({len(s) - n} more characters in the trajectory file)")  # noqa: E731


def commit_of(path: Path) -> str:
    return subprocess.run(["git", "log", "-1", "--format=%h", "--", str(path)], capture_output=True, text=True, cwd=ROOT).stdout.strip()


def spans(traj: Path, attempt: int) -> list[dict]:
    t = json.loads(traj.read_text())
    msgs, out, last_ts = t["messages"], [], None
    pending = []
    for i, m in enumerate(msgs):
        ex = m.get("extra") or {}
        if m["role"] in ("system", "user") and i < 2:
            continue
        if m["role"] == "assistant":
            usage = ((ex.get("response") or {}).get("usage") or {})
            ts = ex.get("timestamp")
            calls = [WS.sub("", json.loads((c.get("function") or {}).get("arguments", "{}")).get("command", "")).replace("cd  && ", "")
                     for c in m.get("tool_calls") or []]
            out.append({"kind": "llm", "name": f"model call {sum(s['kind'] == 'llm' for s in out) + 1}", "attempt": attempt,
                        "input": [clip(WS.sub("", p), 1500) for p in pending], "output": clip(m.get("content") or "", 1500), "tool_calls": calls,
                        "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                        "cached_tokens": usage.get("prompt_cache_hit_tokens"), "cost": ex.get("cost"),
                        "ms": round((ts - last_ts) * 1000) if ts and last_ts else None})
            last_ts, pending = ts or last_ts, []
        elif m["role"] == "tool":
            ts = ex.get("timestamp")
            try:
                o = json.loads(m.get("content") or "{}")
                text, rc = str(o.get("output", "")), o.get("returncode")
            except json.JSONDecodeError:
                text, rc = str(m.get("content") or ""), ex.get("returncode")
            cmd = out[-1]["tool_calls"][0] if out and out[-1]["kind"] == "llm" and out[-1]["tool_calls"] else ""
            out.append({"kind": "tool", "name": "bash", "attempt": attempt, "command": cmd, "rc": rc, "output": clip(WS.sub("", text), 2500),
                        "ms": round((ts - last_ts) * 1000) if ts and last_ts else None})
            last_ts = ts or last_ts
            pending.append(f"[command output, exit {rc}]\n" + WS.sub("", text)[:600])
        elif m["role"] == "user":
            pending.append(WS.sub("", m.get("content") or ""))
    return out


def traces() -> list[dict]:
    rows = []
    for cond in ("attest", "no_memory"):
        for rep in (1, 2, 3):
            for d in sorted((ROOT / f"runs/main/{cond}/r{rep}").glob("H*")):
                r = json.loads((d / "result.json").read_text())
                sp = [{"kind": "retrieve", "name": "memory.retrieve", "injected": r.get("injected_notes") or [],
                       "context": r.get("notes_context") or "", "memory_tokens": r.get("memory_tokens_approx")}] if cond == "attest" else []
                for k, a in enumerate(r["attempts"], 1):
                    if k > 1:
                        sp.append({"kind": "review", "name": "simulated review", "comments": r["attempts"][k - 2].get("review_comments") or []})
                    tp = d / f"attempt{k}.traj.json"
                    if tp.exists():
                        sp += spans(tp, k)
                    sp.append({"kind": "tests", "name": f"hidden tests (attempt {k})", "attempt": k, "passed": a.get("passed"),
                               "conv_failed": a.get("conv_failed") or [], "tests_failed": a.get("tests_failed") or []})
                from attest.benchmark import load_task
                tk = load_task(r["task_id"])
                rows.append({"task": r["task_id"], "title": tk.title, "issue": tk.issue, "condition": cond, "rep": rep, "first_pass": r["first_pass"], "final_pass": r["final_pass"],
                             "attempts": r["n_attempts"], "cost": r.get("cost_usd"), "seconds": r.get("seconds"), "steps": r.get("steps"),
                             "conventions": r.get("conventions"), "commit": commit_of(d / "result.json"), "frozen_at": "cf5d879",
                             "path": f"runs/main/{cond}/r{rep}/{d.name}", "diff": clip((d / "final.diff").read_text() if (d / "final.diff").exists() else "", 8000),
                             "spans": sp})
    return rows


def src() -> dict:
    files = {}
    for p in sorted((ROOT / "attest").rglob("*.py")):
        files[str(p.relative_to(ROOT))] = p.read_text()
    files["web_engine.py"] = (ROOT / "scripts/web_engine.py").read_text()
    files["SCENARIO.md"] = (ROOT / "SCENARIO.md").read_text()  # gateway v4 reads its policy registry from it
    for p in sorted((ROOT / "benchmark/tasks").rglob("*")):
        if p.is_file() and p.suffix in (".json", ".md", ".py", ".txt", ".toml") and p.stat().st_size < 200_000:
            files[str(p.relative_to(ROOT))] = p.read_text()
    return files


def presets() -> list[dict]:
    rows = json.loads((ROOT / "runs/poison_channels/results.json").read_text())
    cases = {c["id"]: c for c in json.loads((ROOT / "benchmark/poison_channels/cases.json").read_text())["cases"]}
    pick = ["review_untrusted:float_audit:applied", "review_forged:skip_audit:applied", "review_insider:hardcoded_key:applied",
            "issue:tls_off:plain", "readme:skip_tests:plain", "control2:review_insider"]
    out = []
    for cid in pick:
        c = cases[cid]
        text = (c["reviews"][0]["text"] if c["reviews"] else (c["issue_extra"] or c["transcript"])).replace("Note from the product owner: ", "").strip()
        recorded = {r["system"]: {"stored": r.get("stored"), "rule": r.get("rule"), "note": (r.get("notes") or [""])[0][:400], "error": r.get("error")}
                    for r in rows if r["case"] == cid}
        out.append({"id": cid, "channel": c["channel"], "payload": c["payload"], "control": c["control"], "applied": c["applied"], "text": text[:600],
                    "applied_line": [l for l in c["added"] if l not in ("    refund_amount = round_money(to_money(amount))",)][-1] if c["applied"] else "",
                    "trusted": any(r["trusted"] for r in c["reviews"]), "recorded": recorded})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = traces()
    (OUT / "traces.json").write_text(json.dumps(t, ensure_ascii=False))
    (OUT / "attest_src.json").write_text(json.dumps(src(), ensure_ascii=False))
    (OUT / "presets.json").write_text(json.dumps(presets(), ensure_ascii=False))
    ev = [json.loads(l) for l in (ROOT / "runs/demo/memory/events.jsonl").read_text().splitlines() if l.strip()]
    (OUT / "demo_events.json").write_text(json.dumps(ev, ensure_ascii=False))
    print(len(t), "traces;", {p.name: p.stat().st_size // 1024 for p in OUT.iterdir()}, "KB")


if __name__ == "__main__":
    main()
