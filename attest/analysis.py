"""Turns result.json files into the numbers reported in the README and the HTML report.

Every number in the write-up must be computable by this module from files in runs/,
so a reviewer can recompute it. Nothing here calls a model.
"""

from __future__ import annotations

import json
import random
import re
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
        if not r["attempts"][0].get("crashed"):  # a crash is a failure, but not a convention miss
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


TIERS = {"discoverable": ("C1", "C2", "C3", "C4"), "review_only": ("C5", "C6")}


def convention_hits(results: list[dict]) -> list[dict]:
    """Per condition and convention: how often the first attempt satisfied it (crashes excluded)."""
    counts = defaultdict(lambda: [0, 0])  # (condition, convention) -> [satisfied, checked]
    for r in results:
        first = r["attempts"][0]
        if first.get("crashed"):
            continue
        for conv in r.get("conventions", []):
            cell = counts[(r["condition"], conv)]
            cell[1] += 1
            cell[0] += conv not in first["conv_failed"]
    rows = []
    for (cond, conv), (ok, n) in sorted(counts.items()):
        tier = next((t for t, cs in TIERS.items() if conv in cs), "simkit")
        rows.append({"condition": cond, "convention": conv, "tier": tier, "satisfied": ok, "checked": n, "rate": ok / n})
    return rows


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


# ---------------------------------------------------------------- tiers, paired comparison, attribution

REVIEW_ONLY = set(TIERS["review_only"])


def task_tier(r: dict) -> str:
    convs = set(r.get("conventions", []))
    if not convs or convs <= {"K1", "K2"}:
        return "simkit"
    return "review_only" if convs & REVIEW_ONLY else "discoverable"


def _tokens(r: dict) -> int:
    return sum((a.get("tokens") or {}).get("prompt", 0) + (a.get("tokens") or {}).get("completion", 0) for a in r["attempts"])


def tier_split(results: list[dict], group: str = "heldout") -> list[dict]:
    """pass@1, steps and tokens per condition, for tasks that need review-only knowledge vs tasks that do not."""
    by = defaultdict(list)
    for r in results:
        if r["group"] == group:
            by[(r["condition"], task_tier(r))].append(r)
    rows = []
    for (cond, tier), rs in sorted(by.items(), key=lambda kv: (CONDITIONS.index(kv[0][0]) if kv[0][0] in CONDITIONS else 99, kv[0][1])):
        rows.append({"condition": cond, "tier": tier, "runs": len(rs), "pass1": _rate(rs, "first_pass"),
                     "steps": sum(r["steps"] for r in rs) / len(rs), "tokens": sum(_tokens(r) for r in rs) / len(rs)})
    return rows


def paired(results: list[dict], group: str = "heldout", baseline: str = "no_memory",
           resamples: int = 10000, seed: int = 0) -> list[dict]:
    """Per-task pass@1 difference against the baseline, with a bootstrap 95% interval over tasks.

    Repetitions of the same task are averaged first, so the unit of analysis is the task.
    """
    rates: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for r in results:
        if r["group"] == group:
            rates[r["condition"]][r["task_id"]].append(bool(r["first_pass"]))
    base = {t: sum(v) / len(v) for t, v in rates.get(baseline, {}).items()}
    rng = random.Random(seed)
    rows = []
    for cond, per_task in rates.items():
        if cond == baseline:
            continue
        tasks = sorted(set(per_task) & set(base))
        if not tasks:
            continue
        diffs = [sum(per_task[t]) / len(per_task[t]) - base[t] for t in tasks]
        boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(resamples))
        rows.append({
            "condition": cond, "tasks": len(tasks), "mean_diff": sum(diffs) / len(diffs),
            "ci_low": boots[int(0.025 * resamples)], "ci_high": boots[int(0.975 * resamples) - 1],
            "wins": sum(d > 0 for d in diffs), "losses": sum(d < 0 for d in diffs), "ties": sum(d == 0 for d in diffs),
        })
    return sorted(rows, key=lambda x: CONDITIONS.index(x["condition"]) if x["condition"] in CONDITIONS else 99)


