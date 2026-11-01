"""Secondary measures for the gate confirmation run (D71), computed from every held-out result.json; descriptive,
not tested (added after the run, at the user's request). Wall-clock time is left out: the arms shared one runner.

Usage: python scripts/gate_confirm_secondary.py runs/gate_confirm
"""

import glob
import json
import sys
from pathlib import Path

ARMS = ["reasoningbank", "ace", "attest", "attest_no_gate", "attest_secure_v31", "attest_secure_v4"]


def main():
    root = Path(sys.argv[1])
    rows = []
    for a in ARMS:
        rs = [json.load(open(f)) for f in glob.glob(str(root / "clean" / a / "r*" / "H*" / "result.json"))]
        n = len(rs)
        conv = {}
        for c in ("C4", "C5", "C6"):
            need = [r for r in rs if c in r["conventions"]]
            conv[c] = f"{sum(c in (r['attempts'][0]['conv_failed'] or []) for r in need)}/{len(need)}"
        mem = [len(json.load(open(p))) for p in glob.glob(str(root / "clean" / a / "r*" / "memory" / "after_learn.json"))]
        rows.append({"arm": a, "runs": n, "first_pass": sum(r["first_pass"] for r in rs) / n, "final_pass": sum(r["final_pass"] for r in rs) / n,
                     "c5_failed": conv["C5"], "c6_failed": conv["C6"], "c4_failed": conv["C4"],
                     "steps": round(sum(r["steps"] for r in rs) / n, 1), "cost_usd": round(sum(r["cost_usd"] for r in rs) / n, 4),
                     "notes_in_memory": round(sum(mem) / max(1, len(mem)), 1),
                     "memory_tokens": round(sum(r.get("memory_tokens_approx") or 0 for r in rs) / n)})
    lines = ["# Gate confirmation, secondary measures (D71; clean stream, held-out, first attempt; descriptive)", "",
             "| Arm | Runs | First pass | Final pass | C5 failed | C6 failed | C4 failed | Steps | Cost / run (USD) | Notes in memory | Memory tokens / task |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r['arm']} | {r['runs']} | {r['first_pass']:.0%} | {r['final_pass']:.0%} | {r['c5_failed']} | {r['c6_failed']} | {r['c4_failed']} | "
              f"{r['steps']} | {r['cost_usd']} | {r['notes_in_memory']} | {r['memory_tokens']} |" for r in rows]
    (root / "secondary.md").write_text("\n".join(lines) + "\n")
    (root / "secondary.json").write_text(json.dumps(rows, indent=1) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
