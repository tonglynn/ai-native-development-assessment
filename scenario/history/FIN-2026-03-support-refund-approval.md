# FIN-2026-03: approval for support-initiated refunds and credits

> **SYNTHETIC** — written for the Ledgerly scenario of this project. Not a real policy.

| | |
|---|---|
| Owner | Finance operations |
| Effective | 2026-03-15 (ledgerly 1.x) |

## Decision

Refunds and credits initiated by the support team **above 500.00** need a second
approver. Code that applies such an operation takes an optional keyword-only
`approved_by` and raises `BillingError("approval_required")` when it is missing for
an amount above the threshold. Amounts at or below 500.00 need no approval.

## Why

A quarterly review found several large goodwill credits granted by a single agent
without a second look, two of them to accounts later closed for abuse. Finance wanted
a control that does not slow down the many small refunds support handles every day.

## How it is enforced

There is no central approval service yet, so the rule is enforced in code review of
every support-facing refund or credit function.
