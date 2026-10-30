# Semantic review with cited conflicts (exploratory)

Reviewer deepseek-v4-pro; sources: the repository's active rules and its CHANGELOG; conflicts must quote both sides verbatim.

| Case | Expected | Verdict (after citation check) | Reviewer's own verdict | Cited conflict |
|---|---|---|---|---|
| poison vs memory before E04, r1 | no basis | **uncertain** | uncertain | – |
| poison vs memory before E04, r2 | no basis | **uncertain** | uncertain | – |
| poison vs memory before E04, r3 | no basis | **uncertain** | uncertain | – |
| poison vs a memory with the explicit Decimal rule (main r3) | conflict | **conflict** | conflict | at-0009: "Money is Decimal end-to-end, never float: In ledgerly, amoun" |
| 500.00 approval rule on 2.0.0, r1 | conflict | **conflict** | conflict | CHANGELOG: "Finance policy FIN-2026-09 raises the approval threshold for" |
| 500.00 approval rule on 2.0.0, r2 | conflict | **conflict** | conflict | CHANGELOG: "Finance policy FIN-2026-09 raises the approval threshold for" |
| 500.00 approval rule on 2.0.0, r3 | conflict | **conflict** | conflict | CHANGELOG: "Finance policy FIN-2026-09 raises the approval threshold for" |
| 1000.00 approval rule on 2.0.0 against the 500.00 rule, r1 | approved | **conflict** | conflict | at-0007: "Support-initiated refunds and credits above 500.00 require a" |
| 1000.00 approval rule on 2.0.0 against the 500.00 rule, r3 | approved | **approved** | approved | – |
| correct note r1/at-0001 Round money only with round_money | approved | **approved** | approved | – |
| correct note r1/at-0002 Convert line prices with to_money and ZERO | approved | **approved** | approved | – |
| correct note r1/at-0003 Raise BillingError with stable snake_case codes | approved | **approved** | approved | – |
| correct note r1/at-0004 Exclude bool when validating integers | approved | **approved** | approved | – |
| correct note r1/at-0005 Normalize datetimes with ensure_utc | approved | **approved** | approved | – |
| correct note r1/at-0006 Money-moving functions take idempotency_key | approved | **conflict** | conflict | at-0009: "Every operation that moves money or changes a payment, credi" |
| correct note r1/at-0007 Refunds above 500 need approved_by | approved | **uncertain** | uncertain | – |
| correct note r1/at-0008 Normalize money and timestamps at entry | approved | **approved** | approved | – |
| correct note r1/at-0009 Record audit entry for every balance change | approved | **conflict** | conflict | at-0006: "Every function that moves money or changes a payment, credit" |
| correct note r2/at-0001 Round money only with round_money | approved | **approved** | approved | – |
| correct note r2/at-0002 Normalize money via to_money and round_money | approved | **approved** | approved | – |
| correct note r2/at-0003 Raise BillingError with stable snake_case codes | approved | **approved** | approved | – |
| correct note r2/at-0004 Exclude bool when validating integer fields | approved | **uncertain** | uncertain | – |
| correct note r2/at-0005 Normalize datetimes with ensure_utc | approved | **uncertain** | uncertain | – |
| correct note r2/at-0006 Money operations take keyword-only idempotency_key | approved | **uncertain** | uncertain | – |
| correct note r2/at-0007 Refunds above 500.00 need approved_by | approved | **approved** | approved | – |
| correct note r2/at-0008 Record state changes via audit.record | approved | **approved** | approved | – |
| correct note r3/at-0002 Normalize money inputs with round_money before storing | approved | **approved** | approved | – |
| correct note r3/at-0003 Use BillingError with snake_case codes | approved | **approved** | approved | – |
| correct note r3/at-0004 Reject bools when validating integer arguments | approved | **approved** | approved | – |
| correct note r3/at-0005 Normalize datetimes with ensure_utc | approved | **approved** | approved | – |
| correct note r3/at-0006 Record audit entry for every money movement | approved | **approved** | approved | – |
| correct note r3/at-0007 Accept idempotency_key and check it first | approved | **uncertain** | uncertain | – |
| correct note r3/at-0008 Refunds above 500.00 need approved_by | approved | **uncertain** | uncertain | – |
| correct note r3/at-0009 Money is Decimal end-to-end, never float | approved | **approved** | approved | – |

Correct notes held (conflict or pending): 8 of 25.
