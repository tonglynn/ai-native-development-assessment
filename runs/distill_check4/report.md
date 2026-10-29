# Write-path check (before freeze)

Source trajectories: `runs/pilot3_nomem` (no memory).

## reasoningbank

### E01 (first attempt failed)
- ADD `rb-0001` Use project money helpers for rounding: Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- ADD `rb-0002` Read existing sibling functions for conventions: When adding a function, inspect neighboring functions like line_total and invoice_total first. They show how money is normalized (to_money), rounded (round_money), and summed with a ZERO start value, so mirror those patterns.
- ADD `rb-0003` Guard division by zero explicitly: Compute total_quantity first and return ZERO if it is falsy, then perform the weighted division. This satisfies the 'invoice without lines has average zero' requirement and avoids ZeroDivisionError.

### E02 (first attempt passed)
- ADD `rb-0004` Read existing modules to match error codes and conventions: Grep for similar validation (e.g. status checks, amount checks) in other modules and reuse the same BillingError codes and message formats. This keeps behavior consistent and satisfies hidden tests expecting specific codes like 'invalid_state' or 'negative_amount'.
- ADD `rb-0005` Guard against bool being an int in type checks: Use `isinstance(x, bool) or not isinstance(x, int) or x <= 0` to reject booleans, floats, and non-positive values. Hidden tests often probe True/False and float inputs.
- ADD `rb-0006` Normalize money inputs via existing to_money helper: Call to_money(unit_price) first, then compare against ZERO for negativity, and store the normalized Decimal on the LineItem. This matches how other modules (e.g. payments) handle amounts.

### E03 (first attempt passed)
- ADD `rb-0007` Reuse existing period arithmetic helpers: Search the codebase for similar functions (e.g., `current_period`) and reuse their exact arithmetic: `n = (at - start) // length`, `start + n * length`. For 'strictly after', add `+ 1` to the quotient; for 'before start', return `start + length`.
- ADD `rb-0008` Normalize datetimes with the repo's ensure_utc: Before doing datetime arithmetic, run inputs through the repo's `ensure_utc` (from `ledgerly/clock.py`) so naive datetimes raise the expected `BillingError` and tz-aware values are converted to UTC, matching existing conventions.
- ADD `rb-0009` Read the hidden-test-adjacent test file first: Before implementing, cat the test file for the target function and grep for related model fields (`started_at`, `period_days`). This reveals constructor signatures, expected return values, and edge cases (boundary, before-start) so the first attempt passes.

### E04 (first attempt failed)
- ADD `rb-0010` Check repo conventions before implementing money-moving functions: Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and audit calls to discover required keyword-only params like idempotency_key and approved_by. Hidden tests often enforce conventions documented only in code or review comments, not the issue.
- ADD `rb-0011` Implement idempotency via audit-event lookup: Add `*, idempotency_key=None` to the signature; before mutating state, scan `audit.events()` for an entry whose `idempotency_key` matches and return the object unchanged if found. Always include `idempotency_key` in the audit entry you write so retries are detectable.
- ADD `rb-0012` Enforce approval threshold for large refunds: Define APPROVAL_THRESHOLD = round_money("500.00") and check `amount > APPROVAL_THRESHOLD and not approved_by` before applying the refund. Record approved_by in the audit entry for traceability.

### E05 (first attempt passed)
- ADD `rb-0013` Reuse existing money helpers for Decimal-safe arithmetic: Inspect ledgerly/money.py and similar modules first; to_money rejects floats and normalizes inputs, round_money applies the finance rounding policy. Composing these keeps behavior consistent with the rest of the codebase and satisfies hidden tests on rounding.
- ADD `rb-0014` Validate numeric inputs before arithmetic: Convert with Decimal(str(x)) inside try/except InvalidOperation/ValueError, then reject non-finite or out-of-range values via BillingError('invalid_tax_rate', ...). This matches existing error conventions and avoids leaking raw Decimal exceptions.
- ADD `rb-0015` Read tests and sibling modules before writing code: Before implementing, cat the target module, its tests, and related utility modules (money, errors) plus grep for existing usages; mirror their patterns (imports, error codes, rounding) rather than inventing new ones.

