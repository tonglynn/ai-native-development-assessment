"""Retrieval at scale: measure first, then decide whether a vector database is needed.

Offline, no API calls. Builds memories of N notes (N = 100, 1,000, 10,000 by
default): six real ledgerly notes, one per convention C1-C6, among N-6
distractors from other teams' repositories whose rules are confusable with
ledgerly's (integer cents, ValueError, naive timestamps, logging instead of an
audit trail ...). Each held-out task (title + issue) is a query; the relevant
notes are the ledgerly notes for the conventions the task needs.

Two settings:
  unscoped  rank all N notes (what ReasoningBank-style memory does)
  scoped    rank only the task repository's notes (what Attest does first)

Measured for the lexical and the embedding ranker, exactly as used in the
experiment (attest/memory/text.py, attest/memory/embedding.py):
  build_s       one-off cost before the first query (embedding: encoding all notes)
  p50/p95 ms    per-query latency after that
  matrix_mb     memory of the embedding matrix (float32)
  recall@5, mrr over the queries

Decision rule, fixed before running: keep in-process brute-force retrieval
while p95 per query stays under 200 ms and the embedding matrix under 1 GB at
the expected size of one team's memory; otherwise move to an approximate
nearest-neighbour index or a vector database. Retrieval runs once per task,
before an agent run of minutes, so 200 ms is a generous budget.

Usage:
    python scripts/retrieval_scale.py --out runs/retrieval_scale [--sizes 100,1000,10000,100000]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attest.benchmark import load_tasks  # noqa: E402
from attest.memory import embedding, text  # noqa: E402
from attest.stress import OTHER_REPOS, TEMPLATES  # noqa: E402

K = 5
LEDGERLY_NOTES = {
    "C1": "Money is Decimal: round every amount with ledgerly.money.round_money to two decimal places, never float.",
    "C2": "Invalid billing input raises ledgerly.errors.BillingError with a snake_case code, not ValueError.",
    "C3": "Pass every datetime through ledgerly.clock.ensure_utc; naive datetimes are rejected.",
    "C4": "Operations that move money or change a payment or credit write ledgerly.audit.record(event, ..._id=, amount=).",
    "C5": "Money-moving functions accept idempotency_key=None and return early if an audit entry with that key exists.",
    "C6": "Support refunds and credits above 500.00 need approved_by, else BillingError('approval_required').",
}
MODULES = ["billing", "payments", "orders", "accounts", "refunds", "payouts", "invoices", "ledger", "wallet", "checkout"]


def build_memory(n: int, seed: int = 0) -> tuple[dict[str, str], dict[str, str]]:
    """(id -> text, id -> repo): the six ledgerly notes plus n-6 distractors."""
    rng = random.Random(seed)
    docs, repo = {}, {}
    for conv, content in LEDGERLY_NOTES.items():
        docs[f"led-{conv}"], repo[f"led-{conv}"] = content, "ledgerly"
    repos = list(OTHER_REPOS)
    k = 0
    while len(docs) < n:
        r = repos[k % len(repos)] if k < len(repos) * len(TEMPLATES) else f"{rng.choice(OTHER_REPOS)}-{rng.choice(MODULES)}-{k // 15}"
        title, content = TEMPLATES[k % len(TEMPLATES)]
        pkg = r.replace("-", "_")
        body = content.format(repo=r, pkg=pkg)
        if k >= len(repos) * len(TEMPLATES):  # vary wording so the large memories are not exact repeats
            body = body.replace("in", rng.choice(["in", "within", "for"]), 1) + f" (see {rng.choice(MODULES)} module)"
        docs[f"d{k:06d}"], repo[f"d{k:06d}"] = f"{title} {body}", r
        k += 1
    return docs, repo


def evaluate(ranker, queries, docs, repo, scoped: bool) -> dict:
    lat, recalls, rrs = [], [], []
    for q in queries:
        pool = {i: t for i, t in docs.items() if repo[i] == "ledgerly"} if scoped else docs
        relevant = {f"led-{c}" for c in q.conventions if c in LEDGERLY_NOTES}
        t0 = time.perf_counter()
        ranked = [i for i, _ in ranker(f"{q.title} {q.issue}", pool, None)]
        lat.append((time.perf_counter() - t0) * 1000)
        recalls.append(len(relevant & set(ranked[:K])) / len(relevant))
        rrs.append(next((1 / (p + 1) for p, i in enumerate(ranked) if i in relevant), 0.0))
    lat.sort()
    return {"p50_ms": round(statistics.median(lat), 2), "p95_ms": round(lat[int(0.95 * (len(lat) - 1))], 2),
            "recall@5": round(sum(recalls) / len(recalls), 3), "mrr": round(sum(rrs) / len(rrs), 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="100,1000,10000")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    queries = load_tasks("heldout")
    rows = []
    for n in [int(x) for x in args.sizes.split(",")]:
        docs, repo = build_memory(n)
        embedding._doc_cache.clear()
        t0 = time.perf_counter()
        embedding.rank("warm up", docs, 1)  # loads the model and encodes every note once
        build = time.perf_counter() - t0
        for name, ranker in (("lexical", text.rank), ("embedding", embedding.rank)):
            for scoped in (False, True):
                row = {"notes": n, "ranker": name, "setting": "scoped" if scoped else "unscoped",
                       "build_s": round(build, 2) if name == "embedding" else 0.0,
                       "matrix_mb": round(n * 384 * 4 / 2**20, 1) if name == "embedding" else 0.0,
                       **evaluate(ranker, queries, docs, repo, scoped)}
                rows.append(row)
                print(json.dumps(row), flush=True)
    info = {"embedding": embedding.info(), "queries": [q.id for q in queries], "k": K,
            "decision_rule": "brute force while p95 < 200 ms and matrix < 1 GB at one team's memory size", "rows": rows}
    (args.out / "scale.json").write_text(json.dumps(info, indent=2) + "\n")
    lines = ["# Retrieval at scale", "", "Six ledgerly notes among N-6 confusable notes from other repositories; queries are the "
             "10 held-out tasks. Unscoped ranks all notes; scoped ranks the task repository's notes only (Attest).", "",
             "| Notes | Ranker | Setting | Build (s) | Matrix (MB) | p50 ms | p95 ms | Recall@5 | MRR |", "|---|---|---|---|---|---|---|---|---|"]
    lines += [f"| {r['notes']:,} | {r['ranker']} | {r['setting']} | {r['build_s']} | {r['matrix_mb']} | {r['p50_ms']} | {r['p95_ms']} | "
              f"{r['recall@5']:.0%} | {r['mrr']:.2f} |" for r in rows]
    (args.out / "scale.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
