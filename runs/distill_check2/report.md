# Write-path check (before freeze)

Source trajectories: `runs/pilot3_nomem` (no memory).

## reasoningbank

### E01 (first attempt failed)
- ADD `rb-0001` Use project money helpers for rounding: Python's round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals. Always import and call ledgerly.money.round_money (half-up to the cent) on any computed money value before returning it.
- ADD `rb-0002` Read existing module conventions before implementing: Before writing a new function, read the surrounding file (e.g. line_total, invoice_total) and ledgerly/money.py. Reuse ZERO, to_money, and round_money exactly as existing functions do, so the new code matches team conventions and passes hidden tests.
- ADD `rb-0003` Guard division by zero explicitly: Compute total_quantity first; if it is falsy, return ZERO. Otherwise sum quantity*unit_price with a ZERO start value and divide, then round the result with round_money.

### E02 (first attempt passed)
- ADD `rb-0004` Match existing error and validation conventions before implementing: Before writing a new function, grep for similar validation in the repo (e.g. `invalid_state`, `negative_amount`) and mirror those error codes and message formats. Reusing `to_money`/`ZERO` from the money module keeps price handling consistent.
- ADD `rb-0005` Guard bool when validating integer inputs in Python: When requiring a positive integer, write `isinstance(x, bool) or not isinstance(x, int) or x <= 0`. This rejects True/False and floats while accepting genuine ints.
- ADD `rb-0006` Verify edge cases with a manual script after tests pass: After the test suite passes, run a short script probing boundary and type-confusion inputs (0, -1, 1.5, True, non-numeric strings, wrong status) and print the resulting error codes. This catches gaps hidden tests may target.

### E03 (first attempt passed)
- ADD `rb-0007` Reuse existing period-arithmetic helpers: Before writing renewal/period logic, grep the codebase for similar functions (e.g. current_period) and reuse their exact pattern: normalize inputs with ensure_utc, compute length = timedelta(days=period_days), and use floor division (at - start) // length. This keeps semantics consistent and avoids subtle off-by-one bugs.
- ADD `rb-0008` Handle the before-start edge case explicitly: Floor division on negative timedeltas can yield surprising results. When after < start, return start + length directly rather than relying on (after - start) // length, which would otherwise produce a negative n and an incorrect renewal.
- ADD `rb-0009` Normalize datetimes via the project's ensure_utc: The project's ensure_utc raises BillingError for naive or non-datetime inputs and converts to UTC. Calling it on both `after` and `sub.started_at` gives consistent validation and comparison behavior, matching how other modules (subscriptions.py) handle inputs.

### E04 (first attempt failed)
- ADD `rb-0010` Check repo conventions before implementing money operations: Before writing a money-moving function, grep the repo for existing audit/approval patterns and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency_key and approval thresholds are often documented outside the issue.
- ADD `rb-0011` Make retryable operations idempotent via audit lookup: Implement a helper that scans audit.events() for a matching idempotency_key and returns early (returning the payment unchanged) if found. Always include idempotency_key in the audit entry you write so future retries can detect it.
- ADD `rb-0012` Enforce approval thresholds for large refunds: Define APPROVAL_THRESHOLD = round_money("500.00") and check amount > threshold before applying. Validate state, amount positivity, and cumulative refunded_amount <= payment.amount, then update refunded_amount and set status to "refunded" on full refund.

### E05 (first attempt passed)
- ADD `rb-0013` Reuse existing money helpers for Decimal-safe arithmetic: Inspect ledgerly/money.py and sibling modules (invoice.py, payments.py) first; they define to_money, round_money, and BillingError conventions. Building add_tax on those helpers gives consistent rounding and error types for free.
- ADD `rb-0014` Validate rate inputs before arithmetic, including non-finite values: Wrap Decimal conversion in try/except (InvalidOperation, ValueError) and check rate.is_finite() plus 0 <= rate <= 100, raising the project's BillingError with a stable code. This prevents silent NaN propagation and matches hidden-test expectations for invalid input.
- ADD `rb-0015` Smoke-test edge cases manually before submitting: The visible test only checked one case; manually calling add_tax with string amounts, 100% rate, and out-of-range rates surfaced a traceback that guided the final robust implementation. Always probe boundaries (0, 100, negatives, non-numeric) before declaring done.