### E06 (first attempt failed)
- ADD `rb-0016` Check repo conventions before implementing money/state operations: Before implementing any payment/credit/state-changing function, scan README, CHANGELOG, and existing sibling functions (e.g. authorize) for conventions like idempotency keys, audit fields, or keyword-only params. Mirror the existing function's signature and audit.record fields rather than inventing a minimal version.
- ADD `rb-0017` Implement idempotency via audit-event lookup: Add a private helper like `_already_applied(idempotency_key)` that returns False for None and otherwise scans `audit.events()` for `e.get("idempotency_key") == idempotency_key`. Call it at the top of each operation, and always pass `idempotency_key=...` into the audit.record call so future replays are detected.
- ADD `rb-0018` Validate state before mutating, normalize datetimes: Order matters: check `payment.status != "authorized"` and raise before any mutation, then `at = ensure_utc(at)`, set `payment.status = "captured"` and `payment.captured_at = at`, and finally `audit.record("payment_captured", payment_id=..., amount=..., idempotency_key=...)`. Return the payment object.

### Shown for H04

```
Memory items from past tasks:
- [rb-0016] Check repo conventions before implementing money/state operations: The first attempt failed because it missed a team convention (keyword-only idempotency_key on money-moving operations) that wasn't in the issue text.
  Before implementing any payment/credit/state-changing function, scan README, CHANGELOG, and existing sibling functions (e.g. authorize) for conventions like idempotency keys, audit fields, or keyword-only params. Mirror the existing function's signature and audit.record fields rather than inventing a minimal version.
- [rb-0002] Read existing sibling functions for conventions: Existing functions in the same module reveal the expected patterns (rounding, type hints, zero handling) before writing new code.
  When adding a function, inspect neighboring functions like line_total and invoice_total first. They show how money is normalized (to_money), rounded (round_money), and summed with a ZERO start value, so mirror those patterns.
- [rb-0005] Guard against bool being an int in type checks: When validating that a value is a positive integer, explicitly exclude bool since isinstance(True, int) is True.
  Use `isinstance(x, bool) or not isinstance(x, int) or x <= 0` to reject booleans, floats, and non-positive values. Hidden tests often probe True/False and float inputs.
- [rb-0003] Guard division by zero explicitly: Return the module's ZERO constant when total quantity is zero rather than dividing.
  Compute total_quantity first and return ZERO if it is falsy, then perform the weighted division. This satisfies the 'invoice without lines has average zero' requirement and avoids ZeroDivisionError.
- [rb-0006] Normalize money inputs via existing to_money helper: Convert unit_price through the project's to_money/round_money helpers before comparing or storing, so strings and Decimals are handled uniformly.
  Call to_money(unit_price) first, then compare against ZERO for negativity, and store the normalized Decimal on the LineItem. This matches how other modules (e.g. payments) handle amounts.
- [rb-0010] Check repo conventions before implementing money-moving functions: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but were expected by hidden tests.
  Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and audit calls to discover required keyword-only params like idempotency_key and approved_by. Hidden tests often enforce conventions documented only in code or review comments, not the issue.
```

### Shown for B01

```
Memory items from past tasks:
- [rb-0006] Normalize money inputs via existing to_money helper: Convert unit_price through the project's to_money/round_money helpers before comparing or storing, so strings and Decimals are handled uniformly.
  Call to_money(unit_price) first, then compare against ZERO for negativity, and store the normalized Decimal on the LineItem. This matches how other modules (e.g. payments) handle amounts.
- [rb-0014] Validate numeric inputs before arithmetic: Check range and finiteness of user-supplied rates/amounts and raise the project's domain error (BillingError) with a stable code.
  Convert with Decimal(str(x)) inside try/except InvalidOperation/ValueError, then reject non-finite or out-of-range values via BillingError('invalid_tax_rate', ...). This matches existing error conventions and avoids leaking raw Decimal exceptions.
- [rb-0004] Read existing modules to match error codes and conventions: Before implementing a new function, inspect sibling modules for established error codes, helper functions, and validation patterns.
  Grep for similar validation (e.g. status checks, amount checks) in other modules and reuse the same BillingError codes and message formats. This keeps behavior consistent and satisfies hidden tests expecting specific codes like 'invalid_state' or 'negative_amount'.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- [rb-0013] Reuse existing money helpers for Decimal-safe arithmetic: When implementing monetary functions, delegate to the repo's existing to_money/round_money helpers instead of raw Decimal or float math.
  Inspect ledgerly/money.py and similar modules first; to_money rejects floats and normalizes inputs, round_money applies the finance rounding policy. Composing these keeps behavior consistent with the rest of the codebase and satisfies hidden tests on rounding.
- [rb-0010] Check repo conventions before implementing money-moving functions: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but were expected by hidden tests.
  Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and audit calls to discover required keyword-only params like idempotency_key and approved_by. Hidden tests often enforce conventions documented only in code or review comments, not the issue.
```

