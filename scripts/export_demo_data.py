"""Export everything the demo app shows into demo-app/src/data.json (D73). Every value is read from committed runs;
nothing is typed in by hand. Re-run after any run changes: python scripts/export_demo_data.py
"""

import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from attest.analysis import load_results, paired, usable  # noqa: E402

DEMO = ROOT / "runs/demo"
WS = re.compile(r"/tmp/attest_workspaces/[^/\s]+/workspace/?")


def trace(path: Path, max_out: int = 900) -> list[dict]:
    """The agent's real steps: each command it ran and the start of its output (workspace path shortened)."""
    if not path.exists():
        return []
    msgs = json.loads(path.read_text())["messages"]
    steps = []
    for i, m in enumerate(msgs):
        for c in m.get("tool_calls") or []:
            try:
                cmd = json.loads((c.get("function") or {}).get("arguments", "{}")).get("command", "")
            except json.JSONDecodeError:
                cmd = ""
            out, rc = "", None
            nxt = msgs[i + 1] if i + 1 < len(msgs) else {}
            try:
                o = json.loads(nxt.get("content") or "{}")
                out, rc = str(o.get("output", "")), o.get("returncode")
            except (json.JSONDecodeError, AttributeError):
                out = str(nxt.get("content") or "")
            steps.append({"cmd": WS.sub("", cmd).replace("cd  && ", "").strip(), "rc": rc, "out": WS.sub("", out)[:max_out],
                          "thought": (m.get("content") or "")[:400]})
    return steps


def read(p: Path) -> str:
    return p.read_text() if p.exists() else ""


def note_events(events: list[dict]) -> dict:
    out = {}
    for e in events:
        iid = e["item"]["id"] if e["type"] == "add" else e.get("id")
        if not iid:
            continue
        fields = e.get("fields") or {}
        out.setdefault(iid, []).append({"seq": e["seq"], "type": e["type"], "reason": e.get("reason", ""),
                                        "state": ((e.get("item") or {}).get("assessment") or fields.get("assessment") or {}).get("state"),
                                        "status": (e.get("item") or {}).get("status") or fields.get("status")})
    return out


def main_experiment() -> dict:
    res, excluded = usable(load_results(ROOT / "runs/main"))
    conds = ["no_memory", "reasoningbank", "ace", "attest", "attest_no_gate", "attest_no_scope"]
    rate = {c: {g: (sum(r["first_pass"] for r in res if r["condition"] == c and r["group"] == g) /
                    max(1, sum(r["condition"] == c and r["group"] == g for r in res))) for g in ("heldout", "stale", "control")} for c in conds}
    vs = {p["condition"]: p for p in paired(res, "heldout", baseline="no_memory")}
    return {"rate": rate, "vs_no_memory": vs, "runs": len(res), "excluded": len(excluded)}


def files_after(diff: str, task_id: str = "H04") -> dict:
    """Apply a recorded final.diff to the task's stub workspace (the agent's real starting point, built by
    attest.benchmark.materialize) and return each changed file before and after, for a side-by-side diff."""
    import subprocess
    import tempfile
    from attest.benchmark import load_task, materialize
    if not diff.strip():
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        base = materialize(load_task(task_id), Path(tmp) / "base", "stub")
        work = materialize(load_task(task_id), Path(tmp) / "work", "stub")
        (Path(tmp) / "p.diff").write_text(diff)
        r = subprocess.run(["git", "apply", "--whitespace=nowarn", str(Path(tmp) / "p.diff")], cwd=work, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"recorded diff does not apply to the {task_id} stub: {r.stderr[:300]}")
        out = {}
        for f in re.findall(r"^\+\+\+ b/(\S+)", diff, re.M):
            if f.startswith("tests/") or not f.endswith(".py"):
                continue
            out[f] = {"before": (base / f).read_text() if (base / f).exists() else "", "after": (work / f).read_text()}
        return out

def main():
    demo = json.loads((DEMO / "demo.json").read_text())
    events = [json.loads(l) for l in read(DEMO / "memory/events.jsonl").splitlines() if l.strip()]
    gc = json.loads((ROOT / "runs/gate_confirm/summary.json").read_text())
    sec = json.loads((ROOT / "runs/gate_confirm/secondary.json").read_text())
    pc = json.loads((ROOT / "runs/poison_channels/results.json").read_text())
    pc_sum = {}
    for r in pc:
        if "error" in r or r["control"]:
            continue
        s = pc_sum.setdefault(r["system"], {"stored": 0, "rule": 0, "n": 0})
        s["stored"] += r["stored"]; s["rule"] += r["rule"]; s["n"] += 1
    poison_down = {}
    for s in ("ace", "attest_secure_v4", "reasoningbank"):
        d = ROOT / "runs/gate_confirm/poison_float" / s / "r1" / "H04"
        r = json.loads(read(d / "result.json") or "{}")
        poison_down[s] = {"first_pass": r.get("first_pass"), "conv_failed": (r.get("attempts") or [{}])[0].get("conv_failed"),
                          "files": files_after(read(d / "final.diff")), "context": (r.get("notes_context") or "")[:4000]}
    reuse_files = {}
    for cond in ("attest_v4", "no_memory"):
        for n in (1, 2, 3):
            d = DEMO / "reuse" / cond / f"run{n}"
            r = json.loads(read(d / "result.json") or "{}")
            reuse_files[f"{cond}/{n}"] = {"files": files_after(read(d / "final.diff")), "trace": trace(d / "attempt1.traj.json"),
                                         "seconds": r.get("seconds"), "steps": r.get("steps"), "cost": r.get("cost_usd")}
    learn_files = {}
    for t in ("E02", "E04", "E06"):
        d = DEMO / "learn" / t
        r = json.loads(read(d / "result.json") or "{}")
        learn_files[t] = {"diff": read(d / "final.diff"), "traces": [trace(p) for p in sorted(d.glob("attempt*.traj.json"))],
                          "seconds": [a.get("seconds") for a in r.get("attempts") or []]}
    data = {"demo": demo, "govern_offline": json.loads(read(DEMO / "govern_offline.json") or "[]"), "note_events": note_events(events),
            "events": [{k: e.get(k) for k in ("seq", "type", "id", "reason")} | {"item_id": (e.get("item") or {}).get("id")} for e in events],
            "reuse_files": reuse_files, "learn_files": learn_files, "poison_downstream": poison_down,
            "d70": pc_sum, "d71": gc, "d71_secondary": sec, "main": main_experiment(),
            "counterfactual": json.loads((ROOT / "runs/counterfactual/results.json").read_text()),
            "source_commit": __import__("subprocess").run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()}
    out = ROOT / "demo-app/src/data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, default=str))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB); traces: E04 {[len(x) for x in learn_files['E04']['traces']]}, "
          f"H04 with {len(reuse_files['attest_v4/1']['trace'])} steps, without {len(reuse_files['no_memory/1']['trace'])}")


if __name__ == "__main__":
    main()
