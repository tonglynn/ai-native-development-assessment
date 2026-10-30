# Benchmark audit (pre-freeze)

Independent audit of `benchmark/` (tasks E01–E06, H01–H10, S01–S04, B01–B03), the
risk mapping in `attest/analysis.py`, and two planned changes: the H11 draft
(`scratchpad/h11_draft.py`) and splitting each C6 hidden test into
`test_conv_c6_blocks_*` / `test_conv_c6_allows_*`. Audited at commit `6222bb9`. The
only file written is this report.

## Summary

The benchmark is mechanically correct. Every reference solution passes, every naive
solution and stub fails as intended (23/23), and the committed tasks are byte-identical
to a fresh run of `author_tasks.py`. The review-only conventions C5 and C6 do not leak
into ledgerly 1.0.0.

The real problems are in measurement and wording:

- **Blocker:** the C6 business-risk metrics are wrong. The planned split is necessary
  but does not fix them alone.
- **Wording:** some review comments are worded loosely, or more loosely than their own
  source documents.
- **Incidental couplings:** some tests fail for reasons unrelated to the convention
  they score.
- **Weak stale tier:** S01–S03 cannot detect stale memory, so H3 rests almost entirely
  on S04.
- **Near-copies:** held-out C6 evidence comes from near-copies of E04 that use the same
  amounts.

All of these can be fixed in `author_tasks.py`, `analysis.py` and the docs, without
redesigning the benchmark.

## What I ran

| Check | Command / method | Result |
|---|---|---|
| Validator | `venv/bin/python scripts/validate_benchmark.py` | 23/23 OK |
| Regeneration in sync | copied `git ls-files` to a scratch dir, ran `benchmark/author_tasks.py <copy>`, `diff -r benchmark <copy>/benchmark` | no differences (tasks and repos) |
| `validation.json` current | validator `--json` to scratch, diffed with the committed file | identical |
| Test names vs metadata | for each task, set of `test_conv_<id>` ids == `task.json.conventions`; every test has a docstring | consistent for all 23 |
| Leakage | `grep -rniE "idempot|approv|threshold|INC-204|FIN-2026|500\.00|retr|duplicate"` over `benchmark/repos`, all `task.json` issues, `attest/config/agent.yaml` | only hit: `ledgerly_v2/CHANGELOG.md` (FIN-2026-07, FIN-2026-09) |
| v1 vs v2 | `diff -r ledgerly_v1 ledgerly_v2` | only `__version__`, `round_money` rounding mode, CHANGELOG |
| Pilot outcomes | read `runs/pilot{,2,3,4}_nomem/**/result.json` | see M3, M4 |
| Planned changes | applied the H11 draft and a C6 split to the scratch copy, regenerated, re-ran the validator and `tests/test_analysis.py` | 24/24 OK; `test_business_risks_from_failed_test_names` fails (see B1) |
| Robustness probes | 19 mutated reference solutions run through `attest.verify.verify` (script: `scratchpad/audit/variants.py`) | table below |

Robustness probes. Each is a mutated reference solution; the right-hand column lists the hidden tests it fails, or "public" when the public tests also fail:

| Task | Mutation of the reference | Fails |
|---|---|---|
| E04, H07 | `approved_by` keyword-only **without default** | public + every hidden test |
| H04, H10 | C5 retry returns `None` | `test_conv_c5_idempotent` |
| H10 | C5 retry rebuilds the dict from the arguments | nothing (passes) |
| E06 | idempotency key checked **after** the state check | `test_conv_c5_idempotent` |
| H08 | rejects amounts with >2 decimals instead of rounding | `test_conv_c1_rounded_cents` |
| H04 | audit event named `invoice_adjusted` | `test_conv_c4_audit_entry` **and** `test_conv_c5_idempotent` |
| H04 | audit field `credit_note_id` instead of `invoice_id` | `test_conv_c4_audit_entry` |
| S04 | no "invoice must be issued" check | `test_conv_c2_billing_error` only |
| E04 / H11 | `None` key deduplicates keyless calls | func test (+ `c6_allows` in E04 after split; `c5` in H11) |
| E04 | C6 on cumulative refunded total | nothing (passes; fine) |
| E04 | C6 inclusive (`>=` 500) | `c6_allows` |
| E04 | approval checked after mutating state | `c6_blocks` (with the state assertion) |
| S04 | stale 500.00 threshold | `c6_allows` only (after split) |
| S01 | hand-written `ROUND_HALF_EVEN` instead of `round_money` | nothing (passes) |
| H05 | no `ensure_utc` (relies on `current_period`) | nothing (passes) |
| H06 | audit entry without `amount` | nothing (passes) |

