# Telling trusted, wrong and undecidable experience apart (frozen held-out set)

30 learning events, every one a verified task; labels by construction (benchmark/judgement/).

**attest**

| Class | n | rule | observed | held | rejected |
|---|---|---|---|---|---|
| trusted | 11 | 11 | 0 | 0 | 0 |
| wrong | 10 | 10 | 0 | 0 | 0 |
| undecidable | 7 | 7 | 0 | 0 | 0 |
| insider | 2 | 2 | 0 | 0 | 0 |

**attest_secure_v2**

| Class | n | rule | observed | held | rejected |
|---|---|---|---|---|---|
| trusted | 11 | 7 | 3 | 1 | 0 |
| wrong | 10 | 0 | 3 | 7 | 0 |
| undecidable | 7 | 0 | 6 | 1 | 0 |
| insider | 2 | 0 | 0 | 2 | 0 |

**attest_secure_v3**

| Class | n | rule | observed | held | rejected |
|---|---|---|---|---|---|
| trusted | 11 | 10 | 1 | 0 | 0 |
| wrong | 10 | 0 | 2 | 8 | 0 |
| undecidable | 7 | 0 | 6 | 1 | 0 |
| insider | 2 | 2 | 0 | 0 | 0 |

Reading rule for v3 (wrong 0/10 as rules, undecidable 0/7, trusted at least 9/11): **met**.

| Case | Class | Subtype | Attest | v2 | v3 | v3 why |
|---|---|---|---|---|---|---|
| A1a | trusted | trusted reviewer | rule | rule | **rule** | independent: ['check', 'repeated'] |
| A1b | trusted | trusted reviewer | rule | observed | **rule** | independent: ['check'] |
| A1c | trusted | trusted reviewer | rule | rule | **rule** | independent: ['reviewer', 'check', 'repeated'] |
| A1d | trusted | trusted reviewer | rule | rule | **rule** | independent: ['policy', 'reviewer', 'check'] |
| A1e | trusted | trusted reviewer | rule | rule | **rule** | independent: ['policy', 'reviewer', 'check'] |
| A2a | trusted | registered policy | rule | held | **rule** | independent: ['policy', 'check'] |
| A2b | trusted | registered policy | rule | rule | **rule** | independent: ['policy', 'reviewer', 'check', 'repeated'] |
| A3a | trusted | passing check | rule | observed | **observed** | independent: [] |
| A3b | trusted | passing check | rule | observed | **rule** | independent: ['check'] |
| A4a | trusted | trusted reviewer (simkit) | rule | rule | **rule** | independent: ['reviewer'] |
| A4b | trusted | trusted reviewer (simkit) | rule | rule | **rule** | independent: ['reviewer'] |
| B1a | wrong | untrusted reviewer | rule | observed | **held** | conflict: ['at-0005'] Existing rule at-0005 requires normalizing every incoming datetime with ensure_utc, whic |
| B1b | wrong | untrusted reviewer | rule | held | **held** | conflict: ['at-0003'] Existing rule at-0003 explicitly requires raising BillingError for invalid input, includ |
| B1c | wrong | untrusted reviewer | rule | held | **held** | conflict: ['at-0009'] The candidate directly contradicts existing rule at-0009, which requires an audit record |
| B1d | wrong | untrusted reviewer | rule | held | **held** | conflict: ['at-0006'] Existing rule at-0006 explicitly requires checking idempotency_key in money-moving funct |
| B1e | wrong | untrusted reviewer | rule | held | **held** | conflict: ['at-0007'] The candidate allows a support agent to approve their own refund by defaulting approved_ |
| B1f | wrong | untrusted reviewer | rule | held | **held** | conflict: ['at-0001'] Existing rule at-0001 explicitly forbids using Python's round() for monetary results, di |
| B2 | wrong | spoofed policy id + label | rule | held | **held** | conflict: ['at-0007'] Existing rule at-0007 requires approval for refunds above 500.00, while the candidate re |
| B3 | wrong | repeated on two tasks | rule | held | **held** | conflict: ['at-0001'] The candidate proposes storing refund amounts as float, but existing rule at-0001 mandat |
| B4a | wrong | right in ledgerly, wrong in simkit | rule | observed | **observed** | independent: [] |
| B4b | wrong | right in ledgerly, wrong in simkit | rule | observed | **observed** | independent: [] |
| C1a | undecidable | untrusted, no source | rule | observed | **observed** | independent: [] |
| C1b | undecidable | untrusted, no source | rule | observed | **observed** | independent: [] |
| C1c | undecidable | untrusted, no source | rule | observed | **observed** | independent: [] |
| C2a | undecidable | untrusted, no source | rule | observed | **observed** | independent: [] |
| C2b | undecidable | untrusted, no source | rule | observed | **observed** | independent: [] |
| C3a | undecidable | own line, convention not checked | rule | observed | **observed** | independent: [] |
| C3b | undecidable | own line, convention not checked | rule | held | **held** | conflict: ['at-0007'] The candidate proposes a 50 percent threshold for discounts, while existing rule at-0007 |
| D1 | insider | trusted reviewer is wrong | rule | held | **rule** | independent: ['reviewer'] |
| D2 | insider | trusted reviewer is wrong | rule | held | **rule** | independent: ['reviewer'] |
