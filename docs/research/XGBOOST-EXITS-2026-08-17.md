# XGBoost-Based ML Exits for the Flagship Library

Research report (flagship topic 11) · 2026-08-17 · **Research-only — NO code, NO trades, NO config changes**

Canonical copy of `02-Research/Findings/XGBoost-Exits-2026-08-17/report.md` (Obsidian vault).

## 1. Objective and scope

- **Goal:** survey how XGBoost can replace or augment the rule-based *exits* of the
  flagship library cores (monthly momentum top-5, SPY SMA200, SPY RSI(2), BTC
  vol-target+SMA100, low-vol), with every factual claim backed by a primary source.
- **Why exits, why now:** Cycle 3's ML decile long-short FAILED its gates, and topic 07's
  ML overlay FAILED 17/17 variants (decision `2026-08-16-ml-overlay.md`). Both tested ML on
  *entries/overlays*. The exit decision boundary — when to sell — is the one ML application
  the library has never tested. This report maps the four published ML-exit pattern
  families to the library and sets honest kill rules for any future test.
- **Guardrails:** free primary sources only; every factual claim followed by a source;
  unverifiable items explicitly flagged (§9); honest negative-result framing; acceptance
  checklist = prompt §7 (all met: no code, citations, flags, risk framing).

## 2. Current exits and failure context

**Current rule-based exits** (from the micro-account strategy YAMLs, 2026-08-16):

| Core | Exit rule (current) | Full Sharpe | OOS Sharpe | maxDD |
|---|---|---|---|---|
| us_momentum_top5 | drop name when it falls out of top-5 at next month-end; drift rebalance >5%; exec_delay 1 | 1.45 | 1.74 | −38.4% (full) / −35.1% (OOS) |
| spy_rsi2 | sell if close > SMA(5) OR RSI(2) > 70 OR 5 trading days elapsed | 0.77 | 1.32 | −23.7% |
| other cores (SPY SMA200, BTC vol-target+SMA100, low-vol top-30) | signal-invalidation / regime-gate exits per registry YAMLs | — | — | — |

**Fee model for any future test (unchanged protocol):** Alpaca $0 commission, 0.05%
slippage per side, T+1 cash, fractional shares, min $1, `exec_delay=1`; Binance 0.1%
taker + 5 bps (crypto cores).

**Cycle 3 ML failure — quoted from `docs/data/cycle3_ml_evaluation.json`:**
claim "ML hybrid (price-only, strict protocol) decile long-short"; `bar_pass: false`:

- `train_consistency`: −0.0014044876016793323 → **FAIL**
- `oos_sharpe_ge_1`: 0.9381778226912734 → **FAIL** (bar 1.0)
- `oos_maxdd_le_25`: −0.12355344660289569 → PASS
- `oos_cagr_ge_15_net`: 0.1297655844000829 → **FAIL** (bar 15%)
- `null_p95`: 0.0026525997860597133 → **FAIL**
- `oos_median_3of4_years`: 2024/2025/2026 true, 2027 false → earliest possible pass
  end-2027 (pre-registered structural constraint)

Model: `GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=3,
min_samples_leaf=20, subsample=0.8, random_state=7, loss='squared_error')`, refit
annually on expanding window, last anchor ≤ 2023-12-31, OOS predicted with final
train-fitted model only. Features: 12 fixed price-only (return lags 1/2/4/12/26/52w
Friday-to-Friday, realized vol 20d/60d × √252, RSI(14) Wilder weekly,
close/SMA20/50/200 − 1). Target: forward 1-week return, rank-normalized. Costs 10
bps/side both legs; null 1000× block-shuffle, seed 7. Honest negative result.

**Topic 07 overlay failure — quoted from decision `2026-08-16-ml-overlay.md`:**
best overlay on momentum OOS 1.786 vs static 1.741 (+0.045 < +0.1 bar, DD −55.5% vs
−38.4% FAIL); GBR gate on BTC 0.988 vs 0.818 (wins) but DD −51.7% vs −33.4% FAIL;
6 of 17 variants passed all 5 standard gates yet still failed the claim.

## 3. Pattern (i) — per-bar "exit now" classification

**Source:** Gerlein, McGinnity, Belatreche & Coleman (2016), "Evaluating machine
learning classification for financial trading: an empirical approach", *Expert Systems
with Applications* 54:193–207. DOI 10.1016/j.eswa.2016.01.018.

- Simple ML classifiers (not deep nets) produce per-bar classification labels for
  profitable trading; evaluated through FOREX trading simulations; the study varies
  attribute selection, periodic retraining, and training-set size.
