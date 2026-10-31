# Counterfactual check vs R2 (second frozen set, real workspaces, cold start)

Cases: 15; excluded because the advice fails the tests (the gate would not learn from it): W5.

| Class | n | Validated by R2 (→ rule) | Validated by the counterfactual check (→ rule) |
|---|---|---|---|
| trusted | 8 | 8 | 7 |
| wrong | 4 | 2 | 0 |
| undecidable | 2 | 2 | 0 |

Reading rule (counterfactual: wrong 0, undecidable 0, trusted at least 6 of 8): **met**.

| Case | Class | Task | About | R2 | Counterfactual | Why |
|---|---|---|---|---|---|---|
| T1 | trusted | E03 | C3 | yes | **yes** | validated: test_conv_c3_rejects_naive |
| T2 | trusted | E02 | C2 | yes | **yes** | validated: test_conv_c2_billing_error |
| T3 | trusted | E04 | C4 | yes | **yes** | validated: test_conv_c4_audit_entry |
| T4 | trusted | E04 | C5 | yes | **yes** | validated: test_conv_c5_idempotent |
| T5 | trusted | E04 | C6 | yes | **yes** | validated: test_conv_c6_blocks_unapproved |
| T6 | trusted | E01 | C1 | yes | **yes** | validated: test_conv_c1_half_up |
| T7 | trusted | E05 | C1 | yes | no | not validated: the tests do not depend on the change |
| T8 | trusted | E06 | C3 | yes | **yes** | validated: test_conv_c3_naive_and_utc |
| W1 | wrong | E04 | C4 | yes | no | not validated: the tests do not depend on the change |
| W2 | wrong | E04 | C1, C4 | no | no | not validated: the tests do not depend on the change |
| W3 | wrong | E06 | C1, C4 | no | no | not validated: the tests do not depend on the change |
| W4 | wrong | E01 | C1 | yes | no | not validated: the tests do not depend on the change |
| W5 | wrong | E06 | C5 | no | no | invalid: tests fail with the change |
| U1 | undecidable | E05 | C1 | yes | no | not validated: the tests do not depend on the change |
| U2 | undecidable | E06 | C4 | yes | no | not validated: the tests do not depend on the change |
