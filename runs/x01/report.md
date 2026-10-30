# X01: refunds through the payment provider, timeouts and retries (exploratory)

First attempt; each arm's memory after the main experiment's learning phase; 3 memory states x 2 runs.

| Arm | Runs | pass@1 | C2 met | C4 met | C5 met | **C7 met** (not taught) | Runs failing behaviour tests | Crashed |
|---|---|---|---|---|---|---|---|---|
| no_memory | 6 | 0% | 100% | 0% | 0% | **100%** | 0 | 0 |
| reasoningbank | 6 | 0% | 100% | 50% | 0% | **100%** | 0 | 0 |
| ace | 6 | 0% | 100% | 0% | 0% | **100%** | 0 | 0 |
| attest | 6 | 33% | 100% | 100% | 33% | **100%** | 0 | 0 |