### Shown for S04

```
Memory items from past tasks:
- [rb-0005] Guard against bool being an int in type checks: When validating that a value is a positive integer, explicitly exclude bool since isinstance(True, int) is True.
  Use `isinstance(x, bool) or not isinstance(x, int) or x <= 0` to reject booleans, floats, and non-positive values. Hidden tests often probe True/False and float inputs.
- [rb-0016] Check repo conventions before implementing money/state operations: The first attempt failed because it missed a team convention (keyword-only idempotency_key on money-moving operations) that wasn't in the issue text.
  Before implementing any payment/credit/state-changing function, scan README, CHANGELOG, and existing sibling functions (e.g. authorize) for conventions like idempotency keys, audit fields, or keyword-only params. Mirror the existing function's signature and audit.record fields rather than inventing a minimal version.
- [rb-0002] Read existing sibling functions for conventions: Existing functions in the same module reveal the expected patterns (rounding, type hints, zero handling) before writing new code.
  When adding a function, inspect neighboring functions like line_total and invoice_total first. They show how money is normalized (to_money), rounded (round_money), and summed with a ZERO start value, so mirror those patterns.
- [rb-0003] Guard division by zero explicitly: Return the module's ZERO constant when total quantity is zero rather than dividing.
  Compute total_quantity first and return ZERO if it is falsy, then perform the weighted division. This satisfies the 'invoice without lines has average zero' requirement and avoids ZeroDivisionError.
- [rb-0006] Normalize money inputs via existing to_money helper: Convert unit_price through the project's to_money/round_money helpers before comparing or storing, so strings and Decimals are handled uniformly.
  Call to_money(unit_price) first, then compare against ZERO for negativity, and store the normalized Decimal on the LineItem. This matches how other modules (e.g. payments) handle amounts.
- [rb-0010] Check repo conventions before implementing money-moving functions: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but were expected by hidden tests.
  Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and audit calls to discover required keyword-only params like idempotency_key and approved_by. Hidden tests often enforce conventions documented only in code or review comments, not the issue.
```

## ace

### E01 (first attempt failed)
- ADD `ace-0001` domain_facts: In ledgerly, monetary values must be rounded with ledgerly.money.round_money (half-up to the cent); Python's round() and bare Decimal.quantize() use banker's rounding and produce wrong invoice totals.
- ADD `ace-0002` strategies: Before implementing a money-related function, inspect ledgerly/money.py and existing helpers (line_total, invoice_total) to reuse to_money/round_money/ZERO and match the repo's rounding conventions.
- ADD `ace-0003` common_mistakes: Returning an unrounded Decimal division for a money value (e.g. weighted_total / total_quantity) fails review; wrap the final monetary result in round_money, and return ZERO for empty/zero-quantity inputs.

### E02 (first attempt passed)
- UPDATE `ace-0002`: reflector: helpful in E02
- UPDATE `ace-0003`: reflector: helpful in E02
- UPDATE `ace-0001`: reflector: helpful in E02
- ADD `ace-0004` strategies: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.authorize's `invoice.status != "issued"` -> "invalid_state") and mirror them so error codes and messages stay consistent.
- ADD `ace-0005` common_mistakes: Accepting bool as an int for quantity validation: `isinstance(True, int)` is True, so explicitly reject bools (e.g. `isinstance(quantity, bool) or not isinstance(quantity, int)`) before checking positivity.
- ADD `ace-0006` domain_facts: In ledgerly, invoice.status is one of draft|issued|paid|void; line items may only be added while status == "draft", and invalid state transitions raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}").

