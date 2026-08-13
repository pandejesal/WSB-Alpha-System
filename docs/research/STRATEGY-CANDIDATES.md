---
title: Strategy Candidates — Next Sell (Mean-Reversion Path) for the $100 Engine
date: 2026-08-09
scope: research-only deliverable — NO code changes, NO trades, NO git operations
sources:
  - web-research/strategies.md (61-source corpus; top-10 evidence ranking)
  - web-research/indicators.md (36-indicator catalog; warmup/lookahead tables)
  - web-research/quant-validation-best-practices.md (sample-size & inflation guards; MeanR §4)
  - web-research/small-account-risk.md ($100 sizing/ruin framework)
  - repo: src/alpha/fade_strategy.py, wsb_alpha_legacy.py, indicators.py
  - repo: src/backtest/engines/*, src/execution/main_live.py, src/risk/position_sizing.py
conventions:
  - OPINION: = my judgment, not a sourced claim.
  - VERIFY = fact about the candidate that still needs verification before commitment.
  - All performance figures are quoted as reported by the cited research; most are pre-cost.
---

# STRATEGY-CANDIDATES.md

Selection of the next **short-side (sell)** candidate for the **mean-reversion path**
of the $100 paper engine, grounded in the research corpus and the current codebase.

**Scope constraints honored**
- $100 paper account, free tier: yfinance daily OHLCV (already exercised in
  `main_live.py`, `wsb_alpha_legacy.py`, `macro_regime.py`), Reddit public RSS feed.
- Repo has a Binance/Bybit `ccxt` bailout path in `src/execution/` (perps, `fetch_historical_ohlcv`
  exists) but nothing currently polls funding-rate history; treated as NOT-yet-reusable.
- No edits to `statistical.py`, `permutation_tester.py`, `fred_macro_provider.py`; no candidate
  here touches them (their documented gaps — mislabeled SPA, destructive shuffle null for MR —
  are flagged as gate constraints in §6, not as edits).

---

## 1) What the codebase already implements (strategy inventory)

| Strategy id | File | Entry signal | Exit / stop | Params | Where it runs |
|---|---|---|---|---|---|
| FadeStrategy (SHORT) | `src/alpha/fade_strategy.py:7` | sentiment_score > 90th pctile of trailing 30d **AND** Heikin-Ashi red **AND** MACD < Signal → SELL | Paper MARKET order; no explicit exit rule (sizing-only 5% stop implied by `PositionSizer`); CVaR alloc | 90th percentile / 30d window | Live paper loop (`main_live.py:210`) |
| AlphaFusion (LONG) | `main_live.py:145` (inline) | ≥2 of 3 confluence: HA bullish, Close>EMA20, MACD>signal AND sentiment>0.5 AND 30<RSI<70; adj. by MacroRegimeFilter | MARKET order; qty by PositionSizer | Kelly frac 0.15, WR 0.55 / R 1.5, max 4 concurrent | Live paper (`main_live.py`) |
| WSBAlphaStrategy | `src/alpha/strategy_wsb_alpha.py:9` | long: Close>EMA20 & RSI<70 & MACD>signal; short: mirror; optional sentiment veto | Exits on opposite signal (via vectorbt from_signals) | RSI_14 30/70 | Backtest only (called through `src/backtest/vectorbt_engine.run_backtest`) — not in live path |
| ManAHLStrategy | `src/alpha/strategy_man_ahl.py:9` | sign of vol-normalized momentum over 5/10/21/42d (63d vol window), EWM14 smoothed | reverse signal / signal=0 | windows [5,10,21,42], vol_window 63 | Backtest only (generic engine) — not in live path |
| wsb_alpha_legacy pipeline | `src/alpha/wsb_alpha_legacy.py:196` | long/short by sentiment sign + 4-indicator vote (HA, EMA20+MACD, RSI zone, BB position) ≥3/4 + GK-vol shield (<1.20) + projected-return forecast + CVaR throttle | T+1 close entry; exits at horizons 1–300d; adaptive holding (10/60/252d | GK_vol scale 0.15–1.20; risk-parity weight 0.15/vol | Feeds `wsb_factual_research_data.csv` read by live loop; not itself an executor |
| MacroRegimeFilter | `src/alpha/macro_regime.py:8` | SPY < SMA-200 → BEAR; rejects weak confluence, slashes 50% | — | SPY 200d | Wraps live signals (main_live) |
| VectorBTEngine / NautilusEngine | `src/backtest/vectorbt_engine.py`, `engines/*` | generic: MA crossover demo with T+1 shift + ADV filter | vectorbt from_signals, fees 0.1%, slippage 0.1% | init_cash 100 | Backtest harness used by tests; MA demo is not a real strategy |

**Read of the table (OPINION):** the only *short* logic that reaches the paper broker today is
FadeStrategy — one sentiment-conditioned fade with a single low-frequency trigger. The
mean-reversion path is thin: no cross-sectional reversal, no residual/spread model, no
volatility-band timing beyond the legacy ensemble. That is the gap the candidates below fill.

---

## 2. Candidate selection from the research top-10 (mean-reversion / short side)

Ranking used (strategies.md §1): #9 Short-term reversal, #6 Avellaneda–Lee s-score stat arb,
#7 crypto funding/basis (excluded: credit where the repo's data layer does not fetch funding
history yet — OPINION but grounded in inventory), #4/#5 pairs (distance/cointegration —
strong literature, but two-leg + pairs-universe infra does not exist in this repo and a
100+ name universe is beyond a $100 research budget — excluded this round),
#13 Bollinger/RSI single-name MR (engineering staple; the formal support for a 1-week decay is
the same short-term reversal literature, so it inherits rank-9 evidence, not independent proof).

**Top-5 families matching a short-side MR path (rank | family | headline evidence):**
| Picked | Rank | Family | Headline evidence (as reported) |
|---|---|---|---|
| C1 | F13→#9 pipeline | Bollinger/RSI overbought fade (single name) | no peer-reviewed direct evidence; closest support: short-term reversal (J1990; DLS 2011) |
| C2 | #9 | Short-term reversal, weekly cross-section | extreme-decile spread 2.49%/mo pre-cost (1934–87); DLS within-industry α 1.20%/mo (t=5.9); classic monthly post-cost α drops to 0.33%/mo (insignificant) |
| C3 | #6 | Stat-arb s-score (Avellaneda–Lee) | entry 1.25σ / exit 0.75–0.5σ; in-sample 100–175 bps/mo (1997–2007), decay noted by 2011 |

Candidate constraints checked: (a) $100 scale — each candidate is fully long/short single-name
or weighted portfolio with no leverage, no margin, no PDT-demanding 4+ day-trades per 5 days
(hold 1+ days; see VERIFY C2-3 for the PDT nuance); (b) data reuses only yfinance OHLCV +
SPY + the existing sentiment CSV — zero paid data; (c) style matches `fade_strategy.py`:
boolean `evaluate()` → SELL signal dict → existing `PositionSizer` + `MacroRegimeFilter`.

---

## 3. Candidate specs (half-page each)

### Candidate C1 — "OBB-Fade": Bollinger/RSI overbought short

**Signal (def):** On daily bars, short when Close ≥ upper Bollinger(20, 2σ) **AND** RSI_14 ≥ 70
**AND** GK_Vol < 1.20 (reuse existing vol shield) **AND** Close > EMA_20 (fade extended rallies,
not knife-catches). Signal evaluated at day-T close; execution at T+1 open (the repo already
applies T+1 in both engines, and indicators.py warmups are respected).
**Entry rules:** first T+1 open after signal; fresh position per name (no pyramiding).
**Exit / SL / TP:** TP = BB_Middle (mid-band) else exit after 5d time-stop; SL = max(1.5×ATR_14, 6%)
above entry (ATR-stop per F13 canon: "stop optional 1 ATR"); hard time stop 5–10 sessions.
**Holding horizon:** 3–10 trading days; most exits expected at TP within 5d (a local
expectation to be confirmed, see VERIFY C1).
**Indicators used (all already in `compute_indicators()`):** RSI_14, BB_Upper/BB_Middle, EMA_20,
ATR_14, GK_Vol, CVaR_95, MACD.
**Existing function reuse:** `compute_indicators()` (src/alpha/indicators.py:5), the
`FadeStrategy.evaluate → generate_signal` pattern (fade_strategy.py:32-70), `PositionSizer`,
`MacroRegimeFilter` gate, and `vectorbt_engine` backtest loop.
**NEW indicator/data needed:** none new for data (yfinance 60d is already downloaded live);
signal needs only existing columns — pure configuration new logic (entry threshold checks),
no new dependency.
**Backtest windows:** daily, per name 2016–2026 (yfinance free history); rolling WFO IS 3y / OOS 1y
(default; Pardo 4:1), 2016–2021 IS hold for parameter sanity, 2022–2026 true out-of-sample.
**Validation bait (the honest gate):** This family has *no formal edge* in the corpus — every
generic oscillator rule fails OOS under data-snooping control (STW 1999). The honest gate is
(1) a **circular/block permutation null** (MeanR §4) on the exact (BB_Upper, RSI≥70) signal set,
(2) **cost-multiplier stress ×3** (fees 0.1%×2 → 0.2%×2, slippage 0.1%×2 — see §4 of
quant-validation; at $100, $0.01–0.02/share friction can eat the entire subset edge),
(3) DSR with an honest trial ledger — N = every threshold-config tried.

### Candidate C2 — "WeeklyTopFade" (cross-sectional short-term reversal SHORT)

**Signal (def):** At each weekly rebalance (Friday close), score every ticker in the sentiment
universe by its trailing 1-week (5 trading-day) return. Short the top quintile (prior-week
winners above the 80th percentile) — the mirror of the reversal literature — optional filter:
only if sentiment_score > 0 (euphoria agrees with the winner state; direction kept short).
**Entry:** T+1 open after Friday signal; **Exit:** next Friday open/close (1-hold), or crossover
time-stop 10d; **No TP, fixed 1-week hold.** **Holding horizon:** 1 week (5 sessions).
**Existing reuse:** yfinance closes (already downloaded in legacy pipeline), the sentiment
database (`wsb_factual_research_data.csv` produced by `wsb_alpha_legacy` phase 1 — the columns
`sentiment_score` and `ticker` exist there), the live loop's weekly cadence.
**Indicators used:** none new — prior-week return is computed from Close columns.
**NEW indicator/data:** cross-sectional decile-rank helper (pure pandas rank on a weekly panel —
no new data, no new library); requires a subtle T+1/rank-alignment discipline (pandas `groupby.rank`).
**Backtest:** 5y daily per name (2016–2026), weekly rebalance; universe = union of top 25
sentiment names (reuse DB) — free.
**Validation bait:** the literature is unambiguous that classic monthly reversal fades *after
costs* (post-cost α ≈ 0.33%/mo insignificant — DLS 2011), and the weekly form is even more
cost-drag-prone. The honest gate is **breakeven at 3× real friction** (two halves × fees ×3 +
spread, worst-case spacing), plus a **block-preserving permutation null** over the *ranking*
(not a plain shuffle — that would destroy the autocorrelation the reversal feeds on). Also
required: **WFO with ≥5 OOS windows** (best-practices §6) — a single-window pass is not
counted as evidence.

### Candidate C3 — "Residual-Short" (Avellaneda–Lee s-score short vs SPY)

**Signal (def):** On daily bars, estimate a rolling 60d OLS of the stock's log-return on
SPY's log-return (β, α). s-score = (residual − mean60) / std60 of the residual.
**Entry:** SHORT when s ≥ +1.25 **and** residual itself positive (ticker overshoot above its
SPY-beta fair value); **Exit:** s ≤ +0.75 (paper short-exit cutoff) or 10-session time stop,
or SL = 1.5× residual std. **Holding horizon:** up to 10 sessions; expected ~5 (A-L trade
cadence is weekly).
**Existing reuse:** SPY series (**already** downloaded in `wsb_alpha_legacy.py:401` and by
`MacroRegimeFilter.fetch_regime`); yfinance daily for tickers (same as C1 path).
**Indicators used:** the residual z of the SPY-adjusted 60d window — one rolling regression.
**NEW indicator/data:** rolling OLS + residual z (numpy `polyfit`/vectorized within window —
no new dependency, matches "statsmodels-free, numpy-timed" note in strategies.md §F9).
**Backtest:** 2016–2026 daily, IS 3y / OOS 1y rolling; per-name half-life pre-check, universe =
sentiment DB names with ≥ 250 tradable days.
**Validation bait:** the authors' own published cutoffs (1.25/0.75) are the least-malleable part;
the decay they documented by 2011 is the target to beat on 2015–2026 data. Honest gate =
(1) **ADF + OU half-life ≤ holding period** on the residual (MeanR §4.2 — if half-life > 10d
the "reversion" is drift noise → reject), (2) rolling walk-forward with WFE ≥ 0.5,
(3) **circular-shift null** (preserve residual autocorrelation), and (4) cost×3 stress on the
single short leg (no separate SPY short — for $100 the repo holds no shorts on SPY; the
strategy is executed as a single-name short benchmarked against SPY).

---

## 4. Feasibility matrix (1–10; higher is better)

Criteria weights (all OPINION per researched context): fit-with-infra 25%, free-tier data 25%,
overfit-cheapness (higher = lower overfit risk) 20%, trade frequency 15%, $R risk-profile 15%.

| Candidate | Fit w/ infra | Data free-tier | Overfit risk (10 = low) | Freq (trades/wk) | $R per trade | Composite |
|---|---|---|---|---|---|---|
| C1 BB/RSI fade | 9 — every indicator and gate exists; drop-in on FadeStrategy | 10 — yfinance 60d already live-pulled | 5 — 2 params (20/2σ, RSI 70) but family has NO formal edge; any grid on thresholds inflates PBO | ~2–5 | −0.5R..+1.5R; SL 1.5×ATR caps but whip spikes on melt-down days | ~7.6 |
| C2 weekly reversal short | 6 — needs a weekly cross-sectional frame (not present) + rank helper; reuses universe+CSV | 10 | 4 — literature says post-cost α≈0 for the monthly form; weekly worse; must pass 3×cost breakeven | 3–8 (batch per week; 5–8 names in top quintile) | −1.0R..+0.8R typical; high turnover = friction dominates | ~6.4 |
| C3 residual short | 6.5 — SPY present, needs new rolling-OLS (numpy only, no deps) | 9 — SPY + ticker daily free, 10y | 7 — published cutoffs keep param count low (60d, 1.25, 0.75); β-drift is the killer → half-life gate | 1–3 | −1.2R..+2.0R; crisis-period convergence gains per bibliography | ~7.4 |

Standout takeaway (OPINION): C3 wins the evidence-adjusted composite (rank-6 family with
published cutoffs + lowest param count) at the cost of one new numpy-only helper; C1 is the
cheapest-to-ship and C2 is the *weakest* science — include it only if the 3×-cost gate passes.

Max-position math (from `position_sizing.py`, $100): 1% risk ≈ $1/trade → on a $25–$40 stock
with 1.5×ATR≈$1.5 stop → ~0.7 shares → $17–$28 notional: all three candidates fit fractional
shares; C2's whole-quintile batch (5–8 names × ~$1 risk) fits inside the 4-position cap only
if batched ≤4.

---

## 5. Open verification list (VERIFY — must be confirmed before promotion)

**C1 — BB/RSI fade**
1. VERIFY: actual distribution of "Close ≥ upper BB and RSI≥70" episode durations on THIS
   universe (repo has sentiment-derived names; the corpus only reports the generic
   sensitivity, strategies.md F13) — needed for the 5d vs 10d stop decision.
2. VERIFY: whether 1.5×ATR stop is wider than the historical TP at BB_Middle (i.e., positive
   expectancy requires TP to arrive before SL — not asserted anywhere in the corpus).
3. VERIFY: trade count under the EMA_20 + GK_Vol<1.2 filters in 2020–21 (trend) vs 2022
   — is the filter block generic enough to starve entries (corpus warns MR collapses in
   trending regimes; actual frequency unknown per name).

**C2 — Weekly reversal short**
1. VERIFY: optimal hold is 1-week vs 2-week on this mid/large-cap sentiment subset (JGT
   evidence is monthly-decile; weekly frequency is an extrapolation to verify).
2. VERIFY: does the sentiment_score>0 filter add any post-cost alpha to the raw rank signal
   (nothing in repo or corpus measures this fusion on the short side — unmeasured).
3. VERIFY: PDT/friction accounting — short leg beneath $25k triggers PDT on 4+ round-trips/5d;
   weekly batch of ≤4 names keeps it legal, this must be double-checked against the venue's
   rule text (strategies.md F22 flags PDT; rule remembered from general knowledge, re-check).

**C3 — s-score short**
1. VERIFY: do the 1.25/0.75 cutoffs still retain a positive edge on 2015–2026 daily data —
   the authors themselves report decay by 2011; no repo-side replication exists yet.
2. VERIFY: per-name OU half-life — we require half-life ≤ 10d for a 5–10-day hold; unmeasured
   on the sentiment DB universe; the repo's existing tickers lean high-momentum market names.
3. VERIFY: single-factor (SPY) residual sufficiency vs multi-factor (sector ETFs) — corpus
   shows the A-L edge used 2–8 factor ETFs with returns in the 4-factor model; single-factor
   exposure may spec a beta drift the repo has no data for.
   (β drift / cointegration breaks also flagged in strategies.md pairs section.)

---

## 6. Validation wiring for the chosen candidate (no code changes here)

Whichever candidate is picked next should enter the existing validation pipeline:
1. Honest trial ledger + DSR — count EVERY grid config tried (best-practices §2).
2. Walk-forward with IS 3y / OOS ≥8 windows and WFE ≥0.5; never retune on OOS (§6).
3. Cost multiplier ×2–3 (fees+slippage) — for MR the deciding test (§4.3); $100 make-or
   break at 20–60 bps round-trip.
4. Mean-R-specific null: circular/block-shift permutation (NOT the plain shuffle — the repo's
   `permutation_tester.py` shuffle null is invalid for MR per best-practices §4.1; that file
   is out of scope — no edit here, only the requirement recorded).
5. MC drawdown envelope 10k-path on the trade list → feed the existing DD guardrails
   (DAILY 5% / WEEKLY 10% / MAX 15% in `position_sizing.py`).

---

## 7. Verification log (2026-08-09) — empirical VERIFY results

Standalone scripts (no repo source touched): `docs/research/verify_c3_scatter.py` (C3) and
`docs/research/verify_c1_c2.py` (C1 + C2), run on anaconda python, yfinance daily closes
2015-01-01→2026-08-09, auto_adjust, universe = 20-name proxy (GME AMC NVDA TSLA AAPL MSFT
META AMD NFLX SHOP ROKU SNAP PINS CRM MU U F KO JNJ BA). Sentiment DB is not yet generated
(`wsb_factual_research_data.csv` is pipeline output), so the proxy universe replaces it —
a representativeness caveat, not the final universe.

**C3 (s-score short) — VERIFY FAIL (does NOT confirm the doc's earlier hypothesis).**
- Daily A-L s-score (60d window, SPY-factor residual, entry s≥1.25 & resid>0, T+1 open,
  exit s≤0.75 / 10d / SL 1.5×std — same spec as §3): 3,465 trades, mean **−0.14%/trade**
  (t≈−1.7 gross, i.e. no edge), win 48–51%; every sub-period ≤ 0 (2015–19 −0.15%, 2020–21
  −0.38%, 2022–26 −0.03%). At 20bp round-trip: −0.34%/t; at 60bp: −0.74%/t.
- Robustness across the honest grid (entry 1.0 / 1.25 / 1.5): identically non-positive.
- OU half-life on residuals: median ≈ 0.2d (nonsense — residual daily autocorr ≈ 0), i.e. the
  residual series are noise, not a tradeable stationary mean reversion. C3-1 answer: the
  published cutoff edge is NOT present on this data/universe (matches the corpus warning of
  2011+ decay). C3 is demoted; the round-trip-cost claim does NOT survive (edge is not
  positive even gross).

**C2 (weekly reversal short) — FAIL (as specced short).**
- Cross-sectional top-quintile-of-20 by last-week return, SHORT, hold 1w / 2w (T+1 fill):
  per-name per-week mean **negative** — the short loses: −0.80%/wk (t≈−2.7) at 1w,
  −1.59%/wk (t≈−3.2) at 2w; costs make it worse (−1.0% at 20bp). Reason: on this universe
  prior-week winners KEEP trending (momentum continuation), so the SHORT leg has no edge.
- Side-finding (useful for the LONG side later): the mirror position (long the top quintile)
  would be +0.80–1.59%/t — consistent with the repo's existing long-side momentum; noted for
  future long-side candidate work, not for a $100 short book.
- C2-1 VERIFY answer: two-week hold clearly worse than one for the short; further build
  behind the short makes the candidate pointless; marked REJECTED as specced.

**C1 (OBB-Fade short) — PASSES initial screen with caveats.**
- Sim per doc spec (signal Close ≥ BB_upper(20,2) AND RSI14≥70, entry T+1 open,
  TP=signal-day BB_mid, SL=1.5×ATR14, time stop ≤5 sessions): 780 trades,
  mean **+1.30%/trade** (t≈+3.0 gross), 60% win rate, episode lengths median 1d,
  p90 4d, max 8d — dry-length answers C1-1.
- Sub-periods all positive: 2015–19 +0.96%/t (t=3.6), 2020–21 +1.78%/t (t=1.3 — squeeze headwinds),
  2022–26 +1.33%/t (t=2.3). At 20bp round-trip mean +1.10%/t; at 60bp +0.70%/t.
- C1-2 geometry answer: TP (BB_mid) fires first only ~3% of the time; SL (1.5×ATR) hits
  ~33% and TIME exits ~64%. Expectancy comes from the time/fade tail — NOT from the TP.
  Assumption "TP before SL" inverted — but expectancy still positive (median +1.09%).
- **Squeeze tail CAUTION (C1-CA):** worst single trade ≈ −223% (2021 GME/AMC-style gap),
  p5 = −7.9%. One such name in a $100/0.7-share book is a >50% path shock. Any C1 build
  MUST add a squeeze/extension filter (e.g. shortlocator-style borrow gate, or skip names
  with 5d move > +40%) and mirror the 4-position cap.

---

**Updated recommendation (OPINION, after verification):** **C1 (OBB-Fade short)** is now the
primary next SHORT strategy — it is the only one of the three with a positive gross edge
under measurement (+1.3%/t, t≈3), survives 60bp costs, reuses only existing indicators/infra, and fits
the $100 fractional-share book. Ship it with (a) squeeze guard (name-level price extension
filter) and (b) the honest-gate chain from §6 — DSR ledger, WFE walk-forward, and the
cost-stress test. C3 and C2 remain REJECTED as specced (no edge / negative edge); the
long-momentum continuation from C2's data is the next LONG-side candidate if desired.

*Prepared by opencode research session, 2026-08-09. Deliverable: this file only; verification
script artifacts live beside it in `docs/research/`. No src files, no validators, no brokers
touched. All numbers above are measured on proxy-universe data with the caveats stated;
judgment is tagged OPINION.*