### E06 (first attempt failed)
- ADD `rb-0016` Check repo conventions before implementing money operations: Before implementing any payment/credit mutation, search the repo (CHANGELOG, README, existing functions, audit module) for conventions like idempotency keys, audit logging, or state guards. Apply them proactively rather than only satisfying the literal issue text.
- ADD `rb-0017` Implement idempotency via audit-event lookup: Add a helper like `_already_applied(key)` that scans `audit.events()` for an entry with the same `idempotency_key`. Guard the operation with it, and always include `idempotency_key` in the audit entry you write so future calls can detect duplicates.
- ADD `rb-0018` Mirror existing function signatures when extending APIs: When a convention applies to a class of operations, update all related functions (e.g., both authorize and capture) with the same keyword-only parameter and default, so callers and tests see uniform behavior.

### Shown for H04

```
Memory items from past tasks:
- [rb-0016] Check repo conventions before implementing money operations: The first attempt failed because it ignored the team convention requiring keyword-only idempotency_key on money-moving operations.
  Before implementing any payment/credit mutation, search the repo (CHANGELOG, README, existing functions, audit module) for conventions like idempotency keys, audit logging, or state guards. Apply them proactively rather than only satisfying the literal issue text.
- [rb-0002] Read existing module conventions before implementing: Inspect sibling functions and the money module to mirror established patterns for type hints, zero handling, and rounding.
  Before writing a new function, read the surrounding file (e.g. line_total, invoice_total) and ledgerly/money.py. Reuse ZERO, to_money, and round_money exactly as existing functions do, so the new code matches team conventions and passes hidden tests.
- [rb-0013] Reuse existing money helpers for Decimal-safe arithmetic: When adding a pricing/money function, delegate to the repo's existing to_money/round_money helpers instead of raw Decimal or float math.
  Inspect ledgerly/money.py and sibling modules (invoice.py, payments.py) first; they define to_money, round_money, and BillingError conventions. Building add_tax on those helpers gives consistent rounding and error types for free.
- [rb-0010] Check repo conventions before implementing money operations: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before writing a money-moving function, grep the repo for existing audit/approval patterns and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency_key and approval thresholds are often documented outside the issue.
- [rb-0003] Guard division by zero explicitly: Return the module's ZERO constant when total quantity is zero rather than dividing.
  Compute total_quantity first; if it is falsy, return ZERO. Otherwise sum quantity*unit_price with a ZERO start value and divide, then round the result with round_money.
- [rb-0004] Match existing error and validation conventions before implementing: Reading sibling modules (payments.py, errors.py, money.py) revealed the exact BillingError codes and state-check pattern to reuse.
  Before writing a new function, grep for similar validation in the repo (e.g. `invalid_state`, `negative_amount`) and mirror those error codes and message formats. Reusing `to_money`/`ZERO` from the money module keeps price handling consistent.
```

### Shown for B01

