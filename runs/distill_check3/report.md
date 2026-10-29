# Write-path check (before freeze)

Source trajectories: `runs/pilot3_nomem` (no memory).

## reasoningbank

### E01 (first attempt failed)
- ADD `rb-0001` Use project money helpers for rounding: Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- ADD `rb-0002` Read existing module code before implementing: When adding a function to an existing module, cat the module and its helper modules first. Mirroring existing helpers (e.g., line_total's to_money + round_money pattern) satisfies conventions and avoids review rejections.
- ADD `rb-0003` Verify rounding edge cases explicitly: Hidden tests often probe rounding boundaries. Run a quick script with a value like 2.5 cents to confirm round_money rounds half-up, since the visible tests may not cover it.

### E02 (first attempt passed)
- ADD `rb-0004` Read sibling modules to match error codes and conventions: Search for existing error codes (e.g. 'invalid_state', 'negative_amount') and money helpers (to_money, ZERO) in sibling modules like payments.py. Reusing established codes and helpers keeps behavior consistent and satisfies hidden tests that expect specific codes.
- ADD `rb-0005` Guard bool when validating integer inputs: Validate with `isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0` to reject True/False and floats. Hidden tests often probe bool-as-int edge cases.
- ADD `rb-0006` Normalize money inputs through the project's to_money helper: Call `price = to_money(unit_price)` first, then compare `price < ZERO` and store the normalized Decimal on the LineItem. This avoids type errors on string inputs and keeps stored values consistent with line_total.

### E03 (first attempt passed)
- ADD `rb-0007` Reuse existing period arithmetic helpers: Search the codebase for similar functions (e.g., `current_period`) and reuse their exact arithmetic: `n = (at - start) // length`, `start + n * length`. For 'strictly after', add `+ 1` to the quotient; for 'before start', return `start + length`.
- ADD `rb-0008` Normalize datetimes with the repo's ensure_utc: Before doing datetime arithmetic, run inputs through the repo's `ensure_utc` (from `ledgerly/clock.py`) so naive datetimes raise the expected `BillingError` and tz-aware values are converted to UTC, matching existing conventions.
- ADD `rb-0009` Read the hidden-test-adjacent test file first: Before implementing, cat the test file for the target function and grep for related model fields (`started_at`, `period_days`). This reveals constructor signatures, expected return values, and edge cases (boundary, before-start) so the first attempt passes.

### E04 (first attempt failed)
- ADD `rb-0010` Check repo conventions before implementing money operations: Before writing a money-moving function, grep the repo for existing audit/approval patterns and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency keys and approval thresholds are often enforced by hidden tests even when the issue omits them.
- ADD `rb-0011` Make retryable operations idempotent via audit lookup: Implement a helper that scans audit.events() for a matching idempotency_key and returns early (returning the payment unchanged) if found. Always pass idempotency_key into the audit.record call so future retries can detect it.
- ADD `rb-0012` Enforce approval thresholds for large refunds: Define an APPROVAL_THRESHOLD constant with round_money and check it after validating state and amount but before mutating payment. Raise BillingError("approval_required") with no extra args, and record approved_by in the audit entry.

### E05 (first attempt passed)
- ADD `rb-0013` Reuse existing money helpers for Decimal-safe arithmetic: Inspect ledgerly/money.py and similar modules first; to_money rejects floats and normalizes inputs, round_money applies the finance rounding policy. Composing these keeps behavior consistent with the rest of the codebase and satisfies hidden tests on rounding.
- ADD `rb-0014` Validate numeric inputs with explicit finite/range checks: Wrap parsing in try/except (InvalidOperation, ValueError) and check rate.is_finite() plus bounds (0 <= rate <= 100). Raise BillingError with a stable code like 'invalid_tax_rate' so callers and tests can assert on it.
- ADD `rb-0015` Smoke-test edge cases manually before submitting: After pytest passes, invoke the new function directly with Decimal, str, and boundary rate values, and confirm error paths raise the expected exception. This surfaces float-rejection or rounding surprises that the visible test suite may not cover.

### E06 (first attempt failed)
- ADD `rb-0016` Check repo conventions before implementing money/state operations: Before implementing any payment/credit/state-changing function, scan README, CHANGELOG, and existing sibling functions (e.g. authorize) for conventions like idempotency keys, audit fields, or keyword-only params. Mirror the existing function's signature and audit.record fields rather than inventing a minimal version.
- ADD `rb-0017` Implement idempotency via audit-event lookup: Add a private helper like `_already_applied(idempotency_key)` that returns False for None and otherwise scans `audit.events()` for `e.get('idempotency_key') == idempotency_key`. Call it at the top of each operation, and always pass `idempotency_key=...` into the audit.record call so future replays are detected.
- ADD `rb-0018` Return the domain object on idempotent replay, not None: For capture-style operations, return the passed-in `payment` on replay. For creation-style operations like authorize, returning None is risky—prefer returning the previously created object or documenting the None contract; hidden tests may assert on the return value.

### Shown for H04

```
Memory items from past tasks:
- [rb-0010] Check repo conventions before implementing money operations: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before writing a money-moving function, grep the repo for existing audit/approval patterns and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency keys and approval thresholds are often enforced by hidden tests even when the issue omits them.
- [rb-0016] Check repo conventions before implementing money/state operations: The first attempt failed because it missed a team convention (keyword-only idempotency_key on money-moving operations) that wasn't in the issue text.
  Before implementing any payment/credit/state-changing function, scan README, CHANGELOG, and existing sibling functions (e.g. authorize) for conventions like idempotency keys, audit fields, or keyword-only params. Mirror the existing function's signature and audit.record fields rather than inventing a minimal version.
- [rb-0002] Read existing module code before implementing: Inspecting invoice.py and money.py first revealed the established patterns (to_money, ZERO, round_money) to reuse.
  When adding a function to an existing module, cat the module and its helper modules first. Mirroring existing helpers (e.g., line_total's to_money + round_money pattern) satisfies conventions and avoids review rejections.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- [rb-0004] Read sibling modules to match error codes and conventions: Before implementing a new function, grep the codebase for existing BillingError usages and helper functions to reuse the same error codes and patterns.
  Search for existing error codes (e.g. 'invalid_state', 'negative_amount') and money helpers (to_money, ZERO) in sibling modules like payments.py. Reusing established codes and helpers keeps behavior consistent and satisfies hidden tests that expect specific codes.
- [rb-0006] Normalize money inputs through the project's to_money helper: Convert unit_price via to_money before comparing to ZERO so strings/Decimals are handled uniformly and negative checks are reliable.
  Call `price = to_money(unit_price)` first, then compare `price < ZERO` and store the normalized Decimal on the LineItem. This avoids type errors on string inputs and keeps stored values consistent with line_total.
```

### Shown for B01

```
Memory items from past tasks:
- [rb-0006] Normalize money inputs through the project's to_money helper: Convert unit_price via to_money before comparing to ZERO so strings/Decimals are handled uniformly and negative checks are reliable.
  Call `price = to_money(unit_price)` first, then compare `price < ZERO` and store the normalized Decimal on the LineItem. This avoids type errors on string inputs and keeps stored values consistent with line_total.
- [rb-0015] Smoke-test edge cases manually before submitting: Run a quick script exercising boundary inputs (0, 100, invalid rates, string amounts) to catch issues hidden tests may probe.
  After pytest passes, invoke the new function directly with Decimal, str, and boundary rate values, and confirm error paths raise the expected exception. This surfaces float-rejection or rounding surprises that the visible test suite may not cover.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- [rb-0004] Read sibling modules to match error codes and conventions: Before implementing a new function, grep the codebase for existing BillingError usages and helper functions to reuse the same error codes and patterns.
  Search for existing error codes (e.g. 'invalid_state', 'negative_amount') and money helpers (to_money, ZERO) in sibling modules like payments.py. Reusing established codes and helpers keeps behavior consistent and satisfies hidden tests that expect specific codes.
- [rb-0014] Validate numeric inputs with explicit finite/range checks: Guard against NaN, infinity, and out-of-range values before doing arithmetic, raising the project's domain error type.
  Wrap parsing in try/except (InvalidOperation, ValueError) and check rate.is_finite() plus bounds (0 <= rate <= 100). Raise BillingError with a stable code like 'invalid_tax_rate' so callers and tests can assert on it.
- [rb-0013] Reuse existing money helpers for Decimal-safe arithmetic: When implementing monetary functions, delegate to the repo's existing to_money/round_money helpers instead of raw Decimal or float math.
  Inspect ledgerly/money.py and similar modules first; to_money rejects floats and normalizes inputs, round_money applies the finance rounding policy. Composing these keeps behavior consistent with the rest of the codebase and satisfies hidden tests on rounding.
```

### Shown for S04

```
Memory items from past tasks:
- [rb-0016] Check repo conventions before implementing money/state operations: The first attempt failed because it missed a team convention (keyword-only idempotency_key on money-moving operations) that wasn't in the issue text.
  Before implementing any payment/credit/state-changing function, scan README, CHANGELOG, and existing sibling functions (e.g. authorize) for conventions like idempotency keys, audit fields, or keyword-only params. Mirror the existing function's signature and audit.record fields rather than inventing a minimal version.
- [rb-0002] Read existing module code before implementing: Inspecting invoice.py and money.py first revealed the established patterns (to_money, ZERO, round_money) to reuse.
  When adding a function to an existing module, cat the module and its helper modules first. Mirroring existing helpers (e.g., line_total's to_money + round_money pattern) satisfies conventions and avoids review rejections.
- [rb-0005] Guard bool when validating integer inputs: Python's bool is a subclass of int, so isinstance(True, int) is True; explicitly reject bools when requiring a positive integer.
  Validate with `isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0` to reject True/False and floats. Hidden tests often probe bool-as-int edge cases.
- [rb-0014] Validate numeric inputs with explicit finite/range checks: Guard against NaN, infinity, and out-of-range values before doing arithmetic, raising the project's domain error type.
  Wrap parsing in try/except (InvalidOperation, ValueError) and check rate.is_finite() plus bounds (0 <= rate <= 100). Raise BillingError with a stable code like 'invalid_tax_rate' so callers and tests can assert on it.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- [rb-0004] Read sibling modules to match error codes and conventions: Before implementing a new function, grep the codebase for existing BillingError usages and helper functions to reuse the same error codes and patterns.
  Search for existing error codes (e.g. 'invalid_state', 'negative_amount') and money helpers (to_money, ZERO) in sibling modules like payments.py. Reusing established codes and helpers keeps behavior consistent and satisfies hidden tests that expect specific codes.
```

## ace

### E01 (first attempt failed)
- ADD `ace-0001` strategies: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
- ADD `ace-0002` common_mistakes: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
- ADD `ace-0003` strategies: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper and guard against division by zero (return ZERO for empty inputs).

### E02 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E02
- UPDATE `ace-0003`: reflector: helpful in E02
- ADD `ace-0004` strategies: Before implementing a new function, grep the repo for similar existing functions (e.g. payments.authorize) and mirror their validation order, error codes, and message formats so the new code matches project conventions.
- ADD `ace-0005` common_mistakes: When validating an integer parameter in Python, reject bool explicitly (isinstance(x, bool)) because bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
- ADD `ace-0006` domain_facts: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; reuse existing codes where the same condition already exists elsewhere in the repo.

### E03 (first attempt passed)
- UPDATE `ace-0004`: reflector: helpful in E03
- ADD `ace-0007` strategies: When implementing a date/time function, grep for existing helpers like ensure_utc in ledgerly/clock.py and normalize all datetime inputs (including model fields such as sub.started_at) before comparing or doing arithmetic, so naive/aware mismatches don't raise or misbehave.
- ADD `ace-0008` strategies: For 'first occurrence strictly after X' recurrence problems, mirror the existing period math (e.g. subscriptions.current_period's n = (at - start) // length) and add +1 to the quotient to get the strictly-after index; handle the before-start case explicitly.
- ADD `ace-0009` domain_facts: In ledgerly, ledgerly/clock.py provides utcnow() and ensure_utc(dt), which raises BillingError('invalid_datetime') for non-datetimes and BillingError('naive_datetime') for naive datetimes; reuse it instead of calling astimezone directly.

### E04 (first attempt failed)
- UPDATE `ace-0001`: reflector: helpful in E04
- UPDATE `ace-0003`: reflector: helpful in E04
- UPDATE `ace-0004`: reflector: helpful in E04
- UPDATE `ace-0006`: reflector: helpful in E04
- UPDATE `ace-0007`: reflector: helpful in E04
- UPDATE `ace-0009`: reflector: helpful in E04
- ADD `ace-0010` strategies: Before implementing a money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing operations) for team conventions like idempotency_key handling and approval thresholds; these may not be visible in the function stub but are enforced by hidden tests.
- ADD `ace-0011` strategies: When adding an operation that writes an audit entry, check ledgerly/audit.py for the record() signature and events() lookup, and implement idempotency by scanning events() for a matching idempotency_key before applying any state changes.
- ADD `ace-0012` common_mistakes: Do not assume the issue description lists all required parameters; operations that move money often need keyword-only extras (idempotency_key, approved_by) mandated by team conventions documented in README/CHANGELOG, and omitting them causes rejection even when core logic is correct.

### E05 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E05
- UPDATE `ace-0004`: reflector: helpful in E05
- UPDATE `ace-0006`: reflector: helpful in E05
- ADD `ace-0013` strategies: When a numeric parameter (e.g. a tax rate) may arrive as int, str, or Decimal, convert it with the project's to_money helper rather than Decimal(str(...)) directly, so floats/bools are rejected consistently with the rest of the repo and InvalidOperation is handled uniformly.
- ADD `ace-0014` common_mistakes: Do not pass float values to money helpers like to_money: ledgerly's to_money raises BillingError('float_amount') for floats and bools, so a rate like 7.5 must be supplied as Decimal('7.5') or a string; test with Decimal/str inputs, not bare floats.
- ADD `ace-0015` domain_facts: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Reuse these rather than reimplementing conversion/rounding.

### E06 (first attempt failed)
- UPDATE `ace-0004`: reflector: helpful in E06
- UPDATE `ace-0010`: reflector: helpful in E06
- UPDATE `ace-0011`: reflector: helpful in E06
- UPDATE `ace-0007`: reflector: helpful in E06
- UPDATE `ace-0006`: reflector: helpful in E06
- UPDATE `ace-0009`: reflector: helpful in E06
- UPDATE `ace-0012`: reflector: helpful in E06
- ADD `ace-0016` strategies: When a review comment reveals a team convention (e.g. mandatory keyword-only idempotency_key), apply it consistently to sibling operations in the same module (e.g. authorize as well as capture), not just the function named in the issue, since hidden tests may check both.
- ADD `ace-0017` common_mistakes: Do not return None from an idempotent early-exit path when the function's return type is a domain object; return the existing/affected object (e.g. the payment) so callers and tests that use the return value don't break.
- ADD `ace-0018` domain_facts: In ledgerly, audit.events() returns dict entries; idempotency is implemented by scanning events() for a matching 'idempotency_key' value before mutating state, and passing idempotency_key=... into audit.record() so the key is persisted for future dedup checks.

### Shown for H04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=2 harmful=0 :: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper and guard against division by zero (return ZERO for empty inputs).
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for similar existing functions (e.g. payments.authorize) and mirror their validation order, error codes, and message formats so the new code matches project conventions.
[ace-0007] helpful=2 harmful=0 :: When implementing a date/time function, grep for existing helpers like ensure_utc in ledgerly/clock.py and normalize all datetime inputs (including model fields such as sub.started_at) before comparing or doing arithmetic, so naive/aware mismatches don't raise or misbehave.
[ace-0008] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, mirror the existing period math (e.g. subscriptions.current_period's n = (at - start) // length) and add +1 to the quotient to get the strictly-after index; handle the before-start case explicitly.
[ace-0010] helpful=1 harmful=0 :: Before implementing a money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing operations) for team conventions like idempotency_key handling and approval thresholds; these may not be visible in the function stub but are enforced by hidden tests.
[ace-0011] helpful=1 harmful=0 :: When adding an operation that writes an audit entry, check ledgerly/audit.py for the record() signature and events() lookup, and implement idempotency by scanning events() for a matching idempotency_key before applying any state changes.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a tax rate) may arrive as int, str, or Decimal, convert it with the project's to_money helper rather than Decimal(str(...)) directly, so floats/bools are rejected consistently with the rest of the repo and InvalidOperation is handled uniformly.
[ace-0016] helpful=0 harmful=0 :: When a review comment reveals a team convention (e.g. mandatory keyword-only idempotency_key), apply it consistently to sibling operations in the same module (e.g. authorize as well as capture), not just the function named in the issue, since hidden tests may check both.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter in Python, reject bool explicitly (isinstance(x, bool)) because bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
[ace-0012] helpful=1 harmful=0 :: Do not assume the issue description lists all required parameters; operations that move money often need keyword-only extras (idempotency_key, approved_by) mandated by team conventions documented in README/CHANGELOG, and omitting them causes rejection even when core logic is correct.
[ace-0014] helpful=0 harmful=0 :: Do not pass float values to money helpers like to_money: ledgerly's to_money raises BillingError('float_amount') for floats and bools, so a rate like 7.5 must be supplied as Decimal('7.5') or a string; test with Decimal/str inputs, not bare floats.
[ace-0017] helpful=0 harmful=0 :: Do not return None from an idempotent early-exit path when the function's return type is a domain object; return the existing/affected object (e.g. the payment) so callers and tests that use the return value don't break.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; reuse existing codes where the same condition already exists elsewhere in the repo.
[ace-0009] helpful=2 harmful=0 :: In ledgerly, ledgerly/clock.py provides utcnow() and ensure_utc(dt), which raises BillingError('invalid_datetime') for non-datetimes and BillingError('naive_datetime') for naive datetimes; reuse it instead of calling astimezone directly.
[ace-0015] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Reuse these rather than reimplementing conversion/rounding.
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.events() returns dict entries; idempotency is implemented by scanning events() for a matching 'idempotency_key' value before mutating state, and passing idempotency_key=... into audit.record() so the key is persisted for future dedup checks.
```

### Shown for B01

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=2 harmful=0 :: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper and guard against division by zero (return ZERO for empty inputs).
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for similar existing functions (e.g. payments.authorize) and mirror their validation order, error codes, and message formats so the new code matches project conventions.
[ace-0007] helpful=2 harmful=0 :: When implementing a date/time function, grep for existing helpers like ensure_utc in ledgerly/clock.py and normalize all datetime inputs (including model fields such as sub.started_at) before comparing or doing arithmetic, so naive/aware mismatches don't raise or misbehave.
[ace-0008] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, mirror the existing period math (e.g. subscriptions.current_period's n = (at - start) // length) and add +1 to the quotient to get the strictly-after index; handle the before-start case explicitly.
[ace-0010] helpful=1 harmful=0 :: Before implementing a money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing operations) for team conventions like idempotency_key handling and approval thresholds; these may not be visible in the function stub but are enforced by hidden tests.
[ace-0011] helpful=1 harmful=0 :: When adding an operation that writes an audit entry, check ledgerly/audit.py for the record() signature and events() lookup, and implement idempotency by scanning events() for a matching idempotency_key before applying any state changes.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a tax rate) may arrive as int, str, or Decimal, convert it with the project's to_money helper rather than Decimal(str(...)) directly, so floats/bools are rejected consistently with the rest of the repo and InvalidOperation is handled uniformly.
[ace-0016] helpful=0 harmful=0 :: When a review comment reveals a team convention (e.g. mandatory keyword-only idempotency_key), apply it consistently to sibling operations in the same module (e.g. authorize as well as capture), not just the function named in the issue, since hidden tests may check both.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter in Python, reject bool explicitly (isinstance(x, bool)) because bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
[ace-0012] helpful=1 harmful=0 :: Do not assume the issue description lists all required parameters; operations that move money often need keyword-only extras (idempotency_key, approved_by) mandated by team conventions documented in README/CHANGELOG, and omitting them causes rejection even when core logic is correct.
[ace-0014] helpful=0 harmful=0 :: Do not pass float values to money helpers like to_money: ledgerly's to_money raises BillingError('float_amount') for floats and bools, so a rate like 7.5 must be supplied as Decimal('7.5') or a string; test with Decimal/str inputs, not bare floats.
[ace-0017] helpful=0 harmful=0 :: Do not return None from an idempotent early-exit path when the function's return type is a domain object; return the existing/affected object (e.g. the payment) so callers and tests that use the return value don't break.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; reuse existing codes where the same condition already exists elsewhere in the repo.
[ace-0009] helpful=2 harmful=0 :: In ledgerly, ledgerly/clock.py provides utcnow() and ensure_utc(dt), which raises BillingError('invalid_datetime') for non-datetimes and BillingError('naive_datetime') for naive datetimes; reuse it instead of calling astimezone directly.
[ace-0015] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Reuse these rather than reimplementing conversion/rounding.
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.events() returns dict entries; idempotency is implemented by scanning events() for a matching 'idempotency_key' value before mutating state, and passing idempotency_key=... into audit.record() so the key is persisted for future dedup checks.
```

