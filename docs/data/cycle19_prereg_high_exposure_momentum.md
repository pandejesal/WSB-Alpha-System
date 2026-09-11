# Pre-registration: high_exposure_momentum
Cycle: 19
Date: 2026-09-11 14:52:19
Spec-SHA256: 0d3ec7bb4f66072a783611dc1ff60ed488f11cf4d5c2f6880c0b52a9c2ca70a9

## Claim
H4: 6-1 formation (126/10) top-12 inverse-vol on 31-name rotation_universe with deleverage-only 15pct vol-target (scale [.5,1]) + DD-trigger 8pct floor .5x compresses H2 crash DD (0.794-><=.35) preserving Sharpe>=.75, excess>=+.05pp, DSR>=.90 (fam N=54), tmin>=.70, trips>=6, perm/boot<=.05 (Track 5)

## Strategy Spec
```yaml
id: high_exposure_momentum_h4
name: "High-Exposure Momentum H4 (126/10/12 broad-panel inv-vol vol-targeted, DD-deleveraged)"
family: high_exposure_momentum
venue: alpaca
universe: "31-symbol rotation_universe panel (config/universe.json; SPY excluded, twin benchmark only), daily OHLCV 2019-2026"
pre_registration_ref: "docs/data/cycle19_prereg_high_exposure_momentum.md (freeze BEFORE backtest; bytes frozen)"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/high_exposure_momentum/20260911-h4-momentum/results/eval_high_exposure_momentum_h4.json"
status: "paper"
version: 1
signal:
  entry: "Rank by 126d formation skip 10d (6-1 Jegadeesh-Titman); top 12 by cumulative return; inverse trailing-60d-vol weights (past-only at each rebalance date); monthly rebalance first trading day, forward-filled daily holding"
  exit: "Re-rank monthly; exit when symbol drops out of top 12"
  sizing: "Inverse-vol normalized within top 12 x monthly gross scale = clip(0.15 / trailing-60d sleeve ann vol, 0.5, 1.0) x DD-deleverage (past-only sleeve DD>8% -> scale down to floor 0.5x); deleverage-only, never levered, never cash-flat (tmin>=0.70 preserved); fractional shares; T+1 execution"
  caps:
    max_concurrent_positions: 12
  rebalance: "monthly, forward-filled daily; scale recomputed monthly (past-only), ffill daily"
parameters:
  lookback: 126
  skip: 10
  top_n: 12
  vol_target_ann: 0.15
  scale_min: 0.5
  scale_max: 1.0
  dd_trigger: 0.08
  dd_floor: 0.5
  exec_delay: 1
  fam_trials_N: 54
indicators:
  - "126d cumulative return formation"
  - "10d skip (reversal avoidance)"
  - "60d trailing inverse-vol weighting (past-only)"
  - "60d trailing sleeve vol target 15% ann (past-only, monthly)"
  - "past-only sleeve DD trigger 8% -> floor 0.5x (never flat)"
position_sizing:
  - "Inverse-vol within top 12 concurrent positions"
  - "Deleverage-only gross scale [0.5, 1.0]; floor 0.5x keeps tmin high"
  - "Fractional shares via Alpaca paper API"
fee_model:
  commission: "$0 (Alpaca) + 2.5bp W5"
  slippage: "5-7bps slippage + vol_scalar scale 2 cap 2 (W5 tiered cost)"
  settlement: "T+1"
benchmark_result:
  benchmark: "SPY identical-window twin (~1910 bars)"
feasibility_at_100:
  - "12 positions x ~$8 fractional; ~2 rebalances/mo; T+1"
risks:
  - "High exposure tmin>=0.70 => DD risk vs 35% cap; H2 failed DD 0.794 on 8-of-10 concentration"
  - "Momentum crash / crowding reversal; vol-target lags gap risk; survivorship bias in large-cap panel (acknowledged)"
  - "DSR>=0.90 at fam N=54 needs Sharpe ~=1.3+; vol compression must preserve drift"
dedup:
  - "us_momentum_top5 / dual_momentum / momentum_breakout_v2 / candidate_momentum_v4_prime / factor_momentum_top3: distinct specs, untouched"
  - "TABOO combos avoided: (126,21,5) (189,5,10) (63,42,3) (95,42,7) (252,21,8)"
  - "Differs from H2: 31-panel breadth (vs 10 names), inv-vol + vol-target + DD-deleverage (vs equal-weight unscaled), 12-of-31 deconcentration (vs 8-of-10)"

```
