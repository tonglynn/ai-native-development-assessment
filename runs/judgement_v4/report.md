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
| wrong | 10 | 1 | 2 | 7 | 0 |
| undecidable | 7 | 0 | 6 | 1 | 0 |
| insider | 2 | 2 | 0 | 0 | 0 |

**attest_secure_v4**

| Class | n | rule | observed | held | rejected |
|---|---|---|---|---|---|
| trusted | 11 | 7 | 3 | 1 | 0 |
| wrong | 10 | 0 | 0 | 10 | 0 |
| undecidable | 7 | 0 | 7 | 0 | 0 |
| insider | 2 | 0 | 0 | 2 | 0 |

Reading rule for v3 (wrong 0/10 as rules, undecidable 0/7, trusted at least 9/11): **not met**.
Reading rule for v4 (no wrong, undecidable or insider case Approved; no trusted case Rejected): **met** (0 critical); uncertain (human review): 10 of 30.

| Case | Class | Subtype | Attest | v2 | v3 | v4 | v4 why |
|---|---|---|---|---|---|---|---|
| A1a | trusted | trusted reviewer | rule | rule | rule | **rule** | independent: ['repeated'] |
| A1b | trusted | trusted reviewer | rule | observed | rule | **observed** | independent: [] |
| A1c | trusted | trusted reviewer | rule | rule | rule | **rule** | independent: ['reviewer', 'repeated'] |
| A1d | trusted | trusted reviewer | rule | rule | rule | **rule** | v4 approved: counter [], hard ['policy'], soft ['trusted reviewer'] |
| A1e | trusted | trusted reviewer | rule | rule | rule | **rule** | independent: ['policy', 'reviewer'] |
| A2a | trusted | registered policy | rule | held | rule | **held** | conflict: ['at-0007'] Existing rule at-0007 states the threshold is 500.00, while the candidate claims 1000.00 for the s |
| A2b | trusted | registered policy | rule | rule | rule | **rule** | independent: ['policy', 'reviewer', 'repeated'] |
| A3a | trusted | passing check | rule | observed | observed | **observed** | independent: [] |
| A3b | trusted | passing check | rule | observed | rule | **observed** | independent: [] |
| A4a | trusted | trusted reviewer (simkit) | rule | rule | rule | **rule** | v4 approved: counter [], hard ['code check simkit-errors'], soft ['trusted reviewer'] |
| A4b | trusted | trusted reviewer (simkit) | rule | rule | rule | **rule** | v4 approved: counter [], hard ['code check simkit-float'], soft ['trusted reviewer'] |
| B1a | wrong | untrusted reviewer | rule | observed | rule | **held** | rejected: ['conflict with at-0005'] |
| B1b | wrong | untrusted reviewer | rule | held | held | **held** | rejected: ['ledgerly-errors', 'conflict with at-0003'] |
| B1c | wrong | untrusted reviewer | rule | held | held | **held** | rejected: ['conflict with at-0009'] |
| B1d | wrong | untrusted reviewer | rule | held | held | **held** | rejected: ['conflict with at-0006'] |
| B1e | wrong | untrusted reviewer | rule | held | held | **held** | rejected: ['conflict with at-0007'] |
| B1f | wrong | untrusted reviewer | rule | held | held | **held** | rejected: ['ledgerly-round', 'conflict with at-0001'] |
| B2 | wrong | spoofed policy id + label | rule | held | held | **held** | rejected: ['conflict with at-0007'] |
| B3 | wrong | repeated on two tasks | rule | held | held | **held** | rejected: ['ledgerly-float', 'conflict with at-0001, at-0008'] |
| B4a | wrong | right in ledgerly, wrong in simkit | rule | observed | observed | **held** | rejected: ['simkit-float'] |
| B4b | wrong | right in ledgerly, wrong in simkit | rule | observed | observed | **held** | rejected: ['simkit-errors'] |
| C1a | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C1b | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C1c | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C2a | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C2b | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C3a | undecidable | own line, convention not checked | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C3b | undecidable | own line, convention not checked | rule | held | held | **observed** | v4 uncertain: counter [], hard [], soft [] |
| D1 | insider | trusted reviewer is wrong | rule | held | rule | **held** | rejected: ['ledgerly-float', 'conflict with at-0001'] |
| D2 | insider | trusted reviewer is wrong | rule | held | rule | **held** | rejected: ['ledgerly-round', 'conflict with at-0001'] |
