# Dynamic forgetting (exploratory)

Config: uniform 50 tasks; type-aware {'business_policy': None, 'code_convention': 200, 'process': 100, 'lesson': 50}; exposure 10 unused injections; archive below R = 0.2. Stream of 400 tasks, 200 one-off notes, maintenance every 50; 3 repetitions (memories from runs/main).

| Scenario | Policy | Needed rule injected | One-off notes injected / task | Learned notes archived (all reps) | One-off notes archived | Active notes | Held-out pass@1 |
|---|---|---|---|---|---|---|---|
| rare | none | 44% | 4.1 | 0 | 0% | 208 | 42% |
| rare | uniform | 47% | 3.7 | 5 | 77% | 53 | 45% |
| rare | type_aware | 48% | 4.0 | 2 | 54% | 99 | 39% |
| rare | exposure | 36% | 4.1 | 5 | 25% | 157 | – |
| rare | exposure_ranked | 40% | 4.2 | 4 | 13% | 181 | 39% |
| steady | none | 45% | 4.0 | 0 | 0% | 208 | – |
| steady | uniform | 59% | 3.5 | 2 | 77% | 54 | – |
| steady | type_aware | 46% | 3.9 | 2 | 54% | 100 | – |
| steady | exposure | 45% | 3.9 | 2 | 23% | 162 | – |
| steady | exposure_ranked | 48% | 3.9 | 2 | 14% | 181 | – |

Learned notes archived (false forgetting), rare scenario:

- none r1: none
- none r2: none
- none r3: none
- uniform r1: at-0007 C6 (business_policy), at-0008 C3 (code_convention)
- uniform r2: at-0004 None (code_convention), at-0007 C6 (business_policy)
- uniform r3: at-0008 C6 (business_policy)
- type_aware r1: at-0008 C3 (code_convention)
- type_aware r2: at-0004 None (code_convention)
- type_aware r3: none
- exposure r1: at-0007 C6 (business_policy), at-0008 C3 (code_convention)
- exposure r2: at-0004 None (code_convention), at-0007 C6 (business_policy)
- exposure r3: at-0008 C6 (business_policy)
- exposure_ranked r1: at-0008 C3 (code_convention)
- exposure_ranked r2: at-0004 None (code_convention), at-0007 C6 (business_policy)
- exposure_ranked r3: at-0008 C6 (business_policy)