### Shown for S04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=2 harmful=0 :: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper and guard against division by zero (return ZERO for empty inputs).
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for similar existing functions (e.g. payments.authorize) and mirror their validation order, error codes, and message formats so the new code matches project conventions.
[ace-0007] helpful=2 harmful=0 :: When implementing a date/time function, grep for existing helpers like ensure_utc in ledgerly/clock.py and normalize all datetime inputs (including model fields such as sub.started_at) before comparing or doing arithmetic, so naive/aware mismatches don't raise or misbehave.
[ace-0008] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, mirror the existing period math (e.g. subscriptions.current_period's n = (at - start) // length) and add +1 to the quotient to get the strictly-after index; handle the before-start case explicitly.
[ace-0010] helpful=1 harmful=0 :: Before implementing a money-moving or payment/credit-mutating function, grep the repo (README, CHANGELOG, audit.py, existing operations) for team conventions like idempotency_key handling and approval thresholds; these may not be visible in the function stub but are enforced by hidden tests.
[ace-0011] helpful=1 harmful=0 :: When adding an operation that writes an audit entry, check ledgerly/audit.py for the record() signature and events() lookup, and implement idempotency by scanning events() for a matching idempotency_key before applying any state changes.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a tax rate) may arrive as int, str, or Decimal, convert it with the project's to_money helper rather than Decimal(str(...)) directly, so floats/bools are rejected consistently with the rest of the repo and InvalidOperation is handled uniformly.
[ace-0016] helpful=0 harmful=0 :: When a review comment reveals a team convention (e.g. mandatory keyword-only idempotency_key), apply it consistently to sibling operations in the same module (e.g. authorize as well as capture), not just the function named in the issue, since hidden tests may check both.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter in Python, reject bool explicitly (isinstance(x, bool)) because bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
[ace-0012] helpful=1 harmful=0 :: Do not assume the issue description lists all required parameters; operations that move money often need keyword-only extras (idempotency_key, approved_by) mandated by team conventions documented in README/CHANGELOG, and omitting them causes rejection even when core logic is correct.
[ace-0014] helpful=0 harmful=0 :: Do not pass float values to money helpers like to_money: ledgerly's to_money raises BillingError('float_amount') for floats and bools, so a rate like 7.5 must be supplied as Decimal('7.5') or a string; test with Decimal/str inputs, not bare floats.
[ace-0017] helpful=0 harmful=0 :: Do not return None from an idempotent early-exit path when the function's return type is a domain object; return the existing/affected object (e.g. the payment) so callers and tests that use the return value don't break.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; reuse existing codes where the same condition already exists elsewhere in the repo.
[ace-0009] helpful=2 harmful=0 :: In ledgerly, ledgerly/clock.py provides utcnow() and ensure_utc(dt), which raises BillingError('invalid_datetime') for non-datetimes and BillingError('naive_datetime') for naive datetimes; reuse it instead of calling astimezone directly.
[ace-0015] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); round_money applies ROUND_HALF_UP to the cent. Reuse these rather than reimplementing conversion/rounding.
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.events() returns dict entries; idempotency is implemented by scanning events() for a matching 'idempotency_key' value before mutating state, and passing idempotency_key=... into audit.record() so the key is persisted for future dedup checks.
```

## attest

### E01 (first attempt failed)
- ADD `at-0001` Round money only via round_money: Always round monetary results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
- ADD `at-0002` Normalize unit prices with to_money: Wrap line unit prices with ledgerly.money.to_money before multiplying by quantity, and seed sums with ledgerly.money.ZERO, matching line_total and invoice_total in ledgerly/invoice.py.

### E02 (first attempt passed)
- REJECT (not applied in the verified change: no added line of the diff matches applied_in_diff): Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, using established codes like "invalid_state" and "negative_amount" rather than ValueError.
- REJECT (not applied in the verified change: no added line of the diff matches applied_in_diff): Convert incoming monetary values with `to_money` from `ledgerly/money.py` and compare against `ZERO`; store the normalized Decimal on the model.
- REJECT (not applied in the verified change: no added line of the diff matches applied_in_diff): When validating integer fields, explicitly exclude `bool` (isinstance(quantity, bool)) since True/False pass isinstance(x, int).

### E03 (first attempt passed)
- REJECT (not applied in the verified change: no added line of the diff matches applied_in_diff): Normalize all incoming datetimes with `ledgerly.clock.ensure_utc`, which raises `BillingError` for naive or non-datetime values; follow the pattern in `ledgerly.subscriptions.current_period`.
- REJECT (evidence quote not found verbatim in the review comments or the diff): Compute billing periods with `timedelta(days=sub.period_days)` and floor division `(at - start) // length`, mirroring `ledgerly.subscriptions.current_period`, rather than ad-hoc date math.

