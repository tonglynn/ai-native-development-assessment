"""Retrieval ablation: lexical vs embedding ranking, for Attest and ReasoningBank-style memory.

Exploratory and reported separately from the preregistered main experiment
(see PREREGISTRATION.md, section 4c). It separates two questions:

1. Retrieval quality (offline, no agent): given the *same* memory, does the
   ranking put the notes a task needs into the top 5?  Recall@5, Precision@5,
   MRR and ranking latency, per query task.
2. Effect on the work (end to end): with the same memory, does changing only the
   ranking change first-attempt pass rate, business-risk check failures, tokens?

Same memory content in both arms: neither arm learns its own experience. Both
start from the main experiment's memory snapshot after the learning phase
(``runs/<main>/<system>/r<rep>/memory/after_learn.json``), which was built with
lexical retrieval. Arms then run held-out, control and stale tasks exactly as in
the main experiment. The candidate set (status, repository scope), k (6 shown to
the agent), prompt, agent and model are identical; only the ranking function
differs.

No leakage: the retrieval query is the task title and issue only; the memory
comes from experience tasks only (checked); relevance labels are assigned per
note by an independent judge model that sees neither the queries nor which
retriever or system produced the note.
"""

from __future__ import annotations

import hashlib
import json
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import llm
from .benchmark import load_tasks
from .experiment import PHASES, run_sequence
from .memory import ABLATION_CONDITIONS, make_memory
from .memory import embedding
from .runner import Settings

K = 5
JUDGE = "deepseek/deepseek-v4-pro"
SYSTEMS = ("attest", "reasoningbank")
QUERY_GROUPS = ("heldout", "control", "stale")

CONVENTIONS = {
    "C1": "ledgerly: money is Decimal with exactly two decimal places (never float), rounded with ledgerly.money.round_money",
    "C2": "ledgerly: invalid billing input raises ledgerly.errors.BillingError with a snake_case code (not ValueError/TypeError)",
    "C3": "ledgerly: datetimes are timezone-aware UTC, passed through ledgerly.clock.ensure_utc (naive datetimes rejected)",
    "C4": "ledgerly: operations that move money or change a payment/credit write an entry with ledgerly.audit.record",
    "C5": "ledgerly: money-moving operations accept an optional idempotency_key and do not apply a retried request twice",
    "C6": "ledgerly: support refunds/credits above an approval threshold require approved_by (raise approval_required otherwise)",
    "K1": "simkit: float-only; no Decimal or datetime in simulation code",
    "K2": "simkit: invalid arguments raise the built-in ValueError",
}

LABEL_SYSTEM = """You label notes that a coding agent wrote for itself while working on software projects.
For each numbered note, list which of the RULES below the note states or clearly instructs (a note may state
several, or none). Judge only what the note says, not whether it is correct.
RULES:
""" + "\n".join(f"{k}: {v}" for k, v in CONVENTIONS.items()) + """
Return JSON: {"labels": [{"n": <number>, "rules": ["C1", ...]}]}"""


# ---------------------------------------------------------------- shared memory for both arms

def snapshot_path(source: Path, system: str, rep: int) -> Path:
    return source / system / f"r{rep}" / "memory" / "after_learn.json"


def seed(memory, items: dict) -> int:
    """Load a memory snapshot into an empty store (idempotent: a resumed run is not seeded twice)."""
    if memory.store.items():
        return 0
    for item_id in sorted(items):
        memory.store.append("add", item=items[item_id], reason="seeded from the main experiment's snapshot after the learning phase")
    return len(items)


def check_no_leakage(items: dict, query_ids: set[str]) -> None:
    sources = {(it.get("source") or {}).get("task_id") for it in items.values()}
    leaked = sources & query_ids
    if leaked:
        raise RuntimeError(f"memory contains notes learned from query tasks {sorted(leaked)}")


# ---------------------------------------------------------------- 1. retrieval quality

def _h(text: str) -> str:
    """Cache key: whitespace-normalised, so the same note gets the same label in both systems."""
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:16]


def label_notes(texts: list[str], cache_path: Path, batch: int = 15) -> dict[str, list[str]]:
    """Rules each note states, by the judge model; cached by text hash so every note is labelled once."""
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    todo = list({_h(t): t for t in texts if _h(t) not in cache}.values())
    for start in range(0, len(todo), batch):
        chunk = todo[start:start + batch]
        numbered = "\n".join(f"{n + 1}. {t}" for n, t in enumerate(chunk))
        out = llm.complete_json(LABEL_SYSTEM, f"NOTES:\n{numbered}", model=JUDGE, thinking="on")
        got = {int(x.get("n", 0)): [r for r in x.get("rules", []) if r in CONVENTIONS] for x in out.get("labels", []) if isinstance(x, dict)}
        for n, t in enumerate(chunk):
            cache[_h(t)] = {"text": t, "rules": got.get(n + 1, [])}
        cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n")
    return {t: cache[_h(t)]["rules"] for t in texts}


