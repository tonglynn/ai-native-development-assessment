# Memory crowding ablation (exploratory)

Offline, same memories, per task (held-out, stale, control):

| Arm | Needed core rules injected | C5 injected when needed | Displaced | Effective notes / task | Notes / task | Wrong injections | Memory tokens / task |
|---|---|---|---|---|---|---|---|
| A | 78/81 (96%) | 16/18 | 2 | 2.8 | 5.1 | 13 | 569 |
| C | 80/81 (99%) | 18/18 | 0 | 2.8 | 5.1 | 13 | 571 |
| D2 | 81/81 (100%) | 18/18 | 0 | 2.8 | 4.8 | 15 | 487 |
| E | 81/81 (100%) | 18/18 | 0 | 3.1 | 4.6 | 12 | 509 |

End to end (456 runs, 0 crashed):

| Arm | Held-out pass@1 | vs A (paired by task) | vs C | Stale | Control | Prompt tokens / run |
|---|---|---|---|---|---|---|
| A | 70% | – | -6% [-17%, +5%] | 93% | 100% | 24,566 |
| C | 76% | +6% [-5%, +17%] | – | 97% | 100% | 24,771 |
| D2 | 85% | +15% [+5%, +27%] | +9% [-0%, +18%] | 100% | 100% | 23,013 |
| E | 83% | +14% [+2%, +26%] | +8% [-0%, +15%] | 100% | 100% | 23,319 |
