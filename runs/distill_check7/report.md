# Write-path check (before freeze)

Source trajectories: `runs/pilot3_nomem` (no memory).

## reasoningbank

### E01 (first attempt failed)
- ADD `rb-0001` Use project money helpers for rounding: Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- ADD `rb-0002` Read existing module code before implementing: When adding a function to an existing module, inspect its imports and sibling functions (e.g. line_total, invoice_total) to mirror established patterns like to_money() coercion and round_money() wrapping.
- ADD `rb-0003` Verify rounding edge cases explicitly: After implementing money math, run a quick script with a half-cent case (e.g. weighted average ending in .005) to confirm half-up behavior, since hidden tests likely check this and the visible suite may not.

### E02 (first attempt passed)
- ADD `rb-0004` Read sibling modules to match error codes and conventions: Search for existing usages of the error class and analogous functions (e.g. payments.py used `invalid_state` with `f"invoice {invoice.id} is {invoice.status}"`). Mirroring these conventions makes the new code consistent and satisfies hidden tests expecting specific codes.
- ADD `rb-0005` Guard bool when validating integer inputs: Use `isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0` to reject True/False, floats, and non-positive values. Hidden tests often probe bool inputs as a trap.
- ADD `rb-0006` Normalize money via to_money before comparing to ZERO: Call `price = to_money(unit_price)` first, then `if price < ZERO: raise BillingError("negative_amount", str(price))`, and store the normalized Decimal on the LineItem. This handles string inputs and keeps line_total math correct.

### E03 (first attempt passed)
- ADD `rb-0007` Reuse existing period arithmetic helpers: Search for sibling functions computing the same period math (e.g. current_period) and reuse their pattern: normalize with ensure_utc, compute length = timedelta(days=period_days), and use floor division (at - start) // length. This keeps edge-case behavior consistent across modules.
- ADD `rb-0008` Handle 'strictly after' with floor division plus one: Floor division gives the index of the period containing `after`; adding 1 yields the next boundary, which is strictly after even when `after` lands exactly on a boundary. Guard the before-start case separately (return start + length).
- ADD `rb-0009` Normalize datetimes via the project's ensure_utc: The codebase's ensure_utc raises BillingError for naive/invalid datetimes and converts to UTC. Calling it on both `after` and `sub.started_at` before arithmetic ensures consistent comparison and matches project conventions.

### E04 (first attempt failed)
- ADD `rb-0010` Check repo conventions before implementing money operations: Before implementing any payment/credit/refund function, grep the repo for existing money-moving operations and read their signatures and audit calls. Conventions like keyword-only idempotency_key and approval thresholds are often enforced by hidden tests even when the issue doesn't mention them.
- ADD `rb-0011` Make money operations idempotent via audit lookup: Implement a helper that scans ledgerly.audit.events() for a matching idempotency_key and returns early (returning the payment unchanged) if found. Always pass idempotency_key into the audit.record call so retries are detectable.
- ADD `rb-0012` Enforce approval threshold for large support refunds: Define APPROVAL_THRESHOLD = round_money("500.00") and check `amount > APPROVAL_THRESHOLD and not approved_by` before applying the operation. Include approved_by in the audit entry for traceability.

### E05 (first attempt passed)
- ADD `rb-0013` Reuse existing money helpers for Decimal math: Inspect ledgerly/money.py and sibling modules (invoice.py, payments.py) first; they define to_money, round_money, and BillingError conventions. Reusing them gives consistent rounding policy and error codes for free.
- ADD `rb-0014` Validate numeric inputs before arithmetic: Convert with Decimal(str(x)) inside try/except InvalidOperation/ValueError, then reject non-finite or out-of-range values with BillingError('invalid_tax_rate', ...). This matches how other modules signal bad input.
- ADD `rb-0015` Smoke-test edge cases beyond the visible test: After implementing, run a quick script calling the function with Decimal, str, and boundary/invalid rates to catch type-handling bugs (e.g. to_money rejecting floats) that the single visible test won't reveal.