```
Memory items from past tasks:
- [rb-0004] Match existing error and validation conventions before implementing: Reading sibling modules (payments.py, errors.py, money.py) revealed the exact BillingError codes and state-check pattern to reuse.
  Before writing a new function, grep for similar validation in the repo (e.g. `invalid_state`, `negative_amount`) and mirror those error codes and message formats. Reusing `to_money`/`ZERO` from the money module keeps price handling consistent.
- [rb-0014] Validate rate inputs before arithmetic, including non-finite values: Guard tax-rate inputs against non-numeric, NaN/Infinity, and out-of-range values before computing.
  Wrap Decimal conversion in try/except (InvalidOperation, ValueError) and check rate.is_finite() plus 0 <= rate <= 100, raising the project's BillingError with a stable code. This prevents silent NaN propagation and matches hidden-test expectations for invalid input.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Python's round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals. Always import and call ledgerly.money.round_money (half-up to the cent) on any computed money value before returning it.
- [rb-0006] Verify edge cases with a manual script after tests pass: The agent ran an ad-hoc script exercising zero, negative, float, bool, bad-string, and non-draft cases to confirm each raised the right error code.
  After the test suite passes, run a short script probing boundary and type-confusion inputs (0, -1, 1.5, True, non-numeric strings, wrong status) and print the resulting error codes. This catches gaps hidden tests may target.
- [rb-0015] Smoke-test edge cases manually before submitting: Run a quick script exercising boundary and invalid inputs after tests pass, since hidden tests probe beyond the visible suite.
  The visible test only checked one case; manually calling add_tax with string amounts, 100% rate, and out-of-range rates surfaced a traceback that guided the final robust implementation. Always probe boundaries (0, 100, negatives, non-numeric) before declaring done.
- [rb-0010] Check repo conventions before implementing money operations: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before writing a money-moving function, grep the repo for existing audit/approval patterns and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency_key and approval thresholds are often documented outside the issue.
```

### Shown for S04

```
Memory items from past tasks:
- [rb-0016] Check repo conventions before implementing money operations: The first attempt failed because it ignored the team convention requiring keyword-only idempotency_key on money-moving operations.
  Before implementing any payment/credit mutation, search the repo (CHANGELOG, README, existing functions, audit module) for conventions like idempotency keys, audit logging, or state guards. Apply them proactively rather than only satisfying the literal issue text.
- [rb-0012] Enforce approval thresholds for large refunds: Support-initiated refunds above 500.00 require a second approver via keyword-only approved_by, raising BillingError("approval_required") otherwise.
  Define APPROVAL_THRESHOLD = round_money("500.00") and check amount > threshold before applying. Validate state, amount positivity, and cumulative refunded_amount <= payment.amount, then update refunded_amount and set status to "refunded" on full refund.
- [rb-0002] Read existing module conventions before implementing: Inspect sibling functions and the money module to mirror established patterns for type hints, zero handling, and rounding.
  Before writing a new function, read the surrounding file (e.g. line_total, invoice_total) and ledgerly/money.py. Reuse ZERO, to_money, and round_money exactly as existing functions do, so the new code matches team conventions and passes hidden tests.
- [rb-0005] Guard bool when validating integer inputs in Python: `isinstance(True, int)` is True, so a bool quantity would pass a naive int check; explicitly reject bools.
  When requiring a positive integer, write `isinstance(x, bool) or not isinstance(x, int) or x <= 0`. This rejects True/False and floats while accepting genuine ints.
- [rb-0014] Validate rate inputs before arithmetic, including non-finite values: Guard tax-rate inputs against non-numeric, NaN/Infinity, and out-of-range values before computing.
  Wrap Decimal conversion in try/except (InvalidOperation, ValueError) and check rate.is_finite() plus 0 <= rate <= 100, raising the project's BillingError with a stable code. This prevents silent NaN propagation and matches hidden-test expectations for invalid input.
- [rb-0003] Guard division by zero explicitly: Return the module's ZERO constant when total quantity is zero rather than dividing.
  Compute total_quantity first; if it is falsy, return ZERO. Otherwise sum quantity*unit_price with a ZERO start value and divide, then round the result with round_money.
```

## ace

### E01 (first attempt failed)
- ADD `ace-0001` strategies: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
- ADD `ace-0002` common_mistakes: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong monetary results; always use the project's half-up rounding helper for money values.
- ADD `ace-0003` strategies: When a function computes a ratio or average of money, round the final result with the project's money-rounding helper, and guard against division by zero (return the project's ZERO constant for empty inputs).

