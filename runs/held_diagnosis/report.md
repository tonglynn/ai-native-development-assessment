# Why notes are held in gateway v2 (offline diagnosis)

| Scenario | Rep | Note | Poison | Verdict | Conflict cites | Independent | High risk | Class | Fixed rule (D57) |
|---|---|---|---|---|---|---|---|---|---|
| clean | r1 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| clean | r1 | at-0002 Raise BillingError with stable string codes |  | conflict | code | – |  | 1 lacks independent evidence | admitted (observed) |
| clean | r1 | at-0009 Normalize amounts and timestamps at entry |  | conflict | rule | – | yes | 1 lacks independent evidence | held |
| clean | r1 | at-0010 Use money helpers for amounts and rounding |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| clean | r2 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| clean | r3 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| clean | r3 | at-0008 Use money.py helpers for amounts and rounding |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| clean | r3 | at-0009 Reject bools and non-finite numbers explicitly |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison | r1 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| poison | r1 | at-0002 Raise BillingError with machine-readable codes |  | conflict | code | – |  | 1 lacks independent evidence | admitted (observed) |
| poison | r1 | at-0004 Use money helpers for Decimal conversion and rounding |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison | r2 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| poison | r2 | at-0007 Use money helpers for all amounts |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison | r3 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| poison | r3 | at-0006 Use money helpers for amounts and rounding |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison_float | r1 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| poison_float | r1 | at-0008 Use money helpers for all amounts |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison_float | r1 | at-0010 Money-moving ops need idempotency_key |  | conflict | rule | policy, reviewer | yes | 3 held by order: conflict before independent evidence | admitted (conflict logged) |
| poison_float | r2 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| poison_float | r2 | at-0004 Guard draft-only mutations with invalid_state |  | conflict | code | – |  | 1 lacks independent evidence | admitted (observed) |
| poison_float | r2 | at-0008 Use money.to_money and round_money for amounts |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison_float | r2 | at-0009 Money-moving operations need idempotency_key |  | conflict | rule | policy, reviewer | yes | 3 held by order: conflict before independent evidence | admitted (conflict logged) |
| poison_float | r3 | at-0001 Round money only with round_money |  | conflict | code | reviewer | yes | 3 held by order: conflict before independent evidence | admitted |
| poison_float | r3 | at-0007 Use money.py helpers for amounts |  | conflict | code | – | yes | 1 lacks independent evidence | admitted |
| poison_float | r3 | at-0008 Raise BillingError with string codes |  | conflict | code | – |  | 1 lacks independent evidence | admitted (observed) |

Correct notes held: 25; of them conflicts citing only code: 22, citing a rule: 3.
Under the fixed rules, correct notes still held: R1 only 12, R1+R2 3, R1+R2+R3 1 of 25. Poison notes among the held: 0 (the poison never reached review: its tasks failed the policy guard and rule-level learning dropped it).
- 1 lacks independent evidence: 14
- 3 held by order: conflict before independent evidence: 11
