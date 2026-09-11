# Pre-registration: tail_risk_sentinel
Cycle: tail_risk_sentinel-20260909-0109_tail-risk-sentinel
Date: 2026-09-09 06:39:55

## Claim
VIX level (20-60d window, entry 22-30) + ATR trailing stop (1.5-3.0x) + vol regime cap (realized vol 0.18-0.25) as tail hedge cuts SPY maxDD 33.7% to <=25% while preserving excess>=0.03pp via selective cash rotation; strictest DD gate (Track 4) blocks high-beta bull-run passengers, perm/boot blocks crash-fit, fallback to drawdown_warrior (maxDD<=35% excess>=0.10) if pure hedge cannot clear excess.

## Strategy Spec
```yaml
family: tail_risk_sentinel

```
