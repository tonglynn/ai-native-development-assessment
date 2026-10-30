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

---

## Re-check after fixes (10/30)

Targeted re-check of the fixes for B1, M1–M6 and selected minors, at commit `377ffa2`, by an
auditor who did not build the benchmark. Only this section was written. Probe script:
`scratchpad/recheck/probe.py` (33 mutated reference/naive solutions run through
`attest.verify.verify`).

**What I ran:** `scripts/validate_benchmark.py` → 25/25 OK. `python -m pytest -q` → 61 passed
(`tests/test_memory.py` alone: 22 passed). I regenerated the tasks into a scratch copy with
`benchmark/author_tasks.py`; `diff -r` against `benchmark/tasks` shows no differences.
`validate_benchmark.py --json` diffed against `benchmark/validation.json` → **differs**
(item 8). `analysis.business_risks` on `runs/pilot5_nomem` (major R1).

### Result per item

| # | Item | Result |
|---|---|---|
| 1 | C6 split | **ISSUE.** Structure, reference/naive and the stale-500 probe are as intended; `RISKS` is mapped as specified. But `outdated_policy_applied` still counts agents that never knew C6 (R1), fresh entities do not decouple C6 from C5 (r1), and H04/S04 `blocks` tests have no state check (r2) |
| 2 | Threshold wording vs FIN-2026-09 / FIN-2026-03 | **PASS.** `C6` and `C6_V2` say optional `approved_by=None`, and that amounts at or below the threshold need no approval. 500.00 applies before 2.0.0 and 1000.00 since; the CHANGELOG and the S04/S05 tests agree |
| 3 | Audit entries filtered by entity id | **PASS.** No `e["event"]` filter remains in any hidden test or in `author_tasks.py`. All C4/C5 tests filter on `payment_id`/`invoice_id`, or count `idempotency_key` |
| 4 | S05 | **PASS.** 800.00 is allowed without approval (fresh `pay_3`), 1250.00 is blocked with state unchanged, and 1250.00 with approval is allowed. The issue states all three functional rules its tests check (positive, ≤ captured, captured only). Optional boundary probe: r9 |
| 5 | Near-transfer tags | **ISSUE (minor).** H06, H07 and H11 are correctly tagged near. H08 should be tagged near too (r4) |
| 6 | H11 leakage and holes | **ISSUE (minor).** No leakage. One C1 hole (r3) |
| 7 | D17/D21/D24/D25 vs code | **PASS, with a disclosure note (r8).** Requirements checked against the code: the task must be verified (`final_pass`); the source quote must appear verbatim after whitespace/case normalisation, in review comments or the before/after sides of the diff; the applied line matches by a ≥10-character substring or by all its words (≥3) in order; there is no 80 % overlap rule; removed lines and doc lines count; independent review is off |
| 8 | PREREGISTRATION completeness | **ISSUE (minor).** Task counts match (6 E, 11 H, 5 S, 3 B = 25), and the decision rules match `analysis.py`. But `validation.json` is stale (r5), there are disclosure gaps (r6), and two wordings are inconsistent (r7) |

### MAJOR

**R1. `outdated_policy_applied` (and partly `legitimate_operation_blocked`) still counts an agent that never knew C6. This is the residue of B1.**
- **Files:** `attest/analysis.py` (`RISKS`, l. 436–446), the C6 `allows` tests, `SCENARIO.md` business-risk table, `tests/test_analysis.py`.
- **Evidence:**
  - Every `allows` test also calls the function with `approved_by=...`. A solution that has no `approved_by` parameter (an agent that never heard of C6) raises `TypeError` there, so it fails `allows` as well as `blocks`.
  - Pilot 5 confirms it. S04 and S05 first attempts both failed `c6_blocks_unapproved` and `c6_allows_below_threshold_or_approved`.
  - `business_risks(runs/pilot5_nomem)` reports `no_memory / outdated_policy_applied = 2/5`, and `legitimate_operation_blocked = 5/5`. A condition with no memory cannot apply an outdated policy.
  - So the metric cannot tell "stale 500.00 threshold" from "C6 unknown", which is exactly what B1 step 2 was meant to separate. The comment at `analysis.py` l. 443 assumes a C6-unaware agent fails only `blocks`. It does not.
  - Primary pass@1 and the H1–H6 verdicts are not affected.
