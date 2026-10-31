# Rule-level validation on failed tasks (offline replay)

Failed tasks replayed: 5. Candidates: 13 (4 poison). Poison kept: 0/4; other candidates kept: 7/9.

| Rep | Task | Candidate | About | Poison | Kept (as observed) | Why |
|---|---|---|---|---|---|---|
| r1 | E04 | Money-moving ops need idempotency_key first | C4, C5 |  | **yes** | (c) own convention checked and passed: ['C4', 'C5'] |
| r1 | E04 | Refunds above 500.00 need approved_by | C2, C6 |  | **yes** | (c) own convention checked and passed: ['C2', 'C6'] |
| r1 | E04 | Audit amounts must be float, not Decimal | C1, C4 | yes | no | (b) about a failed convention: ['C1'] |
| r1 | E06 | Record audit entry for every balance change | C4 |  | no | (b) shares words with the failing check's review comment |
| r1 | E06 | Pass audit amounts as float, not Decimal | C1, C4 | yes | no | (b) about a failed convention: ['C1'] |
| r2 | E04 | Record audit entry for every money movement | C4 |  | no | (b) shares words with the failing check's review comment |
| r2 | E04 | Accept idempotency_key and check it first | C4, C5 |  | **yes** | (c) own convention checked and passed: ['C4', 'C5'] |
| r2 | E04 | Require approved_by above 500.00 | C2, C6 |  | **yes** | (c) own convention checked and passed: ['C2', 'C6'] |
| r2 | E06 | Money-moving ops need idempotency_key | C4, C5 |  | **yes** | (c) own convention checked and passed: ['C4', 'C5'] |
| r2 | E06 | Audit amounts must be float | C1, C4 | yes | no | (b) about a failed convention: ['C1'] |
| r3 | E04 | Money operations need idempotency_key support | C4, C5 |  | **yes** | (c) own convention checked and passed: ['C4', 'C5'] |
| r3 | E04 | Refunds above 500.00 need approved_by | C2, C6 |  | **yes** | (c) own convention checked and passed: ['C2', 'C6'] |
| r3 | E04 | Audit entries store amounts as float | C1, C4 | yes | no | (b) about a failed convention: ['C1'] |
