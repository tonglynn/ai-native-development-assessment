# Forgetting V1.1 vs V1 (offline, rare scenario)

Stream seeds (0, 1), 3 repetitions each. Noise: share of injected one-off notes adopted without being needed. "Verified" in the simulation is a proxy signal (the task's hidden tests check the note's convention), not attribution.

| Arm | Variant | Noise | Runs | Needed rule injected | Active notes | One-offs permanent | Learned permanent | Important rules misarchived | Other learned archived: known correct / value unknown | Useful rules misarchived | Policy rules archived | One-offs reinforced |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no forgetting | - | 0.3 | 6 | 45% | 208 | 200 | 50/52 | 0% (0/44) | 0/8 / 0/0 | 0% (0/52) | 0 | 33 |
| type_aware x1 | V1 | 0.0 | 6 | 46% | 100 | 0 | 46/52 | 5% (2/44) | 2/8 / 0/0 | 8% (4/52) | 0 | 0 |
| type_aware x1 | V1.1 | 0.0 | 6 | 46% | 99 | 0 | 16/52 | 5% (2/44) | 8/8 / 0/0 | 19% (10/52) | 0 | 0 |
| type_aware x1 | V1 | 0.3 | 6 | 45% | 126 | 34 | 46/52 | 5% (2/44) | 2/8 / 0/0 | 8% (4/52) | 0 | 34 |
| type_aware x1 | V1.1 | 0.3 | 6 | 46% | 99 | 0 | 16/52 | 5% (2/44) | 8/8 / 0/0 | 19% (10/52) | 0 | 0 |
| type_aware x0.25 | V1 | 0.0 | 6 | 67% | 32 | 0 | 46/52 | 5% (2/44) | 2/8 / 0/0 | 8% (4/52) | 0 | 0 |
| type_aware x0.25 | V1.1 | 0.0 | 6 | 68% | 31 | 0 | 16/52 | 7% (3/44) | 8/8 / 0/0 | 21% (11/52) | 0 | 0 |
| type_aware x0.25 | V1 | 0.3 | 6 | 54% | 65 | 34 | 46/52 | 5% (2/44) | 2/8 / 0/0 | 8% (4/52) | 0 | 34 |
| type_aware x0.25 | V1.1 | 0.3 | 6 | 68% | 31 | 0 | 16/52 | 7% (3/44) | 8/8 / 0/0 | 21% (11/52) | 0 | 0 |
| tiered + type_aware x1 | V1 | 0.0 | 6 | 82% | 100 | 0 | 46/52 | 5% (2/44) | 2/8 / 0/0 | 8% (4/52) | 0 | 0 |
| tiered + type_aware x1 | V1.1 | 0.0 | 6 | 82% | 99 | 0 | 16/52 | 5% (2/44) | 8/8 / 0/0 | 19% (10/52) | 0 | 0 |
| tiered + type_aware x1 | V1 | 0.3 | 6 | 79% | 106 | 6 | 46/52 | 5% (2/44) | 2/8 / 0/0 | 8% (4/52) | 0 | 6 |
| tiered + type_aware x1 | V1.1 | 0.3 | 6 | 82% | 99 | 0 | 16/52 | 5% (2/44) | 8/8 / 0/0 | 19% (10/52) | 0 | 0 |

Ablation (stream seed 0):

| Arm | Variant | Noise | Runs | Needed rule injected | Active notes | One-offs permanent | Learned permanent | Important rules misarchived | Other learned archived: known correct / value unknown | Useful rules misarchived | Policy rules archived | One-offs reinforced |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| type_aware x0.25 | V1 | 0.3 | 3 | 56% | 65 | 35 | 23/26 | 5% (1/22) | 1/4 / 0/0 | 8% (2/26) | 0 | 35 |
| type_aware x0.25 | V1.1 | 0.3 | 3 | 68% | 30 | 0 | 8/26 | 5% (1/22) | 4/4 / 0/0 | 19% (5/26) | 0 | 0 |
| ablation type_aware x0.25 | + verified-only | 0.3 | 3 | 68% | 31 | 0 | 22/26 | 5% (1/22) | 2/4 / 0/0 | 12% (3/26) | 0 | 0 |
| ablation type_aware x0.25 | + utility decay | 0.3 | 3 | 61% | 49 | 0 | 6/26 | 18% (4/22) | 4/4 / 0/0 | 31% (8/26) | 0 | 40 |
| ablation type_aware x0.25 | + protect cited | 0.3 | 3 | 56% | 65 | 35 | 23/26 | 5% (1/22) | 1/4 / 0/0 | 8% (2/26) | 0 | 35 |

Sensitivity to utility_factor (V1.1, stream seed 0):