### E06 (first attempt failed)
- ADD `rb-0016` Check repo conventions before implementing money-moving operations: Before implementing any operation that changes a payment, credit, or moves money, scan the repo (CHANGELOG, README, existing functions, audit module) for conventions like idempotency keys. Apply the convention to the new function and to related existing functions it mirrors.
- ADD `rb-0017` Implement idempotency via audit-event lookup: Add a helper like `_already_applied(key)` that returns False for None and otherwise scans audit.events() for an entry with that idempotency_key. Call it at the top of the operation and return the existing object (or None) without mutating state if already applied.
- ADD `rb-0018` Record idempotency_key in every audit entry you write: When writing audit.record(...) for a money-moving operation, always pass idempotency_key=idempotency_key alongside the other fields. Without it, the duplicate-detection lookup will never match and idempotency silently fails.

### Shown for H04

```
Memory items from past tasks:
- [rb-0016] Check repo conventions before implementing money-moving operations: The first attempt failed because it ignored the team convention requiring keyword-only idempotency_key on all payment/credit mutations.
  Before implementing any operation that changes a payment, credit, or moves money, scan the repo (CHANGELOG, README, existing functions, audit module) for conventions like idempotency keys. Apply the convention to the new function and to related existing functions it mirrors.
- [rb-0012] Enforce approval threshold for large support refunds: Support-initiated refunds/credits above 500.00 require a second approver via keyword-only approved_by, raising BillingError("approval_required") otherwise.
  Define APPROVAL_THRESHOLD = round_money("500.00") and check `amount > APPROVAL_THRESHOLD and not approved_by` before applying the operation. Include approved_by in the audit entry for traceability.
- [rb-0006] Normalize money via to_money before comparing to ZERO: Convert raw unit_price inputs (strings, ints, Decimals) with the project's to_money helper before checking negativity, so comparisons and stored values are consistent.
  Call `price = to_money(unit_price)` first, then `if price < ZERO: raise BillingError("negative_amount", str(price))`, and store the normalized Decimal on the LineItem. This handles string inputs and keeps line_total math correct.
- [rb-0010] Check repo conventions before implementing money operations: The first attempt failed because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before implementing any payment/credit/refund function, grep the repo for existing money-moving operations and read their signatures and audit calls. Conventions like keyword-only idempotency_key and approval thresholds are often enforced by hidden tests even when the issue doesn't mention them.
- [rb-0002] Read existing module code before implementing: The first attempt reimplemented logic without noticing the module already imported round_money, to_money, and ZERO.
  When adding a function to an existing module, inspect its imports and sibling functions (e.g. line_total, invoice_total) to mirror established patterns like to_money() coercion and round_money() wrapping.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
```

### Shown for B01

```
Memory items from past tasks:
- [rb-0006] Normalize money via to_money before comparing to ZERO: Convert raw unit_price inputs (strings, ints, Decimals) with the project's to_money helper before checking negativity, so comparisons and stored values are consistent.
  Call `price = to_money(unit_price)` first, then `if price < ZERO: raise BillingError("negative_amount", str(price))`, and store the normalized Decimal on the LineItem. This handles string inputs and keeps line_total math correct.
- [rb-0014] Validate numeric inputs before arithmetic: Check range and finiteness of rate/percent inputs and raise the project's domain error rather than letting Decimal raise.
  Convert with Decimal(str(x)) inside try/except InvalidOperation/ValueError, then reject non-finite or out-of-range values with BillingError('invalid_tax_rate', ...). This matches how other modules signal bad input.
- [rb-0015] Smoke-test edge cases beyond the visible test: The provided test only covers one happy path; manually exercise string inputs, boundary rates (0, 100), and invalid rates.
  After implementing, run a quick script calling the function with Decimal, str, and boundary/invalid rates to catch type-handling bugs (e.g. to_money rejecting floats) that the single visible test won't reveal.
- [rb-0001] Use project money helpers for rounding: Monetary results must be rounded with the repository's own round_money helper, not Python's round() or bare Decimal.quantize().
  Before returning any money value, check ledgerly/money.py for round_money/to_money/ZERO and use them. Python round() and Decimal.quantize() default to banker's rounding, which produces wrong invoice totals; the team convention is half-up to the cent.
- [rb-0009] Normalize datetimes via the project's ensure_utc: Use the existing ensure_utc helper to validate and convert inputs instead of ad-hoc tzinfo checks.
  The codebase's ensure_utc raises BillingError for naive/invalid datetimes and converts to UTC. Calling it on both `after` and `sub.started_at` before arithmetic ensures consistent comparison and matches project conventions.
- [rb-0004] Read sibling modules to match error codes and conventions: Before implementing a new function, grep the codebase for similar validation patterns and reuse the same BillingError codes and message formats.
  Search for existing usages of the error class and analogous functions (e.g. payments.py used `invalid_state` with `f"invoice {invoice.id} is {invoice.status}"`). Mirroring these conventions makes the new code consistent and satisfies hidden tests expecting specific codes.
```