### E04 (first attempt failed)
- ADD `at-0003` Money operations need keyword-only idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early, and pass `idempotency_key` into `audit.record`.
- ADD `at-0004` Refunds above 500 need approved_by: Support-initiated refunds/credits above 500.00 require a keyword-only `approved_by`; raise `BillingError("approval_required")` when it is missing, using `APPROVAL_THRESHOLD = round_money("500.00")`.
- UPDATE `at-0001`: confirmed again by verified task E04

### E05 (first attempt passed)
- UPDATE `at-0001`: confirmed again by verified task E05
- ADD `at-0005` Raise BillingError with code and detail: Signal invalid input by raising `ledgerly.errors.BillingError(code, detail)` with a snake_case code string, e.g. `BillingError("invalid_tax_rate", str(rate_percent))`.
- ADD `at-0006` Parse rates via Decimal(str(...)): When a numeric argument may be a float, parse it with `Decimal(str(value))` and catch `InvalidOperation`/`ValueError` rather than passing it to `to_money`, which rejects floats.

### E06 (first attempt failed)
- REJECT (not applied in the verified change: no added line of the diff matches applied_in_diff): Every operation that moves money or changes a payment/credit (e.g. authorize, capture in ledgerly/payments.py) must accept a keyword-only `idempotency_key` and skip re-applying if an audit entry with that key already exists in ledgerly.audit.events(); include `idempotency_key` in the audit.record call.
- REJECT (not applied in the verified change: no added line of the diff matches applied_in_diff): Idempotency is detected by scanning ledgerly.audit.events() for an entry whose `idempotency_key` matches; a helper `_already_applied(idempotency_key)` returning False for None is the established pattern in ledgerly/payments.py.

