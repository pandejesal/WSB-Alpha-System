# Pre-registration: factor_momentum
Cycle: 15
Date: 2026-09-09 08:38:56

## Claim
W11 rehab factor_momentum_top3: 30-stock panel MOM 12-1 VAL inverse P/E QUA ROE stability composite avg z-score with D/E<2 OPM>0 FCF>0 quality filter, monthly forward-filled tmin>=0.80, tiered cost W5, W2 WF strict, targets Track6 buy_hold_companion sharpe>=0.85 oos>=0.55 excess>=0.02 tmin>=0.80 DSR>=0.95 or Track7 sharpe>=0.70 trips>=15 DSR>=0.92, perm/boot<=0.05, SPY identical-window 1910 bars, paper-only

## Strategy Spec
```yaml
id: factor_momentum_top3
name: Factor Momentum Top-3 (Gupta-Kelly style, long-only, W11 rehab)
family: factor_momentum
venue: alpaca
universe: "30-stock liquid large-cap US panel (rotation_universe 30 names: AAPL/MSFT/GOOGL/AMZN/NVDA/META/TSLA/JPM/V/JNJ/WMT/MA/PG/UNH/XOM/HD/DIS/BAC/CVX/KO/PEP/COST/AVGO/LLY/ABBV/NKE/CRM/ORCL/NFLX/AMD; excludes SPY/QQQ/AGG/BND/SHY/GLD/VTI/IWM; SPY baseline identical-window 1910 bars T+1 tiered cost)"
pre_registration_ref: "docs/data/cycle7_prereg_factor_momentum.md"
gates_passed: "0/5"
verdict: "PENDING_W11_REHAB"
eval_records: "docs/data/cycle7_eval_factor_momentum.json"
signal:
  entry: >
    Monthly factor-momentum rotation with quality pre-filter. (1) Quality filter: D/E<2.0, OPM>0, FCF>0 (latest quarterly trailing 4Q, symbolic safety; fail-closed skip if data missing). (2) Compute 3 factor returns: MOM 12-1 (126d skip 21d mean), VAL inverse P/E z-rank (proxied by 1/(price/200d SMA) cross-sectional rank when P/E unavailable), QUA ROE/stability z-rank (proxied by -20d realized vol and trailing 12M Sharpe when ROE unavailable). Rank each factor, composite = avg of 3 z-scores. Select top 3 by trailing 12-month rolling mean of monthly factor returns (factor momentum, Gupta-Kelly TSFM). Long only top 3, equal weight, forward-filled holding (tmin>=0.80).
  exit: >
    Dropped at next monthly rebalance if falls out of top 3 or fails quality re-screen. Drift-band (>5%) only intra-month. Forward-filled weights (not 1-day) to achieve buy_hold_companion tmin>=0.80.
  sizing: "Equal weight 1/3 per position; fractional shares on Alpaca; T+1 execution"
  caps:
    max_concurrent_positions: 3
  rebalance: "monthly, last trading bar of month, forward-filled until next rebalance"
parameters:
  mom_lookback_days: 252
  mom_skip_days: 21
  mom_window_days: 126
  val_metric: "inverse_pe_proxy"
  quality_metric: "roe_stability_proxy"
  quality_filter:
    debt_equity_max: 2.0
    operating_margin_min: 0.0
    fcf_positive: true
  factor_mom_lookback: 12
  factor_mom_skip: 1
  top_n: 3
  rebalance: "monthly"
  exec_delay: 1
  drift_rebal: 0.05
  warmup_days: 340
  universe_size: 30
  cost_model: "tiered W5: equities 5-7bps slippage +1bp commission vol_scalar=rolling_std(20)/median_60 scale 2 cap 2, fallback 5bps never 0; identical in _rotation_result()"
  walk_forward_gate: "W2 strict: avg OOS >=0.40 and consistency <1.5 and windows>=3 and >=2/3 positive (src/backtest/walk_forward_engine.py)"
indicators:
  - "momentum_12_1: 12-month return skipping last 21 days (126d window)"
  - "value_hml: inverse P/E cross-sectional z-rank (price/200SMA proxy when fundamentals missing)"
  - "quality_qm: ROE / std(quarterly ROE, 8Q) z-rank (proxied by -rv20 and Sharpe when ROE missing)"
  - "factor_momentum_composite: trailing 12-month mean of monthly factor z-scores"
  - "quality_filter: D/E<2 OPM>0 FCF>0 symbolic safety pre-filter"
entry_rules:
  - "at each month-end, apply quality filter D/E<2 OPM>0 FCF>0 to 30-stock panel (skip if data unavailable, fail-closed)"
  - "compute z-scores for MOM 12-1, VAL inverse P/E proxy, QUA ROE stability proxy across survivors"
  - "composite = avg of 3 z-scores; rank factors by trailing 12-month factor momentum (skip 1 month, Gupta-Kelly)"
  - "hold top 3 by composite, equal weight 1/3, forward-filled until next month"
exit_rules:
  - "dropped when falls out of top-3 at next month-end or fails D/E/OPM/FCF re-screen"
  - "drift-based rebalance only (>5%); forward-filled tmin>=0.80"
position_sizing:
  - "$100 account: 3 x ~$33.33 fractional shares"
  - "min order $1; no margin, no PDT; T+1"
  - "equal weight at each rebalance, forward-filled"
fee_model:
  commission: "$0 (Alpaca) + 1bp tiered commission per W5"
  slippage: "5-7bps slippage vol-scaled (equities) + 1bp commission; cost_bps = base 5 + commission 1 + (vol_scalar-1).clip(0)*2 cap2; fallback 5bps never 0"
  settlement: "T+1 cash; min $1; identical-window SPY twin for excess"
benchmark_result:
  benchmark: "SPY buy-and-hold, same engine, same 1910-bar window, T+1 tiered cost"
  full: "PENDING_W11_REHAB"
  oos_2023plus: "PENDING"
  expected_range: "Gupta & Kelly 2019 TSFM Sharpe 0.84 (1M) / 0.70 (12M); long-only 3-name expected 0.6-1.0 IS, 0.3-0.7 OOS after decay; W11 30-stock forward-filled targets 0.85-1.2 IS, 0.55+ OOS for Track6"
feasibility_at_100:
  - "3 x ~$33 fractional, $0 commissions, monthly rebalance, forward-filled tmin>=0.80"
  - "cash account avoids PDT; tiered cost realistic"
risks:
  - "factor crowding, 3-name concentration variance, survivorship bias (30 survivors bias +0.05-0.10 Sharpe), fundamentals staleness, no short leg, vol-scaled cost adds 0-2bps"
version: 2
status: "hunting_w11"
w11_rehab: "2026-09-09: expanded to 30-stock panel (config/universe.json rotation_universe), added D/E<2 OPM>0 FCF>0 quality filter, VAL/QUA proxy scoring, forward-filled holding for tmin>=0.80, tiered cost W5, W2 strict WF gate; SPY baseline identical-window kept"

```
