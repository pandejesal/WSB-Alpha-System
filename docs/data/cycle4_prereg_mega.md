# Cycle 4 — Claim 5/1: "Mega" Composite Meta-Model (PRE-REGISTRATION — FROZEN)

Date frozen: 2026-08-16. Status: LOCKED. No backtest has been run against
this document; every number, feature, parameter and gate below is fixed
before any engine execution. Any change requires a pre-registered Appendix B
delta written before the affected run (Q28 discipline, unchanged).

## 1. Claim (user directive)

"What if we use all this indicators together for one mega strategy" — a
single learned meta-model combining ALL existing price/factor signals into
one strategy, evaluated on TWO universes with ONE frozen model spec.

## 2. Design decisions (from /grilling, all user-confirmed)

| # | Decision | Value |
|---|----------|-------|
| Q1 | Universe of signals | Price TA set + factor/flow (13F accumulation, MOM12-1, REV1). Sentiment/news/events EXCLUDED (data-thin: news degraded to 0 articles, Reddit 11 tickers) |
| Q2/Q8 | Combination mechanism | Learned meta-model = GradientBoostingRegressor, EXACT frozen C4 hyperparameters (Appendix A.1) |
| Q3/Q12 | Bar | SAME pre-registered bar as C1-C4 claims (Appendix A.2) |
| Q4/Q13 | Discipline | NEW pre-registered claim C5 "Mega", Cycle 4; kill rules apply; deltas only via pre-registered Appendix B |
| Q5 | Feature reuse | Raw indicators + factor SERIES as features; frozen claim verdicts stay frozen (no resurrection) |
| Q6/Q11 | Universes | BOTH: (L1) 481-name weekly cross-section; (L2) 12-instrument multi-asset (ETFs + crypto). ONE frozen spec, SEPARATE models per leg |
| Q9 | Features | ALL signals, rank-normalized cross-sectionally per rebalance date, NO feature selection |
| Q10 | Training | IDENTICAL to C4: expanding walk-forward, annual refits (52 rebalance dates), last anchor <= 2023-12-31, OOS predicted with final train-fitted model only |
| Q14 | Multi-asset portfolio | Top/bottom QUARTILE L/S (top 3 long / bottom 3 short, equal weight), all 12 instruments required (MIN_N=12) |
| Q15 | Multi-asset features | Price+TA subset only (13F/MOM12-1/REV1 undefined for ETFs/crypto — excluded, frozen) |
| Q16 | Multi-asset costs | C2 tiered: 5bps/side equity/index, 10bps/side crypto |
| Q17 | Verdict | BOTH legs must pass the full bar for C5 to pass |
| Q18 | Cadence | Freeze today, build + run this session, refresh with 2026-09-17 verdict |

## 3. Appendix A — FROZEN SPECIFICATION

### A.1 Model (both legs, identical)

```
GradientBoostingRegressor(
    n_estimators=200, learning_rate=0.05, max_depth=3,
    min_samples_leaf=20, subsample=0.8, random_state=7,
    loss="squared_error")
```

- Refit: annually (every 52 rebalance dates) on the EXPANDING train window;
  last refit anchor <= 2023-12-31. OOS predictions use only the final
  train-fitted model.
- Walk-forward train predictions: at each train date d, model fitted at the
  latest anchor <= d predicts that date's cross-section (train-consistency
  gate input).
- Train window: rebalance dates < 2023-12-31. OOS window: 2024-01-01..
  2026-08-07. Rows whose forward-return window crosses past 2023-12-31 are
  dropped (fail-closed: no OOS-period label in training).

### A.2 Gates / bar (both legs, same as C1-C4)

