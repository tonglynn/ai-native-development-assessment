# Memory crowding ablation (exploratory)

Offline, same memories, per task (held-out, stale, control):

| Arm | Needed core rules injected | C5 injected when needed | Displaced | Effective notes / task | Notes / task | Wrong injections | Memory tokens / task |
|---|---|---|---|---|---|---|---|
| A | 78/81 (96%) | 16/18 | 2 | 2.8 | 5.1 | 13 | 569 |
| B | 78/81 (96%) | 16/18 | 2 | 2.8 | 5.1 | 13 | 569 |
| C | 80/81 (99%) | 18/18 | 0 | 2.8 | 5.1 | 13 | 571 |
| D | 66/81 (81%) | 14/18 | 0 | 2.2 | 3.0 | 12 | 365 |

End to end (456 runs, 0 crashed):

| Arm | Held-out pass@1 | vs A (paired by task) | Stale | Control | Prompt tokens / run |
|---|---|---|---|---|---|
| A | 70% | – | 100% | 100% | 24,156 |
| B | 71% | +2% [-3%, +6%] | 100% | 100% | 23,181 |
| C | 77% | +8% [-0%, +17%] | 100% | 100% | 23,996 |
| D | 70% | -0% [-9%, +9%] | 97% | 100% | 21,307 |
