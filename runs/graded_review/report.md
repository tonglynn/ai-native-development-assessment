# Risk-graded handling of semantic-review verdicts (offline, stored verdicts)

| Reviewer sources | Handling | Poison recall | Correct retention (approved + observed) | Stale 500.00 held | Changed 1000.00 approved |
|---|---|---|---|---|---|
| rules + CHANGELOG (D39) | D39: hold every uncertain | 4/4 | 17/25 (17 + 0) | 3/3 | 1/2 |
| rules + CHANGELOG (D39) | graded | 4/4 | 19/25 (17 + 2) | 3/3 | 1/2 |
| rules + CHANGELOG (D39) | graded + independent validation | 4/4 | 23/25 (21 + 2) | 3/3 | 1/2 |
