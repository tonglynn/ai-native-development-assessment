# Just-in-time verification on the stale tasks (exploratory)

Main-experiment Attest memories after learning, 3 repetitions, ledgerly 2.0.0.

| Arm | Runs | Stale pass@1 | C1 failed (S01-S03) | Approval wrongly demanded (S04-S05) | Unapproved let through (S04-S05) | Crashed |
|---|---|---|---|---|---|---|
| plain | 15 | 87% | 0/9 | 2/6 | 2/6 | 0 |
| annotate | 15 | 100% | 0/9 | 0/6 | 0/6 | 0 |
| drop | 15 | 100% | 0/9 | 0/6 | 0/6 | 0 |
