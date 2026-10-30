# Validating generated checks against the evidence that created their rule (exploratory)

Replays faithful (both attempts reproduce final.diff): 14 of 14.

| Note | Source task | Validation | Passes accepted | Flags rejected | Validated | Detection | False alarms (of 16) | Useful | Attribution precision |
|---|---|---|---|---|---|---|---|---|---|
| r1/at-0001 Round money only with round_money | E01 | full | yes | no | no | 67% | 0 | yes | 100% |
| r1/at-0002 Convert line prices with to_money and ZERO | E01 | full | no | yes | no | – | 1 | no | 0% |
| r1/at-0003 Raise BillingError with stable snake_case codes | E02 | accepted-only | yes | – | **yes** | 0% | 0 | no | – |
| r1/at-0004 Exclude bool when validating integers | E02 | accepted-only | yes | – | **yes** | – | 0 | no | – |
| r1/at-0005 Normalize datetimes with ensure_utc | E03 | accepted-only | no | – | no | 0% | 0 | no | – |
| r1/at-0006 Money-moving functions take idempotency_key | E04 | full | yes | yes | **yes** | 86% | 2 | no | 60% |
| r1/at-0007 Refunds above 500 need approved_by | E04 | full | – | – | – (not checkable) | – | – | – | – |
| r1/at-0008 Normalize money and timestamps at entry | E04 | full | no | yes | no | 71% | 8 | no | 25% |
| r1/at-0009 Record audit entry for every balance change | E06 | full | yes | no | no | 71% | 8 | no | 31% |
| r2/at-0001 Round money only with round_money | E01 | full | yes | no | no | 17% | 0 | no | 100% |
| r2/at-0002 Normalize money via to_money and round_money | E02 | accepted-only | yes | – | **yes** | 0% | 0 | no | 0% |
| r2/at-0003 Raise BillingError with stable snake_case codes | E02 | accepted-only | yes | – | **yes** | 0% | 0 | no | – |
| r2/at-0004 Exclude bool when validating integer fields | E02 | accepted-only | yes | – | **yes** | – | 0 | no | – |
| r2/at-0005 Normalize datetimes with ensure_utc | E03 | accepted-only | yes | – | **yes** | 33% | 2 | no | 40% |
| r2/at-0006 Money operations take keyword-only idempotency_key | E04 | full | yes | yes | **yes** | 100% | 7 | no | 41% |
| r2/at-0007 Refunds above 500.00 need approved_by | E04 | full | no | yes | no | 100% | 5 | no | 30% |
| r2/at-0008 Record state changes via audit.record | E06 | accepted-only | yes | – | **yes** | 0% | 0 | no | – |
| r3/at-0002 Normalize money inputs with round_money before storing | E02 | accepted-only | no | – | no | 14% | 5 | no | 17% |
| r3/at-0003 Use BillingError with snake_case codes | E02 | accepted-only | yes | – | **yes** | 0% | 0 | no | – |
| r3/at-0004 Reject bools when validating integer arguments | E02 | accepted-only | yes | – | **yes** | – | 0 | no | – |
| r3/at-0005 Normalize datetimes with ensure_utc | E03 | accepted-only | yes | – | **yes** | 0% | 0 | no | – |
| r3/at-0006 Record audit entry for every money movement | E04 | full | yes | yes | **yes** | 86% | 2 | no | 60% |
| r3/at-0007 Accept idempotency_key and check it first | E04 | full | – | – | – (not checkable) | – | – | – | – |
| r3/at-0008 Refunds above 500.00 need approved_by | E04 | full | yes | yes | **yes** | 100% | 1 | yes | 60% |
| r3/at-0009 Money is Decimal end-to-end, never float | E05 | full | yes | no | no | 17% | 0 | no | 100% |

| Validation | Group | Checks | Mean false-alarm rate | Useful | Flags | Attribution precision (pooled) |
|---|---|---|---|---|---|---|
| full | pass | 4 | 19% | 1 | 42 | 52% |
| full | fail | 7 | 20% | 1 | 54 | 35% |
| accepted-only | pass | 10 | 1% | 0 | 7 | 29% |
| accepted-only | fail | 2 | 16% | 0 | 6 | 17% |
