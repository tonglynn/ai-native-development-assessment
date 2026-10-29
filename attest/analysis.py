"""Turns result.json files into the numbers reported in the README and the HTML report.

Every number in the write-up must be computable by this module from files in runs/,
so a reviewer can recompute it. Nothing here calls a model.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .memory import CONDITIONS

GROUPS = ("experience", "heldout", "control", "stale")


def load_results(root: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(Path(root).rglob("result.json"))]


def usable(results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split into (kept, excluded). Runs that touched benchmark files are excluded (preregistered rule)."""
    kept = [r for r in results if not r.get("leaks")]
    return kept, [r for r in results if r.get("leaks")]


def _rate(rs: list[dict], key: str) -> float | None:
    return sum(bool(r[key]) for r in rs) / len(rs) if rs else None


def headline(results: list[dict]) -> list[dict]:
    """One row per (condition, group): pass@1, pass@2, mean steps, mean cost, spread across repetitions."""
    by = defaultdict(list)
    for r in results:
        by[(r["condition"], r["group"])].append(r)
    rows = []
    for cond in [c for c in CONDITIONS if any(k[0] == c for k in by)]:
        for group in GROUPS:
            rs = by.get((cond, group), [])
            if not rs:
                continue
            per_rep = defaultdict(list)
            for r in rs:
                per_rep[r.get("rep", 1)].append(r)
            rep_rates = [_rate(v, "first_pass") for v in per_rep.values()]
            rows.append({
                "condition": cond,
                "group": group,
                "runs": len(rs),
                "pass1": _rate(rs, "first_pass"),
                "pass2": _rate(rs, "final_pass"),
                "pass1_min": min(rep_rates),
                "pass1_max": max(rep_rates),
                "steps": sum(r["steps"] for r in rs) / len(rs),
                "cost_usd": sum(r["cost_usd"] for r in rs) / len(rs),
                "notes_shown": sum(len(r["shown_notes"]) for r in rs) / len(rs),
            })
    return rows


def per_task(results: list[dict]) -> dict[str, dict[str, dict]]:
    """task_id -> condition -> {"pass1": k, "runs": n, "missed": {convention: count}}."""
    table: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in results:
        cell = table[r["task_id"]].setdefault(r["condition"], {"pass1": 0, "runs": 0, "missed": defaultdict(int)})
        cell["runs"] += 1
        cell["pass1"] += bool(r["first_pass"])
        for c in r["attempts"][0]["conv_failed"]:
            cell["missed"][c] += 1
    return {t: {c: dict(v, missed=dict(v["missed"])) for c, v in conds.items()} for t, conds in sorted(table.items())}


def regressions(results: list[dict], baseline: str = "no_memory") -> list[dict]:
    """Tasks where a memory condition passes on the first attempt LESS often than the no-memory baseline."""
    out = []
    for task_id, conds in per_task(results).items():
        base = conds.get(baseline)
        if not base:
            continue
        for cond, cell in conds.items():
            if cond == baseline:
                continue
            if cell["pass1"] / cell["runs"] < base["pass1"] / base["runs"]:
                out.append({"task_id": task_id, "condition": cond,
                            "memory": f"{cell['pass1']}/{cell['runs']}", "baseline": f"{base['pass1']}/{base['runs']}"})
    return out


def contamination(results: list[dict]) -> list[dict]:
    """For control tasks (simkit): how many notes learned on another repository were shown, per condition."""
    rows = defaultdict(lambda: {"runs": 0, "foreign_notes_shown": 0, "pass1": 0})
    for r in results:
        if r["group"] != "control":
            continue
        row = rows[r["condition"]]
        row["runs"] += 1
        row["pass1"] += bool(r["first_pass"])
        row["foreign_notes_shown"] += len(r["shown_notes"])  # every note so far was learned on ledgerly
    return [{"condition": c, **v} for c, v in rows.items()]


def stale_timeline(results: list[dict]) -> list[dict]:
    """Stale-phase runs in order with the memory events they caused (for the recovery story)."""
    rows = []
    for r in sorted((r for r in results if r["group"] == "stale"), key=lambda r: (r["condition"], r.get("rep", 1), r["task_id"])):
        changes = [
            {"id": e.get("id") or (e.get("item") or {}).get("id"), "type": e["type"], "reason": e.get("reason", "")}
            for e in r.get("memory_events", [])
            if e["type"] in ("add", "reject") or "status" in (e.get("fields") or {})
        ]
        rows.append({
            "condition": r["condition"], "rep": r.get("rep", 1), "task_id": r["task_id"],
            "first_pass": r["first_pass"], "final_pass": r["final_pass"],
            "shown": r["shown_notes"], "cited": r["cited_notes"],
            "version_warnings": (r.get("retrieval_debug") or {}).get("version_warnings", []),
            "missed": r["attempts"][0]["conv_failed"], "memory_changes": changes,
        })
    return rows


def summarise(root: Path) -> dict:
    results, excluded = usable(load_results(root))
    return {
        "root": str(root),
        "runs": len(results),
        "excluded_for_leaks": [f"{r['condition']}/{r.get('rep', 1)}/{r['task_id']}" for r in excluded],
        "headline": headline(results),
        "per_task": per_task(results),
        "regressions": regressions(results),
        "contamination": contamination(results),
        "stale_timeline": stale_timeline(results),
        "total_cost_usd": round(sum(r["cost_usd"] for r in results), 4),
    }
