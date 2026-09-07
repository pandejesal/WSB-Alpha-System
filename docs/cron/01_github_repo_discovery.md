# Spark Scheduled Task 1 — GitHub Repository & Tool Discovery

Run thrice daily: 06:00, 14:00, 22:00 UTC.
Tracker Doc ID: 1Q6eRu71t8uSio6wQQDQZZmGLtwUfe6FCBBIF9VefqWs, Section 1 only:
"1. Relevant GitHub Repositories & Tools".
Project repo: https://github.com/pandejesal/WSB-Alpha-System.
Environment: Google Spark web app. Web search + Google Docs + Google Drive
only. No terminal, no pip, no local files, no code execution. Research only —
implementation happens later on my laptop.

Use these Skills (invoke with /): /wsb-alpha-universe-context
/repo-entry-format /trackerhygiene. The Skills are the authority if anything
below conflicts with them. Full detail is repeated inline here so this Task
works even if a Skill fails to load.

---

## 1. Strategy universe (summary of /wsb-alpha-universe-context)

Evolve family: spy_sma (trend SPY N=50-300), spy_ltrend (long-term SPY
N=150-400), spy_rsi2 (mean reversion SPY RSI-2), btc_vol (vol targeting BTC
inverse vol + trend filter), btc_donchian (breakout BTC N-day high / M-day
low), us_momentum (cross-section monthly top momentum), us_lowvol
(cross-section monthly low vol), us_ltrend (long-term rotation 1-2y window).

Curated: us_momentum_top5, us_lowvol_top30, dual_momentum, spy_sma200,
spy_rsi2, btc_vol_target_sma100, btc_donchian_20_10, breakout_burst,
momentum_breakout_v2, trend_following_v3 (CTA ensemble), mean_reversion_enhanced,
us_pead_top5/v2 (earnings drift), us_pead_quality_top5 (PEAD + quality),
quality_lowvol_top10, factor_momentum_top3, gold_trend_kelly,
h4_half_kelly/vrp (volatility premium, half-Kelly), continuous_growth,
flagship_portfolio_v1 (multi-sleeve), WSB Alpha / Man AHL (sentiment +
managed futures), SMC / order_blocks (price action).

Category labels (use exactly): evolve_trend, evolve_meanrev, cross_section,
factor_momentum, quality_lowvol, pead, crypto, cta_trend, breakout, vrp,
multi_sleeve, sentiment_managed, price_action, execution, backtest_infra.

Retail sentiment / WSB is ONE sleeve among many. Weight factors, CTA/trend,
crypto, PEAD, VRP, execution, and price action equally.

Module map: factors -> src/alpha/factors.py, PEAD -> src/alpha/pead.py,
CTA ensemble -> src/alpha/cta_ensemble.py, VRP -> src/alpha/vrp.py,
SMC -> src/alpha/smc.py, managed futures -> src/alpha/managed_futures.py,
vol targeting -> src/risk/vol_targeting.py, sentiment decay ->
src/risk/sentiment_decay.py, position sizing -> src/risk/position_sizer.py,
portfolio -> src/portfolio/optimizer.py, backtest -> src/backtest/engine.py,
execution -> src/execution/alpaca_executor.py, sentiment NLP -> src/sentiment/.

---

## 2. Search groups (all eleven, every run)

Use web search and GitHub search. Prefer repos with a commit in the last 90
days, MIT / Apache-2.0 / BSD license, Python 3.10+.

1. Vectorized backtesting engines + research platforms. Examples: vectorbt,
   backtrader, zipline-reloaded, qlib, mlfinlab, moonshot, fastquant.
   Serves: backtest_infra, evolve_trend, evolve_meanrev.
2. Factor libraries + cross-sectional infrastructure. Examples: alphalens,
   pyportfolioopt, riskfolio-lib, quantstats. Serves: cross_section,
   factor_momentum, quality_lowvol.
3. PEAD / earnings data + modeling. Earnings calendars, surprise data, drift
   measurement. Serves: pead.
4. Crypto infrastructure (24/7, perp/spot, vol targeting). Examples: ccxt,
   freqtrade, hummingbot. Serves: crypto.
5. Futures / CTA / trend following + Kelly sizing. Serves: cta_trend,
   multi_sleeve.
6. Volatility risk premium / options backtesting. Serves: vrp.
7. Price action / SMC / order flow / market structure zones. Serves:
   price_action.
8. Financial sentiment NLP — BROAD, not retail-only. FinBERT, FinGPT, news +
   earnings + social transformers, alternative-data sentiment. Serves:
   sentiment_managed.
9. Social scrapers — BROAD. Reddit / Pushshift / Arctic Shift + X / StockTwits
   finance scrapers. Serves: sentiment_managed.
10. Execution / Alpaca / order management / smart routing. Serves: execution.
11. Ticker disambiguation / entity resolution / SEC CIK mapping. Serves:
    cross_section, pead, execution.

For each candidate open the GitHub page and record: stars, last-commit date,
license, language, test/docs presence.

---

## 3. Scoring (per /repo-entry-format)

Required to pass: commit within 30 days, permissive license
(MIT/Apache-2.0/BSD), Python 3.10+. Preferred: stars > 100, tests present,
responsive issues (< 7 days), good docs. Score 70+ = High, 50-69 = Medium,
below 50 = skip. Must serve 2+ strategy categories (exact labels) or skip.

---

## 4. Select 2-3 repos per run and append under Section 1

Format per repo (exact):

### [YYYY-MM-DD HH:MM UTC] — Repo Discovery

| Repo | Stars | Last Commit | License | Relevance |
|------|-------|-------------|---------|-----------|
| [owner/repo](url) | stars | YYYY-MM-DD | MIT | High |

#### [owner/repo](url)
Features:
- [3 concrete bullets]
Stack: Python 3.11, [key deps]
Serves: [2+ exact category labels]
WSB mapping: [specific module paths, e.g. src/alpha/factors.py,
src/backtest/engine.py]
Verdict: [Adopt / Evaluate / Monitor / Reject] — [1-line rationale]

Verdict meanings: Adopt = code change for my laptop agent (Jules PR).
Evaluate = Prime evolution hunt. Monitor = revisit in 90 days. Reject =
one-line rationale, never resurface. Nothing is ever auto-promoted to live
trading.

---

## 5. Hygiene (per /trackerhygiene)

Append ONLY under Section 1, at the end of that section. Before writing,
search the tracker Doc for each repo URL — skip anything already present.
Open every link before writing it; no dead links. Timestamp in
YYYY-MM-DD HH:MM UTC. If zero findings qualify, append one line:
"### [timestamp] — No qualifying repos this run (reason)." Never leave a
scheduled run silent. Never edit Section 2.
