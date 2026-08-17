# Hygiene Pass — 2026-08-16 (non-result-affecting, user-approved Q5/Q7)

Track P item (iv): engineering hygiene executed as non-result-affecting.
No engine output or gate was touched; engine-frozen discipline preserved.

## 1. Ruff cosmetics — DONE (0 findings now)

- Scope: scripts/ (ruff check). Fixed 4 originally-reported findings plus
  all further findings surfaced during the pass:
  - scripts/check_market_data.py: removed unused pandas/json/os imports.
  - scripts/cycle3_13f_engine.py: removed unused norm_class import.
  - scripts/cycle3_ml_engine.py: removed unused ytr/yoos unpacking.
  - scripts/cycle3_lowvol_engine.py: removed dead costs_log list.
  - scripts/cycle3_fetch_names.py: removed unused csv/re/sys imports.
  - scripts/dca_scenario.py / evaluate_factor_claim.py: unused imports
    removed via ruff --fix (F401/F841).
  - scripts/factor_engine.py: removed unused closes dict.
  - scripts/improve_strategy_v2.py: removed unused o/h/l/spy_s locals.
  - scripts/update_readme.py: moved `import re` to top (E402), split
    one-line if (E701).
- Verification: `ruff check scripts` -> "All checks passed!";
  py_compile clean on all edited files. All edits are dead-code removals
  with no behavior change.

## 2. Cost model limits — DOCUMENTED (LOW, unchanged, declared)

- Fixed-bps costs only: 5/10 bps/side (multi-asset), 10 bps/side (decile
  L/S claims). Market-impact/slippage beyond the fixed bps is NOT modeled.
- Borrow costs on short legs (low-vol, ML deciles) are NOT modeled.
- Justification (unchanged from cycle3_check.md): adequate for a fail-closed
  research gate; MUST be revisited for Phase B live sizing before any
  live entry (no claim currently passes).
- No claim approaches its bar, so no cost-model upgrade is scheduled.

## 3. CUSIP map — VERIFIED (LOW, no action)

- `ticker_to_cusips` is empty (0 entries). Verified cause (cycle3_prereg_13f.md
  Appendix A, 2026-08-16): yfinance exposes NO cusip field (Ticker.info and
  get_info() return cusip None/absent); ISIN fallback unreliable (2/9 valid).
- The 13F pipeline resolves holdings via name -> ticker mapping (481-name
  snapshot), which satisfies the pre-registered CUSIP-map rule; no
  CUSIP-dependent analysis is pending. Re-verify before any future
  CUSIP-dependent work (no action today).

## 4. Python environment — DECLARED (fact, no change)

- Installed and used across all cycles: numpy 2.4.6, pandas 3.0.5
  (anaconda 3.11). sklearn 1.6.1 (declared Appendix B.1 delta for the
  learned-model claims C4/C5). C6 uses no sklearn (pure numpy/pandas).
- Frozen pre-reg versions (1.9.0/2.2.0/2.2.3) remain not installed;
  declared-before-run discipline held for every claim.

## 5. Broker capability gate — PENDING (unchanged, pre-live)

- Not implemented. Required before ANY live entry (not a research gate).
  No claim passes, so no live path is open; implementation deferred to
  Phase B readiness.