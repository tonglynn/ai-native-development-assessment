# Poison admission, propagation, and recovery by quarantine (offline, from stored runs)

| Run / condition | Reps admitting poison | Held-out runs exposed | Exposed runs that applied it | Downstream notes (matching) | Exposed after quarantine | Notes lost: hold all downstream / hold matching |
|---|---|---|---|---|---|---|
| stress_poison/attest | 0/3 | 0/33 | 0/0 | 0 (0) | 0 | 0 / 0 |
| stress_poison/attest_no_gate | 3/3 | 9/33 | 0/9 | 0 (0) | 0 | 0 / 0 |
| stress_poison_float/attest | 3/3 | 23/33 | 14/23 | 10 (0) | 0 | 10 / 0 |
| stress_poison_float/attest_no_gate | 3/3 | 20/33 | 10/20 | 7 (0) | 0 | 7 / 0 |
| stress_poison_float_guard/attest | 0/3 | 0/33 | 0/0 | 0 (0) | 0 | 0 / 0 |
| stress_poison_float_guard/attest_no_gate | 3/3 | 22/33 | 0/22 | 6 (0) | 0 | 6 / 0 |
