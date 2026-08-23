# Prior Art — Wave-1 batch (H1–H4), scanned 2026-08-24

## Recalled attempts (memory + ledgers + closed-directions ledger)

| Attempt | Direction | Outcome | Source |
|---|---|---|---|
| Cycle 3 Claim 4/4 | ML GBR decile entries | FAIL (train-consistency, OOS Sharpe 0.94, null p95) | docs/data/cycle3_ml_evaluation.json |
| Topic 07 | ML overlays on cores, 17 variants | FAIL 17/17 | decision 2026-08-16-ml-overlay.md |
| H-SLX-1 | SL-adjusted-label GBDT exits | FAIL all decisive gates 2026-08-24 | docs/data/eval_ml_sl_exit.json |
| Round 1 families (11) | entry-signal variants | 5 FAIL / 6 ABANDON | round1_consolidation.json |
| RSI(2)-entry family | saturated | 8 candidates, 0 pass | hunt-lessons.md |
| Confluence/trend/surge stack | universal signal regime | CLOSED 2026-08-14; exits now also closed; OPEN = sizing, claim scoping, new data | improvement_regime_conclusion.md |
| A_megacap_base rounds 1/2/2b/3 | mega-cap conditioning | cleared B-gates 3×; mega-cap-only adoption explicitly deferred as CLAIM CHANGE | round*_results.json, improvement_regime_conclusion.md §45 |
| us_momentum_top5 SMA sweep | endogenous price regime filters | unfiltered adopted; SMA filters add nothing on this core | strategies/us_momentum_top5.yaml |

## Differentiation per candidate (changed conditions named)

- **H1**: reuses the PRE-EXISTING frozen Universe A verbatim (no post-hoc universe
  choice); changes CORE from closed confluence stack to momentum top-5; executes
  the exact claim change reserved by §45. Closure's excluded lanes = prime ground.
- **H2**: exogenous FRED macro composite vs prior endogenous SMA states and vs
  RSI2-era regime variants — different core AND different regime source.
- **H3**: sizing lane left open by the closure; closed-form deterministic vol
  target, not a learned overlay (topic07 tested learned models only).
- **H4**: genuinely new data class (legislator PTRs + media picks); 13F work was
  institutional quarterly holdings, not disclosure-event trading.

## Standing-rule compliance

- Every overlapping family above is cited with its outcome; changed conditions
  are declared per candidate in the frozen preregs.
- Data/tooling changes since closures: full OHLCV panel with Low column, FRED
  regime file verified local at `data/cache/fred_historical_regimes.json`
  (labels RISK_ON/NEUTRAL/RISK_OFF/STAGFLATION, 2003→2026-08-14), six-gate +
  DSR trial-ledger machinery live.
- Any IS p ≈ 0.05 is recorded as FAIL, never encouragement.