### E02 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E02
- UPDATE `ace-0003`: reflector: helpful in E02
- ADD `ace-0004` strategies: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.py's `invoice.status != "issued"` -> BillingError("invalid_state", ...)) and mirror them exactly for consistency.
- ADD `ace-0005` common_mistakes: When validating an integer parameter, `isinstance(x, bool)` is True for bools since bool subclasses int; explicitly reject bools (and non-int types) before the range check to avoid accepting True/False as quantities.
- ADD `ace-0006` strategies: After implementing, exercise the function directly with edge-case inputs (zero, negative, float, bool, non-numeric strings, wrong invoice state) in a quick script to confirm each raises the expected error code, not just that the test suite passes.

### E03 (first attempt passed)
- UPDATE `ace-0004`: reflector: helpful in E03
- UPDATE `ace-0006`: reflector: helpful in E03
- ADD `ace-0007` strategies: Before implementing a date/time function, inspect sibling modules (e.g. subscriptions.py's current_period) for existing patterns like ensure_utc normalization and timedelta arithmetic, and mirror them for consistency.
- ADD `ace-0008` domain_facts: In ledgerly, datetimes must be timezone-aware; use ledgerly.clock.ensure_utc to normalize inputs (it raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime values).
- ADD `ace-0009` strategies: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length, handling the after < start case separately; this correctly skips the start itself and lands strictly after boundary values.

### E04 (first attempt failed)
- UPDATE `ace-0001`: reflector: helpful in E04
- UPDATE `ace-0003`: reflector: helpful in E04
- UPDATE `ace-0004`: reflector: helpful in E04
- UPDATE `ace-0006`: reflector: helpful in E04
- UPDATE `ace-0008`: reflector: helpful in E04
- ADD `ace-0010` strategies: Before implementing any money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing tests) for team conventions like idempotency_key handling and approval thresholds; these are often not in the issue text but are enforced by hidden tests.
- ADD `ace-0011` strategies: When adding an idempotency_key parameter, check ledgerly.audit.events() for an existing entry with that key and return early without re-applying the operation, and always include idempotency_key in the audit.record() call you write.
- ADD `ace-0012` domain_facts: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when missing; also every money-moving operation must accept a keyword-only idempotency_key (INC-204).

### E05 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E05
- UPDATE `ace-0003`: reflector: helpful in E05
- UPDATE `ace-0004`: reflector: helpful in E05
- UPDATE `ace-0006`: reflector: helpful in E05
- ADD `ace-0013` strategies: When a numeric parameter (e.g. a percentage rate) must be validated for range, convert it with the project's to_money/Decimal helper first so non-numeric strings and floats raise the project's BillingError, then check the range; wrap the conversion in try/except for InvalidOperation/ValueError if you parse with Decimal directly.
- ADD `ace-0014` common_mistakes: Don't reuse to_money for a rate/percentage parameter if it rejects floats (ledgerly's to_money raises BillingError('float_amount') for floats); if the API should accept float rates like 7.5, parse with Decimal(str(x)) and handle InvalidOperation/ValueError yourself, and also reject non-finite values (NaN/Infinity) before the range check.
- ADD `ace-0015` domain_facts: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Use these for amounts, but decide explicitly whether rate/percent parameters should accept floats.

### E06 (first attempt failed)