| Arm | Variant | Noise | Runs | Needed rule injected | Active notes | One-offs permanent | Learned permanent | Important rules misarchived | Other learned archived: known correct / value unknown | Useful rules misarchived | Policy rules archived | One-offs reinforced |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| type_aware x1 | V1.1 | 0.3 | 3 | 48% | 98 | 0 | 8/26 | 5% (1/22) | 4/4 / 0/0 | 19% (5/26) | 0 | 0 |
| type_aware x0.25 | V1.1 | 0.3 | 3 | 68% | 30 | 0 | 8/26 | 5% (1/22) | 4/4 / 0/0 | 19% (5/26) | 0 | 0 |
| sensitivity type_aware x1 | utility_factor 2 | 0.3 | 3 | 47% | 98 | 0 | 8/26 | 9% (2/22) | 4/4 / 0/0 | 23% (6/26) | 0 | 0 |
| sensitivity type_aware x1 | utility_factor 8 | 0.3 | 3 | 48% | 99 | 0 | 8/26 | 5% (1/22) | 2/4 / 0/0 | 12% (3/26) | 0 | 0 |
| sensitivity type_aware x0.25 | utility_factor 2 | 0.3 | 3 | 68% | 30 | 0 | 8/26 | 5% (1/22) | 4/4 / 0/0 | 19% (5/26) | 0 | 0 |
| sensitivity type_aware x0.25 | utility_factor 8 | 0.3 | 3 | 68% | 30 | 0 | 8/26 | 5% (1/22) | 4/4 / 0/0 | 19% (5/26) | 0 | 0 |

Other learned rules (outside C1-C6), labelled by hand against the benchmark's sources after the run:

- `\bbool\b`: known correct, unchecked. E02's reference solution rejects bool quantities and ledgerly.money.to_money rejects bool; no hidden test or review comment checks it
- `to_money`: known correct, unchecked. ledgerly/money.py defines to_money and ZERO and reference solutions use them; no test checks it apart from rounding (C1)

Learned notes archived, per run (main grid):

- type_aware x1 V1 noise 0.0 seed 0 r1: at-0008 C3 (code_convention)
- type_aware x1 V1.1 noise 0.0 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x1 V1 noise 0.3 seed 0 r1: at-0008 C3 (code_convention)
- type_aware x1 V1.1 noise 0.3 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x0.25 V1 noise 0.0 seed 0 r1: at-0008 C3 (code_convention)
- type_aware x0.25 V1.1 noise 0.0 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x0.25 V1 noise 0.3 seed 0 r1: at-0008 C3 (code_convention)
- type_aware x0.25 V1.1 noise 0.3 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- tiered + type_aware x1 V1 noise 0.0 seed 0 r1: at-0008 C3 (code_convention)
- tiered + type_aware x1 V1.1 noise 0.0 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- tiered + type_aware x1 V1 noise 0.3 seed 0 r1: at-0008 C3 (code_convention)
- tiered + type_aware x1 V1.1 noise 0.3 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x1 V1 noise 0.0 seed 0 r2: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.0 seed 0 r2: at-0004 None (code_convention)
- type_aware x1 V1 noise 0.3 seed 0 r2: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.3 seed 0 r2: at-0004 None (code_convention)
- type_aware x0.25 V1 noise 0.0 seed 0 r2: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.0 seed 0 r2: at-0004 None (code_convention)
- type_aware x0.25 V1 noise 0.3 seed 0 r2: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.3 seed 0 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1 noise 0.0 seed 0 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.0 seed 0 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1 noise 0.3 seed 0 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.3 seed 0 r2: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.0 seed 0 r3: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.3 seed 0 r3: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.0 seed 0 r3: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.3 seed 0 r3: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.0 seed 0 r3: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.3 seed 0 r3: at-0004 None (code_convention)
- type_aware x1 V1 noise 0.0 seed 1 r1: at-0008 C3 (code_convention)
- type_aware x1 V1.1 noise 0.0 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x1 V1 noise 0.3 seed 1 r1: at-0008 C3 (code_convention)
- type_aware x1 V1.1 noise 0.3 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x0.25 V1 noise 0.0 seed 1 r1: at-0008 C3 (code_convention)
- type_aware x0.25 V1.1 noise 0.0 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x0.25 V1 noise 0.3 seed 1 r1: at-0008 C3 (code_convention)
- type_aware x0.25 V1.1 noise 0.3 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- tiered + type_aware x1 V1 noise 0.0 seed 1 r1: at-0008 C3 (code_convention)
- tiered + type_aware x1 V1.1 noise 0.0 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- tiered + type_aware x1 V1 noise 0.3 seed 1 r1: at-0008 C3 (code_convention)
- tiered + type_aware x1 V1.1 noise 0.3 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- type_aware x1 V1 noise 0.0 seed 1 r2: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.0 seed 1 r2: at-0004 None (code_convention)
- type_aware x1 V1 noise 0.3 seed 1 r2: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.3 seed 1 r2: at-0004 None (code_convention)
- type_aware x0.25 V1 noise 0.0 seed 1 r2: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.0 seed 1 r2: at-0004 None (code_convention), at-0008 C4 (process)
- type_aware x0.25 V1 noise 0.3 seed 1 r2: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.3 seed 1 r2: at-0004 None (code_convention), at-0008 C4 (process)
- tiered + type_aware x1 V1 noise 0.0 seed 1 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.0 seed 1 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1 noise 0.3 seed 1 r2: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.3 seed 1 r2: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.0 seed 1 r3: at-0004 None (code_convention)
- type_aware x1 V1.1 noise 0.3 seed 1 r3: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.0 seed 1 r3: at-0004 None (code_convention)
- type_aware x0.25 V1.1 noise 0.3 seed 1 r3: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.0 seed 1 r3: at-0004 None (code_convention)
- tiered + type_aware x1 V1.1 noise 0.3 seed 1 r3: at-0004 None (code_convention)