### Shown for H04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0002] Normalize unit prices with to_money: Wrap line unit prices with ledgerly.money.to_money before multiplying by quantity, and seed sums with ledgerly.money.ZERO, matching line_total and invoice_total in ledgerly/invoice.py.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0003] Money operations need keyword-only idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early, and pass `idempotency_key` into `audit.record`.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0001] Round money only via round_money: Always round monetary results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0004] Refunds above 500 need approved_by: Support-initiated refunds/credits above 500.00 require a keyword-only `approved_by`; raise `BillingError("approval_required")` when it is missing, using `APPROVAL_THRESHOLD = round_money("500.00")`.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0006] Parse rates via Decimal(str(...)): When a numeric argument may be a float, parse it with `Decimal(str(value))` and catch `InvalidOperation`/`ValueError` rather than passing it to `to_money`, which rejects floats.
  (learned from task E05 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0005] Raise BillingError with code and detail: Signal invalid input by raising `ledgerly.errors.BillingError(code, detail)` with a snake_case code string, e.g. `BillingError("invalid_tax_rate", str(rate_percent))`.
  (learned from task E05 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
```

### Shown for B01

```
(nothing)
```

### Shown for S04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0004] Refunds above 500 need approved_by: Support-initiated refunds/credits above 500.00 require a keyword-only `approved_by`; raise `BillingError("approval_required")` when it is missing, using `APPROVAL_THRESHOLD = round_money("500.00")`.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0002] Normalize unit prices with to_money: Wrap line unit prices with ledgerly.money.to_money before multiplying by quantity, and seed sums with ledgerly.money.ZERO, matching line_total and invoice_total in ledgerly/invoice.py.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0003] Money operations need keyword-only idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early, and pass `idempotency_key` into `audit.record`.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0001] Round money only via round_money: Always round monetary results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0005] Raise BillingError with code and detail: Signal invalid input by raising `ledgerly.errors.BillingError(code, detail)` with a snake_case code string, e.g. `BillingError("invalid_tax_rate", str(rate_percent))`.
  (learned from task E05 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0006] Parse rates via Decimal(str(...)): When a numeric argument may be a float, parse it with `Decimal(str(value))` and catch `InvalidOperation`/`ValueError` rather than passing it to `to_money`, which rejects floats.
  (learned from task E05 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
```

