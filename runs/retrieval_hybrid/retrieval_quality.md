# Retrieval quality: lexical vs embedding (same memory, offline)

Memory: snapshots after the learning phase in `/home/runner/work/ai-native-development-assessment/ai-native-development-assessment/runs/main`. Queries: held-out, control and stale tasks (title + issue only). Relevance: the note states a rule the task needs (labels by deepseek/deepseek-v4-pro, blind to system and retriever). k = 5. Embedding: BAAI/bge-small-en-v1.5 via fastembed 0.9.1.

| System | Retriever | Queries | Recall@5 | Precision@5 | MRR | Review-only rule in top 5 | Irrelevant in top 5 (control) | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| attest | lexical | 57 | 76% | 55% | 0.83 | 88% | 0.0 | 0.6 | 0.7 |
| attest | hybrid | 57 | 83% | 59% | 0.87 | 79% | 0.0 | 36.9 | 60.3 |
| attest | hybrid_rerank | 57 | 90% | 64% | 0.95 | 82% | 0.0 | 37.5 | 60.4 |

Paired per query (other retriever − lexical), bootstrap 95% interval:

| System | Retriever | Metric | n | Mean difference | 95% CI | Better / worse / same |
|---|---|---|---|---|---|---|
| attest | hybrid | recall | 48 | +0.066 | [+0.026, +0.111] | 10 / 1 / 37 |
| attest | hybrid | precision | 48 | +0.037 | [+0.012, +0.063] | 10 / 1 / 37 |
| attest | hybrid | rr | 48 | +0.036 | [-0.021, +0.097] | 6 / 4 / 38 |
| attest | hybrid_rerank | recall | 48 | +0.135 | [+0.077, +0.197] | 21 / 3 / 24 |
| attest | hybrid_rerank | precision | 48 | +0.088 | [+0.050, +0.129] | 21 / 3 / 24 |
| attest | hybrid_rerank | rr | 48 | +0.118 | [+0.062, +0.181] | 12 / 0 / 36 |
