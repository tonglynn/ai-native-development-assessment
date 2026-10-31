"""Audit the numbers in README.md, RESULTS.md and DECISIONS.md against the committed runs (D67).

Layer 1 (deterministic, no model): split each document into sections; for each section, collect the run folders it
names (`runs/<name>`) and its numbers (fractions like 14/23 and percentages like 85%); check that every named folder
exists, and that each number appears in one of the named folders' report.md / results.json (or elsewhere in the same
document). Unmatched numbers are listed for review: many are derived (differences, means) and are not errors by
themselves.
Layer 2 (--model, needs DEEPSEEK_API_KEY): an independent model (deepseek-v4-pro, which wrote none of the documents)
reads each section with the reports it names and lists numbers that are unsupported or contradict the reports.

Usage: python scripts/audit_numbers.py --out runs/audit_numbers [--model]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DOCS = ("README.md", "RESULTS.md", "DECISIONS.md")
RUN_RE = re.compile(r"runs/([A-Za-z0-9_\-]+)")
NUM_RE = re.compile(r"(?<![\w.])(\d+/\d+|\d+(?:\.\d+)?%)")
AUDIT = """You audit a research write-up against its raw results. You get one SECTION of a document and the REPORTS
(result files) it cites. List every number in the section that is not supported by the reports, contradicts them,
or contradicts another number in the same section. Derived numbers (differences, sums, rates computed from counts in
the reports) are supported if the arithmetic holds; check it. Do not comment on style. Return JSON:
{"issues": [{"claim": "<the sentence or table cell>", "problem": "<what does not match and what the report says>"}]}"""


def sections(text: str):
    parts = re.split(r"(?m)^(#{2,3} .*|\| D\d+ \|.*)$", text)
    out, title = [], "(start)"
    for chunk in parts:
        if re.match(r"^(#{2,3} |\| D\d+ \|)", chunk or ""):
            if chunk.startswith("| D"):
                out.append((chunk.split("|")[1].strip(), chunk))
            title = chunk.strip("# ").strip()[:80]
        elif chunk and chunk.strip():
            out.append((title, chunk))
    return out


def run_text(name: str) -> str:
    d = ROOT / "runs" / name
    parts = []
    for f in ("report.md", "summary.json", "results.json"):
        if (d / f).exists():
            parts.append((d / f).read_text()[:60000])
    for f in sorted(d.glob("*.md"))[:5]:
        if f.name != "report.md":
            parts.append(f.read_text()[:20000])
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", action="store_true")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows, issues = [], []
    for doc in DOCS:
        text = (ROOT / doc).read_text()
        for title, body in sections(text):
            runs = sorted(set(RUN_RE.findall(body)))
            missing = [r for r in runs if not (ROOT / "runs" / r).exists() and not r.endswith(("<name>", "<main>"))]
            refs = "\n".join(run_text(r) for r in runs if (ROOT / "runs" / r).exists())
            nums = sorted(set(NUM_RE.findall(body)))
            unmatched = [n for n in nums if runs and n not in refs and text.count(n) < 2]
            rows.append({"doc": doc, "section": title, "runs": runs, "missing_runs": missing, "numbers": len(nums), "unmatched": unmatched})
            if args.model and runs and nums:
                from attest import llm
                try:
                    res = llm.complete_json(AUDIT, f"SECTION ({doc} / {title}):\n{body[:12000]}\n\nREPORTS:\n{refs[:60000]}",
                                            model="deepseek/deepseek-v4-pro")
                    for it in res.get("issues") or []:
                        issues.append({"doc": doc, "section": title, **it})
                except Exception as exc:  # noqa: BLE001
                    issues.append({"doc": doc, "section": title, "claim": "(audit failed)", "problem": f"{type(exc).__name__}: {exc}"})
                print(json.dumps({"doc": doc, "section": title, "issues_so_far": len(issues)}), flush=True)
    (args.out / "results.json").write_text(json.dumps({"layer1": rows, "layer2": issues}, indent=2, ensure_ascii=False) + "\n")
    miss = [r for r in rows if r["missing_runs"]]
    unm = [r for r in rows if r["unmatched"]]
    lines = ["# Number audit (D67)", "", f"Sections: {len(rows)}; citing a run folder: {sum(bool(r['runs']) for r in rows)}.",
             f"Run folders cited but missing: {sum(len(r['missing_runs']) for r in miss)}.",
             f"Sections with numbers not found in their cited reports (review; many are derived): {len(unm)}.", ""]
    for r in miss:
        lines.append(f"- MISSING {r['doc']} / {r['section']}: {', '.join(r['missing_runs'])}")
    lines += ["", "## Numbers not found in the cited reports", ""]
    for r in unm:
        lines.append(f"- {r['doc']} / {r['section']} ({', '.join(r['runs'])}): {', '.join(r['unmatched'][:25])}")
    if args.model:
        lines += ["", f"## Independent model audit ({len(issues)} issues)", ""]
        lines += [f"- **{i['doc']} / {i['section']}**: {i.get('claim', '')[:200]} — {i.get('problem', '')[:300]}" for i in issues]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:8]))


if __name__ == "__main__":
    main()