- **Fit:** each held position gets a per-bar "hold vs exit now" decision from a
  classifier — a learned replacement for the month-end rank-drop (momentum) and the
  SMA(5)/RSI(2)/5-day triggers (RSI2). RSI2 is the natural first candidate: 762 trades
  in-sample, 1–10 day holds, largest statistical sample in the library.
- **XGBoost mapping:** `binary:logistic` outputs P(exit); threshold tunable; per-bar
  retraining cost is trivial at monthly-rebalance scale.

## 4. Pattern (ii) — predicted-return regression exits

**Source:** Gu, Kelly & Xiu (2020), "Empirical Asset Pricing via Machine Learning",
*Review of Financial Studies* 33(5):2223–2273. DOI 10.1093/rfs/hhaa009.

- Trees and neural nets predict next-period returns from stock characteristics;
  momentum, liquidity, and volatility are the most important signals; predicted-return
  portfolios earn high out-of-sample Sharpe; nonlinear methods dominate linear ones.
- **Fit:** this is exactly the Cycle 3 protocol (12 fixed features, forward 1-week
  return, rank-normalized target). An ML exit = drop a name when its predicted next-week
  return falls below a pre-registered threshold — a point-in-time, learned replacement
  for "fell out of top-5".
- **Honest prior:** Cycle 3's GBR long-short FAILED on this exact protocol at 10 bps.
  Same features + same target ⇒ same weak signal; expect this pattern to fail unless the
  target is changed (e.g., to SL-adjusted labels, §5).

## 5. Pattern (iii) — stop-loss / take-profit integration

**Sources (all verified this session):**

- **Kaminski & Lo (2014),** "When Do Stop-Loss Rules Stop Losses?", *Journal of
  Financial Markets* 18(C):234–254. DOI 10.1016/j.finmar.2013.07.001 (SIFR Research
  Report 63). A stop-loss cannot turn a losing system profitable, but it shifts the
  return distribution; a ~20% stop ("Lester" rule) on momentum dominates momentum alone.
- **Hwang, Park, Lee & Lim (2023),** "Stop-loss adjusted labels for machine
  learning-based trading of risky assets", *Finance Research Letters* 58(PA):104285.
  DOI 10.1016/j.frl.2023.104285. SL-adjusted labeling for ML: `label = 1` iff
  `(Close/Close.shift(1) > 1)` AND `((Low/Close.shift(1) − 1) × 100 ≥ −δ)` — i.e. "price
  went UP AND never hit the stop" within the period. Tested on US futures and
  cryptocurrencies; ML trained on SL-adjusted labels reduces risk vs standard labels.
  Official implementation: github.com/Yoontae6719/Stop-loss-adjusted-labels.
- **Lo & Remorov (2017),** "Stop-loss strategies with serial correlation, regime
  switching, and transaction costs", *Journal of Financial Markets* 34:1–15.
  DOI 10.1016/j.finmar.2017.02.003 (SSRN 2695383). Closed-form results: with realistic
  transaction costs a tight stop underperforms buy-and-hold; outperformance requires
  high serial correlation; in the regime-switching case the gain comes from volatility
  reduction.
- **Dai, Marshall, Nguyen & Visaltanachoti (2021),** "Risk reduction using trailing
  stop-loss rules", *International Review of Finance* 21(4):1334–1352.
  DOI 10.1111/irfi.12328. Trailing stop-losses reduce total and downside risk, most in
  declining markets; transaction costs erode the benefit of tight rules, but wider
  thresholds remain useful.

**XGBoost mapping:** `monotone_constraints` can encode "lower price ⇒ higher exit
probability"; a custom objective (`obj=`, gradient + hessian per the custom_metric_obj
tutorial) can encode Hwang et al. SL-adjusted labels directly; `missing=` handles NaN
natively (sparsity-aware algorithm, Chen & Guestrin 2016, arXiv:1603.02754).

**Fit:** momentum top-5's −38.4% maxDD sits close to the 40% gate — the clearest target
in the library. SL-adjusted-label exits attack drawdown directly; Lo & Remorov says
costs matter, which the 10 bps/side protocol already enforces.

## 6. Pattern (iv) — regime / time exits

**Sources:**

- **Jegadeesh & Titman (1993),** "Returns to Buying Winners and Selling Losers:
  Implications for Stock Market Efficiency", *Journal of Finance* 48(1):65–91.
  DOI 10.1111/j.1540-6261.1993.tb04702.x. Momentum strategies earn significant positive
  returns over 3–12 month holding periods; part of the abnormal returns dissipates in
  the following two years — an empirical anchor for time-based exits (do not hold past
  ~12 months).
- **Lo & Remorov (2017)** regime-switching case (§5): stop value arises from volatility
  reduction in switching markets — a rationale for regime-aware exit timing.

