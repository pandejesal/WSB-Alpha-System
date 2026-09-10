# Pre-registration: factor_rotation
Cycle: factor_rotation-20260909-0306_factor-rotation
Date: 2026-09-09 08:36:56

## Claim
Cross-sectional factor rotation beyond pure momentum/lowvol: MOM 12-1 (126d skip 21d) + VAL inverse P/E (price/200SMA proxy) + QUA ROE/stability (rv20/Sharpe proxy) composite (avg z-score) filtered by quality D/E<2 OPM>0 FCF>0, with 30-stock large-cap panel and forward-filled monthly holding (tmin>=0.80), beats SPY buy-hold net of tiered cost (5-7bps +1bp vol-scaled) with Sharpe>=0.85, OOS>=0.55, excess>=0.02pp, DSR>=0.95 (Track6 buy_hold_companion) or Sharpe>=0.70 trips>=15 DSR>=0.92 (Track7 statistical_rigor), perm_p<=0.05 boot_p<=0.05. Exploits 80% of factor zoo (value 3-5%, quality 2-4%, multi-factor 5-8% Fama-French/Novy-Marx) with realistic cost and W2 strict WF gate.

## Strategy Spec
```yaml
family: factor_rotation

```
