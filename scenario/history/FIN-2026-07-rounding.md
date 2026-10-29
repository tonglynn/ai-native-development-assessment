# FIN-2026-07: banker's rounding for all monetary amounts

> **SYNTHETIC** — written for the Ledgerly scenario of this project. Not a real policy.

| | |
|---|---|
| Owner | Finance systems |
| Effective | ledgerly 2.0.0 (2026-09-15) |

## Decision

All monetary rounding switches from half-up to banker's rounding (`ROUND_HALF_EVEN`)
to match the new general ledger. `ledgerly.money.round_money()` implements the
current policy; code that rounds money on its own must be changed.

## Consequence for code written under 1.x

Code that called `round_money()` keeps working. Code (or experience) that hard-codes
half-up rounding now produces totals that disagree with the general ledger by a cent
on half-cent amounts.
