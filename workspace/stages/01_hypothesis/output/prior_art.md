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
  - AMENDMENT A (2026-08-25, pre-run): Arm P = House-only (Senate eFD 403-blocks
    the machine; live-probed), Arm C window truncated to 2024-12-31 and universe
    limited to long-side directional calls (free-source constraint, Kull CC-BY-4.0
    archive @ 03e33c61). Full text: prereg §6. No run had occurred at declaration.
    A5 adds the per-arm evaluation-span rule (incomplete holds excluded
    symmetrically; Arm C span ends when its last hold expires ~2025-04).

## Standing-rule compliance

- Every overlapping family above is cited with its outcome; changed conditions
  are declared per candidate in the frozen preregs.
- Data/tooling changes since closures: full OHLCV panel with Low column, FRED
  regime file verified local at `data/cache/fred_historical_regimes.json`
  (labels RISK_ON/NEUTRAL/RISK_OFF/STAGFLATION, 2003→2026-08-14), six-gate +
  DSR trial-ledger machinery live.
- Any IS p ≈ 0.05 is recorded as FAIL, never encouragement.

## Wave-3 batch differentiation (frozen 2026-08-25)

| Candidate | New mechanism | Nearest closed family + why distinct |
|---|---|---|
| W3-H1 52wH proximity | salient-anchor level signal (George-Hwang) | TA-rule variants measured rate-of-change; no closure used anchor distance |
| W3-H2 residual momentum | beta-residualized 12-1 ranking (Blitz et al.), market model from local panel only | incumbent raw momentum = same window, different signal object; not ML, not scoping |
| W3-H3 TOM timing | calendar-window concentration (-1/+4 TD) on unchanged incumbent signals | closures cover sizing/scoping/regime gates; none conditioned month-turn dates |
| W3-H4 overnight capture | session-conditioned holding (Mon close→Fri open) | no prior family conditioned intraday-vs-overnight capture |
| — lanes considered and REJECTED pre-freeze | fundamentals screen: market_data_2019_2026/fundamentals/ EMPTY (PIT impossible); sentiment-ranking: CO_MENTION cache absent (round-1 plumbing lesson); BTC/ETH rotation: overlaps registry btc_vol_target_sma100 + absolute-gate mechanism |
