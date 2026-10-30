# Liveness of learned rules against the code (exploratory)

25 active learned notes; status computed from the code and changelog of each version; ground truth from the benchmark design.

| Version | Stale notes | Stale flagged (drifted / review) | Valid notes | Valid wrongly flagged (drifted / review) | Alive | Not checkable |
|---|---|---|---|---|---|---|
| 1.0.0 | 0 | 0 (0 / 0) | 25 | 0 (0 / 0) | 22 | 3 |
| 2.0.0 | 5 | 5 (2 / 3) | 20 | 7 (0 / 7) | 10 | 3 |
| renamed | 12 | 12 (12 / 0) | 13 | 0 (0 / 0) | 10 | 3 |

Per note:

| Note | 1.0.0 | 2.0.0 | renamed copy | Anchors |
|---|---|---|---|---|
| r1/at-0001 Round money only with round_money | alive | drifted (stale) | alive | half-up, money, round_money |
| r1/at-0002 Convert line prices with to_money and ZERO | alive | review | drifted (stale) | ZERO, invoice, invoice_total, ledgerly/invoice.py, line_total, money, to_money |
| r1/at-0003 Raise BillingError with stable snake_case codes | alive | alive | alive | BillingError, errors |
| r1/at-0004 Exclude bool when validating integers | not checkable | not checkable | not checkable | – |
| r1/at-0005 Normalize datetimes with ensure_utc | alive | alive | drifted (stale) | clock, current_period, ensure_utc, ledgerly/subscriptions.py, subscriptions |
| r1/at-0006 Money-moving functions take idempotency_key | alive | alive | drifted (stale) | adjustments, audit, events, ledgerly/adjustments.py, record |
| r1/at-0007 Refunds above 500 need approved_by | alive | review (stale) | alive | BillingError |
| r1/at-0008 Normalize money and timestamps at entry | alive | review | drifted (stale) | BillingError, ZERO, clock, ensure_utc, errors, money, round_money |
| r1/at-0009 Record audit entry for every balance change | alive | alive | drifted (stale) | audit, record |
| r2/at-0001 Round money only with round_money | alive | drifted (stale) | alive | half-up, money, round_money |
| r2/at-0002 Normalize money via to_money and round_money | alive | review | drifted (stale) | ZERO, money, round_money, to_money |
| r2/at-0003 Raise BillingError with stable snake_case codes | alive | review | alive | BillingError, errors, issue_invoice |
| r2/at-0004 Exclude bool when validating integer fields | not checkable | not checkable | not checkable | – |
| r2/at-0005 Normalize datetimes with ensure_utc | alive | alive | drifted (stale) | clock, current_period, ensure_utc, ledgerly/subscriptions.py, subscriptions |
| r2/at-0006 Money operations take keyword-only idempotency_key | alive | alive | drifted (stale) | audit, events, record |
| r2/at-0007 Refunds above 500.00 need approved_by | alive | review (stale) | alive | BillingError |
| r2/at-0008 Record state changes via audit.record | alive | alive | drifted (stale) | audit, record |
| r3/at-0002 Normalize money inputs with round_money before storing | alive | review | alive | ZERO, money, round_money |
| r3/at-0003 Use BillingError with snake_case codes | alive | review | alive | BillingError, errors, invoice |
| r3/at-0004 Reject bools when validating integer arguments | not checkable | not checkable | not checkable | – |
| r3/at-0005 Normalize datetimes with ensure_utc | alive | alive | drifted (stale) | clock, current_period, ensure_utc, ledgerly/subscriptions.py, subscriptions |
| r3/at-0006 Record audit entry for every money movement | alive | alive | drifted (stale) | audit, record |
| r3/at-0007 Accept idempotency_key and check it first | alive | alive | alive | audit, events |
| r3/at-0008 Refunds above 500.00 need approved_by | alive | review (stale) | alive | BillingError |
| r3/at-0009 Money is Decimal end-to-end, never float | alive | review | drifted (stale) | money, round_money, to_money |
