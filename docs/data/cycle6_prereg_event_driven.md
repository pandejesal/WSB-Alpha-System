# Pre-registration: event_driven
Cycle: 6
Date: 2026-08-25 10:59:19

## Claim
US PEAD Top-5 v2: On 100-stock liquid large-cap panel, long Top-5 by earnings Surprise% >=0 next-bar entry hold 5d equal-weight beats SPY on OOS net CAGR and Sharpe and passes stationary bootstrap p<=0.05, CPCV K=6 embargo10, walk-forward 5-fold, permutation null, DSR. Bernard-Thomas drift 4.2%/60d basis.

## Strategy Spec
```yaml
id: us_pead_top5_v2
name: "US PEAD Top-5 v2 (Earnings Surprise Drift)"
family: event_driven
venue: alpaca
version: 2
status: "PASS_ALL_GATES"
universe: >
  100-stock liquid large-cap panel (481-name frozen S&P 500 snapshot,
  2026-08-14) minus SPY/QQQ/AGG/BND/SHY/GLD/VTI/IWM. Survivorship bias
  documented; mitigated by sign gate + permutation null.
pre_registration_ref: "docs/data/cycle6_prereg_pead_top5_v2.md"
gates_passed: "5/5"
verdict: "PASS_ALL_GATES"
eval_records: "docs/data/cycle6_eval_pead_top5_v2.json"
signal:
  entry: >
    On the trading day strictly after an earnings announcement where
    Reported EPS is present AND Surprise(%) >= surprise_threshold_pct,
    the stock becomes eligible. From all eligible stocks, rank by
    Surprise(%) descending, select top max_k (5). Entry executes next
    bar (exec_delay=1) - no lookahead. Earnings dates sourced from
    yfinance get_earnings_dates(limit=100) covering 2001-2026 history
    per name. Filing lag of +1 business day enforced.
  exit: >
    Exit after hold_days trading bars from entry. Cohort exit, target
    weight drops to 0.0 on exit bar. No early stop-loss in frozen spec.
  sizing: >
    Equal weight across active positions: 1/N_active per day, where
    N_active = number of open positions (max max_k). Fractional shares
    permitted via Alpaca.
  caps:
    max_concurrent_positions: 5
  rebalance: >
    Daily target rows. Drift band = drift_rebal (5%): rebalanced when
    weight deviates >5% from target.
params:
  surprise_threshold_pct: 0.0
  hold_days: 5
  max_k: 5
  exec_delay: 1
  drift_rebal: 0.05
variant_grid:
  surprise_threshold_pct: [0.0, 2.0]
  hold_days: [3, 5, 10]
  frozen_combination:
    surprise_threshold_pct: 0.0
    hold_days: 5
indicators:
  - "earnings_dates: yfinance get_earnings_dates(limit=100), 2001-2026"
  - "surprise_pct: Reported EPS vs Estimate EPS"
  - "filing_lag: +1 business day enforced"
position_sizing:
  - "Equal weight up to max 5 concurrent positions"
  - "Fractional shares via Alpaca paper API"
  - "1/N_active per position, rebalanced daily within 5% drift band"
fee_model:
  commission: "$0 (Alpaca)"
  slippage: "0.05% per side (entry + exit = 10 bps round-trip)"
  settlement: "T+1 (Alpaca paper, cash account)"
citations:
  - "Bernard & Thomas 1989, JAR 27:1-36 - SUE decile 4.2%/60d"
  - "Livnat & Mendenhall 2006, TAR - post-2000 3.2%/60d"
  - "Chordia et al. 2009 - 2007+ 1.5-3.0%/60d"
feasibility_at_100:
  - "5 concurrent positions x $20 at $100, fractional shares required"
  - "Earnings quarterly - signal ~4x per stock per year, 15-30 trades/mo"
risks:
  - "Declining PEAD magnitude, aggregation bias, yfinance date quality, slippage"

```
