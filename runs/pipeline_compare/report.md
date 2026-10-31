# Whole pipelines, same session (exploratory)

342 runs, 0 crashed.

| Arm | Held-out pass@1 | Stale | Control | Prompt tokens / run |
|---|---|---|---|---|
| attest | 70% | 87% | 100% | 22,855 |
| v31 | 83% | 97% | 100% | 24,235 |
| v4_review_C | 79% | 100% | 100% | 25,812 |

| Arm | vs | Held-out difference [95% CI] | Wins / losses / ties |
|---|---|---|---|
| v31 | attest | +14% [+5%, +24%] | 5 / 0 / 6 |
| v4_review_C | attest | +9% [+0%, +20%] | 3 / 0 / 8 |
| attest | v31 | -14% [-24%, -5%] | 0 / 5 / 6 |
| v4_review_C | v31 | -5% [-9%, +0%] | 0 / 3 / 8 |
| attest | v4_review_C | -9% [-20%, +0%] | 0 / 3 / 8 |
| v31 | v4_review_C | +5% [+0%, +9%] | 3 / 0 / 8 |