def metrics(ranked: list[str], relevant: set[str], k: int = K) -> dict:
    """Recall@k, Precision@k (over the notes actually returned, at most k) and reciprocal rank of the first relevant note."""
    top = ranked[:k]
    hits = sum(i in relevant for i in top)
    rr = next((1 / (pos + 1) for pos, i in enumerate(ranked) if i in relevant), 0.0)
    return {"recall": hits / len(relevant) if relevant else None,
            "precision": hits / len(top) if top else None,
            "rr": rr if relevant else None,
            "relevant": len(relevant), "returned": len(top), "irrelevant_returned": len(top) - hits}


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _bootstrap_diff(pairs: list[tuple[float, float]], resamples: int = 10000, seed_: int = 0) -> dict | None:
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if not pairs:
        return None
    diffs = [b - a for a, b in pairs]
    rng = random.Random(seed_)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(resamples))
    return {"n": len(diffs), "mean_diff": sum(diffs) / len(diffs), "ci_low": boots[int(0.025 * resamples)],
            "ci_high": boots[int(0.975 * resamples) - 1], "better": sum(d > 0 for d in diffs),
            "worse": sum(d < 0 for d in diffs), "same": sum(d == 0 for d in diffs)}


def retrieval_quality(source: Path, out: Path, reps: int) -> dict:
    """Offline evaluation of both rankers on the same post-learning memories."""
    out.mkdir(parents=True, exist_ok=True)
    queries = [t for g in QUERY_GROUPS for t in load_tasks(g)]
    query_ids = {t.id for t in queries}
    rows = []
    for system in SYSTEMS:
        for rep in range(1, reps + 1):
            path = snapshot_path(source, system, rep)
            if not path.exists():
                print(f"skip {system} r{rep}: no snapshot at {path}")
                continue
            items = json.loads(path.read_text())
            check_no_leakage(items, query_ids)
            arms = {}
            for retriever in ("lexical", "embedding"):
                memory = make_memory(system if retriever == "lexical" else f"{system}_emb", None)
                seed(memory, items)
                arms[retriever] = memory
            all_texts = sorted({t for q in queries for t in arms["lexical"].candidates(q).values()})
            labels = label_notes(all_texts, out / "labels.json")
            for q in queries:
                cands = arms["lexical"].candidates(q)
                relevant = {i for i, t in cands.items() if set(labels[t]) & set(q.conventions)}
                for retriever, memory in arms.items():
                    memory.ranking(q, None)  # warm-up: encodes the notes once, so latency below is per query
                    ranked, ms = memory.ranking(q, None)
                    m = metrics([i for i, _ in ranked], relevant)
                    tier = {c: bool({i for i in [x for x, _ in ranked][:K] if c in labels[cands[i]]}) for c in q.conventions}
                    rows.append({"system": system, "rep": rep, "retriever": retriever, "task": q.id, "group": q.group,
                                 "candidates": len(cands), "ms": ms, "conventions_in_top5": tier, **m})
    summary = []
    for system in SYSTEMS:
        for retriever in ("lexical", "embedding"):
            rs = [r for r in rows if r["system"] == system and r["retriever"] == retriever]
            if not rs:
                continue
            # review-only rules (C5, C6) are where memory matters most: is a note stating them in the top 5?
            review_only = [r["conventions_in_top5"][c] for r in rs for c in ("C5", "C6") if c in r["conventions_in_top5"]]
            summary.append({"system": system, "retriever": retriever, "queries": len(rs),
                            "recall@5": _mean(r["recall"] for r in rs), "precision@5": _mean(r["precision"] for r in rs),
                            "mrr": _mean(r["rr"] for r in rs),
                            "irrelevant_in_top5_control": _mean(r["irrelevant_returned"] for r in rs if r["group"] == "control"),
                            "ms_median": statistics.median(r["ms"] for r in rs),
                            "ms_p95": sorted(r["ms"] for r in rs)[int(0.95 * (len(rs) - 1))],
                            "review_only_rule_in_top5": _mean(float(x) for x in review_only)})
    paired = {}
    for system in SYSTEMS:
        for metric in ("recall", "precision", "rr"):
            key = lambda r: (r["rep"], r["task"])  # noqa: E731
            lex = {key(r): r[metric] for r in rows if r["system"] == system and r["retriever"] == "lexical"}
            emb = {key(r): r[metric] for r in rows if r["system"] == system and r["retriever"] == "embedding"}
            paired[f"{system}:{metric}"] = _bootstrap_diff([(lex[k], emb[k]) for k in sorted(lex) if k in emb])
    result = {"source": str(source), "k": K, "judge": JUDGE, "embedding": embedding.info(), "summary": summary,
              "paired_embedding_minus_lexical": paired, "per_query": rows}
    (out / "retrieval_quality.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    (out / "retrieval_quality.md").write_text(_quality_md(result))
    return result


def _pct(x):
    return "–" if x is None else f"{x:.0%}"


def _quality_md(res: dict) -> str:
    lines = ["# Retrieval quality: lexical vs embedding (same memory, offline)", "",
             f"Memory: snapshots after the learning phase in `{res['source']}`. Queries: held-out, control and stale tasks "
             f"(title + issue only). Relevance: the note states a rule the task needs (labels by {res['judge']}, blind to "
             f"system and retriever). k = {res['k']}. Embedding: {res['embedding']['model']} via fastembed "
             f"{res['embedding']['fastembed']}.", "",
             "| System | Retriever | Queries | Recall@5 | Precision@5 | MRR | Review-only rule in top 5 | Irrelevant in top 5 (control) | ms median | ms p95 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["summary"]:
        irr = "–" if r["irrelevant_in_top5_control"] is None else f"{r['irrelevant_in_top5_control']:.1f}"
        lines.append(f"| {r['system']} | {r['retriever']} | {r['queries']} | {_pct(r['recall@5'])} | {_pct(r['precision@5'])} | "
                     f"{'–' if r['mrr'] is None else format(r['mrr'], '.2f')} | {_pct(r['review_only_rule_in_top5'])} | {irr} | "
                     f"{r['ms_median']:.1f} | {r['ms_p95']:.1f} |")
    lines += ["", "Paired per query (embedding − lexical), bootstrap 95% interval:", "",
              "| System | Metric | n | Mean difference | 95% CI | Better / worse / same |", "|---|---|---|---|---|---|"]
    for key, d in res["paired_embedding_minus_lexical"].items():
        if d:
            s, m = key.split(":")
            lines.append(f"| {s} | {m} | {d['n']} | {d['mean_diff']:+.3f} | [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}] | "
                         f"{d['better']} / {d['worse']} / {d['same']} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 2. end to end

def run_ablation(root: Path, source: Path, reps: int = 3, parallel: int = 4, settings: Settings | None = None) -> None:
    settings = settings or Settings()
    root.mkdir(parents=True, exist_ok=True)
    missing = [str(snapshot_path(source, s, r)) for s in SYSTEMS for r in range(1, reps + 1) if not snapshot_path(source, s, r).exists()]
    if missing:
        raise SystemExit(f"the retrieval ablation starts from the main experiment's memory; missing: {missing}")
    embedding.rank("warm up", {"x": "load the model once before the threads start"}, 1)
    started = time.time()
    (root / "ablation_meta.json").write_text(json.dumps({
        "source": str(source), "conditions": ABLATION_CONDITIONS, "reps": reps, "phases": [p for p, _, _ in PHASES[1:]],
        "shown_to_agent": 6, "embedding": embedding.info(), "model": settings.model, "thinking": settings.thinking,
        "started": started}, indent=2) + "\n")

    def job(condition, rep):
        items = json.loads(snapshot_path(source, condition.removesuffix("_emb"), rep).read_text())

        def before(phase, memory):
            if phase == "heldout":
                seed(memory, items)

        return run_sequence(condition, rep, root, settings, lambda m: print(m, flush=True), phases=PHASES[1:], before_phase=before)

    jobs = [(c, r) for r in range(1, reps + 1) for c in ABLATION_CONDITIONS]
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {pool.submit(job, c, r): (c, r) for c, r in jobs}
        for f in as_completed(futures):
            c, r = futures[f]
            try:
                f.result()
                print(f"== finished {c} r{r}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"== FAILED {c} r{r}: {type(exc).__name__}: {exc}", flush=True)


def summarise_ablation(root: Path) -> dict:
    """End-to-end comparison within each system: embedding arm vs lexical arm."""
    from .analysis import _tokens, business_risks, load_results, paired, usable

    results, excluded = usable(load_results(root))
    out = {"excluded_for_leaks": len(excluded), "systems": {}}
    for system in SYSTEMS:
        arms = [system, f"{system}_emb"]
        rs = [r for r in results if r["condition"] in arms]
        per_arm = {}
        for arm in arms:
            a = [r for r in rs if r["condition"] == arm]
            first = [r for r in a if not r["attempts"][0].get("crashed")]
            ms = [r.get("retrieval_debug", {}).get("retrieval_ms") for r in a]
            ms = [m for m in ms if m is not None]
            per_arm[arm] = {
                "runs": len(a),
                **{f"pass@1_{g}": _mean(float(r["first_pass"]) for r in first if r["group"] == g) for g in QUERY_GROUPS},
                "tokens_mean": _mean(_tokens(r) for r in a),  # prompt + completion over all attempts
                "retrieval_ms_median": statistics.median(ms) if ms else None,
            }
        risks = [x for x in business_risks(rs) if x["condition"] in arms]
        out["systems"][system] = {
            "arms": per_arm,
            "paired_heldout": [p for p in paired(rs, "heldout", baseline=system) if p["condition"] == f"{system}_emb"],
            "paired_stale": [p for p in paired(rs, "stale", baseline=system) if p["condition"] == f"{system}_emb"],
            "business_risks": risks,
        }
    (root / "ablation_summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    return out
