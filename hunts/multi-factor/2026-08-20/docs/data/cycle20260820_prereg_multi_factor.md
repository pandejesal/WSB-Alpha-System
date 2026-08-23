# Pre-registration: multi_factor
Cycle: 20260820
Date: 2026-08-20 05:43:48

## Claim
stocks passing >=4 of 6 CANSLIM-style checks with market breadth >=60 and FRED regime non-recessionary beat the equal-weight benchmark by 0.5 Sharpe at DSR>1

## Strategy Spec
```yaml
acceptance: Edge claim is pre-registered in docs/data/. YAML spec is fully complete
  and parses without errors. registry.json is updated and wired correctly. Strategy
  passes Walk-Forward validation, Permutation tests, and achieves a positive Deflated
  Sharpe Ratio (DSR) ledger entry.
edge_gate_params: {}
family: multi_factor
hypothesis: stocks passing >=4 of 6 CANSLIM-style checks with market breadth >=60
  and FRED regime non-recessionary beat the equal-weight benchmark by 0.5 Sharpe at
  DSR>1
lookback_constraints: 2019-2026 daily
universe: 100-stock liquid large-cap panel (excluding SPY/QQQ/AGG/BND)

```
