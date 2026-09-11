# Pre-registration: vol_regime
Cycle: 14
Date: 2026-09-09 08:27:36

## Claim
Daily vol-of-vol proxy (20d vol <0.8x 60d median ->1.5x, >1.4x ->0.5x/flat) overlays spy_sma (SMA200) and btc_vol (target 0.30/vol30/gate100) with VIX read-only tagging (low<15/normal15-25/high25-35/extreme>35, market_data_2019_2026/ohlcv/^VIX.csv). No intraday data (no feed in repo). Proxy limitation: daily vol-of-vol captures 40-60% of intraday variance concentration (Barndorff-Nielsen); cannot capture gap risk or vol surface; VIX never scales. Paper-only T+1 tiered cost W5. L2 Track 1 core_timing_overlay target +2pp excess vs no-overlay baseline on COVID (2020-02-19 to 2020-12-31) and 2022 (2022-01-01 to 2022-12-31) windows. Specs via hunt_runner only.

## Strategy Spec
```yaml
id: vol_regime_overlay
name: Vol-Regime Overlay Proxy (Daily Vol-of-Vol on SPY_SMA/BTC_Vol)
family: vol_regime
venue: alpaca
universe: "SPY + BTC/USD daily OHLCV 2019-2026 (20-stock panel subset), VIX read-only"
pre_registration_ref: "docs/data/cycle14_prereg_vol_regime.md"
gates_passed: "PENDING"
verdict: "PENDING"
eval_records: "docs/data/eval_vol_regime_overlay.json"
version: 1
status: "paper"

signal:
  entry: "Base signals: spy_sma (SPY close > SMA(200) shifted) and btc_vol (target 0.30 / 30d vol capped by SMA(100) trend gate); overlay scales base signal by daily vol-of-vol: 20d realized vol vs 60d median -> <0.8 => 1.5x, >1.4 => 0.5x, else 1.0x"
  exit: "Base exit: spy_sma flip to cash when close < SMA(200); btc_vol flat when close <= SMA(100) or vol-scaled lev 0; overlay maintains same exit timing, only scales magnitude (clip spy 0-1.5, btc 0-1.0)"
  sizing: "Overlay-scaled position: pos_scaled = clip(base_signal * vol_regime_scale, 0, cap); T+1 execution (signal.shift(1)), tiered cost W5 deducted on turnover"
  caps:
    max_concurrent_positions: 2
  rebalance: "daily target rows, no intraday"
  vix_tagging: "VIX read-only: cut low<15 normal15-25 high25-35 extreme>35 from ^VIX.csv; tagging only, never scales positions (proxy limitation documented)"

parameters:
  vol_window: 20
  median_window: 60
  low_thresh: 0.8
  high_thresh: 1.4
  low_scale: 1.5
  high_scale: 0.5
  spy_sma_window: 200
  btc_target_vol: 0.30
  btc_vol_window: 30
  btc_gate_window: 100
  exec_delay: 1
  cap_spy: 1.5
  cap_btc: 1.0

indicators:
  - vol20: "20-day rolling std of daily returns (realized vol proxy, daily only)"
  - vol_median60: "60-day rolling median of vol20 (regime baseline)"
  - vol_ratio: "vol20 / vol_median60 (vol-of-vol, thresholds 0.8 and 1.4)"
  - vix_close: "VIX close read-only regime tag (low<15 normal15-25 high25-35 extreme>35, market_data_2019_2026/ohlcv/^VIX.csv)"
  - spy_sma200: "200-day SMA of SPY close (base signal)"
  - btc_realized_vol30: "30-day BTC realized vol annualized x sqrt(365) (base signal)"

position_sizing:
  - "SPY overlay: exposure = clip((close > SMA200) * vol_regime_scale, 0, 1.5); 1.5x only in calm (vol<0.8 median), 0.5x in stressed (vol>1.4 median)"
  - "BTC overlay: exposure = clip((target/vol30 * (close > SMA100)) * vol_regime_scale, 0, 1.0); same thresholds"
  - "T+1, fractional, min order $1; no margin; no PDT"
  - "Paper-only: LIVE_TRADING_ENABLED=false, no live promotion"

fee_model:
  commission: "$0 (Alpaca) + 1bp"
  slippage: "tiered W5: SPY 5-7bps + BTC 15-25bps vol-scaled (vol_scalar=rolling_std(20)/median_60, scale 2 cap2 equities / scale10 cap10 BTC)"
  settlement: "T+1 equiv (signal.shift(1)); borrow guard +10bps if short (not used, long/flat only)"

benchmark_result:
  benchmark: "SPY buy-hold, identical window + no-overlay baseline (same spy_sma/btc_vol without scale)"
  full: "Overlay vs no-overlay: full-window (1910 bars 2019-01-02 to 2026-08-07) overlay excess -104.8 vs baseline -120.5 = +15.7pp (SPY sma200 base); BTC overlay trail - see eval"
  covid_window: "COVID (2020-02-19 to 2020-12-31): overlay excess +10.1 vs baseline -8.4 = +18.5pp (SPY sma200); VIX tagging confirms high/extreme regime"
  bear_2022_window: "2022 (2022-01-01 to 2022-12-31): overlay excess +2.0 vs baseline +2.65 = -0.65pp (fails +2pp target; proxy limitation)"
  oos_2023plus: "OOS Sharpe overlay 1.11 vs baseline 1.36 (full), COVID OOS 1.32 vs 0.39"
  sharpe_note: "Full-window Track 1 still fails excess>=0.05 (both -100pp trail SPY bull); L2 overlay delta target is window-specific, not full-window gate"

robustness_notes:
  - "Daily vol-of-vol proxies 40-60% of intraday variance concentration (Barndorff-Nielsen); cannot capture gap risk or vol-surface skew"
  - "No intraday/minute/hourly data attempted (no feed in repo); VIX ^VIX.csv read-only, never used for scaling"
  - "COVID window strongly benefits (+18.5pp) from 0.5x in high vol crash (2020-03) and 1.5x in calm recovery"
  - "2022 bear fails +2pp target (-0.65pp) because 20d/60d vol-of-vol rarely triggers >1.4x in that regime; proxy limitation documented in prereg"
  - "Parameter sweep fixed per spec (20/60/0.8/1.4/1.5/0.5); no lookahead (ratio uses realized vol only), T+1, tiered cost identical"

feasibility_at_100:
  - "Two positions max (SPY + BTC), daily rebalance, 67 trades vs 18 baseline for SPY leg (2020-2026); fees affordable at $0 commission + 5-7bps"
  - "No new data feed: uses existing market_data_2019_2026/ohlcv/*.csv only"
  - "Paper-only via hunt_runner; no live code path"

risks:
  - "Proxy cannot capture intraday volatility clustering or overnight gaps (40-60% capture only)"
  - "Leverage 1.5x in calm raises drawdown if calm precedes crash (vol lags)"
  - "Full-window still trails SPY buy-hold by ~105pp; only window-specific excess improves"
  - "BTC overlay trails baseline on full window (-107pp delta) due to vol scaling whipsaw; SPY leg drives COVID benefit"
  - "Does not beat buy-and-hold on full-period Sharpe or excess; Track 1 still elite-only"

proxy_limitation: "Daily vol-of-vol is a proxy for intraday variance concentration (Barndorff-Nielsen 40-60% realized variance). No intraday, options, or vol-surface feed exists in this repo; VIX ^VIX.csv is read-only regime tagging (low<15/normal15-25/high25-35/extreme>35) never used to scale. Intraday gap risk unobserved."

overlay_on: "spy_sma (SMA200) + btc_vol (target 0.30, vol30, gate 100) via src/backtest/metrics.py vol_regime_scale()"
intraday_data: "none - daily OHLCV only, no 1-min/hourly attempts"
vix_usage: "read-only tagging from market_data_2019_2026/ohlcv/^VIX.csv, never scales positions"

```