**Fit:** RSI2's 5-day hold + SMA(5) is already a time/trend exit; the SPY SMA200 and BTC
SMA100 cores already use regime-gate exits. An ML version would predict a vol/trend
state and adjust hold time — lowest novelty of the four patterns.

## 7. Robustness and honest framing

- **López de Prado (2018),** "The 10 Reasons Most Machine Learning Funds Fail",
  *Journal of Portfolio Management* 44(6):120–133. DOI 10.3905/jpm.2018.44.6.120
  (SSRN 3104816; free PDF at garp.org — see sources.md). ML funds fail from backtest
  bias, non-iid financial data, and lack of statistical discipline — not from model
  choice. (arXiv:1801.09587 could NOT be confirmed — do not cite the arXiv ID.)
- **Bailey, Borwein, López de Prado & Zhu (2014),** "Pseudo-Mathematics and Financial
  Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance",
  *Notices of the AMS* 61(5):458–471 (free PDF, see sources.md; SSRN 2308659). With N
  trials the expected max Sharpe grows like √(2 ln N); as few as **45 configurations**
  on a 5-year dataset can produce a deceptively high in-sample Sharpe with dismal
  out-of-sample results; under memory effects, backtest overfitting implies negative
  expected out-of-sample returns.
- **PBO:** Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest
  Overfitting", *Journal of Computational Finance*. DOI 10.21314/jcf.2016.322.
- **Deflated Sharpe:** Bailey & López de Prado (2014), *JPM* 40(5):94–107.
  SSRN 2460551 — corrects Sharpe for selection bias, non-normality, and backtest
  overfitting.
- **AFML:** López de Prado (2018), *Advances in Financial Machine Learning*, Wiley.
  ISBN 978-1-119-48208-6 — triple-barrier labeling, embargo, purged K-fold CV.
- **sklearn TimeSeriesSplit (1.9.0 docs):** "Provides train/test indices to split
  time-ordered data, where other cross-validation methods are inappropriate, as they
  would lead to training on future data and evaluating on past data"; `gap` = "Number of
  samples to exclude from the end of each train set before the test set" — the simple
  embargo (AFML's full purged CV is the stricter alternative).
- **Pardo, *The Evaluation and Optimization of Trading Strategies*, 2nd ed., Wiley,
  2008** (ISBN 978-0-470-12801-5; Wiley online ed. first published 2012-01-02, DOI
  10.1002/9781119196969), Walk-Forward Analysis ch. 11: "WFA adds another level of
  simulation to the trading strategy process"; performance is evaluated exclusively on
  out-of-sample data; "an unsound strategy will not perform well in a Walk-Forward
  Analysis".
- **Library protocol (already enforced, unchanged):** walk-forward only; train ≤
  2023-12-31; OOS 2024+; same engine and fees; pre-registered gates before any run.

**Kill rules for any future ML-exit test (proposed, mirroring topic 07/cycle 3):**
an ML exit must (1) beat the static exit's OOS Sharpe on the same engine/fees (+0.1 bar,
topic 07 convention), (2) not worsen maxDD, (3) pass train-consistency sign, (4) beat
null p95. Otherwise keep static exits and report an honest FAIL.

## 8. Recommendation

1. **First test (highest leverage):** Pattern (iii) — SL-adjusted-label exit
   (Hwang et al. 2023) with XGBoost + `monotone_constraints` on **momentum top-5**,
   attacking the −38.4% maxDD. Pre-register before running; walk-forward, 10 bps/side.
2. **Second:** Pattern (ii) predicted-return exit — natural continuation of the Cycle 3
   protocol on the same 12 features; honest prior is weak (Cycle 3 FAIL) unless the
   target is switched to SL-adjusted.
3. **Third:** Pattern (i) per-bar classifier on **RSI2** (762-trade sample).
4. **Fourth:** Pattern (iv) learned hold-time/regime adjustment — lowest novelty,
   optional.
5. **No YAML/config changes from this report.** Static exits remain canonical until an
   ML exit beats them under the kill rules. Any FAIL must be recorded like topic 07.

## 9. Verification flags

- arXiv:1801.09587 (LdP "10 Reasons") — NOT confirmed in any fetched output; use the
  JPM DOI + GARP free PDF instead.
- Hamilton (1989) regime-switching paper — not independently verified this session
  (optional; Lo & Remorov 2017 covers the regime case).
- Pardo — print edition 2008 (2nd ed.); Wiley online edition first published
  2012-01-02.
- Everything else cited above was verified against the primary source this session
  (full list with URLs/DOIs in `sources.md`).

*Prepared by OpenCode research session, 2026-08-17. Research-only; see progress.md for
timeline and sources.md for the verification list.*