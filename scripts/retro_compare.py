"""Paired comparison of two systems in a retro run (D46). Reading rule fixed before the run.

Question: on a repository not looked at before (home-assistant/core), does writing notes as general
rules with 2 slots reserved for repository-wide rules (attest_general) anticipate more convention
comments than Attest as evaluated (attest)? The view attest_general_noreserve (same notes, slots off)
separates the wording from the slots.

Rule: unit = test PR; difference = covered(a) - covered(b) summed over PRs, divided by all convention
comments; 95% interval by paired bootstrap over test PRs (10,000 resamples, seed 0). "Improves" only
if the lower bound is > 0; otherwise "direction only" (or "no difference"). Precision is reported
beside it; a precision drop of more than 5 points is reported as a cost. Baselines (ReasoningBank,
ACE) are reported, not tested. Saleor and Flask are development data for this change and are not
used as evidence for it.

Usage: python scripts/retro_compare.py runs/retro_hass attest_general attest
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path


def main() -> None:
    run, a, b = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    rows = [r for r in json.loads((run / "results.json").read_text())["per_pr"] if a in r and b in r]
    conv = [len(r["convention_comments"]) for r in rows]
    da = [r[a]["covered"] for r in rows]
    db = [r[b]["covered"] for r in rows]
    total = sum(conv)
    diff = (sum(da) - sum(db)) / total if total else 0.0
    rng = random.Random(0)
    boots = []
    for _ in range(10_000):
        idx = [rng.randrange(len(rows)) for _ in rows]
        t = sum(conv[i] for i in idx)
        boots.append((sum(da[i] for i in idx) - sum(db[i] for i in idx)) / t if t else 0.0)
    boots.sort()
    lo, hi = boots[250], boots[9749]
    prec = {s: (sum(r[s]["relevant"] for r in rows), sum(len(r[s]["shown"]) for r in rows)) for s in (a, b)}
    verdict = "improves" if lo > 0 else ("no difference" if diff == 0 else "direction only")
    out = {"a": a, "b": b, "test_prs": len(rows), "convention_comments": total, "covered": {a: sum(da), b: sum(db)},
           "difference": round(diff, 3), "ci95": [round(lo, 3), round(hi, 3)], "verdict": verdict,
           "precision": {s: (round(x / n, 3) if n else None) for s, (x, n) in prec.items()}}
    print(json.dumps(out, indent=2))
    (run / f"compare_{a}_vs_{b}.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
