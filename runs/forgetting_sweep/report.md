# Forgetting parameter sensitivity (offline, rare scenario)

Rows: configuration (policy, half-life or scale, archive threshold), 3 repetitions, stream seed 0. Policy rules archived counts learned notes citing a policy or incident or typed business_policy.

| Configuration | Needed rule injected | Active notes | One-off archived | Learned archived | Policy rules archived |
|---|---|---|---|---|---|
| exposure 10 / thr 0.1 | 33% | 176 | 15% | 5 | 3 |
| exposure 10 / thr 0.2 | 36% | 157 | 25% | 5 | 3 |
| exposure 10 / thr 0.3 | 39% | 141 | 32% | 8 | 3 |
| exposure 20 / thr 0.1 | 34% | 198 | 5% | 5 | 3 |
| exposure 20 / thr 0.2 | 34% | 184 | 11% | 5 | 3 |
| exposure 20 / thr 0.3 | 33% | 167 | 19% | 8 | 3 |
| exposure 40 / thr 0.1 | 44% | 208 | 0% | 1 | 0 |
| exposure 40 / thr 0.2 | 44% | 201 | 3% | 2 | 0 |
| exposure 40 / thr 0.3 | 33% | 193 | 6% | 8 | 3 |
| exposure 5 / thr 0.1 | 38% | 150 | 28% | 5 | 3 |
| exposure 5 / thr 0.2 | 42% | 134 | 36% | 5 | 3 |
| exposure 5 / thr 0.3 | 42% | 114 | 46% | 8 | 3 |
| none - / thr 0.2 | 44% | 208 | 0% | 0 | 0 |
| type_aware 0.25 / thr 0.1 | 56% | 44 | 82% | 2 | 0 |
| type_aware 0.25 / thr 0.2 | 68% | 31 | 88% | 2 | 0 |
| type_aware 0.25 / thr 0.3 | 69% | 25 | 91% | 5 | 0 |
| type_aware 0.5 / thr 0.1 | 48% | 78 | 65% | 2 | 0 |
| type_aware 0.5 / thr 0.2 | 54% | 55 | 76% | 2 | 0 |
| type_aware 0.5 / thr 0.3 | 60% | 39 | 84% | 5 | 0 |
| type_aware 1 / thr 0.1 | 46% | 131 | 39% | 0 | 0 |
| type_aware 1 / thr 0.2 | 48% | 99 | 54% | 2 | 0 |
| type_aware 1 / thr 0.3 | 47% | 70 | 68% | 4 | 0 |
| type_aware 2 / thr 0.1 | 45% | 180 | 14% | 0 | 0 |
| type_aware 2 / thr 0.2 | 44% | 150 | 29% | 0 | 0 |
| type_aware 2 / thr 0.3 | 47% | 118 | 44% | 4 | 0 |
| type_aware 4 / thr 0.1 | 44% | 208 | 0% | 0 | 0 |
| type_aware 4 / thr 0.2 | 44% | 200 | 4% | 0 | 0 |
| type_aware 4 / thr 0.3 | 44% | 171 | 19% | 0 | 0 |
| uniform 100 / thr 0.1 | 36% | 148 | 30% | 5 | 3 |
| uniform 100 / thr 0.2 | 34% | 98 | 55% | 5 | 3 |
| uniform 100 / thr 0.3 | 33% | 68 | 69% | 7 | 3 |
| uniform 200 / thr 0.1 | 44% | 208 | 0% | 0 | 0 |
| uniform 200 / thr 0.2 | 44% | 190 | 9% | 2 | 0 |
| uniform 200 / thr 0.3 | 34% | 129 | 38% | 8 | 3 |
| uniform 25 / thr 0.1 | 49% | 43 | 82% | 5 | 3 |
| uniform 25 / thr 0.2 | 54% | 30 | 89% | 5 | 3 |
| uniform 25 / thr 0.3 | 65% | 22 | 92% | 8 | 3 |
| uniform 400 / thr 0.1 | 44% | 208 | 0% | 0 | 0 |
| uniform 400 / thr 0.2 | 44% | 208 | 0% | 0 | 0 |
| uniform 400 / thr 0.3 | 44% | 207 | 0% | 4 | 0 |
| uniform 50 / thr 0.1 | 34% | 78 | 64% | 5 | 3 |
| uniform 50 / thr 0.2 | 47% | 53 | 77% | 5 | 3 |
| uniform 50 / thr 0.3 | 48% | 37 | 85% | 8 | 3 |
| uniform 800 / thr 0.1 | 44% | 208 | 0% | 0 | 0 |
| uniform 800 / thr 0.2 | 44% | 208 | 0% | 0 | 0 |
| uniform 800 / thr 0.3 | 44% | 208 | 0% | 0 | 0 |

Feasible (no policy rule archived, at most 1 other learned note): 13 of 45.
Chosen on seed 0: **type_aware 1 / thr 0.1**.

Validation on stream seed 1:

| Configuration | Needed rule injected | Active notes | One-off archived | Learned archived | Policy rules archived |
|---|---|---|---|---|---|
| type_aware 1 / thr 0.1 | 44% | 134 | 37% | 0 | 0 |
| uniform 50 / thr 0.2 | 47% | 53 | 77% | 5 | 3 |
| type_aware 1 / thr 0.2 | 44% | 101 | 53% | 2 | 0 |
| exposure 10 / thr 0.2 | 33% | 161 | 23% | 5 | 3 |
| none - / thr 0.2 | 45% | 208 | 0% | 0 | 0 |
