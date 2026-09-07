# Spark Scheduled Task 2 — Quantitative Research Papers & Strategies

Run thrice daily: 06:00, 14:00, 22:00 UTC (stagger a few minutes after Task 1).
Tracker Doc ID: 1Q6eRu71t8uSio6wQQDQZZmGLtwUfe6FCBBIF9VefqWs, Section 2 only:
"2. Quantitative Research, Papers & Strategies".
Project repo: https://github.com/pandejesal/WSB-Alpha-System.
Environment: Google Spark web app. Web search + Google Docs + Google Drive
only. No terminal, no code execution. Research only — implementation happens
later on my laptop.

Use these Skills (invoke with /): /wsb-alpha-universe-context
/research-entry-format /trackerhygiene. The Skills are the authority if
anything below conflicts with them. Full detail is repeated inline here so
this Task works even if a Skill fails to load.

---

## 1. Strategy universe (summary of /wsb-alpha-universe-context)

Same universe as Task 1: evolve family (spy_sma, spy_ltrend, spy_rsi2,
btc_vol, btc_donchian, us_momentum, us_lowvol, us_ltrend) plus curated
(us_momentum_top5, us_lowvol_top30, dual_momentum, spy_sma200, spy_rsi2,
btc_vol_target_sma100, btc_donchian_20_10, breakout_burst,
momentum_breakout_v2, trend_following_v3, mean_reversion_enhanced,
us_pead_top5/v2, us_pead_quality_top5, quality_lowvol_top10,
factor_momentum_top3, gold_trend_kelly, h4_half_kelly/vrp, continuous_growth,
flagship_portfolio_v1, WSB Alpha / Man AHL, SMC / order_blocks).

Category labels (use exactly): evolve_trend, evolve_meanrev, cross_section,
factor_momentum, quality_lowvol, pead, crypto, cta_trend, breakout, vrp,
multi_sleeve, sentiment_managed, price_action, execution, backtest_infra.

Research needs per sleeve: walk-forward CV + permutation tests (evolve +
all), factor momentum/timing + quality/low-vol construction (cross-section),
drift decay + surprise measurement (PEAD), vol-targeting efficacy + trend
filters + perp funding (crypto), multi-speed ensembles + Kelly sizing
(CTA/trend), oscillator triggers (mean reversion), VRP term structure
+ half-Kelly (vrp), sleeve correlation + rebalancing (flagship),
sentiment decay half-life + signal fusion (WSB/Man AHL), zone reliability
(SMC), slippage/impact models (execution).

Module map: factors -> src/alpha/factors.py, PEAD -> src/alpha/pead.py,
CTA ensemble -> src/alpha/cta_ensemble.py, VRP -> src/alpha/vrp.py,
SMC -> src/alpha/smc.py, managed futures -> src/alpha/managed_futures.py,
vol targeting -> src/risk/vol_targeting.py, sentiment decay ->
src/risk/sentiment_decay.py, position sizing -> src/risk/position_sizer.py,
portfolio -> src/portfolio/optimizer.py, backtest -> src/backtest/engine.py,
execution -> src/execution/alpaca_executor.py.

---

## 2. Sources (all five groups, every run, last 180 days)

1. arXiv q-fin: factor momentum, quality/low-vol, PEAD, trend/CTA/managed
   futures, vol-targeting/Kelly/position-sizing, VRP, crypto/BTC/perp,
   mean-reversion/RSI/breakout/Donchian, social/retail sentiment (Reddit,
   wallstreetbets, StockTwits — one topic among many), sentiment/attention
   decay, hype cycles, microstructure/execution/slippage, portfolio
   optimization/regime-switching/ensembles, walk-forward/combinatorial
   CV/deflated Sharpe/permutation/overfitting.
2. Semantic Scholar: same topics — record citation counts. Prefer cited > 50.
3. SSRN: working papers — factor momentum, quality, PEAD, CTA, vol targeting,
   VRP, crypto, sentiment decay, backtest rigor.
4. Quant blogs: QuantConnect, Alpha Architect, Flirting with Models,
   QuantStart, Turnkey Analyst.
5. Datasets: Arctic Shift dumps, Kaggle WSB/finance, Polygon.io news, Alpaca
   news feed, CBOE VIX term structure, Kenneth French factors, earnings
   calendars.

For each candidate open the abstract page and record: title, authors, date,
source, citation count, data description, headline quantitative result.

---

## 3. Selection (per /research-entry-format, 2-3 per run)

Required: clear methodology, reproducible or public data, out-of-sample
validation (walk-forward, purged CV, or holdout), reported significance
(p-values, t-stats, or confidence intervals), mapping to 2+ strategy
categories (exact labels). Prefer: peer-reviewed, cited > 50, or with a code
repo. Skip purely qualitative pieces — every finding needs a NUMBER.

---

## 4. Select and append under Section 2

Format per item (exact):

### [YYYY-MM-DD HH:MM UTC] — Research Discovery

| Paper / Dataset | Source | Date | Citations | Relevance |
|-----------------|--------|------|-----------|-----------|
| [Title](url) | arXiv:XXXX.XXXXX | YYYY-MM-DD | XXX | High |

#### [Title](url) — [arXiv:XXXX.XXXXX / SSRN:XXXXXX / Blog]
Authors: [names]
Method: [2 sentences: design, data, model]
Data: [source, period, frequency, size, e.g. "CRSP 1963-2024, monthly, 10K stocks"]
Key finding: [1 sentence WITH numbers, e.g. "Factor momentum earns 1.2%/mo
(t=4.3) after costs, peaks at 3-month formation"]
Serves: [2+ exact category labels]
WSB takeaways:
- [module path + concrete change, e.g. src/alpha/factors.py — add 3-mo factor momentum sleeve]
- [module path + concrete change, e.g. src/backtest/engine.py — adopt purged combinatorial CV]
- [module path + concrete change, e.g. src/risk/position_sizer.py — half-Kelly per Eq.12]
Verdict: [Implement / Prototype / Archive / Reject] — [1-line rationale]

Verdict meanings: Implement = code change for my laptop agent (Jules PR).
Prototype = Prime evolution hunt. Archive = revisit in 90 days. Reject =
one-line rationale, never resurface. Nothing is ever auto-promoted to live
trading.

---

## 5. Hygiene (per /trackerhygiene)

Append ONLY under Section 2, at the end of that section. Before writing,
search the tracker Doc for each URL, arXiv ID, and DOI — skip anything
already present. Open every link before writing it; no dead links. Timestamp
in YYYY-MM-DD HH:MM UTC. If zero findings qualify, append one line:
"### [timestamp] — No qualifying papers this run (reason)." Never leave a
scheduled run silent. Never edit Section 1.
