"""Build docs/demo/index.html: a step-by-step replay of the recorded demo run (D72) with narration.

Every value on the page is read from committed records: runs/demo/demo.json (the real end-to-end run) and, for what
stored poison does later, runs/gate_confirm (D71, H04 under the test-passing poison). Nothing is typed in by hand
except the narration. The governance steps come from scripts/demo_govern.py (offline, on the recorded memory).

Usage: python scripts/build_demo_page.py [--demo runs/demo] [--out docs/demo/index.html]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def diff_lines(path: Path, n: int = 60) -> list[str]:
    if not path.exists():
        return []
    return [l[1:] for l in path.read_text().splitlines() if l.startswith("+") and not l.startswith("+++")][:n]


def around(lines: list[str], pattern: str, before: int = 3, after: int = 4) -> list[str]:
    for i, l in enumerate(lines):
        if re.search(pattern, l):
            return lines[max(0, i - before): i + after]
    return lines[:8]


def recorded_poison() -> dict:
    out = {}
    for s in ("ace", "attest_secure_v4"):
        d = ROOT / "runs/gate_confirm/poison_float" / s / "r1" / "H04"
        r = json.loads((d / "result.json").read_text())
        ctx = r.get("notes_context") or ""
        i = ctx.find("float(amount)")
        out[s] = {"first_pass": r["first_pass"], "conv_failed": r["attempts"][0]["conv_failed"],
                  "audit_lines": around(diff_lines(d / "final.diff"), r"audit\.record"),
                  "note_with_poison": ctx[max(0, ctx.rfind("\n", 0, i)): ctx.find("\n", i)].strip() if i >= 0 else ""}
    summ = json.loads((ROOT / "runs/gate_confirm/summary.json").read_text())
    out["d71"] = {"pass": summ["pass@1"], "applied": {k: v["heldout_runs_applying_poison"] for k, v in summ["poison_float"].items()},
                  "runs": {k: v["heldout_runs"] for k, v in summ["poison_float"].items()}}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=Path, default=ROOT / "runs/demo")
    ap.add_argument("--out", type=Path, default=ROOT / "docs/demo/index.html")
    args = ap.parse_args()
    demo = json.loads((args.demo / "demo.json").read_text())
    for run in demo["reuse"]["runs"]:
        run["context"] = run["context"][:3000]
    def secs(path):
        return json.loads(path.read_text()).get("seconds") if path.exists() else None
    e04 = json.loads((args.demo / "learn/E04/result.json").read_text())
    timing = {"E04": [a.get("seconds") for a in e04["attempts"]],
              "H04": max([secs(p) or 0 for p in (args.demo / "reuse").glob("*/run*/result.json")] or [0])}
    govern = json.loads((args.demo / "govern_offline.json").read_text())
    data = {"demo": demo, "recorded": recorded_poison(), "govern": govern, "timing": timing,
            "chart": "data:image/png;base64," + base64.b64encode((ROOT / "docs/effect_safety.png").read_bytes()).decode()}
    html = (Path(__file__).with_name("demo_page_template.html")).read_text()
    html = html.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)
    print(f"wrote {args.out} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