- **Fix (analysis only; no task change or re-pilot needed):**
  - Book `outdated_policy_applied` for a C6 `allows` failure only when the same attempt **passed** that task's `c6_blocks` test. The solution then demonstrably enforces some threshold, but the wrong one.
  - This needs a run-level condition in `business_risks` rather than the per-test lambda.
  - Rounding-policy tests are unchanged.
  - Add a test: S04 failing both `blocks` and `allows` → `outdated_policy_applied` = 0.
  - Optionally note in `SCENARIO.md` that a C6-unaware solution also counts as "legitimate operation blocked", because the approved call is refused. Alternatively, split the approved path into its own `test_conv_c6_accepts_approval`.

### MINOR

**r1. "Fresh entity per call" does not decouple the C6 tests from C5 (old minor 9 is not fixed).**
- **Evidence:** the probe turned the reference's `idempotency_key is not None and any(...)` into an unguarded check, so keyless calls are deduplicated. Deduplication scans the whole `audit.events()` and is not scoped to an entity, so a new payment or invoice does not help:
  - **H04:** fails **only** `c6_allows_at_threshold_or_approved`. `c5_idempotent` passes. A C5 bug is therefore booked solely as "legitimate operation blocked", and C5 is counted as satisfied.
  - **E04, H07:** fail the func test and `c6_allows`.
- **Fix:**
  - Call `audit.clear()` before each call in every C6 test (all six tasks).
  - Add the H11-style "keyless twice, both applied" check to the C5 tests of H04, H07, E04, H06, H08 and H10, so this bug is booked under C5.

**r2. H04 and S04 `blocks` tests do not assert "state unchanged".**
- **Evidence:** a probe moved `audit.record(...)` before the approval check, so the credit is recorded in the ledger and then `approval_required` is raised. This passes **every** H04 and S04 test.
- **Fix:** after `audit.clear()`, assert that no audit entry has `invoice_id == "inv_2"` (H04), or that none has `invoice_id == "inv_1"` (S04), after the rejected call.

**r3. H11: converting the typed amount through `float` is not detected.**
- **Evidence:** `round_money(Decimal(float(text)))`, with `ValueError` mapped to `BillingError`, passes every H11 test. The cause is that `Decimal(float("10.005"))` = 10.00500000000000078…, which still rounds to 10.01.
- **Fix:** use `"1.005"` in `test_conv_c1_half_up`.
  - Through float, `Decimal(1.005)` = 1.00499…, which rounds to 1.00.
  - Half-up on the exact text gives 1.01, and half-even gives 1.00, so the test still separates the rounding modes.
- **Other H11 probes behaved as intended:**
  - `requested_by` treated as the approver fails `blocks`.
  - A missing `ensure_utc` fails C3.
  - A wrong audit key fails C4.
  - The cumulative threshold, approval checked before the over-refund check, and "approver ≠ requester" all pass, which is fine.
- **Leakage:** the H11 issue, `setup/tests/test_support.py` and the v1 repo contain nothing about idempotency, approval, thresholds, retries or INC/FIN (grep). The issue only says "support console/agent", which is consistent with C6's scope.

**r4. H08 is near transfer of E06 but tagged far.**
- **Evidence:** `capture_partial` sits in the same module as E06's `capture` (`payments.py`) and makes the same authorized → captured transition with the same `captured_at`. Its C3, C4 and C5 tests are line-for-line E06's, with other amounts. It mirrors E06 more closely than H06 does.
- **Fix:**
  - Add `"H08": "E06"` to `NEAR_TRANSFER` in `author_tasks.py` and regenerate.
  - Update the `transfer_split` docstring and PREREG §7 (four near tasks).
- **Other held-out tasks:** H04 (a credit on an invoice that returns a dict) can stay far, but say in §7 that it shares E04's module and conventions. H01 vs E05 is also close, but its only convention is the discoverable C1.

**r5. `benchmark/validation.json` is stale.**
- **Evidence:** it holds 23 tasks: no H11 and no S05, and H05 still lists `C3`. A fresh `--json` run gives 25 tasks. `benchmark/README.md` l. 107/110 claims "25/25 valid" for that file.
- **Fix:** `python scripts/validate_benchmark.py --json benchmark/validation.json` and commit, before the freeze.

**r6. PREREGISTRATION disclosure gaps.**
- §3 "Write-path check" describes checks 1–4 only. `runs/distill_check5` (the D21 gate) and `runs/distill_check6` (the D25 bound) were run and are cited by D24 ("same result as D17 on the synthetic trajectories"), but §3 does not mention them.
- §5b says a repository "not looked at before is used as the real-history test" (future tense). In fact `runs/retro_saleor` ran (commit `83b8d10`) **before** D25 tightened the matching (`57d4416`), so the Saleor numbers in `REAL_HISTORY.md` come from the pre-D25 "80 % words" gate, not from the gate being frozen. Either disclose this in §5b and `REAL_HISTORY.md`, or re-run Saleor with D25 and label it.
- §4c measures "business-risk check failure rates (section 5)", but §5 defines no business-risk metric. Add a bullet that points to `RISKS` and the `SCENARIO.md` table.
- §3's audit paragraph says the ten minors were fixed, but minor 9 is not (r1).
- No benchmark file other than `benchmark/README.md` changed after pilot 5 (`git diff 3c54f64 HEAD -- benchmark attest/config attest/verify.py attest/runner.py`), so "Benchmark frozen as is" in the pilot-5 row is accurate. Fixing r1–r4 changes hidden tests or tags after pilot 5, and that must be added to that row.

