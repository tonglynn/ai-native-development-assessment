# Retrieval at scale

Six ledgerly notes among N-6 confusable notes from other repositories; queries are the 10 held-out tasks. Unscoped ranks all notes; scoped ranks the task repository's notes only (Attest).

| Notes | Ranker | Setting | Build (s) | Matrix (MB) | p50 ms | p95 ms | Recall@5 | MRR |
|---|---|---|---|---|---|---|---|---|
| 100 | lexical | unscoped | 0.0 | 0.0 | 2.82 | 3.13 | 32% | 0.61 |
| 100 | lexical | scoped | 0.0 | 0.0 | 0.22 | 0.29 | 95% | 0.80 |
| 100 | embedding | unscoped | 10.73 | 0.1 | 40.99 | 48.37 | 48% | 0.73 |
| 100 | embedding | scoped | 10.73 | 0.1 | 35.75 | 40.98 | 94% | 0.87 |
| 1,000 | lexical | unscoped | 0.0 | 0.0 | 29.0 | 31.2 | 26% | 0.60 |
| 1,000 | lexical | scoped | 0.0 | 0.0 | 0.25 | 0.41 | 95% | 0.80 |
| 1,000 | embedding | unscoped | 18.6 | 1.5 | 41.86 | 52.69 | 30% | 0.53 |
| 1,000 | embedding | scoped | 18.6 | 1.5 | 37.14 | 39.98 | 94% | 0.87 |
| 10,000 | lexical | unscoped | 0.0 | 0.0 | 334.06 | 360.58 | 26% | 0.60 |
| 10,000 | lexical | scoped | 0.0 | 0.0 | 0.29 | 0.31 | 95% | 0.80 |
| 10,000 | embedding | unscoped | 235.54 | 14.6 | 78.09 | 91.42 | 12% | 0.24 |
| 10,000 | embedding | scoped | 235.54 | 14.6 | 40.37 | 50.08 | 94% | 0.87 |
