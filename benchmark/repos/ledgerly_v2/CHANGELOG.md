# Changelog

## 2.0.0 — 2026-09-15

- **Breaking:** finance policy FIN-2026-07 switches all monetary rounding to
  banker's rounding (`ROUND_HALF_EVEN`) to match the new general ledger.
  `round_money()` now rounds half to even. Any code that rounds money on its
  own must be updated.
- Finance policy FIN-2026-09 raises the approval threshold for support-initiated
  refunds and credits from 500.00 to 1000.00.

## 1.0.0 — 2026-03-02

- Initial internal release: invoices, payment authorization, subscription periods.
