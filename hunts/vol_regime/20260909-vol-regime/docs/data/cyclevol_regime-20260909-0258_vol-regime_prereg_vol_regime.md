# Pre-registration: vol_regime
Cycle: vol_regime-20260909-0258_vol-regime
Date: 2026-09-09 08:28:29

## Claim
Daily vol-of-vol proxy (20d realized vol vs 60d median) overlays spy_sma and btc_vol signals: low vol regime (vol <0.8x median) -> 1.5x leverage, high vol regime (vol >1.4x median) -> 0.5x/flat, else 1.0x. VIX is read-only regime tagging (low<15/normal 15-25/high 25-35/extreme>35) never used for scaling. Proxy captures 40-60% of intraday variance concentration (Barndorff-Nielsen) without intraday feed. Expected: overlay improves COVID/2022 window excess by +2pp vs no-overlay baseline on same signals via reduced drawdown in stress and levered carry in calm, while maintaining paper-only T+1 + tiered cost (W5).

## Strategy Spec
```yaml
family: vol_regime

```
