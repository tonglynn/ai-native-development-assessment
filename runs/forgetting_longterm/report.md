# Forgetting over time (exploratory)

Config: uniform 50 tasks; type-aware {'business_policy': None, 'code_convention': 200, 'process': 100, 'lesson': 50}; exposure 10 unused injections; archive below R = 0.2. E04 absent for tasks 1-300, back after; 3 repetitions.

| Tasks | Policy | Active: business policy / code / process / one-off | Learned archived | Policy rules archived | Needed rule injected | One-off / task | Old threshold on S04/S05 | Misses → reactivations | Held-out pass@1 | S04/S05 pass@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| 100 | none | 6/6 / 16/17 / 3/3 / 150/150 | 0 | 0 | 56% | 3.8 | 6/6 | 0 → 0 | 39% | 83% |
| 100 | uniform | 6/6 / 14/17 / 3/3 / 138/150 | 2 | 0 | 56% | 3.7 | 6/6 | 0 → 0 | 39% | 83% |
| 100 | type_aware | 6/6 / 16/17 / 3/3 / 144/150 | 0 | 0 | 57% | 3.8 | 6/6 | 0 → 0 | 39% | 83% |
| 200 | none | 6/6 / 16/17 / 3/3 / 300/300 | 0 | 0 | 43% | 4.3 | 6/6 | 0 → 0 | 42% | 83% |
| 200 | uniform | 3/6 / 15/17 / 3/3 / 138/300 | 4 | 3 | 47% | 3.8 | 0/6 | 1 → 1 | 39% | 0% |
| 200 | type_aware | 6/6 / 16/17 / 3/3 / 215/300 | 0 | 0 | 44% | 4.2 | 6/6 | 0 → 0 | 42% | 100% |
| 400 | none | 6/6 / 16/17 / 3/3 / 600/600 | 0 | 0 | 43% | 4.2 | 6/6 | 0 → 0 | 36% | 83% |
| 400 | uniform | 6/6 / 15/17 / 3/3 / 138/600 | 1 | 0 | 58% | 3.4 | 6/6 | 4 → 4 | 45% | 83% |
| 400 | type_aware | 6/6 / 15/17 / 3/3 / 276/600 | 1 | 0 | 49% | 4.0 | 6/6 | 1 → 1 | 33% | 83% |

Held-out pass@1 against no forgetting, paired by task (bootstrap 95% interval):

- after 100 tasks, type_aware: +0% [+0%, +0%]
- after 100 tasks, uniform: +0% [-9%, +9%]
- after 200 tasks, type_aware: +0% [-9%, +9%]
- after 200 tasks, uniform: -3% [-12%, +6%]
- after 400 tasks, type_aware: -3% [-18%, +15%]
- after 400 tasks, uniform: +9% [-6%, +27%]