### Shown for H04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=3 harmful=0 :: When a function computes a ratio or average of money, round the final result with the project's money-rounding helper, and guard against division by zero (return the project's ZERO constant for empty inputs).
[ace-0004] helpful=3 harmful=0 :: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.py's `invoice.status != "issued"` -> BillingError("invalid_state", ...)) and mirror them exactly for consistency.
[ace-0006] helpful=3 harmful=0 :: After implementing, exercise the function directly with edge-case inputs (zero, negative, float, bool, non-numeric strings, wrong invoice state) in a quick script to confirm each raises the expected error code, not just that the test suite passes.
[ace-0007] helpful=0 harmful=0 :: Before implementing a date/time function, inspect sibling modules (e.g. subscriptions.py's current_period) for existing patterns like ensure_utc normalization and timedelta arithmetic, and mirror them for consistency.
[ace-0009] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length, handling the after < start case separately; this correctly skips the start itself and lands strictly after boundary values.
[ace-0010] helpful=0 harmful=0 :: Before implementing any money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing tests) for team conventions like idempotency_key handling and approval thresholds; these are often not in the issue text but are enforced by hidden tests.
[ace-0011] helpful=0 harmful=0 :: When adding an idempotency_key parameter, check ledgerly.audit.events() for an existing entry with that key and return early without re-applying the operation, and always include idempotency_key in the audit.record() call you write.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a percentage rate) must be validated for range, convert it with the project's to_money/Decimal helper first so non-numeric strings and floats raise the project's BillingError, then check the range; wrap the conversion in try/except for InvalidOperation/ValueError if you parse with Decimal directly.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong monetary results; always use the project's half-up rounding helper for money values.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter, `isinstance(x, bool)` is True for bools since bool subclasses int; explicitly reject bools (and non-int types) before the range check to avoid accepting True/False as quantities.
[ace-0014] helpful=0 harmful=0 :: Don't reuse to_money for a rate/percentage parameter if it rejects floats (ledgerly's to_money raises BillingError('float_amount') for floats); if the API should accept float rates like 7.5, parse with Decimal(str(x)) and handle InvalidOperation/ValueError yourself, and also reject non-finite values (NaN/Infinity) before the range check.
## domain_facts
[ace-0008] helpful=1 harmful=0 :: In ledgerly, datetimes must be timezone-aware; use ledgerly.clock.ensure_utc to normalize inputs (it raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime values).
[ace-0012] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when missing; also every money-moving operation must accept a keyword-only idempotency_key (INC-204).
[ace-0015] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Use these for amounts, but decide explicitly whether rate/percent parameters should accept floats.
```

### Shown for B01

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=3 harmful=0 :: When a function computes a ratio or average of money, round the final result with the project's money-rounding helper, and guard against division by zero (return the project's ZERO constant for empty inputs).
[ace-0004] helpful=3 harmful=0 :: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.py's `invoice.status != "issued"` -> BillingError("invalid_state", ...)) and mirror them exactly for consistency.
[ace-0006] helpful=3 harmful=0 :: After implementing, exercise the function directly with edge-case inputs (zero, negative, float, bool, non-numeric strings, wrong invoice state) in a quick script to confirm each raises the expected error code, not just that the test suite passes.
[ace-0007] helpful=0 harmful=0 :: Before implementing a date/time function, inspect sibling modules (e.g. subscriptions.py's current_period) for existing patterns like ensure_utc normalization and timedelta arithmetic, and mirror them for consistency.
[ace-0009] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length, handling the after < start case separately; this correctly skips the start itself and lands strictly after boundary values.
[ace-0010] helpful=0 harmful=0 :: Before implementing any money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing tests) for team conventions like idempotency_key handling and approval thresholds; these are often not in the issue text but are enforced by hidden tests.
[ace-0011] helpful=0 harmful=0 :: When adding an idempotency_key parameter, check ledgerly.audit.events() for an existing entry with that key and return early without re-applying the operation, and always include idempotency_key in the audit.record() call you write.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a percentage rate) must be validated for range, convert it with the project's to_money/Decimal helper first so non-numeric strings and floats raise the project's BillingError, then check the range; wrap the conversion in try/except for InvalidOperation/ValueError if you parse with Decimal directly.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong monetary results; always use the project's half-up rounding helper for money values.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter, `isinstance(x, bool)` is True for bools since bool subclasses int; explicitly reject bools (and non-int types) before the range check to avoid accepting True/False as quantities.
[ace-0014] helpful=0 harmful=0 :: Don't reuse to_money for a rate/percentage parameter if it rejects floats (ledgerly's to_money raises BillingError('float_amount') for floats); if the API should accept float rates like 7.5, parse with Decimal(str(x)) and handle InvalidOperation/ValueError yourself, and also reject non-finite values (NaN/Infinity) before the range check.
## domain_facts
[ace-0008] helpful=1 harmful=0 :: In ledgerly, datetimes must be timezone-aware; use ledgerly.clock.ensure_utc to normalize inputs (it raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime values).
[ace-0012] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when missing; also every money-moving operation must accept a keyword-only idempotency_key (INC-204).
[ace-0015] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Use these for amounts, but decide explicitly whether rate/percent parameters should accept floats.
```