### Shown for S04

```
Memory items from past tasks:
- [rb-0012] Enforce approval threshold for large support refunds: Support-initiated refunds/credits above 500.00 require a second approver via keyword-only approved_by, raising BillingError("approval_required") otherwise.
  Define APPROVAL_THRESHOLD = round_money("500.00") and check `amount > APPROVAL_THRESHOLD and not approved_by` before applying the operation. Include approved_by in the audit entry for traceability.
- [rb-0016] Check repo conventions before implementing money-moving operations: The first attempt failed because it ignored the team convention requiring keyword-only idempotency_key on all payment/credit mutations.
  Before implementing any operation that changes a payment, credit, or moves money, scan the repo (CHANGELOG, README, existing functions, audit module) for conventions like idempotency keys. Apply the convention to the new function and to related existing functions it mirrors.
- [rb-0006] Normalize money via to_money before comparing to ZERO: Convert raw unit_price inputs (strings, ints, Decimals) with the project's to_money helper before checking negativity, so comparisons and stored values are consistent.
  Call `price = to_money(unit_price)` first, then `if price < ZERO: raise BillingError("negative_amount", str(price))`, and store the normalized Decimal on the LineItem. This handles string inputs and keeps line_total math correct.
- [rb-0002] Read existing module code before implementing: The first attempt reimplemented logic without noticing the module already imported round_money, to_money, and ZERO.
  When adding a function to an existing module, inspect its imports and sibling functions (e.g. line_total, invoice_total) to mirror established patterns like to_money() coercion and round_money() wrapping.
- [rb-0005] Guard bool when validating integer inputs: Python's bool is a subclass of int, so `isinstance(True, int)` is True; explicitly reject bools when requiring a positive integer.
  Use `isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0` to reject True/False, floats, and non-positive values. Hidden tests often probe bool inputs as a trap.
- [rb-0010] Check repo conventions before implementing money operations: The first attempt failed because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before implementing any payment/credit/refund function, grep the repo for existing money-moving operations and read their signatures and audit calls. Conventions like keyword-only idempotency_key and approval thresholds are often enforced by hidden tests even when the issue doesn't mention them.
```

## ace

### E01 (first attempt failed)
- ADD `ace-0001` strategies: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
- ADD `ace-0002` common_mistakes: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
- ADD `ace-0003` strategies: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper, and guard against division by zero (return ZERO for empty inputs).

### E02 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E02
- UPDATE `ace-0003`: reflector: helpful in E02
- ADD `ace-0004` strategies: Before implementing a new function, grep the repo for similar functions (e.g. payments.authorize) and mirror their validation order, error codes, and BillingError message formats so the new code matches existing conventions.
- ADD `ace-0005` common_mistakes: When validating an integer parameter, reject bool explicitly (isinstance(x, bool)) since bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
- ADD `ace-0006` domain_facts: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; state checks compare invoice.status against string literals like 'draft'/'issued'.