| Gate | Pass condition |
|------|----------------|
| train_consistency | mean walk-forward train factor return > 0 |
| oos_median_3of4_years | OOS median > 0 in >= 3 of {2024, 2025, 2026, 2027} (2026 partial, 2027 not computable -> earliest possible pass end-2027, pre-registered structural constraint) |
| oos_sharpe_ge_1 | annualized Sharpe (x sqrt(52)) >= 1.0 |
| oos_maxdd_le_25 | max drawdown >= -25% |
| oos_cagr_ge_15 | net CAGR >= 15% |
| null_p95 | OOS mean weekly factor return > p95 of 1000x block-shuffle null (permutation of the leg's full weekly factor series, OOS-mean statistic, RNG seed 7) |

C5 bar_pass = (L1 bar_pass) AND (L2 bar_pass). Q17.

### A.3 Leg 1 (L1) — 481-name weekly cross-section

- Universe: frozen 481-name S&P 500 snapshot (cache/cycle3_13f_ticker_map.json).
- Rebalance: last trading bar of each ISO week (Friday close), union of
  snapshot calendars.
- Target: forward 1-week Friday-to-Friday return (close(t+1)/close(t)-1 on
  consecutive rebalance bars), rank-normalized within each rebalance date
  (rank -> uniform -> inverse normal CDF, same transform as C4).
- FEATURES (26, ALL rank-normalized cross-sectionally per rebalance date,
  no selection, no imputation — rows with any NaN feature dropped):
  1-12. C4 price features: r1w r2w r4w r12w r26w r52w vol20 vol60 rsi14
        d_sma20 d_sma50 d_sma200 (exact C4 definitions)
  13.   EMA20 distance: close/EMA_20(20d) - 1
  14.   ATR14 relative: ATR_14(14d)/close
  15.   RSI_14 (daily, compute_indicators definition)
  16.   MACD relative: MACD/close
  17.   MACD_Signal relative: MACD_Signal/close
  18.   MACD_Hist relative: MACD_Hist/close
  19.   HA_Close distance: HA_Close/close - 1
  20.   BB position: (close - BB_Lower)/(BB_Upper - BB_Lower)
  21.   GK_Vol (Garman-Klass 20d, annualized)
  22.   VaR_95 (rolling 20d 95% VaR)
  23.   CVaR_95 (rolling 20d 95% CVaR)
  24.   13F accumulation (quarterly, CARRY-FORWARD at last-known value:
        for rebalance date d, use the most recent quarter q with entry
        date (q_end + 45d + 1 trading day) <= d; names with no 13F
        value at q excluded that week)
  25.   MOM12-1 (monthly: close(M-2)/close(M-12)-1; row M knowable at end
        of month M-1 -> used for signal bars in month M, exact C2
        factor_engine.py definition)
  26.   REV1 (monthly: close(M-1)/close(M-2)-1; same timing rule)
- Portfolio: rank by prediction; long top decile, short bottom decile,
  equal weight; MIN_N=20 rankable names; costs 10bps/side on traded
  notional (turnover-based, both legs, weight change vs prior rebalance;
  first week charges full entry notional) — C4 convention.
- Null: 1000x block-shuffle of L1's weekly factor series, OOS-mean
  statistic, RNG seed 7.

### A.4 Leg 2 (L2) — 12-instrument multi-asset

- Universe: SPY QQQ IWM EFA EEM TLT GLD SLV HYG UUP BTC-USD ETH-USD (12).
- Rebalance: last trading bar of each ISO week on the SPY calendar; crypto
  reindexed to the same Fridays (C2 convention).
- Target: forward 1-week Friday-to-Friday return, rank-normalized within
  each rebalance date (same transform).
- FEATURES (23, rank-normalized cross-sectionally across the 12
  instruments per rebalance date): C4 set 1-12 + TA set 13-23 (identical
  definitions to L1 items 13-23). 13F/MOM12-1/REV1 EXCLUDED (not defined
  for ETFs/crypto — Q15).
- Portfolio: rank by prediction; long top quartile (top 3), short bottom
  quartile (bottom 3), equal weight per leg; ALL 12 instruments required
  (MIN_N=12 — any missing feature skips the week); costs C2 tiered:
  5bps/side equity/index (SPY QQQ IWM EFA EEM TLT GLD SLV HYG UUP),
  10bps/side crypto (BTC-USD ETH-USD), turnover-based vs prior weights,
  first week charges full entry notional.
- Null: 1000x block-shuffle of L2's weekly factor series, OOS-mean
  statistic, RNG seed 7.

### A.5 Data

- Prices: market_data_2019_2026/ohlcv/*.csv (501 files; skip
  INSTRUMENTS.csv, MISSING.csv). Adjusted closes from yfinance; crypto
  trades daily.
- 13F: cache/13f/*.xml, 50 funds, SOLE discretion only, name->ticker via
  cycle3_13f_map.py resolver (exact Claim 1 pipeline; missing-filing rule:
  zero-change contribution).
- First full-feature L1 row ~2020-01 (52w lag + 200d SMA + 12-month
  MOM12-1 warm-up; 13F first entry ~2019-05-16) — declared availability
  fact, not a bug.
- TA indicators computed daily via compute_indicators (src/alpha/
  indicators.py, lowercase OHLCV columns renamed to Open/High/Low/Close
  before the call), values taken at each rebalance date.

### A.6 Environment

- Python: C:\Users\DELL\anaconda3\python.exe. Installed versions used:
  sklearn 1.6.1, numpy 2.4.6, pandas 3.0.5 (Appendix B.1 delta, same as
  C4 — frozen versions 1.9.0/2.2.0/2.2.3 not installed; declared BEFORE
  any run).

## 4. Appendix B — PRE-REGISTERED DELTAS (all declared before this run)

- B.1 sklearn/numpy/pandas versions (see A.6).
- B.2 Target and features rank-normalized via inverse normal CDF of
  cross-sectional ranks (norm.ppf(rank/(n+1))) — declared combination
  transform for the meta-model (no lookahead; per-date transform).
- B.3 The two legs are evaluated with identical model spec but separate
  fitted models (Q11); no weights are shared or tuned between legs.
- B.4 13F carry-forward rule (A.3 item 24) — quarterly factor is
  time-aligned to weekly rebalances at its last-known value; this is the
  Q12-locked rule, no lookahead (entry date strictly after q_end + 45d).

## 5. Kill rules (unchanged from C3, Q28)

- Any change to this document after the first backtest = disqualification
  of the claim unless written as a delta BEFORE the affected run.
- Wrong train sign (train_consistency False) = dead on arrival.
- No tuning, no re-scoring, no re-ranking after seeing results.
- Losers reopenable only via a NEW pre-registered delta.

## 6. Outputs

- docs/data/cycle4_mega_evaluation.json (gate verdicts per leg + C5 verdict)
- docs/data/cycle4_mega_results.json (full numbers per leg)
- Engine: scripts/cycle4_mega_engine.py (this pre-reg is the contract)