CONVENTION_PATTERNS = {
    "C1": r"round_money|half[- ]up|ROUND_HALF|quantiz|two decimal|2 decimal|Decimal",
    "C2": r"BillingError",
    "C3": r"ensure_utc|time[- ]?zone|tz-aware|aware UTC|naive",
    "C4": r"audit\.record|audit entr|audit trail|audit log",
    "C5": r"idempoten",
    "C6": r"approv",
}
NOTE_RE = re.compile(r"\[((?:at|rb|ace)-\d{4})\](.*?)(?=\n\s*-?\s*\[(?:at|rb|ace)-\d{4}\]|\n## |\Z)", re.S)


def _notes_by_id(context: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in NOTE_RE.finditer(context or "")}


def attribution(results: list[dict]) -> list[dict]:
    """Was a note about convention X shown or cited, and did the first attempt actually satisfy X?

    Judged from behaviour (the hidden test for X), not from the agent's own claim.
    """
    cells = defaultdict(lambda: defaultdict(int))
    for r in results:
        first = r["attempts"][0]
        if first.get("crashed") or r["condition"] == "no_memory":
            continue
        notes = _notes_by_id(r.get("notes_context", ""))
        cited = set(r.get("cited_notes", []))
        for conv in r.get("conventions", []):
            pattern = CONVENTION_PATTERNS.get(conv)
            if not pattern:
                continue
            related = {i for i, text in notes.items() if re.search(pattern, text, re.I)}
            ok = conv not in first["conv_failed"]
            c = cells[(r["condition"], conv)]
            c["checked"] += 1
            if related:
                c["shown"] += 1
                c["shown_ok"] += ok
                if related & cited:
                    c["cited"] += 1
                    c["cited_ok"] += ok
                elif ok:
                    c["followed_uncited"] += 1
            else:
                c["not_shown"] += 1
                c["not_shown_ok"] += ok
    rows = []
    for (cond, conv), c in sorted(cells.items(), key=lambda kv: (CONDITIONS.index(kv[0][0]) if kv[0][0] in CONDITIONS else 99, kv[0][1])):
        rows.append({"condition": cond, "convention": conv, **dict(c),
                     "ok_when_shown": c["shown_ok"] / c["shown"] if c["shown"] else None,
                     "ok_when_not_shown": c["not_shown_ok"] / c["not_shown"] if c["not_shown"] else None})
    return rows


# ---------------------------------------------------------------- memory funnel: where did the needed note get lost?

FUNNEL_STAGES = ("not_in_memory", "excluded", "not_retrieved", "retrieved_not_injected", "injected")


def funnel_stage(trace: dict, pattern: str) -> tuple[str, list[str]]:
    """How far the notes about one convention got: (furthest stage, excluded reasons if stuck there)."""
    about = {i for i, text in (trace.get("texts") or {}).items() if re.search(pattern, text, re.I)}
    if not about:
        return "not_in_memory", []
    if about & set(trace.get("injected") or []):
        return "injected", []
    if about & set(trace.get("retrieved") or []):
        return "retrieved_not_injected", []
    excluded = trace.get("excluded") or {}
    if about <= set(excluded):
        return "excluded", sorted({excluded[i].split(":")[0].split(" by ")[0] for i in about})
    return "not_retrieved", []