### E03 (first attempt passed)
- UPDATE `ace-0004`: reflector: helpful in E03
- ADD `ace-0007` strategies: When implementing a date/time function, reuse the repo's timezone-normalization helper (e.g. ledgerly/clock.py's ensure_utc) on all datetime inputs before comparing or doing arithmetic, and mirror the arithmetic pattern of a sibling function (e.g. subscriptions.current_period's floor-division on timedelta) rather than reinventing it.
- ADD `ace-0008` strategies: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length; handle the after < start case separately (return start + length) since the start itself is not a renewal.
- ADD `ace-0009` common_mistakes: Don't forget the strict-inequality boundary: when after falls exactly on a renewal boundary, the answer must be the next renewal, not that boundary — the +1 in the floor-division formula handles this, but a naive ceil or <= comparison would return the boundary itself.

### E04 (first attempt failed)
- UPDATE `ace-0001`: reflector: helpful in E04
- UPDATE `ace-0004`: reflector: helpful in E04
- UPDATE `ace-0006`: reflector: helpful in E04
- UPDATE `ace-0007`: reflector: helpful in E04
- ADD `ace-0010` strategies: Before implementing any money-moving or payment/credit-mutating function, check the repo's audit module (e.g. ledgerly/audit.py) and README/CHANGELOG for team conventions: accept a keyword-only idempotency_key, short-circuit if an audit entry with that key already exists, and include the key in the audit entry you record.
- ADD `ace-0011` domain_facts: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when it is missing for amounts above the threshold.
- ADD `ace-0012` common_mistakes: Don't implement a payment mutation without checking README/CHANGELOG for post-hoc team conventions (idempotency keys, approval thresholds) — hidden tests enforce them even when the issue text doesn't mention them.

### E05 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E05
- UPDATE `ace-0004`: reflector: helpful in E05
- UPDATE `ace-0006`: reflector: helpful in E05
- ADD `ace-0013` strategies: When a numeric parameter (e.g. a tax rate) must be range-validated, convert it with the repo's to_money/Decimal helper first so strings and Decimals are accepted uniformly, then check bounds and raise BillingError with a descriptive code; note to_money rejects floats/bools, which is usually the desired strictness.
- ADD `ace-0014` common_mistakes: Don't reuse to_money for a percentage/rate parameter without checking its semantics: to_money rejects floats and bools and raises 'float_amount'/'invalid_amount', so a float rate like 7.5 will fail — decide whether to accept floats via Decimal(str(x)) or document the restriction, and test with the value types hidden tests likely use.
- ADD `ace-0015` domain_facts: In ledgerly, pricing.py functions should import round_money/to_money from .money and BillingError from .errors; percentage math is done as base * (1 + rate / Decimal(100)) then round_money, and invalid rates raise BillingError('invalid_tax_rate', ...).

### E06 (first attempt failed)
- UPDATE `ace-0004`: reflector: helpful in E06
- UPDATE `ace-0010`: reflector: helpful in E06
- UPDATE `ace-0012`: reflector: helpful in E06
- UPDATE `ace-0006`: reflector: helpful in E06
- UPDATE `ace-0007`: reflector: helpful in E06
- ADD `ace-0016` strategies: When adding a keyword-only idempotency_key to a mutation, also retrofit sibling mutating functions (e.g. authorize) in the same module to accept and record the key, and factor the duplicate-check into a small helper like _already_applied(key) that scans audit.events() for a matching idempotency_key.
- ADD `ace-0017` common_mistakes: When short-circuiting on an existing idempotency key, return the existing object (e.g. the payment) rather than None, so callers can keep using the return value; returning None from a function typed -> Payment breaks callers and hidden tests.
- ADD `ace-0018` domain_facts: In ledgerly, audit.record(...) accepts arbitrary keyword fields; idempotency entries are detected by scanning audit.events() for a dict with matching 'idempotency_key'. Payment status transitions are string literals ('authorized' -> 'captured'), and capture must set both payment.status and payment.captured_at (UTC-normalized via ensure_utc).

### Shown for H04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=1 harmful=0 :: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper, and guard against division by zero (return ZERO for empty inputs).
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for similar functions (e.g. payments.authorize) and mirror their validation order, error codes, and BillingError message formats so the new code matches existing conventions.
[ace-0007] helpful=2 harmful=0 :: When implementing a date/time function, reuse the repo's timezone-normalization helper (e.g. ledgerly/clock.py's ensure_utc) on all datetime inputs before comparing or doing arithmetic, and mirror the arithmetic pattern of a sibling function (e.g. subscriptions.current_period's floor-division on timedelta) rather than reinventing it.
[ace-0008] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length; handle the after < start case separately (return start + length) since the start itself is not a renewal.
[ace-0010] helpful=1 harmful=0 :: Before implementing any money-moving or payment/credit-mutating function, check the repo's audit module (e.g. ledgerly/audit.py) and README/CHANGELOG for team conventions: accept a keyword-only idempotency_key, short-circuit if an audit entry with that key already exists, and include the key in the audit entry you record.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a tax rate) must be range-validated, convert it with the repo's to_money/Decimal helper first so strings and Decimals are accepted uniformly, then check bounds and raise BillingError with a descriptive code; note to_money rejects floats/bools, which is usually the desired strictness.
[ace-0016] helpful=0 harmful=0 :: When adding a keyword-only idempotency_key to a mutation, also retrofit sibling mutating functions (e.g. authorize) in the same module to accept and record the key, and factor the duplicate-check into a small helper like _already_applied(key) that scans audit.events() for a matching idempotency_key.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter, reject bool explicitly (isinstance(x, bool)) since bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
[ace-0009] helpful=0 harmful=0 :: Don't forget the strict-inequality boundary: when after falls exactly on a renewal boundary, the answer must be the next renewal, not that boundary — the +1 in the floor-division formula handles this, but a naive ceil or <= comparison would return the boundary itself.
[ace-0012] helpful=1 harmful=0 :: Don't implement a payment mutation without checking README/CHANGELOG for post-hoc team conventions (idempotency keys, approval thresholds) — hidden tests enforce them even when the issue text doesn't mention them.
[ace-0014] helpful=0 harmful=0 :: Don't reuse to_money for a percentage/rate parameter without checking its semantics: to_money rejects floats and bools and raises 'float_amount'/'invalid_amount', so a float rate like 7.5 will fail — decide whether to accept floats via Decimal(str(x)) or document the restriction, and test with the value types hidden tests likely use.
[ace-0017] helpful=0 harmful=0 :: When short-circuiting on an existing idempotency key, return the existing object (e.g. the payment) rather than None, so callers can keep using the return value; returning None from a function typed -> Payment breaks callers and hidden tests.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; state checks compare invoice.status against string literals like 'draft'/'issued'.
[ace-0011] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when it is missing for amounts above the threshold.
[ace-0015] helpful=0 harmful=0 :: In ledgerly, pricing.py functions should import round_money/to_money from .money and BillingError from .errors; percentage math is done as base * (1 + rate / Decimal(100)) then round_money, and invalid rates raise BillingError('invalid_tax_rate', ...).
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.record(...) accepts arbitrary keyword fields; idempotency entries are detected by scanning audit.events() for a dict with matching 'idempotency_key'. Payment status transitions are string literals ('authorized' -> 'captured'), and capture must set both payment.status and payment.captured_at (UTC-normalized via ensure_utc).
```

### Shown for B01

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=1 harmful=0 :: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper, and guard against division by zero (return ZERO for empty inputs).
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for similar functions (e.g. payments.authorize) and mirror their validation order, error codes, and BillingError message formats so the new code matches existing conventions.
[ace-0007] helpful=2 harmful=0 :: When implementing a date/time function, reuse the repo's timezone-normalization helper (e.g. ledgerly/clock.py's ensure_utc) on all datetime inputs before comparing or doing arithmetic, and mirror the arithmetic pattern of a sibling function (e.g. subscriptions.current_period's floor-division on timedelta) rather than reinventing it.
[ace-0008] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length; handle the after < start case separately (return start + length) since the start itself is not a renewal.
[ace-0010] helpful=1 harmful=0 :: Before implementing any money-moving or payment/credit-mutating function, check the repo's audit module (e.g. ledgerly/audit.py) and README/CHANGELOG for team conventions: accept a keyword-only idempotency_key, short-circuit if an audit entry with that key already exists, and include the key in the audit entry you record.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a tax rate) must be range-validated, convert it with the repo's to_money/Decimal helper first so strings and Decimals are accepted uniformly, then check bounds and raise BillingError with a descriptive code; note to_money rejects floats/bools, which is usually the desired strictness.
[ace-0016] helpful=0 harmful=0 :: When adding a keyword-only idempotency_key to a mutation, also retrofit sibling mutating functions (e.g. authorize) in the same module to accept and record the key, and factor the duplicate-check into a small helper like _already_applied(key) that scans audit.events() for a matching idempotency_key.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter, reject bool explicitly (isinstance(x, bool)) since bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
[ace-0009] helpful=0 harmful=0 :: Don't forget the strict-inequality boundary: when after falls exactly on a renewal boundary, the answer must be the next renewal, not that boundary — the +1 in the floor-division formula handles this, but a naive ceil or <= comparison would return the boundary itself.
[ace-0012] helpful=1 harmful=0 :: Don't implement a payment mutation without checking README/CHANGELOG for post-hoc team conventions (idempotency keys, approval thresholds) — hidden tests enforce them even when the issue text doesn't mention them.
[ace-0014] helpful=0 harmful=0 :: Don't reuse to_money for a percentage/rate parameter without checking its semantics: to_money rejects floats and bools and raises 'float_amount'/'invalid_amount', so a float rate like 7.5 will fail — decide whether to accept floats via Decimal(str(x)) or document the restriction, and test with the value types hidden tests likely use.
[ace-0017] helpful=0 harmful=0 :: When short-circuiting on an existing idempotency key, return the existing object (e.g. the payment) rather than None, so callers can keep using the return value; returning None from a function typed -> Payment breaks callers and hidden tests.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; state checks compare invoice.status against string literals like 'draft'/'issued'.
[ace-0011] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when it is missing for amounts above the threshold.
[ace-0015] helpful=0 harmful=0 :: In ledgerly, pricing.py functions should import round_money/to_money from .money and BillingError from .errors; percentage math is done as base * (1 + rate / Decimal(100)) then round_money, and invalid rates raise BillingError('invalid_tax_rate', ...).
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.record(...) accepts arbitrary keyword fields; idempotency entries are detected by scanning audit.events() for a dict with matching 'idempotency_key'. Payment status transitions are string literals ('authorized' -> 'captured'), and capture must set both payment.status and payment.captured_at (UTC-normalized via ensure_utc).
```

### Shown for S04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=1 harmful=0 :: When a function computes a ratio or average of monetary values, round the final result with the project's money-rounding helper, and guard against division by zero (return ZERO for empty inputs).
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for similar functions (e.g. payments.authorize) and mirror their validation order, error codes, and BillingError message formats so the new code matches existing conventions.
[ace-0007] helpful=2 harmful=0 :: When implementing a date/time function, reuse the repo's timezone-normalization helper (e.g. ledgerly/clock.py's ensure_utc) on all datetime inputs before comparing or doing arithmetic, and mirror the arithmetic pattern of a sibling function (e.g. subscriptions.current_period's floor-division on timedelta) rather than reinventing it.
[ace-0008] helpful=0 harmful=0 :: For 'first occurrence strictly after X' recurrence problems, compute n = (after - start) // length + 1 and return start + n*length; handle the after < start case separately (return start + length) since the start itself is not a renewal.
[ace-0010] helpful=1 harmful=0 :: Before implementing any money-moving or payment/credit-mutating function, check the repo's audit module (e.g. ledgerly/audit.py) and README/CHANGELOG for team conventions: accept a keyword-only idempotency_key, short-circuit if an audit entry with that key already exists, and include the key in the audit entry you record.
[ace-0013] helpful=0 harmful=0 :: When a numeric parameter (e.g. a tax rate) must be range-validated, convert it with the repo's to_money/Decimal helper first so strings and Decimals are accepted uniformly, then check bounds and raise BillingError with a descriptive code; note to_money rejects floats/bools, which is usually the desired strictness.
[ace-0016] helpful=0 harmful=0 :: When adding a keyword-only idempotency_key to a mutation, also retrofit sibling mutating functions (e.g. authorize) in the same module to accept and record the key, and factor the duplicate-check into a small helper like _already_applied(key) that scans audit.events() for a matching idempotency_key.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding (round-half-to-even), which produces wrong invoice totals; always round monetary results with the project's half-up helper.
[ace-0005] helpful=0 harmful=0 :: When validating an integer parameter, reject bool explicitly (isinstance(x, bool)) since bool is a subclass of int and True/False would otherwise pass an isinstance(x, int) check.
[ace-0009] helpful=0 harmful=0 :: Don't forget the strict-inequality boundary: when after falls exactly on a renewal boundary, the answer must be the next renewal, not that boundary — the +1 in the floor-division formula handles this, but a naive ceil or <= comparison would return the boundary itself.
[ace-0012] helpful=1 harmful=0 :: Don't implement a payment mutation without checking README/CHANGELOG for post-hoc team conventions (idempotency keys, approval thresholds) — hidden tests enforce them even when the issue text doesn't mention them.
[ace-0014] helpful=0 harmful=0 :: Don't reuse to_money for a percentage/rate parameter without checking its semantics: to_money rejects floats and bools and raises 'float_amount'/'invalid_amount', so a float rate like 7.5 will fail — decide whether to accept floats via Decimal(str(x)) or document the restriction, and test with the value types hidden tests likely use.
[ace-0017] helpful=0 harmful=0 :: When short-circuiting on an existing idempotency key, return the existing object (e.g. the payment) rather than None, so callers can keep using the return value; returning None from a function typed -> Payment breaks callers and hidden tests.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, BillingError takes a short machine-readable code (e.g. 'invalid_state', 'negative_amount', 'non_positive_amount') plus a detail string; state checks compare invoice.status against string literals like 'draft'/'issued'.
[ace-0011] helpful=0 harmful=0 :: In ledgerly, support-initiated refunds/credits above 500.00 require a second approver (finance policy FIN-2026-03): accept a keyword-only approved_by and raise BillingError('approval_required') when it is missing for amounts above the threshold.
[ace-0015] helpful=0 harmful=0 :: In ledgerly, pricing.py functions should import round_money/to_money from .money and BillingError from .errors; percentage math is done as base * (1 + rate / Decimal(100)) then round_money, and invalid rates raise BillingError('invalid_tax_rate', ...).
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.record(...) accepts arbitrary keyword fields; idempotency entries are detected by scanning audit.events() for a dict with matching 'idempotency_key'. Payment status transitions are string literals ('authorized' -> 'captured'), and capture must set both payment.status and payment.captured_at (UTC-normalized via ensure_utc).
```

## attest

### E01 (first attempt failed)
- ADD `at-0001` Round money only with round_money: Always round monetary Decimal results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
- ADD `at-0002` Coerce unit prices with to_money: Wrap line unit prices with ledgerly.money.to_money before arithmetic, and seed sums with ledgerly.money.ZERO, as line_total and invoice_total in ledgerly/invoice.py do.

### E02 (first attempt passed)
- ADD `at-0003` Raise BillingError with machine-readable codes: Reject invalid input by raising BillingError(code, detail) from ledgerly.errors, reusing existing codes like "invalid_state" and "negative_amount" and passing the offending value as the message (e.g. str(price), repr(quantity)).
- UPDATE `at-0002`: confirmed again by verified task E02
- ADD `at-0004` Exclude bool when validating integer inputs: When validating an int parameter, check isinstance(x, bool) first because bool is a subclass of int, then require isinstance(x, int) and the range constraint.

### E03 (first attempt passed)
- ADD `at-0005` Normalize datetimes with ensure_utc: In ledgerly, normalize every incoming datetime with `ledgerly.clock.ensure_utc` before comparing or doing arithmetic; it raises BillingError for naive or non-datetime values. Follow the pattern in `ledgerly.subscriptions.current_period`.
- REJECT (source: evidence quote not found verbatim in the review comments or the diff): Compute billing periods with `length = timedelta(days=sub.period_days)` and `n = (at - start) // length`, then `start + n * length`, mirroring `ledgerly.subscriptions.current_period`; do not use day counts or month arithmetic.

### E04 (first attempt failed)
- ADD `at-0006` Money operations require idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and pass `idempotency_key` into `audit.record`.
- ADD `at-0007` Refunds above 500 need approved_by: Support-initiated refunds/credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing.
- UPDATE `at-0001`: confirmed again by verified task E04

### E05 (first attempt passed)
- UPDATE `at-0001`: confirmed again by verified task E05
- UPDATE `at-0003`: confirmed again by verified task E05

### E06 (first attempt failed)
- UPDATE `at-0006`: confirmed again by verified task E06
- UPDATE `at-0006`: confirmed again by verified task E06

### Shown for H04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0002] Coerce unit prices with to_money: Wrap line unit prices with ledgerly.money.to_money before arithmetic, and seed sums with ledgerly.money.ZERO, as line_total and invoice_total in ledgerly/invoice.py do.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0006] Money operations require idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and pass `idempotency_key` into `audit.record`.
  (learned from task E04 on ledgerly 1.0.0; source INC-204; relied on 0x, 0 passed, 0 failed)
- [at-0001] Round money only with round_money: Always round monetary Decimal results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0003] Raise BillingError with machine-readable codes: Reject invalid input by raising BillingError(code, detail) from ledgerly.errors, reusing existing codes like "invalid_state" and "negative_amount" and passing the offending value as the message (e.g. str(price), repr(quantity)).
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0007] Refunds above 500 need approved_by: Support-initiated refunds/credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing.
  (learned from task E04 on ledgerly 1.0.0; source FIN-2026-03; relied on 0x, 0 passed, 0 failed)