---

## BLOCKER

### B1. C6 business-risk metrics are wrong and one promised metric is never computed
- **Tasks:** E04, H04, H07, S04 (and H11 once added)
- **Files:** `attest/analysis.py` (`RISKS`), `SCENARIO.md` (business risk table), `tests/test_analysis.py`
- **Evidence:**
  - All four C6 tests are single tests named `test_conv_c6_approval` or
    `test_conv_c6_approval_threshold`.
  - `legitimate_operation_blocked` matches `test_conv_c6_allows*`, which does not
    exist, so that risk never appears in any report. Yet `SCENARIO.md` lists it, with
    "700.00 under the 2.0.0 threshold" as its example.
  - Worse, the combined test is counted as `unauthorised_operation`. In S04, an agent
    using the stale 500.00 threshold fails because it *blocks* 700.00, so that failure
    is booked as "an over-threshold operation went through without approval", which is
    the opposite of what happened.
  - `outdated_policy_applied` counts any S04 C6 failure. This includes a no-memory
    agent that never heard of C6 (pilot 3: S04 failed C6 on the first attempt with no
    memory at all), which is a missing rule, not an outdated one.
- **Fix:**
  1. Apply the planned split (verified: validator stays green, and the stale-500 naive
     solution for S04 now fails only the `allows` test).
  2. Change `outdated_policy_applied` to
     `task.startswith("S") and ("rounding_policy" in test or test.startswith("test_conv_c6_allows"))`.
     Only the allows check can show a stale threshold; a `blocks` failure in S04 means
     "C6 unknown".
  3. Update `tests/test_analysis.py::test_business_risks_from_failed_test_names`. It
     uses `test_conv_c6_approval` and fails after the split (verified).
  4. See the split review below for how to arrange the two tests.

---

## MAJOR

### M1. The C6 review comment repeats the "required parameter" ambiguity that broke H06 in pilot 3
- **Tasks:** E04, H04, H07, S04 (C6 and C6_V2 text)
- **File:** `benchmark/author_tasks.py` (constants `C6`, `C6_V2`)
- **Evidence:**
  - The comment says "accept a keyword-only `approved_by`". It does not say optional,
    does not give a default, and does not say that amounts at or below the threshold
    need no approval.
  - The source decision `scenario/history/FIN-2026-03-support-refund-approval.md`
    says "optional keyword-only `approved_by`" and "Amounts at or below 500.00 need no
    approval". The comment is weaker than its own source.
  - Pilot 3 showed this exact failure for C5 (H06 failed even after review). The C5
    text was fixed; the C6 text was not.
  - Probe: a required `approved_by` fails the public test and every hidden test (E04,
    H07).
  - This text is what memory systems learn from E04, so it must be final before the
    freeze.
- **Fix:** Reword to: "accept an optional keyword-only `approved_by=None` (callers that
  do not need approval keep working); amounts at or below 500.00 need no approval;
  above it, raise `BillingError("approval_required")` when `approved_by` is missing".
  Make the same change to `C6_V2` with 1000.00.

### M2. C4 and C5 tests select audit entries by event-name substring, which couples them to a choice no comment specifies
- **Tasks:** E04, E06, H04, H06 (C4 and C5); S04 (C4); H11 draft (C4 and C5)
- **File:** `benchmark/author_tasks.py` (hidden tests)
- **Evidence:**
  - C4 says only `audit.record("<past_tense_event>", ...)`. The event name is free.
  - Yet E04 filters on `"refund" in e["event"]`, E06 on `"captur"`, H06 on `"void"`,
    H04 on `"credit"`, and S04 on `"credit"` or `"goodwill"`.
  - Probe: H04 with the event `invoice_adjusted`, a sensible past-tense name, fails C4
    **and** C5. So one naming choice registers as a duplicate-money-operation risk.
  - H07, H08 and H10 already filter by entity id, which is robust.
- **Fix:**
  - Filter by entity id everywhere (`e.get("payment_id") == "pay_1"` or
    `e.get("invoice_id") == "inv_1"`).
  - In C5 tests, additionally assert
    `sum(e.get("idempotency_key") == key for e in audit.events()) == 1`.

