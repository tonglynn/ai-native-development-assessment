# Retrieval quality: lexical vs embedding (same memory, offline)

Memory: snapshots after the learning phase in `/home/runner/work/ai-native-development-assessment/ai-native-development-assessment/runs/main`. Queries: held-out, control and stale tasks (title + issue only). Relevance: the note states a rule the task needs (labels by deepseek/deepseek-v4-pro, blind to system and retriever). k = 5. Embedding: BAAI/bge-small-en-v1.5 via fastembed 0.9.1.

| System | Retriever | Queries | Recall@5 | Precision@5 | MRR | Review-only rule in top 5 | Irrelevant in top 5 (control) | ms median | ms p95 |
|---|---|---|---|---|---|---|---|---|---|
| attest | lexical | 57 | 76% | 55% | 0.83 | 88% | 0.0 | 0.3 | 0.4 |
| attest | embedding | 57 | 88% | 63% | 0.85 | 76% | 0.0 | 22.1 | 35.0 |
| reasoningbank | lexical | 57 | 39% | 44% | 0.79 | 73% | 5.0 | 1.0 | 2.1 |
| reasoningbank | embedding | 57 | 49% | 53% | 0.86 | 67% | 5.0 | 26.2 | 49.4 |

Paired per query (embedding − lexical), bootstrap 95% interval:

| System | Metric | n | Mean difference | 95% CI | Better / worse / same |
|---|---|---|---|---|---|
| attest | recall | 48 | +0.113 | [+0.059, +0.171] | 17 / 2 / 29 |
| attest | precision | 48 | +0.071 | [+0.037, +0.108] | 17 / 2 / 29 |
| attest | rr | 48 | +0.018 | [-0.053, +0.091] | 7 / 7 / 34 |
| reasoningbank | recall | 48 | +0.096 | [+0.044, +0.151] | 28 / 9 / 11 |
| reasoningbank | precision | 57 | +0.091 | [+0.042, +0.140] | 28 / 9 / 20 |
| reasoningbank | rr | 48 | +0.074 | [-0.014, +0.165] | 13 / 8 / 27 |
