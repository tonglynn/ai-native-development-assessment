# Learned rules as executable checks (exploratory)

25 active learned notes of the main experiment; checks written by deepseek-flash from the note alone; evaluated on the reference (follows every convention) and naive (breaks the task's conventions) solutions of the 17 ledgerly 1.0.0 tasks.

| Note | Conventions | Checkable | Usable | Detection | False alarms (of 17 references) | Useful |
|---|---|---|---|---|---|---|
| r1/at-0001 Round money only with round_money | C1 | yes | yes | 71% | 0 | **yes** |
| r1/at-0002 Convert line prices with to_money and ZERO | outside C1-C6 | yes | yes | – | 2 | no |
| r1/at-0003 Raise BillingError with stable snake_case codes | C2 | yes | yes | 0% | 0 | no |
| r1/at-0004 Exclude bool when validating integers | outside C1-C6 | yes | yes | – | 0 | no |
| r1/at-0005 Normalize datetimes with ensure_utc | C3 | yes | yes | 0% | 0 | no |
| r1/at-0006 Money-moving functions take idempotency_key | C4, C5 | yes | yes | 88% | 2 | no |
| r1/at-0007 Refunds above 500 need approved_by | C2, C6 | no | no | – | – | no |
| r1/at-0008 Normalize money and timestamps at entry | C1, C2, C3 | yes | yes | 76% | 9 | no |
| r1/at-0009 Record audit entry for every balance change | C4 | yes | yes | 62% | 8 | no |
| r2/at-0001 Round money only with round_money | C1 | yes | yes | 14% | 0 | no |
| r2/at-0002 Normalize money via to_money and round_money | C1 | yes | yes | 0% | 0 | no |
| r2/at-0003 Raise BillingError with stable snake_case codes | C2 | yes | yes | 0% | 0 | no |
| r2/at-0004 Exclude bool when validating integer fields | outside C1-C6 | yes | yes | – | 0 | no |
| r2/at-0005 Normalize datetimes with ensure_utc | C3 | yes | yes | 43% | 2 | no |
| r2/at-0006 Money operations take keyword-only idempotency_key | C4, C5 | yes | yes | 100% | 7 | no |
| r2/at-0007 Refunds above 500.00 need approved_by | C2, C6 | yes | yes | 42% | 6 | no |
| r2/at-0008 Record state changes via audit.record | C4 | yes | yes | 0% | 0 | no |
| r3/at-0002 Normalize money inputs with round_money before storing | C1 | yes | yes | 14% | 6 | no |
| r3/at-0003 Use BillingError with snake_case codes | C2 | yes | yes | 0% | 0 | no |
| r3/at-0004 Reject bools when validating integer arguments | outside C1-C6 | yes | yes | – | 0 | no |
| r3/at-0005 Normalize datetimes with ensure_utc | C3 | yes | yes | 0% | 0 | no |
| r3/at-0006 Record audit entry for every money movement | C4 | yes | yes | 88% | 2 | no |
| r3/at-0007 Accept idempotency_key and check it first | C4, C5 | no | no | – | – | no |
| r3/at-0008 Refunds above 500.00 need approved_by | C2, C6 | yes | yes | 33% | 1 | no |
| r3/at-0009 Money is Decimal end-to-end, never float | C1 | yes | yes | 29% | 0 | no |

| Convention | Notes | Checkable | Usable | Useful |
|---|---|---|---|---|
| C1 | 6 | 6 | 6 | 1 |
| C2 | 7 | 6 | 6 | 0 |
| C3 | 4 | 4 | 4 | 0 |
| C4 | 6 | 5 | 5 | 0 |
| C5 | 3 | 2 | 2 | 0 |
| C6 | 3 | 2 | 2 | 0 |
| outside C1-C6 | 4 | 4 | 4 | 0 |

Useful checks: **1 of 25**. Usable: 23. Declared not checkable: 2.

Sensitivity (added after the run): scored against each note's primary convention only.

| Note | Conventions | Checkable | Usable | Detection | False alarms (of 17 references) | Useful |
|---|---|---|---|---|---|---|
| r1/at-0001 Round money only with round_money | C1 | yes | yes | 71% | 0 | **yes** |
| r1/at-0002 Convert line prices with to_money and ZERO | outside C1-C6 | yes | yes | – | 2 | no |
| r1/at-0003 Raise BillingError with stable snake_case codes | C2 | yes | yes | 0% | 0 | no |
| r1/at-0004 Exclude bool when validating integers | outside C1-C6 | yes | yes | – | 0 | no |
| r1/at-0005 Normalize datetimes with ensure_utc | C3 | yes | yes | 0% | 0 | no |
| r1/at-0006 Money-moving functions take idempotency_key | C5 | yes | yes | 88% | 2 | no |
| r1/at-0007 Refunds above 500 need approved_by | C6 | no | no | – | – | no |
| r1/at-0008 Normalize money and timestamps at entry | C3 | yes | yes | 71% | 9 | no |
| r1/at-0009 Record audit entry for every balance change | C4 | yes | yes | 62% | 8 | no |
| r2/at-0001 Round money only with round_money | C1 | yes | yes | 14% | 0 | no |
| r2/at-0002 Normalize money via to_money and round_money | C1 | yes | yes | 0% | 0 | no |
| r2/at-0003 Raise BillingError with stable snake_case codes | C2 | yes | yes | 0% | 0 | no |
| r2/at-0004 Exclude bool when validating integer fields | outside C1-C6 | yes | yes | – | 0 | no |
| r2/at-0005 Normalize datetimes with ensure_utc | C3 | yes | yes | 43% | 2 | no |
| r2/at-0006 Money operations take keyword-only idempotency_key | C5 | yes | yes | 100% | 7 | no |
| r2/at-0007 Refunds above 500.00 need approved_by | C6 | yes | yes | 100% | 6 | no |
| r2/at-0008 Record state changes via audit.record | C4 | yes | yes | 0% | 0 | no |
| r3/at-0002 Normalize money inputs with round_money before storing | C1 | yes | yes | 14% | 6 | no |
| r3/at-0003 Use BillingError with snake_case codes | C2 | yes | yes | 0% | 0 | no |
| r3/at-0004 Reject bools when validating integer arguments | outside C1-C6 | yes | yes | – | 0 | no |
| r3/at-0005 Normalize datetimes with ensure_utc | C3 | yes | yes | 0% | 0 | no |
| r3/at-0006 Record audit entry for every money movement | C4 | yes | yes | 88% | 2 | no |
| r3/at-0007 Accept idempotency_key and check it first | C5 | no | no | – | – | no |
| r3/at-0008 Refunds above 500.00 need approved_by | C6 | yes | yes | 100% | 1 | **yes** |
| r3/at-0009 Money is Decimal end-to-end, never float | C1 | yes | yes | 29% | 0 | no |

| Convention | Notes | Checkable | Usable | Useful |
|---|---|---|---|---|
| C1 | 5 | 5 | 5 | 1 |
| C2 | 3 | 3 | 3 | 0 |
| C3 | 4 | 4 | 4 | 0 |
| C4 | 3 | 3 | 3 | 0 |
| C5 | 3 | 2 | 2 | 0 |
| C6 | 3 | 2 | 2 | 1 |
| outside C1-C6 | 4 | 4 | 4 | 0 |

Useful checks: **2 of 25**. Usable: 23. Declared not checkable: 2.