### M3. S01–S03 cannot detect stale memory, so H3 rests on S04 alone
- **Tasks:** S01, S02, S03
- **Files:** task definitions, `PREREGISTRATION.md` section 4 (H3)
- **Evidence:**
  - The v1 review comment `C1_ROUND` teaches "round only with `round_money`".
  - In v2, `round_money` itself switched to half-even. So an agent that follows the
    v1 lesson passes S01–S03 automatically, without noticing anything.
  - The tests fail only if an agent hand-codes `ROUND_HALF_UP`. No pilot agent did:
    S01–S03 passed on the first attempt in all four pilots.
  - The probe also shows that a hand-coded `ROUND_HALF_EVEN` passes, because the tests
    check outcomes. That is reasonable, but it confirms the tests only measure "did not
    hard-code half-up".
  - Only S04 (a literal threshold that memory carries) can show "outdated experience
    hurts". With 1 task × 3 repetitions, H3's pooled S pass@1 is dominated by three
    tasks at ceiling.
- **Fix:** Before freezing, do one of the following:
  - **(a)** Add a second threshold-dependent stale task. For example, an S05 refund on
    a captured payment in `adjustments.py`, where 800.00 must be allowed without
    approval and 1200.00 blocked. Also state in README/PREREG that S01–S03 are "no
    false recall" sanity checks.
  - **(b)** Preregister H3 as reported separately for S04 (with S01–S03 as a secondary
    pooled number).

  Doing both is better.

### M4. Held-out C5/C6 evidence comes from near-copies of experience tasks, with the same numbers
- **Tasks:** H07 vs E04, H06 vs E06, H11 (draft) vs E04; H04 vs E04 to a lesser degree
- **Files:** `benchmark/author_tasks.py`, `benchmark/README.md`, `PREREGISTRATION.md` section 7
- **Evidence:**
  - H07 `refund_shipping` is E04 `refund` under another name. Same module, same
    rules, same payment shape, same C5 test, and an identical C6 test (2000.00 payment;
    500.00 allowed; 600.00 blocked; 600.00 approved; total 1100.00).
  - H04 reuses 500/600 as well. H06 `void` mirrors E06 `capture` line for line.
  - The H11 draft again uses 2000/600/500 on a captured payment.
  - "Same conventions, different functions" is technically true. But the held-out
    gain on review-only tasks measures near-transfer, and a note that only recorded
    "600 needs approval, 500 doesn't" would pass every C6 check.
- **Fix:**
  - Vary the C6 boundary probes per task: for example 500.01 blocked and 500.00
    allowed in H04; 750.00 blocked and 499.99 allowed in H07; and different payment
    sizes.
  - Tag tasks `near` (H06, H07, H11) or `far` in `task.json`, and report the held-out
    result split by that tag (exploratory).
  - Add one sentence to Threats to validity.

