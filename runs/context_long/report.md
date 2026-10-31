# Context management, long session with policy changes (exploratory)

Session: 169 messages (~40,601 tokens), 9 real task trajectories and 5 synthetic policy messages; then S05.

Offline: is each needed fact in the context the model receives?

| Budget | Strategy | Tokens (saving vs full) | 1000.00 | approved_by | approval_required | audit.record | FIN-2026-11 | outdated 500.00 present | supersession present |
|---|---|---|---|---|---|---|---|---|---|
| – | full | 40,762 (–) | yes | yes | yes | yes | yes | yes | yes |
| 4000 | window | 3,386 (92%) | **no** | **no** | **no** | **no** | **no** | no | no |
| 4000 | summary | 3,960 (90%) | yes | yes | yes | yes | yes | yes | yes |
| 4000 | manager | 3,933 (90%) | yes | yes | yes | yes | yes | yes | yes |
| 8000 | window | 7,642 (81%) | yes | **no** | **no** | yes | **no** | yes | no |
| 8000 | summary | 7,845 (81%) | yes | yes | yes | yes | yes | yes | no |
| 8000 | manager | 7,941 (81%) | yes | yes | yes | yes | yes | yes | yes |
| 12000 | window | 11,245 (72%) | yes | yes | yes | yes | yes | yes | yes |
| 12000 | summary | 11,843 (71%) | yes | yes | yes | yes | yes | yes | yes |
| 12000 | manager | 11,949 (71%) | yes | yes | yes | yes | yes | yes | yes |

End to end (S05, first attempt):

| Model | Arm | Budget | Runs | pass@1 | C6 failed | C4 failed | Prompt tokens / run |
|---|---|---|---|---|---|---|---|
| deepseek-flash | full | – | 3 | 100% | 0 | 0 | 491,937 |
| deepseek-flash | manager | 4000 | 3 | 100% | 0 | 0 | 52,684 |
| deepseek-flash | manager | 8000 | 3 | 100% | 0 | 0 | 67,956 |
| deepseek-flash | manager | 12000 | 3 | 100% | 0 | 0 | 107,524 |
| deepseek-flash | no_session | – | 3 | 0% | 3 | 0 | 68,196 |
| deepseek-flash | summary | 4000 | 3 | 33% | 2 | 0 | 31,229 |
| deepseek-flash | summary | 8000 | 3 | 0% | 3 | 0 | 67,134 |
| deepseek-flash | summary | 12000 | 3 | 0% | 3 | 0 | 103,546 |
| deepseek-flash | window | 4000 | 3 | 0% | 3 | 0 | 34,762 |
| deepseek-flash | window | 8000 | 3 | 0% | 3 | 0 | 76,881 |
| deepseek-flash | window | 12000 | 3 | 0% | 3 | 0 | 106,989 |
| deepseek/deepseek-v4-pro | full | – | 3 | 67% | 1 | 0 | 474,377 |
| deepseek/deepseek-v4-pro | manager | 8000 | 3 | 100% | 0 | 0 | 75,379 |