### E03 (first attempt passed)
- UPDATE `ace-0002`: reflector: helpful in E03
- UPDATE `ace-0004`: reflector: helpful in E03
- ADD `ace-0007` strategies: Before implementing a date/time function, inspect sibling modules (e.g. ledgerly/subscriptions.py current_period) and ledgerly/clock.py to reuse ensure_utc and mirror the existing floor-division period arithmetic pattern.
- ADD `ace-0008` common_mistakes: Computing the next occurrence with `(after - start) // length` alone returns the current period start when `after` is exactly on a boundary; add +1 to get the first occurrence strictly after `after`, and handle `after < start` separately.
- ADD `ace-0009` domain_facts: In ledgerly, datetimes must be normalized with ledgerly.clock.ensure_utc, which raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime inputs; subscriptions expose started_at and period_days.

### E04 (first attempt failed)
- UPDATE `ace-0001`: reflector: helpful in E04
- UPDATE `ace-0002`: reflector: helpful in E04
- UPDATE `ace-0004`: reflector: helpful in E04
- UPDATE `ace-0006`: reflector: helpful in E04
- UPDATE `ace-0009`: reflector: helpful in E04
- ADD `ace-0010` domain_facts: In ledgerly, every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; if an audit entry with that key already exists in ledgerly.audit.events(), return without reapplying, and include idempotency_key in the audit entry written (team convention after INC-204).
- ADD `ace-0011` domain_facts: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only `approved_by` and raise BillingError("approval_required") when it is missing for amounts above the threshold.
- ADD `ace-0012` strategies: Before implementing a money-moving function, grep the repo (README, CHANGELOG, tests, audit.py) for team conventions and policy codes (idempotency_key, approved_by, approval thresholds) that hidden tests may enforce but that are not stated in the issue text.

### E05 (first attempt passed)
- UPDATE `ace-0002`: reflector: helpful in E05
- UPDATE `ace-0001`: reflector: helpful in E05
- UPDATE `ace-0004`: reflector: helpful in E05
- ADD `ace-0013` common_mistakes: Passing a float tax rate (e.g. 7.5) through to_money raises BillingError('float_amount') because to_money rejects floats; convert rates with Decimal(str(rate_percent)) instead, and catch InvalidOperation/ValueError to raise a domain-specific error like BillingError('invalid_tax_rate').
- ADD `ace-0014` domain_facts: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); use it for monetary amounts but not for non-money numeric parameters like percentages or rates.
- ADD `ace-0015` strategies: When a numeric parameter has a documented range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before computing, raising a BillingError with a descriptive code.

### E06 (first attempt failed)