### M5. S04's C2 test enforces a functional rule that the S04 issue never states
- **Task:** S04
- **File:** `benchmark/author_tasks.py` (S04 issue and hidden test)
- **Evidence:**
  - `test_conv_c2_billing_error` includes a draft invoice and expects `BillingError`.
  - The S04 issue says only "credits `amount` against an issued invoice … amount must
    be positive and must not exceed the invoice total". It never says to reject
    non-issued invoices (H04's issue does).
  - S04 has no `test_func_rejects_*`.
  - Probe: dropping the status check fails only `test_conv_c2_billing_error`. A
    missing functional requirement is therefore scored as a C2 ("misclassified
    failure") violation, and in the stale group.
- **Fix:**
  - Add "Only issued invoices can be credited." to the S04 issue.
  - Add a `test_func_rejects_invalid` with the same three cases, so C2 measures only
    the exception type.

### M6. H11 and the split are changes after pilot 4, which PREREGISTRATION says froze the benchmark "as is"
- **Files:** `PREREGISTRATION.md` sections 2 and 3, `benchmark/README.md`, `SCENARIO.md`, `benchmark/validation.json`
- **Evidence:**
  - Section 3's pilot-4 row says "None. Benchmark frozen as is".
  - Section 2 says 10 held-out tasks. The README coverage table and "23/23" do not
    include H11.
  - `SCENARIO.md` already refers to "the end-to-end refund-request task", which does
    not exist yet.
  - H11 has never been piloted, so its difficulty is unknown, although pilots are
    precisely the tool reserved for difficulty checks.
- **Fix:**
  - Run a no-memory pilot of H11 only (as pilot 4 did for H07–H10).
  - Add a pilot row to section 3 describing H11 and the C6 split.
  - Set section 2 to 11 held-out tasks, and update the README coverage table (C1–C6
    add H11), the counts and `validation.json`.
  - Do all of this in the commit before the freeze commit.

---

## MINOR

1. **C5 comment does not say what a retry returns, or when the key is checked** (H04,
   H10, E06, H06; `C5` constant).
   - H04 and H10 assert `again == first`. Returning `None` fails, while rebuilding the
     dict from the arguments passes (probes).
   - E06, H06 and H10 retry after the state has already changed, so checking the key
     after the state validation fails (probe).
   - The comment only says "return without applying the operation again".
   - Fix: append "Check the key first, before validating state, and return the
     original result (for functions that return a record, the same record)." The same
     wording is in the INC-204 template, so update that too.
2. **"Support-initiated" qualifier in C6** (E04, H04, H07).
   - None of these issues says the operation is support-initiated. Only the
     `adjustments.py` module docstring ("made by the support team") implies it; S04
     and H11 say it explicitly.
   - A faithful memory note could reasonably skip C6 for a shipping refund.
   - Fix: add "used by the support team" to the E04, H04 and H07 issues, or drop the
     qualifier from the comment.
3. **H08 C1 test requires rounding a 3-decimal input** (`33.335` → `33.34`).
   - The issue never says inputs can have more than two decimals.
   - Rejecting such input with `BillingError` is also a defensible reading of C1
     ("exactly two decimal places"), and it fails (probe).
   - Fix: add the sentence H11 uses ("amounts with more than two decimals are rounded
     to the cent").
4. **C4 entity field for credits** (H04, S04).
   - The tests require `invoice_id`. An agent could reasonably write `credit_note_id`
     (probe fails).
   - It is inferable from the returned dict.
   - Fix: C4 text "…`<entity>_id` of the payment or invoice the money moves against".
5. **Listed conventions that cannot discriminate.**
   - H05's C3 is satisfied by any solution that calls `current_period`, which already
     calls `ensure_utc`. The naive solution passes it, and so does the probe without
     `ensure_utc`. This inflates C3 hit rates in `convention_hits`.
   - Fix: drop C3 from H05, or test a path that does not go through `current_period`.
   - Optionally make the validator report, per task, which listed conventions the
     naive solution passes, so this is visible.
6. **C5 scope wording vs coverage.**
   - H10 (write-off) is tested for C5 although the comment's scope is "moves money or
     changes a payment/credit".
   - S04 (a goodwill *credit*) falls under that scope but is not tested for C5.
   - Fix: widen the wording ("…or an invoice balance") and either list C5 in S04 or
     note why not.
7. **H06 C4 does not check `amount`**, while E06 and H08 do. Harmless, but
   inconsistent; align it.
8. **README is stale on legacy placement.**
   - It says "Seven tasks" go into legacy modules. Actually ten do: E03, E04, E05,
     H01, H02, H03, H04, H07, H10 and S04.
   - Fix the README task list.
9. **Split tests should not depend on C5 behaviour.**
   - In the split `allows` test, two keyless calls on one payment mean that a
     `None`-key dedup bug shows up as `legitimate_operation_blocked` (probe on E04).
   - Fix: use a fresh payment or invoice per call in C6 tests.
10. **`restore_tests` resets only `tests/` and `conftest.py`.**
    - A test file the agent leaves elsewhere (for example `test_tmp.py` at the root)
      still runs in the public suite and can fail the attempt.
    - Fix: delete `test_*.py` outside `tests/` before verifying, or run pytest on
      `tests/` only.

---

## Review of the planned changes

### C6 split (E04, H04, H07, S04)

The split is sound and needed (B1). In a scratch copy it kept the validator at 24/24,
and the stale-500 naive S04 solution then fails only the `allows` test, which is the
point of the split. `verify.conv_failed` aggregates by convention, so pass/fail,
`convention_hits` and the tier split are unchanged; only `RISKS` changes. Arrange the
tests as follows:

- **`test_conv_c6_blocks_unapproved`:** over-threshold without `approved_by` raises
  `BillingError`, and the state is unchanged (`refunded_amount` unchanged or no audit
  entry). Nothing else.
- **`test_conv_c6_allows_*`:** at or below the threshold succeeds without approval
  (500.00 in v1; 700.00 in S04), and over-threshold *with* `approved_by` succeeds. The
  approved path belongs here. If it sits in `blocks`, a solution that does not accept
  `approved_by` at all is booked as "unauthorised".
- Use a fresh entity per call (minor 9), and vary the amounts per task (M4).
- Then apply the `RISKS` and `tests/test_analysis.py` changes from B1.

### H11 draft (`h11_draft.py`)

The draft is sound as a task. In the scratch copy the reference passes everything; the
naive solution passes the public and functional tests and fails C1 (half-up via a bare
`quantize`), C2 (`"ten"` raises `InvalidOperation`), C3, C4, C5 and C6. The
issue states the rounding rule explicitly, which is better than H08. The C5 check that
"callers without a key keep working … every time" is a good addition: it catches the
`None`-key dedup bug (probe). Change the following:

1. Move `process_refund_request(big, "600.00", ..., approved_by=...)` out of
   `test_conv_c6_blocks_unapproved` into `test_conv_c6_allows_*`. Rename that test
   `test_conv_c6_allows_at_threshold_or_approved` for symmetry with the other tasks.
2. Do not reuse E04's numbers (2000/600/500). For example: payment 1200.00; 500.01
   blocked; 500.00 allowed; 700.00 with approval (M4). Mark H11 as `near` transfer.
3. Filter C4 and C5 audit entries by `payment_id`, not by `"refund" in e["event"]` (M2).
4. `requested_by` is never checked. That is fine, but do not add a "second approver
   differs from the requester" check later unless the C6 comment says so.
5. Pilot it without memory and update the docs before the freeze (M6).

---

## Checked and found fine

- **Correctness.** Every reference passes its public and hidden tests. Every stub fails
  behaviour tests. Every naive solution passes public and behaviour tests and fails at
  least one convention (control naives are allowed to fail behaviour tests). The
  committed tasks and repos match regeneration exactly, and `validation.json` is
  current.
- **No C5/C6 leakage in v1.** There is nothing about idempotency, retries, approval or
  thresholds in v1 code, tests, README, CHANGELOG, issues or the agent prompt. In v2,
  the CHANGELOG states the threshold change (intended for S04) but neither the
  parameter name nor the error code. S04 is therefore partly discoverable for a
  no-memory agent, which is consistent with its role.
- **Rounding values discriminate the modes.** Half-up vs half-even:
  - E01 0.025 → 0.03; E05 0.125 → 0.13; H01 and H05 0.465 → 0.47; H08 33.335 → 33.34.
  - S01 0.445 → 0.44; S02 1.025 → 1.02; S03 0.125 → 0.12.
  - The expected Decimal values are exact. The simkit float checks use `close()` on
    already-rounded values, so there is no flakiness.
- **Lenient checks.**
  - Error codes are never asserted. Every C2 and C6 check accepts any `BillingError`,
    so the codes in the comments are examples, not requirements.
  - C6 passes under a per-operation or a cumulative reading of "above 500.00".
- **Comment and test agreement.** Apart from the items above, each test checks what
  its docstring says. C1_TYPE asks for "exactly two decimals" and the tests check
  exponent −2. C3 asks for "rejects naive, normalises to UTC" and the tests check
  `BillingError` plus `utcoffset() == 0`.
- **Isolation.** The hidden runner resets the audit log between tests. Workspaces live
  outside the project, and `LEAK_PATTERNS` covers the project root and task files.
- **Control tasks.** B01–B03 have opposite, internally consistent conventions. Their
  naive solutions are realistic "ledgerly habits".

## Overall verdict

The benchmark is mechanically trustworthy. It builds reproducibly, every reference
solution passes, every naive solution fails, and there is no C5/C6 leakage in v1. It
is close to ready.

It should not be frozen yet. B1 means the preregistered business-risk table would
misreport the stale-threshold failure as an unauthorised operation, and would never
report wrongly blocked operations. The majors are cheap text and test edits:

- the C6 wording, which is learned verbatim by the memory systems and so cannot change
  after the freeze;
- entity-based audit filtering;
- the S04 issue sentence;
- varying the C6 amounts;
- one more threshold-dependent stale task, or an S04-specific H3 report;
- disclosing H11 and the split, with a quick H11 pilot.

Once these are applied, regenerated, re-validated and recorded in PREREGISTRATION
section 3, I consider the benchmark ready to freeze. Its remaining limitations
(author-designed tasks, simulated review, near-transfer held-out tasks) are then
honestly disclosed rather than hidden in the numbers.
