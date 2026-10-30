"""Point 5 of forgetting V2: check learned rules against the code they describe (exploratory).

Question: can the repository itself say whether a remembered rule still holds? A rule whose
anchors still exist is positive evidence against archiving it for lack of use; a rule whose
anchors are gone, or that a newer changelog entry mentions, should be reviewed.

For each of the 25 active learned notes of the main experiment:
  anchors       names the note mentions that the project defines at the version the note was
                learned on (functions, classes, module constants, module names, file paths),
                plus domain terms found in the code at that version ("half-up" in
                ROUND_HALF_UP) and decimal amounts. Python builtins (bool, isinstance) are not
                anchors: they never disappear, so they prove nothing.
  status on a version:
    drifted       an anchor is missing from the code
    review        a changelog entry newer than the note's version mentions one of its
                  names, terms or amounts
    alive         every anchor is present and no newer entry mentions it
    not checkable no anchor and no mention
Versions: ledgerly 1.0.0 (all notes valid), 2.0.0 (rounding became half-even, the approval
threshold went from 500.00 to 1000.00; both in CHANGELOG) and a copy of 1.0.0 with three APIs
silently renamed (ensure_utc -> to_utc, audit.record -> audit.log_event, to_money ->
parse_money; no changelog entry).
Ground truth (from the benchmark design, by pattern on the note text): on 2.0.0 a note is
stale if it claims half-up rounding or the 500.00 approval threshold; on the renamed copy if
it names a renamed API; otherwise valid.

Changed after the first run (disclosed; the first run's report is kept beside the final one):
changelog mentions are matched only on project names other than module names, domain terms
and amounts, as whole words; the first run matched any word of 4+ letters as a substring.

Reported, no threshold chosen: on 1.0.0 the false-dead count (must be 0 for "alive" to be
usable as positive evidence) and coverage (share checkable); on the other two versions,
stale notes flagged and valid notes wrongly flagged. Known limit, stated before running: an
"alive" verdict means the names a rule mentions still exist, not that the rule still holds;
rules that live only in review comments (idempotency, approval) mention few project names.

Usage: python scripts/liveness_check.py --out runs/liveness
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.analysis import CONVENTION_PATTERNS  # noqa: E402
from attest.memory.verify import anchors, corpus, mentions, present  # noqa: E402,F401
from attest.memory.verify import status as _status  # noqa: E402

RENAMES = {"ensure_utc": "to_utc", "record": "log_event", "to_money": "parse_money"}
# The first run matched any mentioned word of 4+ letters as a substring of newer changelog
# entries; generic words ("code", the module name "money") flagged 3 valid notes for review.
# Changed after seeing that run (runs/liveness/report_first_run.md): see status().
FIRST_RUN_MATCHING = False


def status(note: dict, base: dict, current: dict) -> dict:
    return _status(note, base, current, first_run_matching=FIRST_RUN_MATCHING)


def renamed_copy(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    for p in (dst / "ledgerly").rglob("*.py"):
        s = p.read_text()
        s = re.sub(r"\bensure_utc\b", "to_utc", s)
        s = re.sub(r"\bto_money\b", "parse_money", s)
        s = re.sub(r"\baudit\.record\b", "audit.log_event", s)
        if p.name == "audit.py":
            s = re.sub(r"\bdef record\b", "def log_event", s)
        s = re.sub(r"from \.audit import record\b", "from .audit import log_event", s)
        p.write_text(s)
    return dst


def about(text: str) -> set[str]:
    return {c for c, p in CONVENTION_PATTERNS.items() if re.search(p, text, re.I)}


def truth(note: dict, version: str) -> str:
    text = f"{note['title']} {note['content']}"
    if version == "2.0.0":
        stale = bool(re.search(r"half[- ]?up", text, re.I)) or ("C6" in about(text) and bool(re.search(r"\b500(\.00)?\b", text)))
    elif version == "renamed":
        stale = bool(re.search(r"\bensure_utc\b|\baudit\.record\b|\bto_money\b", text))
    else:
        stale = False
    return "stale" if stale else "valid"


def notes() -> list[dict]:
    out = []
    for rep in (1, 2, 3):
        items = json.loads((ROOT / f"runs/main/attest/r{rep}/memory/after_learn.json").read_text())
        for i, it in sorted(items.items()):
            if it.get("status") in ("active", "suspect"):
                out.append({"key": f"r{rep}/{i}", "title": it["title"], "content": it["content"],
                            "version": (it.get("scope") or {}).get("observed_version") or "1.0.0"})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    v1 = ROOT / "benchmark/repos/ledgerly_v1"
    with tempfile.TemporaryDirectory() as tmp:
        corpora = {"1.0.0": corpus(v1), "2.0.0": corpus(ROOT / "benchmark/repos/ledgerly_v2"),
                   "renamed": corpus(renamed_copy(v1, Path(tmp) / "ledgerly_renamed"))}
    base = corpora["1.0.0"]
    rows = []
    for n in notes():
        for version, c in corpora.items():
            rows.append({"key": n["key"], "title": n["title"], "version": version, "truth": truth(n, version), **status(n, base, c)})
    (args.out / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
    lines = ["# Liveness of learned rules against the code (exploratory)", "",
             "25 active learned notes; status computed from the code and changelog of each version; ground truth from the benchmark design.", "",
             "| Version | Stale notes | Stale flagged (drifted / review) | Valid notes | Valid wrongly flagged (drifted / review) | Alive | Not checkable |",
             "|---|---|---|---|---|---|---|"]
    for version in corpora:
        rs = [r for r in rows if r["version"] == version]
        stale = [r for r in rs if r["truth"] == "stale"]
        valid = [r for r in rs if r["truth"] == "valid"]
        cnt = lambda xs, s: sum(r["status"] == s for r in xs)  # noqa: E731
        lines.append(f"| {version} | {len(stale)} | {cnt(stale, 'drifted') + cnt(stale, 'review')} ({cnt(stale, 'drifted')} / {cnt(stale, 'review')}) | "
                     f"{len(valid)} | {cnt(valid, 'drifted') + cnt(valid, 'review')} ({cnt(valid, 'drifted')} / {cnt(valid, 'review')}) | "
                     f"{cnt(rs, 'alive')} | {cnt(rs, 'not checkable')} |")
    lines += ["", "Per note:", "", "| Note | 1.0.0 | 2.0.0 | renamed copy | Anchors |", "|---|---|---|---|---|"]
    for key in dict.fromkeys(r["key"] for r in rows):
        rs = {r["version"]: r for r in rows if r["key"] == key}
        cell = lambda r: f"{r['status']}{' (stale)' if r['truth'] == 'stale' else ''}"  # noqa: E731
        lines.append(f"| {key} {rs['1.0.0']['title']} | {cell(rs['1.0.0'])} | {cell(rs['2.0.0'])} | {cell(rs['renamed'])} | "
                     f"{', '.join(rs['1.0.0']['anchors']) or '–'} |")
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
