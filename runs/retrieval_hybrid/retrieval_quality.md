# Retrieval quality: lexical vs embedding (same memory, offline)

Memory: snapshots after the learning phase in `/home/runner/work/ai-native-development-assessment/ai-native-development-assessment/runs/main`. Queries: held-out, control and stale tasks (title + issue only). Relevance: the note states a rule the task needs (labels by deepseek/deepseek-v4-pro, blind to system and retriever). k = 5. Embedding: BAAI/bge-small-en-v1.5 via fastembed 0.9.1.

| System | Retriever | Queries | Recall@5 | Precision@5 | MRR | Review-only rule in top 5 | Irrelevant in top 5 (control) | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| attest | lexical | 57 | 76% | 55% | 0.83 | 88% | 0.0 | 0.8 | 0.9 |
| attest | hybrid | 57 | 83% | 59% | 0.87 | 79% | 0.0 | 44.4 | 72.0 |
| attest | hybrid_rerank | 57 | 90% | 65% | 0.95 | 85% | 0.0 | 44.5 | 72.6 |

Paired per query (other retriever − lexical), bootstrap 95% interval:

| System | Retriever | Metric | n | Mean difference | 95% CI | Better / worse / same |
|---|---|---|---|---|---|---|
| attest | hybrid | recall | 48 | +0.066 | [+0.026, +0.111] | 10 / 1 / 37 |
| attest | hybrid | precision | 48 | +0.037 | [+0.012, +0.063] | 10 / 1 / 37 |
| attest | hybrid | rr | 48 | +0.038 | [-0.017, +0.097] | 6 / 4 / 38 |
| attest | hybrid_rerank | recall | 48 | +0.139 | [+0.081, +0.202] | 21 / 3 / 24 |
| attest | hybrid_rerank | precision | 48 | +0.092 | [+0.050, +0.133] | 21 / 3 / 24 |
| attest | hybrid_rerank | rr | 48 | +0.118 | [+0.062, +0.181] | 12 / 0 / 36 |
