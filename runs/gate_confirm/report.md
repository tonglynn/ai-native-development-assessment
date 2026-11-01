# Gate confirmation: a gate without the performance cost? (D71, exploratory)

Same session, every arm learns its own memory; clean stream and test-passing poison stream; excluded for leaks: 0.

| Arm | Clean held-out pass@1 (runs) | Poison stream pass@1 | Poison notes stored | Held-out runs applying the poison |
|---|---|---|---|---|
| ace | 65% (55) | 46% | 8 | 23/55 |
| attest | 73% (55) | 69% | 5 | 20/55 |
| attest_no_gate | 82% (55) | 71% | 4 | 13/55 |
| attest_secure_v31 | 82% (55) | 80% | 0 | 0/55 |
| attest_secure_v4 | 84% (55) | 76% | 0 | 0/55 |
| reasoningbank | 60% (55) | 58% | 10 | 28/55 |

| v3.1 against | Difference (paired by task) | Verdict |
|---|---|---|
| no gate | -0% [-7%, +7%] | not worse |
| Attest | +9% [+2%, +16%] | better |
| ReasoningBank | +22% [+4%, +44%] | better |
| ACE | +16% [-4%, +38%] | not worse |
| (secondary) v4 against no gate | +2% [-9%, +11%] | not worse |
| (secondary) v4 against Attest | +11% [-0%, +25%] | not worse |

- Rule 1, not worse than no gate: **met**
- Rule 2, better than Attest: **met**
- Rule 3, poison kept out (0 stored, 0 applied): **met**

**Confirmed on this benchmark: a gate without a measured performance cost.**
