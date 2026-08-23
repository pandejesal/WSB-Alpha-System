# Prior Art — H-SLX-1 (SL-adjusted-label GBDT exit overlay)

## Recalled attempts (memory + ledgers scanned 2026-08-24)

| Attempt | Direction | Outcome | Source |
|---|---|---|---|
| Cycle 3 Claim 4/4 | ML (GBR regression) decile long-short on entries | FAIL — train-consistency, OOS Sharpe 0.94 (<1.0), null p95 all failed | docs/data/cycle3_ml_evaluation.json |
| Topic 07 | ML overlay on existing cores, 17 variants | FAIL 17/17 — best momentum overlay +0.045 Sharpe (<+0.1 bar), DD −55.5% vs −38.4% | decision 2026-08-16-ml-overlay.md |
| Round 1 (11 candidates) | entry-signal families | 5 FAIL / 6 HONEST_ABANDON / 0 winners | round1_consolidation.json |
| Round 3.5 (8 candidates) | RSI(2)-family entries + tweaks | 0 passed; closest ta_rules_rsi2_stop_v1 IS p=0.05 borderline = failure | hunt-lessons.md |
| Improvement regime | confluence/trend/surge signal stack | CLOSED 2026-08-14 "no universal edge" for that stack; exits/sizing/data/scoping declared OUTSIDE mandate | improvement_regime_conclusion.md |

## Why this hypothesis differs (changed conditions)

1. **Untested decision boundary.** All prior ML tests attacked *entries or whole-portfolio
   overlays*. The exit rule ("when to sell") has never had an ML test in this library.
   This is stated verbatim as the open lever in docs/research/XGBOOST-EXITS-2026-08-17.md §1.
2. **Changed target.** Cycle 3 regressed forward returns (weak price-only signal, honest
   prior: fails again). H-SLX-1 switches to Hwang et al. (2023) SL-adjusted BINARY labels:
   "rises AND never touches −20%" over a fixed horizon — a risk-shaped target the library
   has never used. The XGBoost-exits report itself flags this as the fix for pattern (ii)'s
   weak prior (§4 → §8 recommendation #1).
3. **Exit-only intervention.** Entries, universe, sizing, fees identical in both arms;
   the ONLY difference is per-bar early-exit decisions while holding. Any delta is
   attributable to exit timing, not signal selection.
4. **Monotone structure.** Position-P&L feature carries a hard increasing monotone
   constraint (lower P&L ⇒ higher exit pressure), encoding Kaminski & Lo (2014)/trailing-stop
   economics instead of free-form fitting.
5. **Endorsement from failed-round lessons.** Round 3.5's standing lesson says
   differentiation must come from "regime/exit structure, not entry tweak". This is an
   exit-structure candidate, satisfying that rule directly.

## Standing-rule compliance

- Rule 1 cited: overlaps no failed family; nearest relative is topic 07 overlays — changed
  condition = SL-adjusted labels + exit-boundary-only scope + monotone constraint.
- Rule 2: data/tooling DID change since abandonments — full OHLCV panel (Low column enables
  stop-touch labels) confirmed local at market_data_2019_2026/ohlcv/, sklearn 1.6.1 with
  native monotonic_cst verified installed.
- Rule 3: any IS p-value near 0.05 will be recorded as FAIL, not encouragement.