### Shown for H04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0002] helpful=4 harmful=0 :: Before implementing a money-related function, inspect ledgerly/money.py and existing helpers (line_total, invoice_total) to reuse to_money/round_money/ZERO and match the repo's rounding conventions.
[ace-0004] helpful=3 harmful=0 :: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.authorize's `invoice.status != "issued"` -> "invalid_state") and mirror them so error codes and messages stay consistent.
[ace-0007] helpful=0 harmful=0 :: Before implementing a date/time function, inspect sibling modules (e.g. ledgerly/subscriptions.py current_period) and ledgerly/clock.py to reuse ensure_utc and mirror the existing floor-division period arithmetic pattern.
[ace-0012] helpful=0 harmful=0 :: Before implementing a money-moving function, grep the repo (README, CHANGELOG, tests, audit.py) for team conventions and policy codes (idempotency_key, approved_by, approval thresholds) that hidden tests may enforce but that are not stated in the issue text.
[ace-0015] helpful=0 harmful=0 :: When a numeric parameter has a documented range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before computing, raising a BillingError with a descriptive code.
## common_mistakes
[ace-0003] helpful=1 harmful=0 :: Returning an unrounded Decimal division for a money value (e.g. weighted_total / total_quantity) fails review; wrap the final monetary result in round_money, and return ZERO for empty/zero-quantity inputs.
[ace-0005] helpful=0 harmful=0 :: Accepting bool as an int for quantity validation: `isinstance(True, int)` is True, so explicitly reject bools (e.g. `isinstance(quantity, bool) or not isinstance(quantity, int)`) before checking positivity.
[ace-0008] helpful=0 harmful=0 :: Computing the next occurrence with `(after - start) // length` alone returns the current period start when `after` is exactly on a boundary; add +1 to get the first occurrence strictly after `after`, and handle `after < start` separately.
[ace-0013] helpful=0 harmful=0 :: Passing a float tax rate (e.g. 7.5) through to_money raises BillingError('float_amount') because to_money rejects floats; convert rates with Decimal(str(rate_percent)) instead, and catch InvalidOperation/ValueError to raise a domain-specific error like BillingError('invalid_tax_rate').
## domain_facts
[ace-0001] helpful=3 harmful=0 :: In ledgerly, monetary values must be rounded with ledgerly.money.round_money (half-up to the cent); Python's round() and bare Decimal.quantize() use banker's rounding and produce wrong invoice totals.
[ace-0006] helpful=1 harmful=0 :: In ledgerly, invoice.status is one of draft|issued|paid|void; line items may only be added while status == "draft", and invalid state transitions raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}").
[ace-0009] helpful=1 harmful=0 :: In ledgerly, datetimes must be normalized with ledgerly.clock.ensure_utc, which raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime inputs; subscriptions expose started_at and period_days.
[ace-0010] helpful=0 harmful=0 :: In ledgerly, every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; if an audit entry with that key already exists in ledgerly.audit.events(), return without reapplying, and include idempotency_key in the audit entry written (team convention after INC-204).
[ace-0011] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only `approved_by` and raise BillingError("approval_required") when it is missing for amounts above the threshold.
[ace-0014] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); use it for monetary amounts but not for non-money numeric parameters like percentages or rates.
```

### Shown for B01

```
Playbook (accumulated from past tasks):
## strategies
[ace-0002] helpful=4 harmful=0 :: Before implementing a money-related function, inspect ledgerly/money.py and existing helpers (line_total, invoice_total) to reuse to_money/round_money/ZERO and match the repo's rounding conventions.
[ace-0004] helpful=3 harmful=0 :: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.authorize's `invoice.status != "issued"` -> "invalid_state") and mirror them so error codes and messages stay consistent.
[ace-0007] helpful=0 harmful=0 :: Before implementing a date/time function, inspect sibling modules (e.g. ledgerly/subscriptions.py current_period) and ledgerly/clock.py to reuse ensure_utc and mirror the existing floor-division period arithmetic pattern.
[ace-0012] helpful=0 harmful=0 :: Before implementing a money-moving function, grep the repo (README, CHANGELOG, tests, audit.py) for team conventions and policy codes (idempotency_key, approved_by, approval thresholds) that hidden tests may enforce but that are not stated in the issue text.
[ace-0015] helpful=0 harmful=0 :: When a numeric parameter has a documented range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before computing, raising a BillingError with a descriptive code.
## common_mistakes
[ace-0003] helpful=1 harmful=0 :: Returning an unrounded Decimal division for a money value (e.g. weighted_total / total_quantity) fails review; wrap the final monetary result in round_money, and return ZERO for empty/zero-quantity inputs.
[ace-0005] helpful=0 harmful=0 :: Accepting bool as an int for quantity validation: `isinstance(True, int)` is True, so explicitly reject bools (e.g. `isinstance(quantity, bool) or not isinstance(quantity, int)`) before checking positivity.
[ace-0008] helpful=0 harmful=0 :: Computing the next occurrence with `(after - start) // length` alone returns the current period start when `after` is exactly on a boundary; add +1 to get the first occurrence strictly after `after`, and handle `after < start` separately.
[ace-0013] helpful=0 harmful=0 :: Passing a float tax rate (e.g. 7.5) through to_money raises BillingError('float_amount') because to_money rejects floats; convert rates with Decimal(str(rate_percent)) instead, and catch InvalidOperation/ValueError to raise a domain-specific error like BillingError('invalid_tax_rate').
## domain_facts
[ace-0001] helpful=3 harmful=0 :: In ledgerly, monetary values must be rounded with ledgerly.money.round_money (half-up to the cent); Python's round() and bare Decimal.quantize() use banker's rounding and produce wrong invoice totals.
[ace-0006] helpful=1 harmful=0 :: In ledgerly, invoice.status is one of draft|issued|paid|void; line items may only be added while status == "draft", and invalid state transitions raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}").
[ace-0009] helpful=1 harmful=0 :: In ledgerly, datetimes must be normalized with ledgerly.clock.ensure_utc, which raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime inputs; subscriptions expose started_at and period_days.
[ace-0010] helpful=0 harmful=0 :: In ledgerly, every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; if an audit entry with that key already exists in ledgerly.audit.events(), return without reapplying, and include idempotency_key in the audit entry written (team convention after INC-204).
[ace-0011] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only `approved_by` and raise BillingError("approval_required") when it is missing for amounts above the threshold.
[ace-0014] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); use it for monetary amounts but not for non-money numeric parameters like percentages or rates.
```

### Shown for S04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0002] helpful=4 harmful=0 :: Before implementing a money-related function, inspect ledgerly/money.py and existing helpers (line_total, invoice_total) to reuse to_money/round_money/ZERO and match the repo's rounding conventions.
[ace-0004] helpful=3 harmful=0 :: Before implementing a validation-heavy function, grep the repo for existing BillingError codes and state-check patterns (e.g. payments.authorize's `invoice.status != "issued"` -> "invalid_state") and mirror them so error codes and messages stay consistent.
[ace-0007] helpful=0 harmful=0 :: Before implementing a date/time function, inspect sibling modules (e.g. ledgerly/subscriptions.py current_period) and ledgerly/clock.py to reuse ensure_utc and mirror the existing floor-division period arithmetic pattern.
[ace-0012] helpful=0 harmful=0 :: Before implementing a money-moving function, grep the repo (README, CHANGELOG, tests, audit.py) for team conventions and policy codes (idempotency_key, approved_by, approval thresholds) that hidden tests may enforce but that are not stated in the issue text.
[ace-0015] helpful=0 harmful=0 :: When a numeric parameter has a documented range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before computing, raising a BillingError with a descriptive code.
## common_mistakes
[ace-0003] helpful=1 harmful=0 :: Returning an unrounded Decimal division for a money value (e.g. weighted_total / total_quantity) fails review; wrap the final monetary result in round_money, and return ZERO for empty/zero-quantity inputs.
[ace-0005] helpful=0 harmful=0 :: Accepting bool as an int for quantity validation: `isinstance(True, int)` is True, so explicitly reject bools (e.g. `isinstance(quantity, bool) or not isinstance(quantity, int)`) before checking positivity.
[ace-0008] helpful=0 harmful=0 :: Computing the next occurrence with `(after - start) // length` alone returns the current period start when `after` is exactly on a boundary; add +1 to get the first occurrence strictly after `after`, and handle `after < start` separately.
[ace-0013] helpful=0 harmful=0 :: Passing a float tax rate (e.g. 7.5) through to_money raises BillingError('float_amount') because to_money rejects floats; convert rates with Decimal(str(rate_percent)) instead, and catch InvalidOperation/ValueError to raise a domain-specific error like BillingError('invalid_tax_rate').
## domain_facts
[ace-0001] helpful=3 harmful=0 :: In ledgerly, monetary values must be rounded with ledgerly.money.round_money (half-up to the cent); Python's round() and bare Decimal.quantize() use banker's rounding and produce wrong invoice totals.
[ace-0006] helpful=1 harmful=0 :: In ledgerly, invoice.status is one of draft|issued|paid|void; line items may only be added while status == "draft", and invalid state transitions raise BillingError("invalid_state", f"invoice {invoice.id} is {invoice.status}").
[ace-0009] helpful=1 harmful=0 :: In ledgerly, datetimes must be normalized with ledgerly.clock.ensure_utc, which raises BillingError('naive_datetime') for naive datetimes and BillingError('invalid_datetime') for non-datetime inputs; subscriptions expose started_at and period_days.
[ace-0010] helpful=0 harmful=0 :: In ledgerly, every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; if an audit entry with that key already exists in ledgerly.audit.events(), return without reapplying, and include idempotency_key in the audit entry written (team convention after INC-204).
[ace-0011] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only `approved_by` and raise BillingError("approval_required") when it is missing for amounts above the threshold.
[ace-0014] helpful=0 harmful=0 :: In ledgerly, to_money rejects bool and float inputs with BillingError('float_amount') and non-numeric strings with BillingError('invalid_amount'); use it for monetary amounts but not for non-money numeric parameters like percentages or rates.
```

## attest

### E01 (first attempt failed)
- ADD `at-0001` Round money with round_money, not bare division: Always wrap monetary results in ledgerly.money.round_money (half-up to the cent); never return a bare Decimal division or use Python's round()/quantize(), which use banker's rounding.
- REJECT (evidence quote not found verbatim in the review comments or the diff): Use ledgerly.money's ZERO, round_money, and to_money helpers for all money arithmetic; coerce unit prices with to_money and seed sums with ZERO.

### E02 (first attempt passed)
- ADD `at-0002` Use BillingError with machine-readable codes: Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, using existing codes like "invalid_state" and "negative_amount" rather than ValueError.
- ADD `at-0003` Normalize amounts via to_money and ZERO: Convert incoming amounts with `to_money` from `ledgerly/money.py` and compare against `ZERO` before storing on models.
- ADD `at-0004` Reject bool where int is required: When validating integer inputs, explicitly reject `bool` via `isinstance(x, bool)` since Python treats True/False as ints.

### E03 (first attempt passed)
- ADD `at-0005` Normalize datetimes with ensure_utc: Normalize all incoming datetimes with `ensure_utc` from `ledgerly.clock` before arithmetic; it raises `BillingError` for naive or non-datetime values.
- REJECT (evidence quote not found verbatim in the review comments or the diff): Compute billing periods the same way as `current_period` in `ledgerly/subscriptions.py`: `length = timedelta(days=sub.period_days)` and `n = (at - start) // length`.

