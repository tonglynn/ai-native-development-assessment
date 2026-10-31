# Where Attest lost the Saleor convention comments (offline, hand labels)

| Stage | Comments | Of which ReasoningBank / ACE credited | Ids |
|---|---|---|---|
| not taught | 13 | 1 / 0 | T02, T03, T06, T07, T10, T11, T12, T15, T16, T17, T18, T19, T23 |
| taught, not provable by a diff | 2 | 1 / 0 | T01, T22 |
| taught, not stored | 1 | 0 / 0 | T25 |
| stored, not shown | 6 | 0 / 5 | T04, T05, T08, T13, T20, T24 |
| shown, not credited | 2 | 1 / 2 | T09, T21 |
| credited | 1 | 1 / 1 | T14 |

| Id | Rule | Taught | Kind | Attest notes | Shown | Lost at |
|---|---|---|---|---|---|---|
| T01 | Port latest commit into main branch | yes | process | – | – | taught, not provable by a diff |
| T02 | When backporting changes with migrations, include migration source in the backport. | no | process | – | – | not taught |
| T03 | Test names should not repeat the module/mutation context prefix. | no | code | – | – | not taught |
| T04 | Use pytest parametrize to simplify complex test cases. | yes | code | at-0041, at-0047 | – | stored, not shown |
| T05 | Add tests covering edge cases like empty string; ensure behavior is consistent with other models supporting external_reference. | partly | code | at-0039 | – | stored, not shown |
| T06 | Rebase with the target branch and resolve all review conversations before merging. | no | process | – | – | not taught |
| T07 | Analogous checkout error types should expose the same voucher rejection details. | no | code | – | – | not taught |
| T08 | Include ADDED_IN version in descriptions for newly added enum values. | yes | code | at-0051 | – | stored, not shown |
| T09 | Voucher validation should return NOT_FOUND for inaccessible vouchers before revealing other statuses. | partly | code | at-0028 | at-0028 | shown, not credited |
| T10 | Type optional parameters explicitly as `Type | None`. | no | code | – | – | not taught |
| T11 | Type function arguments explicitly. | no | code | – | – | not taught |
| T12 | Use user-friendly enum value names for storefront errors (e.g., NO_ELIGIBLE_PRODUCTS over NO_ELIGIBLE_LINES). | no | code | – | – | not taught |
| T13 | Add test coverage for all affected code paths. | yes | code | at-0038, at-0039 | – | stored, not shown |
| T14 | Changes must include a CHANGELOG entry. | yes | code | at-0004, at-0013, at-0022, at-0034, at-0044, at-0049 | at-0004 | credited |
| T15 | Rebase pull requests onto the latest target branch before merging. | no | process | – | – | not taught |
| T16 | Renumber migration files sequentially to avoid conflicts with the latest base branch. | no | code | – | – | not taught |
| T17 | Avoid merge migrations unless absolutely required; renumber migrations to keep history clean. | no | code | – | – | not taught |
| T18 | Restore DB cache only on PRs; main branch should rebuild DB from migrations and save a fresh copy. | no | ci | – | – | not taught |
| T19 | Always pass -y to apt-get install in CI to avoid interactive prompts. | no | ci | – | – | not taught |
| T20 | Tests should cover dataclass-based deferred events (e.g. VariantDiscountedPriceChange). | partly | code | at-0039 | – | stored, not shown |
| T21 | Use descriptive variable names and reuse existing helpers (e.g. is_deferrable_event, get_is_deferred_payload). | yes | code | at-0027, at-0060 | at-0027 | shown, not credited |
| T22 | Changes should be ported to maintained release branches; no changelog entry needed if the change is invisible to main users. | partly | process | – | – | taught, not provable by a diff |
| T23 | Use mocker instead of relying on fixture ordering to avoid incorrect assertions. | no | code | – | – | not taught |
| T24 | Ensure tests cover both True and False cases (parametrize) to properly assert behavior. | yes | code | at-0041, at-0047 | – | stored, not shown |
| T25 | Keep similar logic branches consistent and consider extracting a helper to avoid divergent handling. | yes | code | – | – | taught, not stored |
