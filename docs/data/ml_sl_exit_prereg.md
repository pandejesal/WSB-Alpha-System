# Pre-registration — H-SLX-1: SL-adjusted-label GBDT exit overlay on us_momentum_top5

Status: FROZEN before any in-sample model run. Committed 2026-08-24.
Companion artifacts: `workspace/stages/01_hypothesis/output/hypothesis_brief.yaml`,
`workspace/stages/01_hypothesis/output/prior_art.md`.
Research basis: `docs/research/XGBOOST-EXITS-2026-08-17.md` §5 pattern (iii), §7 kill rules,
§8 recommendation #1 (Hwang et al. 2023 SL-adjusted labels; Kaminski & Lo 2014; Lo & Remorov 2017).

## Claim (single, falsifiable)

An SL-adjusted-label gradient-boosting exit overlay applied to us_momentum_top5 holdings
beats the static rank-drop exit on OOS Sharpe by ≥ +0.10 without worsening maxDD, passing
train-consistency sign and permutation-null survival. Otherwise: honest FAIL, static exits
stay canonical (mirrors topic-07 recording discipline).

## Arms (identical except exit logic)

Both arms share one engine, one data panel, one cost model. Absolute levels may differ
from strategies/us_momentum_top5.yaml benchmark_result because the universe here is the
declared frozen snapshot; ALL gates compare arms within-engine, never against YAML numbers.

