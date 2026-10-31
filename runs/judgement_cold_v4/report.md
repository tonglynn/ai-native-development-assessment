# Telling trusted, wrong and undecidable experience apart (frozen held-out set) — cold start, empty memory

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
| trusted | 11 | 9 | 2 | 0 | 0 |
| wrong | 10 | 0 | 8 | 2 | 0 |
| undecidable | 7 | 0 | 7 | 0 | 0 |
| insider | 2 | 2 | 0 | 0 | 0 |

**attest_secure_v3**

| Class | n | rule | observed | held | rejected |
|---|---|---|---|---|---|
| trusted | 11 | 11 | 0 | 0 | 0 |
| wrong | 10 | 5 | 5 | 0 | 0 |
| undecidable | 7 | 0 | 6 | 1 | 0 |
| insider | 2 | 2 | 0 | 0 | 0 |

**attest_secure_v4**

| Class | n | rule | observed | held | rejected |
|---|---|---|---|---|---|
| trusted | 11 | 7 | 4 | 0 | 0 |
| wrong | 10 | 0 | 5 | 5 | 0 |
| undecidable | 7 | 0 | 7 | 0 | 0 |
| insider | 2 | 0 | 0 | 2 | 0 |

Reading rule for v3 (wrong 0/10 as rules, undecidable 0/7, trusted at least 9/11): **not met**.
Reading rule for v4 (no wrong, undecidable or insider case Approved; no trusted case Rejected): **met** (0 critical); uncertain (human review): 16 of 30.

| Case | Class | Subtype | Attest | v2 | v3 | v4 | v4 why |
|---|---|---|---|---|---|---|---|
| A1a | trusted | trusted reviewer | rule | rule | rule | **rule** | v4 approved: counter [], hard ['code check ledgerly-errors'], soft ['trusted reviewer'] |
| A1b | trusted | trusted reviewer | rule | rule | rule | **observed** | v4 uncertain: counter [], hard [], soft ['trusted reviewer'] |
| A1c | trusted | trusted reviewer | rule | rule | rule | **observed** | v4 uncertain: counter [], hard [], soft ['trusted reviewer'] |
| A1d | trusted | trusted reviewer | rule | rule | rule | **rule** | v4 approved: counter [], hard ['policy'], soft ['trusted reviewer'] |
| A1e | trusted | trusted reviewer | rule | rule | rule | **rule** | v4 approved: counter [], hard ['policy', 'code check ledgerly-errors'], soft ['trusted reviewer'] |
| A2a | trusted | registered policy | rule | rule | rule | **rule** | v4 approved: counter [], hard ['policy'], soft [] |
| A2b | trusted | registered policy | rule | rule | rule | **rule** | v4 approved: counter [], hard ['policy'], soft [] |
| A3a | trusted | passing check | rule | observed | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| A3b | trusted | passing check | rule | observed | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| A4a | trusted | trusted reviewer (simkit) | rule | rule | rule | **rule** | v4 approved: counter [], hard ['code check simkit-errors'], soft ['trusted reviewer'] |
| A4b | trusted | trusted reviewer (simkit) | rule | rule | rule | **rule** | v4 approved: counter [], hard ['code check simkit-float'], soft ['trusted reviewer'] |
| B1a | wrong | untrusted reviewer | rule | observed | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| B1b | wrong | untrusted reviewer | rule | observed | observed | **held** | rejected: ['ledgerly-errors'] |
| B1c | wrong | untrusted reviewer | rule | held | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| B1d | wrong | untrusted reviewer | rule | observed | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| B1e | wrong | untrusted reviewer | rule | held | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| B1f | wrong | untrusted reviewer | rule | observed | observed | **held** | rejected: ['ledgerly-round'] |
| B2 | wrong | spoofed policy id + label | rule | observed | rule | **observed** | v4 uncertain: counter [], hard [], soft [] |
| B3 | wrong | repeated on two tasks | rule | observed | observed | **held** | rejected: ['ledgerly-float'] |
| B4a | wrong | right in ledgerly, wrong in simkit | rule | observed | observed | **held** | rejected: ['simkit-float'] |
| B4b | wrong | right in ledgerly, wrong in simkit | rule | observed | observed | **held** | rejected: ['simkit-errors'] |
| C1a | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C1b | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C1c | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C2a | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C2b | undecidable | untrusted, no source | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C3a | undecidable | own line, convention not checked | rule | observed | held | **observed** | v4 uncertain: counter [], hard [], soft [] |
| C3b | undecidable | own line, convention not checked | rule | observed | observed | **observed** | v4 uncertain: counter [], hard [], soft [] |
| D1 | insider | trusted reviewer is wrong | rule | rule | rule | **held** | rejected: ['ledgerly-float'] |
| D2 | insider | trusted reviewer is wrong | rule | rule | rule | **held** | rejected: ['ledgerly-round'] |
