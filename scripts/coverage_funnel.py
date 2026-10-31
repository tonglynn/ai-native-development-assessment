"""Where the convention comments Attest missed on Saleor were lost (offline; hand labels).

Stages, for each of the 25 convention comments in the 16 test PRs of runs/retro_saleor:
  taught     a training PR's reviewer comment states the rule (yes / partly / no)
  provable   a changed line can show the rule was followed (code, test, docs, config) or not
             (process: porting, rebasing, resolving conversations); the gate needs one
  stored     Attest kept a note that states it
  shown      that note was among the 6 recalled for the test PR
  credited   the independent judge said a recalled note anticipated the comment (from results.json)
The first three are hand labels (runs/retro_saleor_funnel/labels.json, written by Claude after
reading the training comments and Attest's notes); shown and credited come from the stored run.
The comments were re-fetched by number (scripts/fetch_pr_comments.py), so edits since the run are
possible. Reading rule: report the count lost at each stage; no improvement is claimed here.

Usage: python scripts/coverage_funnel.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN, OUT = ROOT / "runs/retro_saleor", ROOT / "runs/retro_saleor_funnel"


def main() -> None:
    res = json.loads((RUN / "results.json").read_text())
    labels = json.loads((OUT / "labels.json").read_text())["rules"]
    by_pr = {r["pr"]: r for r in res["per_pr"]}
    rows = []
    for lab in labels:
        r = by_pr[lab["pr"]]
        shown = set(r["attest"]["shown"])
        credited = any(a["i"] == lab["comment"] for a in r["attest"]["anticipated"])
        stage = ("not taught" if lab["taught_in_train"] == "no" else
                 "taught, not provable by a diff" if lab["kind"] == "process" else
                 "taught, not stored" if not lab["attest_notes"] else
                 "stored, not shown" if not shown & set(lab["attest_notes"]) else
                 "shown, not credited" if not credited else "credited")
        rows.append({**lab, "shown_notes": sorted(shown & set(lab["attest_notes"])), "credited": credited, "lost_at": stage,
                     "baselines_credited": {s: any(a["i"] == lab["comment"] for a in r[s]["anticipated"]) for s in ("reasoningbank", "ace")}})
    order = ["not taught", "taught, not provable by a diff", "taught, not stored", "stored, not shown", "shown, not credited", "credited"]
    lines = ["# Where Attest lost the Saleor convention comments (offline, hand labels)", "",
             "| Stage | Comments | Of which ReasoningBank / ACE credited | Ids |", "|---|---|---|---|"]
    for st in order:
        g = [x for x in rows if x["lost_at"] == st]
        rb = sum(x["baselines_credited"]["reasoningbank"] for x in g)
        ace = sum(x["baselines_credited"]["ace"] for x in g)
        lines.append(f"| {st} | {len(g)} | {rb} / {ace} | {', '.join(x['id'] for x in g)} |")
    lines += ["", "| Id | Rule | Taught | Kind | Attest notes | Shown | Lost at |", "|---|---|---|---|---|---|---|"]
    for x in rows:
        lines.append(f"| {x['id']} | {x['rule']} | {x['taught_in_train']} | {x['kind']} | {', '.join(x['attest_notes']) or '–'} | "
                     f"{', '.join(x['shown_notes']) or '–'} | {x['lost_at']} |")
    (OUT / "funnel.json").write_text(json.dumps(rows, indent=1) + "\n")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