### Shown for S04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=3 harmful=0 :: When a function computes a ratio or average of money, round the final result with the project's money-rounding helper, and guard against division by zero (return the project's ZERO constant for empty inputs).
[ace-0004] helpful=3 harmful=0 :: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.py's `invoice.status != "issued"` -> BillingError("invalid_state", ...)) and mirror them exactly for consistency.
[ace-0006] helpful=3 harmful=0 :: After implementing, exercise the function directly with edge-case inputs (zero, negative, float, bool, non-numeric strings, wrong invoice state) in a quick script to confirm each raises the expected error code, not just that the test suite passes.
[ace-0007] helpful=0 harmful=0 :: Before implementing a date/time function, inspect sibling modules (e.g. subscriptions.py's current_period) for existing patterns like ensure_utc normalization and timedelta arithmetic, and mirror them for consistency.
[ace-0009] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length, handling the after < start case separately; this correctly skips the start itself and lands strictly after boundary values.
[ace-0010] helpful=0 harmful=0 :: Before implementing any money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing tests) for team conventions like idempotency_key handling and approval thresholds; these are often not in the issue text but are enforced by hidden tests.
[ace-0011] helpful=0 harmful=0 :: When adding an idempotency_key parameter, check ledgerly.audit.events() for an existing entry with that key and return early without re-applying the operation, and always include idempotency_key in the audit.record() call you write.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a percentage rate) must be validated for range, convert it with the project's to_money/Decimal helper first so non-numeric strings and floats raise the project's BillingError, then check the range; wrap the conversion in try/except for InvalidOperation/ValueError if you parse with Decimal directly.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong monetary results; always use the project's half-up rounding helper for money values.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter, `isinstance(x, bool)` is True for bools since bool subclasses int; explicitly reject bools (and non-int types) before the range check to avoid accepting True/False as quantities.
[ace-0014] helpful=0 harmful=0 :: Don't reuse to_money for a rate/percentage parameter if it rejects floats (ledgerly's to_money raises BillingError('float_amount') for floats); if the API should accept float rates like 7.5, parse with Decimal(str(x)) and handle InvalidOperation/ValueError yourself, and also reject non-finite values (NaN/Infinity) before the range check.
## domain_facts
[ace-0008] helpful=1 harmful=0 :: In ledgerly, datetimes must be timezone-aware; use ledgerly.clock.ensure_utc to normalize inputs (it raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime values).
[ace-0012] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when missing; also every money-moving operation must accept a keyword-only idempotency_key (INC-204).
[ace-0015] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Use these for amounts, but decide explicitly whether rate/percent parameters should accept floats.
```

## attest

### E01 (first attempt failed)
- ADD `at-0001` Round money only via round_money: Always round monetary results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
- REJECT (evidence quote not found verbatim in the review comments or the diff): ledgerly.money exposes ZERO, to_money, and round_money; coerce line prices with to_money and seed sums with ZERO, as line_total and invoice_total in ledgerly/invoice.py do.

### E02 (first attempt passed)
- ADD `at-0002` Use BillingError with machine-readable codes: Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, reusing existing codes like "invalid_state" and "negative_amount" (see `ledgerly/payments.py`).
- REJECT (evidence quote not found verbatim in the review comments or the diff): Convert any incoming amount with `to_money` from `ledgerly/money.py` and compare against `ZERO`; store `Decimal` on models, never raw floats or strings.
- ADD `at-0003` Reject bools when validating integer quantities: When validating integer fields, check `isinstance(x, bool)` first because `bool` subclasses `int`; otherwise `True` passes as quantity 1.

### E03 (first attempt passed)
- REJECT (evidence quote not found verbatim in the review comments or the diff): Call `ledgerly.clock.ensure_utc` on every incoming datetime (including `sub.started_at`) before comparing or doing arithmetic; it raises `BillingError` for naive or non-datetime values.
- REJECT (evidence quote not found verbatim in the review comments or the diff): Compute billing periods with `timedelta(days=sub.period_days)` and floor division `(at - start) // length` as done in `ledgerly.subscriptions.current_period`, rather than calendar-month logic.

