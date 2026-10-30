# Context management on a long session (exploratory)

Earlier session: 70 messages (~19067 tokens) from S04, S01, S02, S03; then task S05. Budget 6000 tokens for window / summary / manager. No long-term memory.

| Arm | Runs | Crashed | pass@1 | C6 blocks failed | C6 allows failed | Prompt tokens / run |
|---|---|---|---|---|---|---|
| no_session | 3 | 0 | 0% | 3 | 3 | 39,165 |
| full | 3 | 0 | 100% | 0 | 0 | 185,929 |
| window | 3 | 0 | 0% | 3 | 3 | 46,177 |
| summary | 3 | 0 | 33% | 2 | 2 | 43,603 |
| manager | 3 | 0 | 0% | 3 | 3 | 43,352 |

Facts S05 needs, present in the context the model receives (offline):

| Budget | Strategy | Tokens | 1000.00 | approved_by | approval_required | Summary kept pinned tokens |
|---|---|---|---|---|---|---|
| 4000 | full | 19,222 | yes | yes | yes |  |
| 4000 | window | 3,348 | no | no | no |  |
| 4000 | summary | 3,073 | no | no | no | 0/8 |
| 4000 | manager | 3,982 | yes | yes | yes |  |
| 6000 | full | 19,222 | yes | yes | yes |  |
| 6000 | window | 5,610 | yes | no | no |  |
| 6000 | summary | 4,804 | no | no | no | 0/8 |
| 6000 | manager | 5,983 | yes | yes | yes |  |
| 8000 | full | 19,222 | yes | yes | yes |  |
| 8000 | window | 7,561 | yes | no | no |  |
| 8000 | summary | 7,299 | yes | no | no | 0/8 |
| 8000 | manager | 7,982 | yes | yes | yes |  |
