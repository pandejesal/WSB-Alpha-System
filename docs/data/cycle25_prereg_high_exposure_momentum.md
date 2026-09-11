# Pre-registration: high_exposure_momentum
Cycle: 25
Date: 2026-09-11 17:06:45
Spec-SHA256: e1a141c1eea3656298e4727b0b624c1093bd790b62af53d112b84b8f0ed550bd

## Claim
H10: 252d breakout-persistence set-membership (63d confirmation, NO ranking, NO SMA) with SPY-fill always-invested slots breaks rotation perm-death (discrete leadership episodes) and own-trend perm-death (sparse event sleeve); targets Track 5 (Sharpe>=0.75 DD<=0.35 excess>=+0.05pp DSR>=0.90 fam N=57 oos>=0.50 tmin>=0.70 trips>=6 perm/boot<=0.05)

## Strategy Spec
```yaml
id: high_exposure_momentum_h10
name: "High-Exposure Momentum H10 (252d breakout-persistence + 63d confirmation, SPY-fill, monthly, always invested)"
family: high_exposure_momentum
venue: alpaca
universe: "31-symbol rotation_universe panel (config/universe.json; SPY excluded from panel, twin benchmark + SPY-fill sleeve only), daily OHLCV 2019-2026"
pre_registration_ref: "docs/data/cycle24_prereg_high_exposure_momentum.md (freeze BEFORE backtest; bytes frozen)"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/high_exposure_momentum/20260911-h10-momentum/results/eval_high_exposure_momentum_h10.json"
status: "paper"
version: 1
signal:
  entry: "Breakout-persistence set-membership (NO ranking, NO SMA): at each monthly signal date m (past-only closes.loc[:m]), name qualifies iff close[m] >= 0.98 * max252 (max of prior 252 closes before m) AND 63d return (close[m]/close[m-63]-1) > 0; warmup (<316 bars history) holds SPY-fill"
  exit: "No exit to cash; de-qualified names rotate back to SPY-fill at next monthly refresh; portfolio gross stays 1.0 so tmin=1.0 by construction"
  sizing: "Slot design: slot i holds name i at 1/31 if qualified else SPY at 1/31; equal-weight qualifiers, SPY-fill remainder; never levered, never flat; fractional shares; T+1 execution"
  caps:
    max_concurrent_positions: 31
  rebalance: "monthly signal refresh (first trading day), forward-filled daily"
parameters:
  breakout_lookback: 252
  confirm_lookback: 63
  proximity_band: 0.98
  signal_refresh: monthly
  fill: SPY
  exec_delay: 1
  fam_trials_N: 57
indicators:
  - "252d-high proximity filter (past-only, no SMA)"
  - "63d positive-return confirmation filter (past-only)"
  - "SPY-fill always-invested aggregation (gross 1.0)"
position_sizing:
  - "1/31 per qualified name, (31-K)/31 SPY-fill"
  - "Gross 1.0 always; fractional shares via Alpaca paper API"
fee_model:
  commission: "$0 (Alpaca) + 2.5bp W5"
  slippage: "5-7bps slippage + vol_scalar scale 2 cap 2 (W5 tiered cost)"
  settlement: "T+1"
benchmark_result:
  benchmark: "SPY identical-window twin (~1910 bars)"
feasibility_at_100:
  - "31 slots x ~$3 fractional; ~1 signal refresh/month; T+1"
risks:
  - "High exposure tmin=1.0 => DD tracks panel/SPY DD vs 35% cap; SPY-fill dilutes active edge toward index-hugger excess"
  - "Breakout chases late-stage momentum; 63d confirmation lags sharp reversals; survivorship bias in large-cap panel (acknowledged)"
  - "DSR>=0.90 at fam N=57 needs Sharpe ~=1.3+; perm<=0.05 requires genuine time-specific timing content"
dedup:
  - "us_momentum_top5 / dual_momentum (SPY/QQQ/AGG GEM) / momentum_breakout_v2/v4 / candidate_momentum_v4_prime / factor_momentum_top3 / breakout_burst (20d-high/20d-hold event-driven, max 10): distinct specs, untouched"
  - "TABOO formation-rank combos avoided: (126,21,5) (189,5,10) (63,42,3) (95,42,7) (252,21,8) (126,10,12)+inv-vol+voltarget15+dd-deleverage(H4) (189,21,28)+quarterly+voltarget12(H6)"
  - "TABOO own-trend avoided: H8 (SMA50/200, weak 0.5, monthly) perm 0.695 HONEST_ABANDON cycle23"
  - "Differs from H2/H4/H6: zero cross-sectional ranking, zero formation lookback/skip/top_n; set-membership breakout-persistence + SPY-fill instead of top-N rotation"
  - "Differs from H8: zero SMA (no SMA50/200/warmup-trend); price-level breakout + return-confirmation only"

```