### E04 (first attempt failed)
- ADD `at-0006` Money-moving ops need idempotency_key: Every operation that moves money or changes a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and include `idempotency_key` in the audit entry written.
- ADD `at-0007` Refunds above 500 need approved_by: Support-initiated refunds and credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing for amounts above the threshold.

### E05 (first attempt passed)
- UPDATE `at-0001`: confirmed again by verified task E05
- UPDATE `at-0002`: confirmed again by verified task E05

### E06 (first attempt failed)
- UPDATE `at-0006`: confirmed again by verified task E06
- UPDATE `at-0006`: confirmed again by verified task E06
- UPDATE `at-0005`: confirmed again by verified task E06

### Shown for H04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0003] Normalize amounts via to_money and ZERO: Convert incoming amounts with `to_money` from `ledgerly/money.py` and compare against `ZERO` before storing on models.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0006] Money-moving ops need idempotency_key: Every operation that moves money or changes a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and include `idempotency_key` in the audit entry written.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0002] Use BillingError with machine-readable codes: Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, using existing codes like "invalid_state" and "negative_amount" rather than ValueError.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0001] Round money with round_money, not bare division: Always wrap monetary results in ledgerly.money.round_money (half-up to the cent); never return a bare Decimal division or use Python's round()/quantize(), which use banker's rounding.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0004] Reject bool where int is required: When validating integer inputs, explicitly reject `bool` via `isinstance(x, bool)` since Python treats True/False as ints.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0005] Normalize datetimes with ensure_utc: Normalize all incoming datetimes with `ensure_utc` from `ledgerly.clock` before arithmetic; it raises `BillingError` for naive or non-datetime values.
  (learned from task E03 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
```

### Shown for B01

```
(nothing)
```

### Shown for S04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0007] Refunds above 500 need approved_by: Support-initiated refunds and credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing for amounts above the threshold.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0002] Use BillingError with machine-readable codes: Raise `BillingError(code, detail)` from `ledgerly/errors.py` for domain validation failures, using existing codes like "invalid_state" and "negative_amount" rather than ValueError.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0003] Normalize amounts via to_money and ZERO: Convert incoming amounts with `to_money` from `ledgerly/money.py` and compare against `ZERO` before storing on models.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0006] Money-moving ops need idempotency_key: Every operation that moves money or changes a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and include `idempotency_key` in the audit entry written.
  (learned from task E04 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0001] Round money with round_money, not bare division: Always wrap monetary results in ledgerly.money.round_money (half-up to the cent); never return a bare Decimal division or use Python's round()/quantize(), which use banker's rounding.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0004] Reject bool where int is required: When validating integer inputs, explicitly reject `bool` via `isinstance(x, bool)` since Python treats True/False as ints.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
```

