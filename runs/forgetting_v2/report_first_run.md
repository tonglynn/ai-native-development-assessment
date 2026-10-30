# Forgetting V2, points 1-4 (offline, constructed cases)

Stream seeds (0, 1) x 3 repetitions; tiered admission; 30% adoption noise; verified-once details, wrong notes and convention outcomes constructed as described in scripts/forgetting_v2.py.

| Arm | Needed rule injected | Injectable notes | Dormant | Useful rules archived | Useful rules dormant | Policy rules archived | Stale verified-once still active | One-offs permanent | One-off notes injected / held-out task | Wrong-note injections (stream) | Wrong notes injectable at end | Wrong notes injected (held-out, per run) | Demand reactivations | Wrong notes credited by demand |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 57% | 132 | 0 | 4/52 | 0 | 0 | 114/115 | 36 | 3.0 | 609.0 | 9.0 | 3.8 | 0.0 | 0.0 |
| V1.1 | 64% | 122 | 0 | 12/52 | 0 | 0 | 68/115 | 0 | 2.7 | 656.0 | 9.0 | 4.5 | 0.0 | 0.0 |
| base (verified-only) | 57% | 130 | 0 | 6/52 | 0 | 0 | 114/115 | 34 | 3.0 | 646.0 | 9.0 | 4.2 | 0.0 | 0.0 |
| base + stability | 64% | 122 | 0 | 8/52 | 0 | 0 | 70/115 | 0 | 2.7 | 647.0 | 9.0 | 4.5 | 0.0 | 0.0 |
| base + three-state | 63% | 125 | 87 | 0/52 | 6 | 0 | 115/115 | 34 | 3.0 | 81.7 | 4.0 | 0.7 | 0.0 | 0.0 |
| base + demand | 57% | 130 | 0 | 4/52 | 0 | 0 | 114/115 | 34 | 3.0 | 646.0 | 9.0 | 4.2 | 0.0 | 220.3 |
| all four | 66% | 118 | 94 | 0/52 | 4 | 0 | 70/115 | 0 | 2.9 | 81.7 | 4.0 | 0.7 | 181.3 | 303.2 |
| exposure (V1) | 52% | 211 | 0 | 6/52 | 0 | 6 | 115/115 | 199 | 3.4 | 288.7 | 4.2 | 0.7 | 0.0 | 0.0 |
| exposure + scoped | 61% | 216 | 0 | 0/52 | 0 | 0 | 115/115 | 200 | 2.7 | 455.2 | 7.7 | 6.8 | 0.0 | 0.0 |
| V1 x0.25 | 66% | 54 | 0 | 4/52 | 0 | 0 | 76/115 | 23 | 3.1 | 242.8 | 0.0 | 0.0 | 0.0 | 0.0 |
| all four x0.25 | 71% | 44 | 168 | 0/52 | 8 | 0 | 11/115 | 0 | 2.6 | 81.7 | 4.0 | 0.8 | 179.7 | 287.3 |

Learned notes archived, per run:

- V1 seed 0 r1: at-0008 C3 (code_convention)
- V1 seed 0 r2: at-0004 None (code_convention)
- V1 seed 1 r1: at-0008 C3 (code_convention)
- V1 seed 1 r2: at-0004 None (code_convention)
- V1.1 seed 0 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- V1.1 seed 0 r2: at-0004 None (code_convention), at-0008 C4 (process)
- V1.1 seed 0 r3: at-0004 None (code_convention)
- V1.1 seed 1 r1: at-0002 None (code_convention), at-0004 None (code_convention), at-0008 C3 (code_convention)
- V1.1 seed 1 r2: at-0004 None (code_convention), at-0008 C4 (process)
- V1.1 seed 1 r3: at-0004 None (code_convention)
- base (verified-only) seed 0 r1: at-0008 C3 (code_convention)
- base (verified-only) seed 0 r2: at-0004 None (code_convention)
- base (verified-only) seed 0 r3: at-0004 None (code_convention)
- base (verified-only) seed 1 r1: at-0008 C3 (code_convention)
- base (verified-only) seed 1 r2: at-0004 None (code_convention)
- base (verified-only) seed 1 r3: at-0004 None (code_convention)
- base + stability seed 0 r1: at-0008 C3 (code_convention)
- base + stability seed 0 r2: at-0004 None (code_convention), at-0008 C4 (process)
- base + stability seed 0 r3: at-0004 None (code_convention)
- base + stability seed 1 r1: at-0008 C3 (code_convention)
- base + stability seed 1 r2: at-0004 None (code_convention), at-0008 C4 (process)
- base + stability seed 1 r3: at-0004 None (code_convention)
- base + demand seed 0 r2: at-0004 None (code_convention)
- base + demand seed 0 r3: at-0004 None (code_convention)
- base + demand seed 1 r2: at-0004 None (code_convention)
- base + demand seed 1 r3: at-0004 None (code_convention)
- exposure (V1) seed 0 r1: at-0007 C6 (business_policy)
- exposure (V1) seed 0 r2: at-0007 C6 (business_policy)
- exposure (V1) seed 0 r3: at-0008 C6 (business_policy)
- exposure (V1) seed 1 r1: at-0007 C6 (business_policy)
- exposure (V1) seed 1 r2: at-0007 C6 (business_policy)
- exposure (V1) seed 1 r3: at-0008 C6 (business_policy)
- V1 x0.25 seed 0 r1: at-0008 C3 (code_convention)
- V1 x0.25 seed 0 r2: at-0004 None (code_convention)
- V1 x0.25 seed 1 r1: at-0008 C3 (code_convention)
- V1 x0.25 seed 1 r2: at-0004 None (code_convention)
