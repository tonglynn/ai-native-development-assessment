# FIN-2026-09: approval threshold raised to 1000.00

> **SYNTHETIC** — written for the Ledgerly scenario of this project. Not a real policy.

| | |
|---|---|
| Owner | Finance operations |
| Effective | ledgerly 2.0.0 (2026-09-15) |
| Replaces | the threshold in FIN-2026-03 |

## Decision

The approval threshold for support-initiated refunds and credits rises from 500.00
to **1000.00**. Operations at or below 1000.00 need no second approver.

## Why

Six months of data showed the approval queue was dominated by routine credits between
500 and 1000, delaying customers by days while finding no abuse in that band.

## Consequence

Code or experience that still applies the 500.00 threshold now **blocks legitimate
operations** (for example a 700.00 goodwill credit), which is a customer-facing
failure, not just a style problem. ledgerly 2.0.0's CHANGELOG records the change.