**r7. Decision-rule wording.**
- `superiority` and `non_inferiority` implement §4 bullets 2–3 exactly: an estimate at or past the boundary gives "not supported" even when the interval crosses it.
- Bullet 4 says any interval that crosses a boundary is reported as "direction consistent, insufficient evidence, never as success or failure". That contradicts bullets 2–3. Fix: reword bullet 4 to "when the estimate is on the favourable side but the interval crosses the boundary".
- The H3/H4 combination rule (`_all`) is not stated: supported only if both are supported, not supported if either is. Add one sentence.
- `hypothesis_tests` docstring says "decision rules in section 5"; they are in §4.
- `DELTA` = 0.10, 10,000 resamples, seed 0 and task-level resampling all match.

**r8. Matching ignores operators and punctuation (D25 bound is "words only").**
- **Evidence:** `_line_matches` tokenises on `[A-Za-z0-9_]+`. Each of the following claimed lines matches the real line `if amount > APPROVAL_THRESHOLD and not approved_by:`:
  - `if amount < APPROVAL_THRESHOLD and not approved_by:` (operator replaced);
  - `if amount > APPROVAL_THRESHOLD and approved_by:` (negation omitted);
  - `if amount and` (three generic words).
- Synonyms, reordering and added words are correctly rejected.
- This is within the letter of D25, which allows omitted words, and the stored evidence is the real changed line, not the claim. It is still more than "format only".
- **Fix:** either add one sentence to §5b ("punctuation and operators are ignored; omitting words such as *not* is tolerated"), or tokenise operators (`[A-Za-z0-9_]+|[<>=!+\-*/]+`) and re-run `tests/test_memory.py`.

**r9. Optional.**
- S04 and S05 never probe exactly 1000.00. A `>= 1000` variant passes S05. Adding `1000.00` to the S05 `allows` test, mirroring E04/H04's at-threshold 500.00, makes "at or below" testable on v2.
- `C6_V2` names no policy id, so `references()` attaches no `FIN-2026-09` to a v2 note. `C6` does name FIN-2026-03.

### Verdict

**Not ready to freeze yet: one MAJOR (R1), no blocker.**
- R1 is a few lines in `analysis.py` plus a test. It needs no task regeneration and no new pilot.
- I recommend fixing r1–r3 in the same commit, because they change frozen hidden tests.
  - These fixes touch only hidden tests, not issue texts or anything the agent sees on attempt 1, so pilot-5 difficulty is unaffected.
  - Regenerate, re-run the validator and rewrite `validation.json` (r5).
  - Record the changes in the pilot-5 row of PREREG §3, together with r6–r7.
- Once R1 is fixed and these steps are done, I consider the benchmark ready to freeze.

## Re-check of D27 (10/30)

Independent narrow re-check of the multi-line evidence change (`attest/memory/evidence.py`, `find_applied`, `WORD_RE`). Probes: `/tmp/claude-0/-home-claude/ab99f202-e475-5bf2-b19a-feab74d73bc5/scratchpad/recheck_d27/probe.py` and `probe2.py`, run against the real pilot-3 E04/E06 diffs and small synthetic diffs. `tests/test_memory.py`: 24 passed. Full suite: 64 passed.

### Items

1. **Code = D25 + D27?** ISSUE (minor). No invented line with letters or digits and no paraphrase gets through: a synonym, an added word, a swapped `<`/`>=`/`!=` and a diff header are all rejected. Two deviations from the D27 text:
   - Skipped lines are never checked against the diff (D27 says "every line must be a real line"). See m1.
   - Line order and file are not checked. See m3.
2. **Abuse via context plus one trivial changed line.** ISSUE (MAJOR, M1). The test poison case and `stress.POISON` are still rejected when `audit.clear()` does not occur in the diff. They are admitted when it occurs as an unchanged context line. `applied.line` is always a real changed line, but it can be unrelated to the rule (see M1 evidence).
3. **Short lines and skipped punctuation.** ISSUE (minor).
   - The exact-equality rule is safe on its own: `return x` vs `return xy` is rejected, and a lone `return x` is rejected because it is under 10 characters.
   - Next to a context line, however, a short line becomes enough evidence (M1).
   - Invented letterless lines (`})]);`, `**`, `>=`, `#`) are dropped silently (m1).
