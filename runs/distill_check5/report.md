# Write-path check (before freeze)

Source trajectories: `runs/pilot3_nomem` (no memory).

## reasoningbank

### E01 (first attempt failed)
- ADD `rb-0001` Use the project's money rounding helper for any monetary result: Before returning any money-valued result, check the money module for a rounding helper (e.g. ledgerly.money.round_money) and wrap the final computation in it. Banker's rounding silently produces wrong invoice totals on .5 cases.
- ADD `rb-0002` Reuse existing money helpers and ZERO constant for sums: Convert inputs with to_money and seed sums with ZERO (sum(..., ZERO)) rather than int 0, so Decimal arithmetic and rounding stay consistent with sibling functions like line_total and invoice_total.
- ADD `rb-0003` Guard division by zero before computing averages: Compute total_quantity first and return ZERO when it is falsy, before dividing; this satisfies the empty-invoice spec and avoids ZeroDivisionError.

### E02 (first attempt passed)
- ADD `rb-0004` Read existing modules to match error codes and conventions: Grep for similar validation patterns (e.g. `invalid_state`, `negative_amount`) and reuse the same BillingError codes and message shapes. This keeps behavior consistent and satisfies hidden tests that expect project conventions.
- ADD `rb-0005` Guard bool when validating integer inputs: Use `isinstance(x, bool) or not isinstance(x, int)` before range checks when a parameter must be a true integer, otherwise True/False silently pass as 1/0.
- ADD `rb-0006` Normalize money inputs through the project's to_money helper: Call `to_money(unit_price)` first, then compare against `ZERO` and store the normalized Decimal on the LineItem; this matches how other modules round and validate amounts.

