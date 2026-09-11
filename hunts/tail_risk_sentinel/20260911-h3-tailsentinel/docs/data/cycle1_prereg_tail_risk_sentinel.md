# Pre-registration: tail_risk_sentinel
Cycle: 1
Date: 2026-09-11 14:37:41
Spec-SHA256: 60ae312f0177dfe06a25a3169405273362a6e4b8931f76f16dabd93bfbccf114

## Claim
Pure SMA-trend graduated de-risk ladder on SPY (50/100/200, levels 1.00/0.65/0.30/0.00, no VIX/ATR/volcap) cuts SPY maxDD<=25% with identical-window excess>=+0.03pp (Track 4 tail_risk_sentinel; fallback Track 2 drawdown_warrior)

## Strategy Spec
```yaml
id: tail_risk_sentinel_h3
name: "Tail Risk Sentinel H3 (SMA50/100/200 graduated de-risk ladder, no VIX)"
family: tail_risk_sentinel
venue: alpaca
universe: "SPY daily OHLCV 2019-2026 (market_data_2019_2026/ohlcv/SPY.csv, T=1910 bars)"
pre_registration_ref: "hunts/tail_risk_sentinel/20260911-h3-tailsentinel/docs/data/H3_tail_risk_sentinel_h3_prereg.md"
gates_passed: "0/5"
verdict: "PENDING"
eval_records: "hunts/tail_risk_sentinel/20260911-h3-tailsentinel/results/eval_tail_risk_sentinel_h3.json"
status: "paper"
version: 1
signal:
  entry: "Graduated SPY exposure from close vs SMA50/100/200 (all past-only, shift1): above all three -> 1.00; below SMA50 only -> 0.65; below SMA100 -> 0.30; below SMA200 -> 0.00 (flat)"
  exit: "Ladder re-risk symmetrically as price reclaims each SMA; no stop, no vol cap, no VIX input"
  sizing: "Fractional SPY vs cash per ladder level (1.00/0.65/0.30/0.00)"
  caps:
    max_concurrent_positions: 1
  rebalance: "daily"
parameters:
  sma_fast: 50
  sma_mid: 100
  sma_slow: 200
  level_all_above: 1.0
  level_below_fast: 0.65
  level_below_mid: 0.30
  level_below_slow: 0.0
  exec_delay: 1
indicators:
  - "SPY close vs SMA50 (past-only, shift1)"
  - "SPY close vs SMA100 (past-only, shift1)"
  - "SPY close vs SMA200 (past-only, shift1)"

```
