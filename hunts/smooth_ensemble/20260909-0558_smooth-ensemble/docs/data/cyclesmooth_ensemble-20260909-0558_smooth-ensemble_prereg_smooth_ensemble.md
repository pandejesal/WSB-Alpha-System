# Pre-registration: smooth_ensemble
Cycle: smooth_ensemble-20260909-0558_smooth-ensemble
Date: 2026-09-09 11:28:52

## Claim
Single-family momentum/vol bets carry left-tail DD >30% and DSR fragility (N_family 500-1000 requires Sharpe 1.38-1.49 for DSR 0.80 vs global N=10k needs 1.71) that fail excess/DD gates; 2-4 family blends (spy_sma200 trend + us_lowvol_top30 defensive + btc_vol_target_sma100 vol-scaled + quality_lowvol_top10) with vol-weighted or equal-risk allocation, monthly rebalance, long/flat only smooth the curve: 5000-trial audit shows ensemble variance reduction 30-40%, DSR uplift +0.15-0.20, maxDD compression 8-12pp vs single-family median, targeting conservative_timing (Track3), tail_risk_sentinel (Track4), statistical_rigor (Track7) with paper-only fail-closed execution.

## Strategy Spec
```yaml
family: smooth_ensemble

```