- **Data:** market_data_2019_2026/ohlcv/*.csv daily OHLCV, 2019-01-02 .. 2026-08-07.
- **Universe:** tickers in frozen snapshot `cache/cycle3_13f_ticker_map.json`
  (`ticker_to_names` keys) ∩ local CSVs. SPY excluded from selection (kept as data sanity
  anchor). Survivorship bias of today's-membership snapshot is inherited and DECLARED;
  it applies equally to both arms.
- **Entry:** on the last trading bar of each month, rank eligible tickers by momentum =
  Close[t−21]/Close[t−147] − 1 (126-bar lookback skipping most recent 21 bars, computed on
  closes up to and including decision bar t). Buy the top 5 at the NEXT bar's close
  (exec_delay=1), equal weight current-equity/5 each, cash-only, no margin.
  Eligibility: ticker has ≥ 260 prior bars of history and all 13 features computable.
  Fewer than 5 eligible ⇒ take best available (min 1); none ⇒ hold cash that month.
- **Static arm exits:** a held name is sold at the next bar's close when, at a month-end
  decision bar, it is not in the new top-5. No other exits.
- **ML arm adds one rule:** while holding a name, at each bar t compute p_good(t) from the
  frozen model; if p_good(t) < θ, sell at close of bar t+1 (same exec_delay convention).
  An ML-exited name stays OUT until a later month-end re-selects it. Static month-end
  rank-drop exits still apply.
- **Accounting:** $100,000 initial equity (scale-invariant metrics), daily mark-to-market
  at close, cash yields 0%, same-day settlement (declared simplification; identical in
  both arms). NO interim drift rebalancing in either arm (declared simplification;
  surviving top-5 names are NOT resized at month-ends). Costs: 0.05% (5 bps) slippage
  per side on every fill (core fee_model), commission $0.

## Label (training target)

Observation = (ticker, bar t) on the STATIC-arm holding path (holding bars only, entry
through exit−1). With K=10, δ=0.20:

    label = 1  iff  min_{j=1..K}( Low[t+j]/Close[t] − 1 ) ≥ −δ   AND   Close[t+K]/Close[t] − 1 > 0
    label = 0  otherwise

Rows needing future bars beyond available data are dropped. Train set = such rows with
t ≤ 2023-12-31. (Hwang et al. 2023 adaptation: their daily futures/crypto formulation
applied to our daily equity panel with position-relative stop level.)

## Features (13, all price-only, computed at bar t from data ≤ t)

| # | name | definition |
|---|---|---|
| 1 | r1 | Close.pct_change(1) |
| 2 | r2 | pct_change(2) |
| 3 | r5 | pct_change(5) |
| 4 | r21 | pct_change(21) |
| 5 | r63 | pct_change(63) |
| 6 | r252 | pct_change(252) |
| 7 | vol20 | std(daily ret, 20)·√252 |
| 8 | vol60 | std(daily ret, 60)·√252 |
| 9 | rsi14 | Wilder RSI(14), daily |
| 10 | d_sma20 | Close/SMA20 − 1 |
| 11 | d_sma50 | Close/SMA50 − 1 |
| 12 | d_sma200 | Close/SMA200 − 1 |
| 13 | pos_ret | Close[t]/entry_close − 1 (position P&L since entry) |

NaNs handled natively by the model (`HistGradientBoostingClassifier` supports missing).

## Model (fixed, no tuning)

`sklearn 1.6.1 HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05,
max_depth=3, min_samples_leaf=20, l2_regularization=0.0, random_state=7)` with
`monotonic_cst = [0]*12 + [+1]` (higher position P&L can only increase predicted
P(good)). xgboost is not installed in this environment; HGB classifier is the declared
same-family substitute with native monotone constraints. Hyperparameters mirror the
cycle3 GBR protocol constants (200/0.05/3/20, seed 7) — chosen blind, recorded now.

## Splits and leakage control

- **Train:** all label rows with t ≤ 2023-12-31.
- **OOS (2024-01-01 .. 2026-08-07):** predictions ONLY from the single model trained on
  ALL train rows (no refits, no rolling updates) — cycle3 convention.
- **IS walk-forward consistency (Gate 3):** ML-arm simulation is ALSO run over 2021–2023
  with annual expanding refits (model trained ≤Y−1-12-31 predicts year Y; 2020 runs pure
  static because no fold model exists yet). Gate 3 statistic = mean over years
  {2021, 2022, 2023} of annual return(ML) − return(static) > 0.

## Threshold θ (anti-cherry-pick)

Grid pre-declared: **θ ∈ {0.30, 0.40}**, absolute probabilities, chosen before seeing any
label base rate or result. BOTH arms are reported. EVERY gate below is evaluated on the
WORSE-performing θ (worse = lower OOS Sharpe delta vs static). Selecting the better θ
post hoc is prohibited.

## Auto-fail guard

If total OOS ML-exit events < 20 summed across both θ arms ⇒ verdict FAIL with reason
"insufficient intervention" (honest no-op; the model almost never fires ⇒ untestable claim).

## Gates (verbatim kill rules, XGBOOST-EXITS §7)

Evaluated on the worse-θ ML arm against the static arm:

1. OOS Sharpe(ML) − Sharpe(static) ≥ **+0.10**
2. |maxDD(ML)| ≤ |maxDD(static)| + 0.005 (no worsening beyond 50 bps float tolerance)
3. mean IS annual excess (ML − static, 2021–2023 folds) > 0 (train-consistency sign)
4. observed OOS Sharpe delta > null p95 (below)

Sharpe = mean(daily ret)/std(daily ret, ddof=1) · √252 on the daily equity curve;
maxDD = min(equity/cummax(equity) − 1).

## Permutation null (Gate 4)

Statistic D = Sharpe_OOS(ML, worse-θ) − Sharpe_OOS(static). Null: for each draw d ∈ 1..1000
(global RNG seed 7), for each ticker independently, cut its full-length p_good series into
consecutive non-overlapping 10-bar blocks, permute block order uniformly at random
(circular block shuffle), re-run ONLY the OOS ML-arm simulation with the shuffled
p_good values, recompute D_d. PASS iff D_observed > percentile(D_null, 95).
This tests whether exit TIMING carries information beyond exit FREQUENCY (shuffling
preserves each ticker's marginal p_good distribution and block autocorrelation length).

## Metrics recorded regardless of verdict

Per arm (static, ML@0.30, ML@0.40): OOS Sharpe, OOS CAGR, OOS maxDD, trade count,
ML-exit count, IS yearly returns, IS fold excesses, observed D, null p95, gate verdicts.
Full numbers → `docs/data/ml_sl_exit_results.json`; gate ledger →
`docs/data/eval_ml_sl_exit.json` (bar_pass true iff all four gates pass).

## Prohibited after freezing

Changing K, δ, θ grid, features, model hyperparameters, splits, universe, costs, or any
gate threshold after the first model run — for ANY reason, including near-misses.
Failures are recorded and the direction is closed unless a NEW pre-registration changes
conditions explicitly.
