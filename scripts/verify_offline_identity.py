"""Offline check behind verify_eval's claim that just-in-time verification changes nothing outside the stale tasks (D67).

For each main-experiment repetition, replay Attest's memory event log and, at every intermediate memory state (empty,
after each event), retrieve for every experience, held-out and control task with plain Attest and with verification
(annotate and drop). The claim holds for a task if the injected context is byte-identical in all three at every state.
This covers every state each task's run could have seen, so it is stronger than checking one state per run. No model,
no agent; seconds. The stale tasks are listed separately: that is where verification is meant to change the context.

Usage: python scripts/verify_offline_identity.py --out runs/verify_offline_identity
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from attest.benchmark import load_tasks  # noqa: E402
from attest.memory.earned import EarnedMemory  # noqa: E402
from attest.memory.verify import VerifiedMemory  # noqa: E402
from attest.runner import REPOS_DIR, repo_version  # noqa: E402

GROUPS = ("experience", "heldout", "control", "stale")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tasks = {g: load_tasks(g) for g in GROUPS}
    ver = {t.id: repo_version(REPOS_DIR / t.repo) for g in GROUPS for t in tasks[g]}
    rows = []
    for rep in (1, 2, 3):
        events = [json.loads(l) for l in (ROOT / f"runs/main/attest/r{rep}/memory/events.jsonl").read_text().splitlines() if l.strip()]
        with tempfile.TemporaryDirectory() as tmp:
            mems = {"plain": EarnedMemory(Path(tmp) / "p"), "annotate": VerifiedMemory(Path(tmp) / "a", mode="annotate"),
                    "drop": VerifiedMemory(Path(tmp) / "d", mode="drop")}
            ident = {(g, t.id): True for g in GROUPS for t in tasks[g]}
            states = 0
            for k in range(len(events) + 1):
                if k:
                    e = {x: y for x, y in events[k - 1].items() if x not in ("seq", "ts", "type")}
                    for m in mems.values():
                        m.store.append(events[k - 1]["type"], **e)
                states += 1
                for g in GROUPS:
                    for t in tasks[g]:
                        ctx = {a: m.retrieve(t, ver[t.id]).context for a, m in mems.items()}
                        if not (ctx["plain"] == ctx["annotate"] == ctx["drop"]):
                            ident[(g, t.id)] = False
            for (g, tid), same in ident.items():
                rows.append({"rep": rep, "group": g, "task": tid, "identical_at_every_state": same, "states": states})
    summary = {g: f"{sum(r['identical_at_every_state'] for r in rows if r['group'] == g)}/{sum(r['group'] == g for r in rows)}" for g in GROUPS}
    (args.out / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n")
    lines = ["# Offline: is the injected context unchanged by verification outside the stale tasks? (D67)", "",
             "Main-experiment Attest event logs, every intermediate memory state, 3 repetitions; plain vs annotate vs drop.", "",
             "| Group | Task runs with byte-identical context at every state |", "|---|---|"]
    lines += [f"| {g} | {s} |" for g, s in summary.items()]
    lines += ["", "Stale is expected to differ: that is where notes drift (ledgerly 2.0.0)."]
    (args.out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