- [at-0004] Exclude bool when validating integer inputs: When validating an int parameter, check isinstance(x, bool) first because bool is a subclass of int, then require isinstance(x, int) and the range constraint.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
```

### Shown for B01

```
(nothing)
```

### Shown for S04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0007] Refunds above 500 need approved_by: Support-initiated refunds/credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing.
  (learned from task E04 on ledgerly 1.0.0; source FIN-2026-03; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0002] Coerce unit prices with to_money: Wrap line unit prices with ledgerly.money.to_money before arithmetic, and seed sums with ledgerly.money.ZERO, as line_total and invoice_total in ledgerly/invoice.py do.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0003] Raise BillingError with machine-readable codes: Reject invalid input by raising BillingError(code, detail) from ledgerly.errors, reusing existing codes like "invalid_state" and "negative_amount" and passing the offending value as the message (e.g. str(price), repr(quantity)).
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0006] Money operations require idempotency_key: Every operation that moves money or mutates a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and pass `idempotency_key` into `audit.record`.
  (learned from task E04 on ledgerly 1.0.0; source INC-204; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0001] Round money only with round_money: Always round monetary Decimal results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0004] Exclude bool when validating integer inputs: When validating an int parameter, check isinstance(x, bool) first because bool is a subclass of int, then require isinstance(x, int) and the range constraint.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
```

