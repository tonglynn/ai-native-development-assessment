# Offline: is the injected context unchanged by verification outside the stale tasks? (D67)

Main-experiment Attest event logs, every intermediate memory state, 3 repetitions; plain vs annotate vs drop.

| Group | Task runs with byte-identical context at every state |
|---|---|
| experience | 18/18 |
| heldout | 33/33 |
| control | 9/9 |
| stale | 0/15 |

Stale is expected to differ: that is where notes drift (ledgerly 2.0.0).