def funnel(results: list[dict], groups=("heldout", "stale")) -> list[dict]:
    """For every (run, convention the task needs): how far a note about it got, and whether the first
    attempt then satisfied the convention (its hidden test). Separates "memory never had it" from
    "had it but filtered", "not ranked high enough", "cut before injection" and "injected but not followed".

    Notes are matched to conventions with CONVENTION_PATTERNS (approximate, the same for every system).
    """
    cells = defaultdict(lambda: {"checked": 0, **{f"{s}_{o}": 0 for s in FUNNEL_STAGES for o in ("ok", "fail")}})
    reasons = defaultdict(lambda: defaultdict(int))
    for r in results:
        first = r["attempts"][0]
        trace = (r.get("retrieval_debug") or {}).get("trace")
        if first.get("crashed") or r["group"] not in groups or trace is None:
            continue
        for conv in r.get("conventions", []):
            pattern = CONVENTION_PATTERNS.get(conv)
            if not pattern:
                continue
            stage, why = funnel_stage(trace, pattern)
            ok = conv not in first["conv_failed"]
            c = cells[(r["condition"], conv)]
            c["checked"] += 1
            c[f"{stage}_{'ok' if ok else 'fail'}"] += 1
            for w in why:
                reasons[(r["condition"], conv)][w] += 1
    rows = []
    for (cond, conv), c in sorted(cells.items(), key=lambda kv: (CONDITIONS.index(kv[0][0]) if kv[0][0] in CONDITIONS else 99, kv[0][1])):
        injected = c["injected_ok"] + c["injected_fail"]
        rows.append({"condition": cond, "convention": conv, **c,
                     "followed_when_injected": c["injected_ok"] / injected if injected else None,
                     "excluded_reasons": dict(reasons[(cond, conv)])})
    return rows


# ---------------------------------------------------------------- business risks (see SCENARIO.md)

RISKS = {
    "duplicate_money_operation": lambda task, test: test.startswith("test_conv_c5"),
    "unauthorised_operation": lambda task, test: test.startswith("test_conv_c6") and "allows" not in test,
    "legitimate_operation_blocked": lambda task, test: test.startswith("test_conv_c6_allows"),
    "amount_precision_violation": lambda task, test: test.startswith("test_conv_c1"),
    "unaudited_money_movement": lambda task, test: test.startswith("test_conv_c4"),
    "outdated_policy_applied": lambda task, test: task.startswith("S") and ("rounding_policy" in test or test.startswith("test_conv_c6")),
    "rule_in_wrong_repository": lambda task, test: task.startswith("B") and test.startswith("test_conv_k"),
}


def _hidden_test_names(task_id: str) -> list[str]:
    from .benchmark import load_task
    from .verify import _parse_hidden_tests

    return [t.name for t in _parse_hidden_tests(load_task(task_id).hidden_test)]


def business_risks(results: list[dict], groups=("heldout", "stale", "control")) -> list[dict]:
    """Per condition and risk: how often the first attempt failed a check guarding against it."""
    names = {}
    cells = defaultdict(lambda: [0, 0])  # (condition, risk) -> [failed, checked]
    for r in results:
        if r["group"] not in groups or r["attempts"][0].get("crashed"):
            continue
        tid = r["task_id"]
        names.setdefault(tid, _hidden_test_names(tid))
        failed = set(r["attempts"][0].get("tests_failed", []))
        for test in names[tid]:
            for risk, applies in RISKS.items():
                if applies(tid, test):
                    cell = cells[(r["condition"], risk)]
                    cell[1] += 1
                    cell[0] += test in failed
    rows = []
    for (cond, risk), (bad, n) in sorted(cells.items(), key=lambda kv: (CONDITIONS.index(kv[0][0]) if kv[0][0] in CONDITIONS else 99, list(RISKS).index(kv[0][1]))):
        rows.append({"condition": cond, "risk": risk, "failed": bad, "checked": n, "rate": bad / n})
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
        "convention_hits": convention_hits(results),
        "tier_split": tier_split(results),
        "paired": paired(results),
        "attribution": attribution(results),
        "funnel": funnel(results),
        "business_risks": business_risks(results),
        "stale_timeline": stale_timeline(results),
        "total_cost_usd": round(sum(r["cost_usd"] for r in results), 4),
    }