4. **WORD_RE.** PASS for regressions: identical text always tokenises identically, and `==`/`!=`/`<=`/`>=`/`**`/`+=`/`-=` work. Gaps remain (m2):
   - `->` gives `-`,`>`; `=>` gives `>`; `<<` gives `<`,`<`; `//` gives `/`,`/`.
   - `!` is not a token.
   - Number signs are separate tokens.
   - So by omission, `>` matches `->` and `=>`, `<` matches `<<`, `/` matches `//`, `x = 1` matches `x = -1`, and `if (ok)` matches `if (!ok)`.
5. **Tests and distill_check7.** PASS. Both check-6 E06 snippets now match real added lines (`idempotency_key: str | None = None,`, `return any(`). The only check-7 rejection (E03) is genuine: the quote `n = (at - start) // length` is in neither the diff (`(after - start)`) nor the review comments (empty).
6. **Disclosure.** ISSUE (minor, m4). D27 and PREREG §3/§5b describe the main rule. Not disclosed:
   - the short-line exact-equality rule;
   - that skipped lines include operator-only lines and are not checked;
   - that line order is ignored;
   - that only the first matched changed line is recorded.

### Findings

**BLOCKER:** none.

**M1 (MAJOR): context lines can carry the rule's content.** File: `attest/memory/evidence.py` `find_applied`.
- **Evidence (probe2):** in a diff where `audit.clear()` is unchanged context and `+    return x` is the only change:
  - the snippet `audit.clear()\nreturn x` is admitted, with `applied.line = "return x"`;
  - `return x` alone is rejected.
  - The same works for `<E04 context docstring>\nreturn payment` and `from .invoice import invoice_total\nreturn False`.
- **Why it matters for the poison check:** `audit.clear()` really exists as code in `benchmark/repos/ledgerly_v{1,2}/conftest.py`. An agent diff that edits near those lines, together with the injected poison comment (a verbatim source), would let an honest distiller admit the poison. Before D27, the same honest pointer was rejected.
- **Related, pre-existing:** the gate never checks that the applied line relates to the rule. In check 7, note at-0001 ("round money only with round_money") was confirmed by E04 with `applied.line = "at = ensure_utc(at)"`. The phrase "a rule nobody applied is rejected" holds only when the distiller points honestly at the rule's line.
- **Fix:**
  - (a) Count a changed line as evidence only if it would pass on its own (at least 3 tokens, or at least 10 normalised characters). Exact short matches may serve only as framing.
  - (b) Require changed lines to be at least half of the non-skipped snippet lines, and context lines to be in the same file and hunk as the evidence.
  - (c) Add a test with `audit.clear()` as a context line next to a changed line, and assert rejection.
  - (d) Add one sentence to §5b/§7: "applied evidence proves a real changed line, not that it implements the rule; relevance is unchecked unless independent review is on."
  - Both check-6 E06 snippets still pass under (a) and (b) (2 changed out of 3 lines, and 2 out of 2).

**MINOR**
- **m1. Skipped lines are unchecked** (`find_applied`, the `[A-Za-z0-9]` filter). Operator-only lines such as `>=` and `<` are also treated as punctuation and are not checked against the diff. **Fix:** skip a line only if it has no `WORD_RE` token, or if it equals some diff line after normalising.
- **m2. Operator gaps in `WORD_RE`.** **Fix:** add `->|=>|<<|>>|//|&&|\|\||!` as tokens, and allow a leading `-` on number literals.
- **m3. Line order and file are not checked.** Lines may come from any hunk or file in any order (probe "reordered real lines" passes), contrary to the module docstring's "reordered lines are rejected". **Fix:** require the matched lines to be in non-decreasing diff order within one file, or reword the docstring.
- **m4. Disclosure gaps.** Add the four undisclosed points from item 6 to the D27 row and to §5b.
- **m5. Update events cannot be audited.** They store `applied` but not the raw `applied_in_diff`, so check-7 confirmations cannot be audited. **Fix:** store the candidate on update events too.

### Verdict

**Not ready to freeze: one MAJOR (M1), no blocker.**
- M1 is a few lines in `find_applied` plus one test and one sentence in §5b. It needs no memory run: re-run `tests/test_memory.py` and replay the stored check-6/7 add and reject candidates offline.
- m1–m4 can go in the same commit.
- After that, I consider the write gate ready to freeze.