### E04 (first attempt failed)
- ADD `at-0004` Money-moving operations require idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and pass `idempotency_key` into `audit.record(...)`.
- ADD `at-0005` Refunds above 500.00 need approved_by: Support-initiated refunds and credits above 500.00 must accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing (finance policy FIN-2026-03).
- UPDATE `at-0001`: confirmed again by verified task E04

### E05 (first attempt passed)
- UPDATE `at-0001`: confirmed again by verified task E05
- UPDATE `at-0002`: confirmed again by verified task E05
- ADD `at-0006` Parse rates via Decimal(str(...)) not to_money: `to_money` rejects floats, so parse numeric rates with `Decimal(str(rate_percent))` and catch `InvalidOperation`/`ValueError` to raise `BillingError` instead.

### E06 (first attempt failed)
- UPDATE `at-0004`: confirmed again by verified task E06
- REJECT (evidence quote not found verbatim in the review comments or the diff): `ledgerly.audit.events()` returns audit entries as dicts; dedupe by scanning for `e.get("idempotency_key") == idempotency_key`. Pass `idempotency_key` through to `audit.record(...)` so future calls can detect replays.
- REJECT (evidence quote not found verbatim in the review comments or the diff): Normalize any incoming `at` datetime with `ledgerly.clock.ensure_utc` before storing it on models or comparing, as `authorize` does for `created_at`.

### Shown for H04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0001] Round money only via round_money: Always round monetary results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0004] Money-moving operations require idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and pass `idempotency_key` into `audit.record(...)`.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0002] Use BillingError with machine-readable codes: Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, reusing existing codes like "invalid_state" and "negative_amount" (see `ledgerly/payments.py`).
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0006] Parse rates via Decimal(str(...)) not to_money: `to_money` rejects floats, so parse numeric rates with `Decimal(str(rate_percent))` and catch `InvalidOperation`/`ValueError` to raise `BillingError` instead.
  (learned from task E05 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0003] Reject bools when validating integer quantities: When validating integer fields, check `isinstance(x, bool)` first because `bool` subclasses `int`; otherwise `True` passes as quantity 1.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0005] Refunds above 500.00 need approved_by: Support-initiated refunds and credits above 500.00 must accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing (finance policy FIN-2026-03).
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
```

### Shown for B01

```
(nothing)
```

### Shown for S04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0005] Refunds above 500.00 need approved_by: Support-initiated refunds and credits above 500.00 must accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing (finance policy FIN-2026-03).
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0001] Round money only via round_money: Always round monetary results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0002] Use BillingError with machine-readable codes: Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, reusing existing codes like "invalid_state" and "negative_amount" (see `ledgerly/payments.py`).
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0004] Money-moving operations require idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and pass `idempotency_key` into `audit.record(...)`.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0003] Reject bools when validating integer quantities: When validating integer fields, check `isinstance(x, bool)` first because `bool` subclasses `int`; otherwise `True` passes as quantity 1.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0006] Parse rates via Decimal(str(...)) not to_money: `to_money` rejects floats, so parse numeric rates with `Decimal(str(rate_percent))` and catch `InvalidOperation`/`ValueError` to raise `BillingError` instead.
  (learned from task E05 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
```

