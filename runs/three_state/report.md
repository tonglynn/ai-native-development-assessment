# Three states on frozen sets (offline, real workspaces, empty memory)

## set3 (13 cases; excluded, advice fails the tests: K4)

| Truth | n | v3.1 rule | v4 approved | v4 uncertain | v4 rejected |
|---|---|---|---|---|---|
| correct | 6 | 5 | 6 | 0 | 0 |
| wrong | 5 | 4 | 0 | 1 | 4 |
| undecidable | 2 | 0 | 0 | 2 | 0 |

Critical errors: v3.1 4, v4 0.

| Case | Truth | Kind | v3.1 | v4 | Counter-evidence | Hard | Soft | Counterfactual |
|---|---|---|---|---|---|---|---|---|
| S1 | correct | business | rule | **approved** | – | test | – | validated |
| S2 | correct | business | rule | **approved** | – | test | – | validated |
| S3 | correct | business | rule | **approved** | – | test | – | validated |
| K1 | correct | code | rule | **approved** | – | code check ledgerly-round | trusted reviewer | validated |
| K2 | wrong | code | rule | **rejected** | ledgerly-round | – | – | validated |
| K3 | correct | code | rule | **approved** | – | code check ledgerly-errors | trusted reviewer | validated |
| K4 | wrong | code | not a rule | **rejected** | ledgerly-errors, the advice fails the tests | – | – | invalid: tests fail with the change |
| K5 | wrong | code | not a rule | **rejected** | naming | – | – | inconclusive: no counterfactual edit |
| K6 | correct | code | not a rule | **approved** | – | code check simkit-errors | – | not validated: the tests do not depend on the change |
| I1 | wrong | business | rule | **rejected** | ledgerly-float | – | trusted reviewer | not validated: the tests do not depend on the change |
| I2 | wrong | business | rule | **uncertain** | – | – | trusted reviewer | not validated: the tests do not depend on the change |
| I3 | wrong | code | rule | **rejected** | ledgerly-round | – | trusted reviewer | validated |
| U1 | undecidable | style | not a rule | **uncertain** | – | – | – | not validated: the tests do not depend on the change |
| U2 | undecidable | business | not a rule | **uncertain** | – | – | – | not validated: the tests do not depend on the change |

## set2 (14 cases; excluded, advice fails the tests: W5)

| Truth | n | v3.1 rule | v4 approved | v4 uncertain | v4 rejected |
|---|---|---|---|---|---|
| correct | 8 | 7 | 7 | 1 | 0 |
| wrong | 4 | 1 | 0 | 1 | 3 |
| undecidable | 2 | 0 | 0 | 2 | 0 |

Critical errors: v3.1 1, v4 0.

| Case | Truth | Kind | v3.1 | v4 | Counter-evidence | Hard | Soft | Counterfactual |
|---|---|---|---|---|---|---|---|---|
| T1 | correct |  | rule | **approved** | – | test | – | validated |
| T2 | correct |  | rule | **approved** | – | code check ledgerly-errors | – | validated |
| T3 | correct |  | rule | **approved** | – | test | – | validated |
| T4 | correct |  | rule | **approved** | – | test | – | validated |
| T5 | correct |  | rule | **approved** | – | test | – | validated |
| T6 | correct |  | rule | **approved** | – | code check ledgerly-round | – | validated |
| T7 | correct |  | not a rule | **uncertain** | – | – | – | not validated: the tests do not depend on the change |
| T8 | correct |  | rule | **approved** | – | test | – | validated |
| W1 | wrong |  | not a rule | **uncertain** | – | – | – | not validated: the tests do not depend on the change |
| W2 | wrong |  | not a rule | **rejected** | ledgerly-float | – | – | not validated: the tests do not depend on the change |
| W3 | wrong |  | not a rule | **rejected** | ledgerly-float | – | – | not validated: the tests do not depend on the change |
| W4 | wrong |  | rule | **rejected** | ledgerly-round | – | – | validated |
| W5 | wrong |  | not a rule | **rejected** | the advice fails the tests | – | – | invalid: tests fail with the change |
| U1 | undecidable |  | not a rule | **uncertain** | – | – | – | not validated: the tests do not depend on the change |
| U2 | undecidable |  | not a rule | **uncertain** | – | – | – | inconclusive: no counterfactual edit |