### E03 (first attempt passed)
- ADD `rb-0007` Reuse existing period math helpers: Search the codebase for similar period/boundary functions before writing new math. Copying the established pattern (ensure_utc on inputs, timedelta length, (t - start) // length) keeps semantics consistent and avoids subtle timezone bugs.
- ADD `rb-0008` Handle before-start edge case explicitly: Floor division on negative deltas can yield surprising results; add an explicit `if after < start: return start + length` branch so the first renewal after a pre-start time is the first period boundary.
- ADD `rb-0009` Normalize datetimes via project helper: Calling ensure_utc on both `after` and `sub.started_at` enforces the project's naive-datetime error contract and converts to UTC, matching behavior of other modules and satisfying hidden tests around timezone handling.

### E04 (first attempt failed)
- ADD `rb-0010` Check repo conventions before implementing money-moving functions: Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency_key and approval thresholds are often enforced by hidden tests even when the issue omits them.
- ADD `rb-0011` Implement idempotency via audit-event lookup: Accept keyword-only idempotency_key, scan audit.events() for a matching entry and return the object unchanged if found, then pass idempotency_key into the audit.record call so retries are detectable.
- ADD `rb-0012` Enforce approval thresholds with BillingError codes: Define a module-level APPROVAL_THRESHOLD constant, accept keyword-only approved_by, and raise BillingError("approval_required") before mutating state when amount exceeds the threshold and approved_by is falsy; include approved_by in the audit entry.

### E05 (first attempt passed)
- ADD `rb-0013` Reuse existing money helpers for Decimal math: Inspect ledgerly/money.py and sibling modules (invoice.py, payments.py) first; they define to_money, round_money, and BillingError conventions. Reusing them gives consistent rounding policy and error codes for free.
- ADD `rb-0014` Validate numeric inputs before arithmetic: Check rate.is_finite() and range bounds explicitly and raise BillingError with a stable code like 'invalid_tax_rate'. Wrap Decimal(str(x)) in try/except (InvalidOperation, ValueError) so bad input surfaces as BillingError, not a raw exception.
- ADD `rb-0015` Smoke-test edge cases beyond the provided test: After implementing, run a quick script with Decimal, str, and boundary inputs (0, 100, -1, 101). The first attempt used to_money for the rate, which rejects floats, so add_tax('19.99', 7.5) failed; the final version parses the rate with Decimal(str(...)) directly.

### E06 (first attempt failed)
- ADD `rb-0016` Check repo conventions before implementing money operations: Before implementing any payment/credit mutation, scan the repo (CHANGELOG, README, existing functions, audit module) for cross-cutting conventions like idempotency keys, audit logging, or UTC normalization. The issue text alone may not capture team conventions introduced after incidents.
- ADD `rb-0017` Idempotency pattern: check audit events, skip if key seen, record key: Add a keyword-only `idempotency_key: str | None = None` parameter. Helper: return True if any e.get('idempotency_key') == key in audit.events(). On replay, return without mutating state; on first application, pass idempotency_key into audit.record so future calls can detect it.
- ADD `rb-0018` Apply conventions consistently across related functions: If a convention applies to 'every operation that moves money', update all such functions in the module, not just the new one. Hidden tests may exercise the convention on pre-existing functions like authorize as well as the new capture.

### Shown for H04

```
Memory items from past tasks:
- [rb-0003] Guard division by zero before computing averages: Quantity-weighted averages must handle invoices with no lines or zero total quantity by returning ZERO.
  Compute total_quantity first and return ZERO when it is falsy, before dividing; this satisfies the empty-invoice spec and avoids ZeroDivisionError.
- [rb-0010] Check repo conventions before implementing money-moving functions: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency_key and approval thresholds are often enforced by hidden tests even when the issue omits them.
- [rb-0016] Check repo conventions before implementing money operations: The first attempt implemented capture correctly per the issue but was rejected because it missed the team's idempotency_key convention for money-moving operations.
  Before implementing any payment/credit mutation, scan the repo (CHANGELOG, README, existing functions, audit module) for cross-cutting conventions like idempotency keys, audit logging, or UTC normalization. The issue text alone may not capture team conventions introduced after incidents.
- [rb-0013] Reuse existing money helpers for Decimal math: When adding a pricing/money function, delegate to the repo's existing to_money/round_money helpers instead of raw Decimal arithmetic.
  Inspect ledgerly/money.py and sibling modules (invoice.py, payments.py) first; they define to_money, round_money, and BillingError conventions. Reusing them gives consistent rounding policy and error codes for free.
- [rb-0002] Reuse existing money helpers and ZERO constant for sums: Existing functions like to_money and the ZERO constant keep arithmetic consistent with the rest of the codebase.
  Convert inputs with to_money and seed sums with ZERO (sum(..., ZERO)) rather than int 0, so Decimal arithmetic and rounding stay consistent with sibling functions like line_total and invoice_total.
- [rb-0006] Normalize money inputs through the project's to_money helper: Convert raw unit_price values with the existing money helper before comparing or storing, so strings/Decimals are handled uniformly.
  Call `to_money(unit_price)` first, then compare against `ZERO` and store the normalized Decimal on the LineItem; this matches how other modules round and validate amounts.
```

### Shown for B01

```
Memory items from past tasks:
- [rb-0014] Validate numeric inputs before arithmetic: Guard against non-finite or out-of-range values (NaN, Infinity, negative, >100) before computing, raising the project's domain error.
  Check rate.is_finite() and range bounds explicitly and raise BillingError with a stable code like 'invalid_tax_rate'. Wrap Decimal(str(x)) in try/except (InvalidOperation, ValueError) so bad input surfaces as BillingError, not a raw exception.
- [rb-0006] Normalize money inputs through the project's to_money helper: Convert raw unit_price values with the existing money helper before comparing or storing, so strings/Decimals are handled uniformly.
  Call `to_money(unit_price)` first, then compare against `ZERO` and store the normalized Decimal on the LineItem; this matches how other modules round and validate amounts.
- [rb-0016] Check repo conventions before implementing money operations: The first attempt implemented capture correctly per the issue but was rejected because it missed the team's idempotency_key convention for money-moving operations.
  Before implementing any payment/credit mutation, scan the repo (CHANGELOG, README, existing functions, audit module) for cross-cutting conventions like idempotency keys, audit logging, or UTC normalization. The issue text alone may not capture team conventions introduced after incidents.
- [rb-0001] Use the project's money rounding helper for any monetary result: Monetary values must be rounded with the repository's round_money (half-up to the cent), not Python's round() or a bare Decimal.quantize(), which use banker's rounding.
  Before returning any money-valued result, check the money module for a rounding helper (e.g. ledgerly.money.round_money) and wrap the final computation in it. Banker's rounding silently produces wrong invoice totals on .5 cases.
- [rb-0004] Read existing modules to match error codes and conventions: Before implementing a new function, inspect sibling modules for established error codes, helper usage, and message formats.
  Grep for similar validation patterns (e.g. `invalid_state`, `negative_amount`) and reuse the same BillingError codes and message shapes. This keeps behavior consistent and satisfies hidden tests that expect project conventions.
- [rb-0002] Reuse existing money helpers and ZERO constant for sums: Existing functions like to_money and the ZERO constant keep arithmetic consistent with the rest of the codebase.
  Convert inputs with to_money and seed sums with ZERO (sum(..., ZERO)) rather than int 0, so Decimal arithmetic and rounding stay consistent with sibling functions like line_total and invoice_total.
```

### Shown for S04

```
Memory items from past tasks:
- [rb-0016] Check repo conventions before implementing money operations: The first attempt implemented capture correctly per the issue but was rejected because it missed the team's idempotency_key convention for money-moving operations.
  Before implementing any payment/credit mutation, scan the repo (CHANGELOG, README, existing functions, audit module) for cross-cutting conventions like idempotency keys, audit logging, or UTC normalization. The issue text alone may not capture team conventions introduced after incidents.
- [rb-0002] Reuse existing money helpers and ZERO constant for sums: Existing functions like to_money and the ZERO constant keep arithmetic consistent with the rest of the codebase.
  Convert inputs with to_money and seed sums with ZERO (sum(..., ZERO)) rather than int 0, so Decimal arithmetic and rounding stay consistent with sibling functions like line_total and invoice_total.
- [rb-0003] Guard division by zero before computing averages: Quantity-weighted averages must handle invoices with no lines or zero total quantity by returning ZERO.
  Compute total_quantity first and return ZERO when it is falsy, before dividing; this satisfies the empty-invoice spec and avoids ZeroDivisionError.
- [rb-0004] Read existing modules to match error codes and conventions: Before implementing a new function, inspect sibling modules for established error codes, helper usage, and message formats.
  Grep for similar validation patterns (e.g. `invalid_state`, `negative_amount`) and reuse the same BillingError codes and message shapes. This keeps behavior consistent and satisfies hidden tests that expect project conventions.
- [rb-0006] Normalize money inputs through the project's to_money helper: Convert raw unit_price values with the existing money helper before comparing or storing, so strings/Decimals are handled uniformly.
  Call `to_money(unit_price)` first, then compare against `ZERO` and store the normalized Decimal on the LineItem; this matches how other modules round and validate amounts.
- [rb-0010] Check repo conventions before implementing money-moving functions: The first attempt was rejected because it missed two team conventions (idempotency_key and approved_by) that were not in the issue text but are required by the codebase.
  Before writing a payment/credit/refund function, grep the repo for existing money-moving operations and read README/CHANGELOG for policy notes. Conventions like keyword-only idempotency_key and approval thresholds are often enforced by hidden tests even when the issue omits them.
```

## ace

### E01 (first attempt failed)
- ADD `ace-0001` strategies: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
- ADD `ace-0002` common_mistakes: Python's round() and bare Decimal.quantize() use banker's rounding, which produces wrong invoice totals; always round monetary results with the project's half-up round_money helper.
- ADD `ace-0003` strategies: When a function computes a ratio or average of monetary values, wrap the final division result in the project's money-rounding helper and return the project's ZERO constant for empty/zero-denominator cases.

### E02 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E02
- UPDATE `ace-0003`: reflector: helpful in E02
- ADD `ace-0004` strategies: Before implementing a new function, grep the repo for sibling functions that raise the same error type (e.g. BillingError) and mirror their error codes and message formats (e.g. "invalid_state", f"invoice {invoice.id} is {invoice.status}") so new code matches existing conventions.
- ADD `ace-0005` common_mistakes: When validating that a value is a positive integer, remember isinstance(True, int) is True in Python; explicitly reject bools (isinstance(x, bool)) before the int check to avoid accepting True/False as quantities.
- ADD `ace-0006` domain_facts: In ledgerly, Invoice.status is a plain string with values draft|issued|paid|void, and LineItem/Invoice are dataclasses; state guards should compare invoice.status to the literal string and raise BillingError("invalid_state", ...) as payments.py does.

### E03 (first attempt passed)
- UPDATE `ace-0004`: reflector: helpful in E03
- ADD `ace-0007` strategies: When implementing a date/time function, grep the repo for sibling functions (e.g. current_period in subscriptions.py) that do similar period arithmetic and mirror their use of ensure_utc, timedelta, and floor-division ((at - start) // length) so timezone handling and boundary logic stay consistent.
- ADD `ace-0008` common_mistakes: For 'first X strictly after t' computations, don't forget the strict inequality: use n = (t - start) // length + 1 so that when t lands exactly on a boundary the next (not current) period is returned, and handle t < start separately.
- ADD `ace-0009` domain_facts: In ledgerly, ledgerly/clock.py provides ensure_utc(dt) which raises BillingError('naive_datetime'/'invalid_datetime') and normalizes to UTC; call it on any datetime input (including sub.started_at) before doing arithmetic.

### E04 (first attempt failed)
- UPDATE `ace-0001`: reflector: helpful in E04
- UPDATE `ace-0003`: reflector: helpful in E04
- UPDATE `ace-0004`: reflector: helpful in E04
- UPDATE `ace-0006`: reflector: helpful in E04
- UPDATE `ace-0009`: reflector: helpful in E04
- ADD `ace-0010` strategies: Before implementing any money-moving operation (refund, credit, capture), grep the repo for audit.record usage and idempotency_key handling; team convention requires a keyword-only idempotency_key that short-circuits when an audit entry with that key already exists, and the key must be included in the audit entry written.
- ADD `ace-0011` domain_facts: In ledgerly, finance policy FIN-2026-03 requires a keyword-only approved_by for support-initiated refunds/credits above 500.00; raise BillingError('approval_required') when it is missing. Check README/CHANGELOG for such policy thresholds before implementing money operations.
- ADD `ace-0012` common_mistakes: When adding a new function to a module, re-read the whole file first: existing functions like manual_adjustment must be preserved verbatim, and new imports (audit, ensure_utc, BillingError, money helpers) must be added without dropping existing ones such as invoice_total.

### E05 (first attempt passed)
- UPDATE `ace-0001`: reflector: helpful in E05
- UPDATE `ace-0003`: reflector: helpful in E05
- UPDATE `ace-0004`: reflector: helpful in E05
- UPDATE `ace-0006`: reflector: helpful in E05
- ADD `ace-0013` common_mistakes: Don't reuse to_money() for non-amount numeric parameters like percentages or rates: to_money rejects floats (raising BillingError('float_amount')), so a caller passing rate_percent=7.5 would fail. Parse such values with Decimal(str(x)) and catch InvalidOperation/ValueError, raising the domain error yourself.
- ADD `ace-0014` strategies: When a numeric parameter has a documented valid range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before arithmetic, since NaN comparisons silently pass range checks.
- ADD `ace-0015` common_mistakes: When a function accepts a percentage/rate, convert it to Decimal and divide by Decimal(100) rather than multiplying by a float like 0.08; mixing float multipliers into Decimal arithmetic raises TypeError or loses precision.

### E06 (first attempt failed)
- UPDATE `ace-0004`: reflector: helpful in E06
- UPDATE `ace-0006`: reflector: helpful in E06
- UPDATE `ace-0009`: reflector: helpful in E06
- UPDATE `ace-0010`: reflector: helpful in E06
- UPDATE `ace-0012`: reflector: helpful in E06
- ADD `ace-0016` strategies: Before implementing any payment/credit operation, check README/CHANGELOG and existing audit.record calls for team conventions that apply to ALL such operations (e.g. keyword-only idempotency_key with short-circuit on existing audit entry), not just the specific function named in the issue; the issue text may omit these cross-cutting requirements.
- ADD `ace-0017` common_mistakes: When adding a keyword-only idempotency_key to a new function, also update sibling functions in the same module (e.g. authorize) that perform the same class of operation, since the convention applies to every money-moving/changing operation and hidden tests may exercise them.
- ADD `ace-0018` domain_facts: In ledgerly, audit.events() returns recorded audit entries as dicts; idempotency short-circuit is implemented by scanning for an entry whose 'idempotency_key' matches, and the key must be passed into audit.record(...) for the operation being performed.

### Shown for H04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=3 harmful=0 :: When a function computes a ratio or average of monetary values, wrap the final division result in the project's money-rounding helper and return the project's ZERO constant for empty/zero-denominator cases.
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for sibling functions that raise the same error type (e.g. BillingError) and mirror their error codes and message formats (e.g. "invalid_state", f"invoice {invoice.id} is {invoice.status}") so new code matches existing conventions.
[ace-0007] helpful=0 harmful=0 :: When implementing a date/time function, grep the repo for sibling functions (e.g. current_period in subscriptions.py) that do similar period arithmetic and mirror their use of ensure_utc, timedelta, and floor-division ((at - start) // length) so timezone handling and boundary logic stay consistent.
[ace-0010] helpful=1 harmful=0 :: Before implementing any money-moving operation (refund, credit, capture), grep the repo for audit.record usage and idempotency_key handling; team convention requires a keyword-only idempotency_key that short-circuits when an audit entry with that key already exists, and the key must be included in the audit entry written.
[ace-0014] helpful=0 harmful=0 :: When a numeric parameter has a documented valid range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before arithmetic, since NaN comparisons silently pass range checks.
[ace-0016] helpful=0 harmful=0 :: Before implementing any payment/credit operation, check README/CHANGELOG and existing audit.record calls for team conventions that apply to ALL such operations (e.g. keyword-only idempotency_key with short-circuit on existing audit entry), not just the specific function named in the issue; the issue text may omit these cross-cutting requirements.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding, which produces wrong invoice totals; always round monetary results with the project's half-up round_money helper.
[ace-0005] helpful=0 harmful=0 :: When validating that a value is a positive integer, remember isinstance(True, int) is True in Python; explicitly reject bools (isinstance(x, bool)) before the int check to avoid accepting True/False as quantities.
[ace-0008] helpful=0 harmful=0 :: For 'first X strictly after t' computations, don't forget the strict inequality: use n = (t - start) // length + 1 so that when t lands exactly on a boundary the next (not current) period is returned, and handle t < start separately.
[ace-0012] helpful=1 harmful=0 :: When adding a new function to a module, re-read the whole file first: existing functions like manual_adjustment must be preserved verbatim, and new imports (audit, ensure_utc, BillingError, money helpers) must be added without dropping existing ones such as invoice_total.
[ace-0013] helpful=0 harmful=0 :: Don't reuse to_money() for non-amount numeric parameters like percentages or rates: to_money rejects floats (raising BillingError('float_amount')), so a caller passing rate_percent=7.5 would fail. Parse such values with Decimal(str(x)) and catch InvalidOperation/ValueError, raising the domain error yourself.
[ace-0015] helpful=0 harmful=0 :: When a function accepts a percentage/rate, convert it to Decimal and divide by Decimal(100) rather than multiplying by a float like 0.08; mixing float multipliers into Decimal arithmetic raises TypeError or loses precision.
[ace-0017] helpful=0 harmful=0 :: When adding a keyword-only idempotency_key to a new function, also update sibling functions in the same module (e.g. authorize) that perform the same class of operation, since the convention applies to every money-moving/changing operation and hidden tests may exercise them.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, Invoice.status is a plain string with values draft|issued|paid|void, and LineItem/Invoice are dataclasses; state guards should compare invoice.status to the literal string and raise BillingError("invalid_state", ...) as payments.py does.
[ace-0009] helpful=2 harmful=0 :: In ledgerly, ledgerly/clock.py provides ensure_utc(dt) which raises BillingError('naive_datetime'/'invalid_datetime') and normalizes to UTC; call it on any datetime input (including sub.started_at) before doing arithmetic.
[ace-0011] helpful=0 harmful=0 :: In ledgerly, finance policy FIN-2026-03 requires a keyword-only approved_by for support-initiated refunds/credits above 500.00; raise BillingError('approval_required') when it is missing. Check README/CHANGELOG for such policy thresholds before implementing money operations.
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.events() returns recorded audit entries as dicts; idempotency short-circuit is implemented by scanning for an entry whose 'idempotency_key' matches, and the key must be passed into audit.record(...) for the operation being performed.
```

### Shown for B01

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=3 harmful=0 :: When a function computes a ratio or average of monetary values, wrap the final division result in the project's money-rounding helper and return the project's ZERO constant for empty/zero-denominator cases.
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for sibling functions that raise the same error type (e.g. BillingError) and mirror their error codes and message formats (e.g. "invalid_state", f"invoice {invoice.id} is {invoice.status}") so new code matches existing conventions.
[ace-0007] helpful=0 harmful=0 :: When implementing a date/time function, grep the repo for sibling functions (e.g. current_period in subscriptions.py) that do similar period arithmetic and mirror their use of ensure_utc, timedelta, and floor-division ((at - start) // length) so timezone handling and boundary logic stay consistent.
[ace-0010] helpful=1 harmful=0 :: Before implementing any money-moving operation (refund, credit, capture), grep the repo for audit.record usage and idempotency_key handling; team convention requires a keyword-only idempotency_key that short-circuits when an audit entry with that key already exists, and the key must be included in the audit entry written.
[ace-0014] helpful=0 harmful=0 :: When a numeric parameter has a documented valid range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before arithmetic, since NaN comparisons silently pass range checks.
[ace-0016] helpful=0 harmful=0 :: Before implementing any payment/credit operation, check README/CHANGELOG and existing audit.record calls for team conventions that apply to ALL such operations (e.g. keyword-only idempotency_key with short-circuit on existing audit entry), not just the specific function named in the issue; the issue text may omit these cross-cutting requirements.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding, which produces wrong invoice totals; always round monetary results with the project's half-up round_money helper.
[ace-0005] helpful=0 harmful=0 :: When validating that a value is a positive integer, remember isinstance(True, int) is True in Python; explicitly reject bools (isinstance(x, bool)) before the int check to avoid accepting True/False as quantities.
[ace-0008] helpful=0 harmful=0 :: For 'first X strictly after t' computations, don't forget the strict inequality: use n = (t - start) // length + 1 so that when t lands exactly on a boundary the next (not current) period is returned, and handle t < start separately.
[ace-0012] helpful=1 harmful=0 :: When adding a new function to a module, re-read the whole file first: existing functions like manual_adjustment must be preserved verbatim, and new imports (audit, ensure_utc, BillingError, money helpers) must be added without dropping existing ones such as invoice_total.
[ace-0013] helpful=0 harmful=0 :: Don't reuse to_money() for non-amount numeric parameters like percentages or rates: to_money rejects floats (raising BillingError('float_amount')), so a caller passing rate_percent=7.5 would fail. Parse such values with Decimal(str(x)) and catch InvalidOperation/ValueError, raising the domain error yourself.
[ace-0015] helpful=0 harmful=0 :: When a function accepts a percentage/rate, convert it to Decimal and divide by Decimal(100) rather than multiplying by a float like 0.08; mixing float multipliers into Decimal arithmetic raises TypeError or loses precision.
[ace-0017] helpful=0 harmful=0 :: When adding a keyword-only idempotency_key to a new function, also update sibling functions in the same module (e.g. authorize) that perform the same class of operation, since the convention applies to every money-moving/changing operation and hidden tests may exercise them.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, Invoice.status is a plain string with values draft|issued|paid|void, and LineItem/Invoice are dataclasses; state guards should compare invoice.status to the literal string and raise BillingError("invalid_state", ...) as payments.py does.
[ace-0009] helpful=2 harmful=0 :: In ledgerly, ledgerly/clock.py provides ensure_utc(dt) which raises BillingError('naive_datetime'/'invalid_datetime') and normalizes to UTC; call it on any datetime input (including sub.started_at) before doing arithmetic.
[ace-0011] helpful=0 harmful=0 :: In ledgerly, finance policy FIN-2026-03 requires a keyword-only approved_by for support-initiated refunds/credits above 500.00; raise BillingError('approval_required') when it is missing. Check README/CHANGELOG for such policy thresholds before implementing money operations.
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.events() returns recorded audit entries as dicts; idempotency short-circuit is implemented by scanning for an entry whose 'idempotency_key' matches, and the key must be passed into audit.record(...) for the operation being performed.
```

### Shown for S04

```
Playbook (accumulated from past tasks):
## strategies
[ace-0001] helpful=3 harmful=0 :: Before implementing a money-related function, inspect the repo's money helpers (e.g. ledgerly/money.py) and reuse existing utilities like round_money, to_money, and ZERO rather than Python's round() or bare Decimal.quantize().
[ace-0003] helpful=3 harmful=0 :: When a function computes a ratio or average of monetary values, wrap the final division result in the project's money-rounding helper and return the project's ZERO constant for empty/zero-denominator cases.
[ace-0004] helpful=4 harmful=0 :: Before implementing a new function, grep the repo for sibling functions that raise the same error type (e.g. BillingError) and mirror their error codes and message formats (e.g. "invalid_state", f"invoice {invoice.id} is {invoice.status}") so new code matches existing conventions.
[ace-0007] helpful=0 harmful=0 :: When implementing a date/time function, grep the repo for sibling functions (e.g. current_period in subscriptions.py) that do similar period arithmetic and mirror their use of ensure_utc, timedelta, and floor-division ((at - start) // length) so timezone handling and boundary logic stay consistent.
[ace-0010] helpful=1 harmful=0 :: Before implementing any money-moving operation (refund, credit, capture), grep the repo for audit.record usage and idempotency_key handling; team convention requires a keyword-only idempotency_key that short-circuits when an audit entry with that key already exists, and the key must be included in the audit entry written.
[ace-0014] helpful=0 harmful=0 :: When a numeric parameter has a documented valid range (e.g. tax rate 0-100 inclusive), validate the range explicitly and also reject non-finite values (NaN/Infinity) via Decimal.is_finite() before arithmetic, since NaN comparisons silently pass range checks.
[ace-0016] helpful=0 harmful=0 :: Before implementing any payment/credit operation, check README/CHANGELOG and existing audit.record calls for team conventions that apply to ALL such operations (e.g. keyword-only idempotency_key with short-circuit on existing audit entry), not just the specific function named in the issue; the issue text may omit these cross-cutting requirements.
## common_mistakes
[ace-0002] helpful=0 harmful=0 :: Python's round() and bare Decimal.quantize() use banker's rounding, which produces wrong invoice totals; always round monetary results with the project's half-up round_money helper.
[ace-0005] helpful=0 harmful=0 :: When validating that a value is a positive integer, remember isinstance(True, int) is True in Python; explicitly reject bools (isinstance(x, bool)) before the int check to avoid accepting True/False as quantities.
[ace-0008] helpful=0 harmful=0 :: For 'first X strictly after t' computations, don't forget the strict inequality: use n = (t - start) // length + 1 so that when t lands exactly on a boundary the next (not current) period is returned, and handle t < start separately.
[ace-0012] helpful=1 harmful=0 :: When adding a new function to a module, re-read the whole file first: existing functions like manual_adjustment must be preserved verbatim, and new imports (audit, ensure_utc, BillingError, money helpers) must be added without dropping existing ones such as invoice_total.
[ace-0013] helpful=0 harmful=0 :: Don't reuse to_money() for non-amount numeric parameters like percentages or rates: to_money rejects floats (raising BillingError('float_amount')), so a caller passing rate_percent=7.5 would fail. Parse such values with Decimal(str(x)) and catch InvalidOperation/ValueError, raising the domain error yourself.
[ace-0015] helpful=0 harmful=0 :: When a function accepts a percentage/rate, convert it to Decimal and divide by Decimal(100) rather than multiplying by a float like 0.08; mixing float multipliers into Decimal arithmetic raises TypeError or loses precision.
[ace-0017] helpful=0 harmful=0 :: When adding a keyword-only idempotency_key to a new function, also update sibling functions in the same module (e.g. authorize) that perform the same class of operation, since the convention applies to every money-moving/changing operation and hidden tests may exercise them.
## domain_facts
[ace-0006] helpful=3 harmful=0 :: In ledgerly, Invoice.status is a plain string with values draft|issued|paid|void, and LineItem/Invoice are dataclasses; state guards should compare invoice.status to the literal string and raise BillingError("invalid_state", ...) as payments.py does.
[ace-0009] helpful=2 harmful=0 :: In ledgerly, ledgerly/clock.py provides ensure_utc(dt) which raises BillingError('naive_datetime'/'invalid_datetime') and normalizes to UTC; call it on any datetime input (including sub.started_at) before doing arithmetic.
[ace-0011] helpful=0 harmful=0 :: In ledgerly, finance policy FIN-2026-03 requires a keyword-only approved_by for support-initiated refunds/credits above 500.00; raise BillingError('approval_required') when it is missing. Check README/CHANGELOG for such policy thresholds before implementing money operations.
[ace-0018] helpful=0 harmful=0 :: In ledgerly, audit.events() returns recorded audit entries as dicts; idempotency short-circuit is implemented by scanning for an entry whose 'idempotency_key' matches, and the key must be passed into audit.record(...) for the operation being performed.
```

## attest

### E01 (first attempt failed)
- ADD `at-0001` Round money only with round_money: Always round monetary Decimal results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
- ADD `at-0002` Use to_money and ZERO from ledgerly.money: Coerce line prices with ledgerly.money.to_money and seed sums with ledgerly.money.ZERO, as line_total and invoice_total in ledgerly/invoice.py do, so Decimal arithmetic stays consistent.

### E02 (first attempt passed)
- ADD `at-0003` Raise BillingError with machine-readable codes: Reject invalid input by raising BillingError(code, detail) from ledgerly.errors, using existing codes like "invalid_state" and "negative_amount" and a short machine-readable reason string.
- UPDATE `at-0002`: confirmed again by verified task E02
- ADD `at-0004` Exclude bool when validating integer inputs: When validating an int parameter, reject bool explicitly (isinstance(x, bool)) before the int check, since True/False pass isinstance(x, int).

### E03 (first attempt passed)
- ADD `at-0005` Normalize datetimes with ensure_utc: In ledgerly, normalize every incoming datetime (arguments and model fields like sub.started_at) with ledgerly.clock.ensure_utc before comparing or doing arithmetic; it raises BillingError for naive or non-datetime values.
- REJECT (source: evidence quote not found verbatim in the review comments or the diff): Compute billing periods like ledgerly.subscriptions.current_period: length = timedelta(days=sub.period_days), then n = (at - start) // length and start + n * length, rather than using day counts or date arithmetic.

### E04 (first attempt failed)
- ADD `at-0006` Money operations require idempotency_key: Every operation that moves money or changes a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and include `idempotency_key` in the audit entry you record.
- ADD `at-0007` Refunds above 500 need second approver: Support-initiated refunds and credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing for amounts above the threshold.

### E05 (first attempt passed)
- UPDATE `at-0001`: confirmed again by verified task E05
- UPDATE `at-0003`: confirmed again by verified task E05
- REJECT (source: evidence quote not found verbatim in the review comments or the diff): `to_money` rejects floats, so parse non-amount numeric inputs like tax rates with `Decimal(str(value))` and catch `InvalidOperation`/`ValueError` instead.

### E06 (first attempt failed)
- UPDATE `at-0006`: confirmed again by verified task E06
- UPDATE `at-0006`: confirmed again by verified task E06

### Shown for H04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0002] Use to_money and ZERO from ledgerly.money: Coerce line prices with ledgerly.money.to_money and seed sums with ledgerly.money.ZERO, as line_total and invoice_total in ledgerly/invoice.py do, so Decimal arithmetic stays consistent.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0003] Raise BillingError with machine-readable codes: Reject invalid input by raising BillingError(code, detail) from ledgerly.errors, using existing codes like "invalid_state" and "negative_amount" and a short machine-readable reason string.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0006] Money operations require idempotency_key: Every operation that moves money or changes a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and include `idempotency_key` in the audit entry you record.
  (learned from task E04 on ledgerly 1.0.0; source INC-204; relied on 0x, 0 passed, 0 failed)
- [at-0001] Round money only with round_money: Always round monetary Decimal results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0004] Exclude bool when validating integer inputs: When validating an int parameter, reject bool explicitly (isinstance(x, bool)) before the int check, since True/False pass isinstance(x, int).
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
- [at-0005] Normalize datetimes with ensure_utc: In ledgerly, normalize every incoming datetime (arguments and model fields like sub.started_at) with ledgerly.clock.ensure_utc before comparing or doing arithmetic; it raises BillingError for naive or non-datetime values.
  (learned from task E03 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
```

### Shown for B01

```
(nothing)
```

### Shown for S04

```
These notes were distilled from earlier work in this repository that passed verification. Follow them unless the code or CHANGELOG.md shows they no longer hold.
- [at-0003] Raise BillingError with machine-readable codes: Reject invalid input by raising BillingError(code, detail) from ledgerly.errors, using existing codes like "invalid_state" and "negative_amount" and a short machine-readable reason string.
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0007] Refunds above 500 need second approver: Support-initiated refunds and credits above 500.00 require a second approver per finance policy FIN-2026-03: accept a keyword-only `approved_by` and raise `BillingError("approval_required")` when it is missing for amounts above the threshold.
  (learned from task E04 on ledgerly 1.0.0; source FIN-2026-03; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0002] Use to_money and ZERO from ledgerly.money: Coerce line prices with ledgerly.money.to_money and seed sums with ledgerly.money.ZERO, as line_total and invoice_total in ledgerly/invoice.py do, so Decimal arithmetic stays consistent.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0006] Money operations require idempotency_key: Every operation that moves money or changes a payment/credit must accept a keyword-only `idempotency_key`; check `ledgerly.audit.events()` for an existing entry with that key and return early without reapplying, and include `idempotency_key` in the audit entry you record.
  (learned from task E04 on ledgerly 1.0.0; source INC-204; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0001] Round money only with round_money: Always round monetary Decimal results with ledgerly.money.round_money (half-up to the cent); never use Python's round() or a bare Decimal.quantize(), which use banker's rounding and produce wrong invoice totals.
  (learned from task E01 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
- [at-0004] Exclude bool when validating integer inputs: When validating an int parameter, reject bool explicitly (isinstance(x, bool)) before the int check, since True/False pass isinstance(x, int).
  (learned from task E02 on ledgerly 1.0.0; relied on 0x, 0 passed, 0 failed)
  WARNING: learned on version 1.0.0, this checkout is 2.0.0. Check CHANGELOG.md before relying on it.
```

