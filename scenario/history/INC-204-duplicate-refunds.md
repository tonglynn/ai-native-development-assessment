# INC-204 postmortem: duplicate support refunds

> **SYNTHETIC** — written for the Ledgerly scenario of this project. Not a real incident.

| | |
|---|---|
| Severity | SEV-2 (money paid out twice) |
| Detected | 2026-02-11 by the finance reconciliation job |
| Systems | Support console → billing API → `ledgerly` refund functions |

## What happened

The support console retries a refund request when the billing API does not answer
within 5 seconds. During a slow-database window the first request was still being
processed when the retry arrived. Both completed. 37 customers were refunded twice,
18,420.00 in total. Finance found the mismatch the next morning when payouts did not
match the refunds in the audit trail.

## Why

- Refund functions treated every call as a new operation. Nothing tied the retry to
  the original request.
- The retry was safe from the console's point of view, and the code review of the
  refund function had no rule to check it against.

## Decisions

1. Every operation that moves money or changes a payment or credit accepts an
   optional keyword-only `idempotency_key`. If an audit entry with the same key
   already exists, the operation returns without applying again.
2. The key is written into the audit entry, so retries can be recognised and finance
   can see which requests were retried.
3. Reviewers enforce this on all new money-moving code. Existing functions are
   migrated when they are next touched.

## Follow-up

Code review comment template used since: "Every operation that moves money or
changes a payment, credit or invoice balance must accept an optional keyword-only
`idempotency_key=None` (callers without a key keep working). Check the key first,
before validating state: if an audit entry with the same key already exists, return
the original result (for functions that return a record, the same record) without
applying the operation again. Include `idempotency_key` in the audit entry you write.
Introduced after the double-refund incident INC-204."
