# Human review replay (exploratory)

| Queue | Reviewed | Approved | Rejected |
|---|---|---|---|
| gateway v4, clean | 5 | 5 | 0 |
| gateway v4, poison | 5 | 5 | 0 |
| gateway v4, poison_float | 7 | 7 | 0 |
| first frozen set, cold start | 16 | 4 | 12 (of them wrong advice v4 had left uncertain: 5) |

| Scenario | Attest | v4 before review | v4 after review | after vs Attest | after vs before | poison shown / applied |
|---|---|---|---|---|---|---|
| clean | 85% | 79% | 70% | -15% [-30%, -3%] | -9% [-24%, +0%] | 0 / 0 |
| poison_float | 73% | 55% | 52% | -21% [-42%, -3%] | -3% [-21%, +12%] | 0 / 0 |

Review time: not measured (the reviewer is simulated).
