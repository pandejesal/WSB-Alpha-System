# Pre-registration: smooth_trend
Cycle: smooth_trend-20260909-0607_smooth-trend
Date: 2026-09-09 11:37:36

## Claim
Slow SMA (150-300d) + vol-scaled long/flat conservative timing is SMOOTH not hot: low-DD (DD<=25-35%) + moderate Sharpe(>=0.55) + OOS>=0.35 beats high-Sharpe hot candidates that die on DSR~0.2 + DD>35%; audit of 5000 trials shows winners must be smooth. Tests slow windows 150-300, ATR/vol caps, exposure 30-70% tmin, targeting drawdown_warrior (sharpe>=0.55 DD<=35% oos>=0.35 excess>=0.10) and tail_risk_sentinel (sharpe>=0.55 DD<=25% excess>=0.03) with DSR per-family N, perm/boot<=0.05, excess>0 binding.

## Strategy Spec
```yaml
family: smooth_trend

```
