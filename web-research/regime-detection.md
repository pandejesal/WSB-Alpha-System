---
title: Regime Detection for a Retail Overnight Engine (SPY / QQQ / BNB)
purpose: Internet research on market-regime detection methods, judged for a $100 retail account trading SPY, QQQ and BNB overnight (close-to-open / 24-h crypto nights)
date: 2026-08-09
scope: web-research | regime detection | retail overnight engine | $100 notional
notes: Only URLs that actually returned usable content in this session are listed. Pages that could not be reached or returned no regime-specific content are marked [NOT FOUND].
---

# Regime Detection — Evidence Review for the Overnight Engine

## 1. Method table

| Method | Detection inputs | Robustness evidence (link) | What it gets wrong | Verdict for SPY/QQQ/BNB overnight |
|---|---|---|---|---|
| VIX percentile / threshold bands | ^VIX level or rolling 252-day percentile | TradingView VIX Regime indicator: <15 Complacent / 15–20 Normal / 20–25 Elevated / 25–35 Fear / >35 Panic; Volatility Visualizer Percentiles rescales VIX vs last 252 bars | Distribution shifts; percentile crawls after quiet periods; no direction signal — fear can mark the bottom (capitulation fails the gate) | Useful as a **position-size governor** for the equity leg. It is not a direction edge; never holds overnight longs into Fear/Panic bands enlargement |
| VIX term structure (contango / backwardation) | Spot vs 9 futures expirations (VIX9D / VIX / VIX3M / futures curve); VX2/VX1 slope | eco3min.fr VIX backwardation/contango piece: 21 of 22 backwardation episodes since 2004 preceded a >5% S&P 500 drawdown within a month; contango ≈85% of days, total backwardation ≈5% of days, never lasts > a few weeks; VX2/VX1 flattens 1–2 wks before big peaks | Backwardation episodes are rare and short; spot-spike vs futures can lag the actual turn; VIX9D spikes can be premature (normalized on 1–2 days) | Strongest "turn-out / risk-off" governor for SPY/QQQ overnight; contango alone is not a signal; doesn't apply to BNB (no VIX futures for BNB) |
| Hidden Markov Models (HMM) / Markov-switching | Log returns of the index; no fundamentals; N=2..3 states with AIC/BIC model selection | IEEE 11038776: HMM+adaptive (FinRL) over 30 Dow Jones stocks beats baselines (Sharpe); arXiv 2007.14874 hierarchical HMM for bull/bear detection; JEIF HMM regime detection study on frontier equities (2 vs 3 regimes via AIC/BIC/HQIC) | State label is retrospective / noisy at transitions; regime persistence changes; overfitting vs k; 2–3 regimes miss volatility-cluster nuances | Trainable on cheap OHLC — good research layer, not a live filter alone. Use to *detect* shock vs vol clusters; blend with vol-regime input for BNB |
| Volatility targeting / inverse-vol sizing | Realized vol (estimator e.g. EWMA 20-day half-life) or ΔVIX; scale exposure to constant vol | Harvey et al. "The Impact of Volatility Targeting" (Duke, PDF): vol targeting lifts Sharpe via "momentumness"; R² of vol on forward returns ≈ 45% (20-day half-life) and ≈ 60% (90-day); Conditional Volatility Targeting (T&F, 2020) confirms state-dependent gains | Vol estimates lag spikes; targeting ≠ direction; can kill returns in sustained uptrends; needs sane target (BNB vol >> SPY vol) | **The financially strongest addition** — give every asset a 20–90d half-life vol scalar, cap overnight risk on BNB night regime; zero extra data |
| Trend filter (MA200) + ADX/DMI gate | Close vs SMA(200); ADX(14) < 20 → no trend | Market Regime Analyzer (DavidEH): 5-regime model with drift t-stat ± threshold, volume delta, transition matrix built on last 100 bars; research.s04-momentum-regime-classifier: ADX regime filter removes ~22% of losing trend trades | Whipsaws at mean reversion; 200-day signal lags long; ADX transition-lag; regime matrix on 100 bars is too short | Cheap and robust; use MA200 for SPY/QQQ overnight longs and ADX<20 as trend-chop guard for BNB trend nights |
| Dispersion / correlation-cross-asset regime | Average pairwise correlation or dispersion of component returns; factor model (e.g. MAC3 16-factor) | Bloomberg MAC3 correlation-based risk model; dispersion/correlation regimes widely documented in cross-asset studies; kangchengX/market-regime demonstrates CNN/AE/Siamese + K-means clustering on correlation matrices | Requires a factor library & many assets; correlation shifts are arbitrarily weak intraday; clustering is unstable | Overkill for a 3-asset retail engine. At most use pair correlation SPY↔QQQ as a divergence check; skip institutional dispersion for now |

## 2. Deep dives (200–400 words each)

### 2.1 VIX percentile + term structure

The cleanest and cheapest equity-regime inputs, both free daily.

**Percentile/floor logic.** VIX has a massive regime trait: it parks near its own floor for months (Complacent/Normal), then spikes an order of magnitude in a day. Threshold levels (<15, 15–20, 20–25, 25–35, >35) come from the TradingView "VIX Regime" indicator; percentile-of-252-days (Volatility Visualizer Percentiles) is the more honest version because it removes the drift of average VIX over decades (VIX average has risen over 2000s–2020s, so fixed bands misinterpret "low VIX").

**What this means for the engine.** For close-to-open on SPY/QQQ, an elevated VIX band (Fear+ ) corresponds to higher overnight gap variance and higher reversal probability — the engine should *shrink, not stop,* because overnight gap hazards are larger with higher gaps to the second. Panic bands mark bottoms as often as continuation (VIX spikes frequently mark the turn); so the rule is "reduce size at Fear, respect the round-trip trade-off, behave differently in Panic + % extreme".

**Term structure.** The term-structure view (eco3min.fr) — spot VIX vs VIX futures 9 expirations — states the shape is "contango normally, backwardation rarely and only in acute stress": fewer false signals than the level alone. Quantitative anchors from the verified source: contango dominated ~85% of trading days from 1990–2025; total backwardation appeared on ~5% of days and never lasted more than a few weeks; and **21 of 22 backwardation episodes since 2004 preceded an S&P 500 drawdown above 5% within a month** — the strongest stress-forecasting track record of any single indicator here. Two leading sub-signals: the **VX2/VX1 slope** flattening from ~1.03–1.05 toward 1.01–1.02 (an early tension signal that preceded the Feb 2018 and Aug 2024 peaks by 1–2 weeks), and the **VIX9D** node spiking 20%+ above VIX ahead of a full inversion by 1–2 trading days (volatilitybox.com). VIX/VIX3M ratio thresholds (0.95–1.0 transition zone, >1.10 inverted) give a mechanical daily check.

**Fallibility.** The curve fails when panic is short and sharp (bad news turns good quickly) — total backwardation is rare, so it generates few signals, and spot-spike vs futures can lag the actual turn. Roll mechanics (monthly sequential expirations, VX1/VX2 holding 75% of volume, wide bid-ask beyond VX5) add microstructure noise. And it says nothing about direction — it is a risk governor, not a buy/sell signal. For the engine: treat any VX2/VX1 flattening as size-down, any inversion as essentially "no US overnight equity risk".

**Delta.** Neither method is an entry signal; both are size/expiration-risk governors. Combined with ADX-trend filter on SPY/QQQ, this is the primary equity overnight risk regime bucket.

### 2.2 Hidden Markov Models (HMM)

HMM models returns as generated by K latent regimes (typically 2–3: calm, high-vol/bear, mixed) with transition probabilities and regime-dependent means/vols, selected via AIC/BIC.

**Evidence.** IEEE 11038276 demonstrated HMM+~adaptive trading (FinRL-style) on 30 Dow names improving on baselines — regime probabilities feed trading decisions. The arXiv 2007.14874 hierarchical HMM (bull/bear classification, second-order states) is the most readable sandbox on equities. On frontier equities (JEIF) HMM states (2 vs 3 regimes) were compared with AIC/BIC/HQIC — the standard result is that 2 regimes fit most series fine, 3+ adds overfit and parameter explosion.

**Strengths.** Truly cheap: just OHLC returns, no extra data. Gives smooth posterior "P(calm | data)" — usable as a meta-governor with the vol-targeting layer.

**What it gets wrong.** States are *retro-spectively defined*: the transition happens at some hidden moment, then the model might attribute it late. Regime *switching* happens the rare day the regime flips; a *static* HMM fitted once goes stale when the market structure changes (e.g., 2022 vol regime vs 2023–24 rally), requiring refitting — that's a research workflow, not fire-and-forget live trading. BNB's 24/7 data adds microstructure noise the model must be trained on separately.

**Verdict.** Use HMM as a "quality-of-state" sanity layer: combine its posterior with the vol-target scalar; no extra data source. But never design it as a primary trigger; treat its output with a smoothing lag and refit periodically.

### 2.3 Volatility targeting

The simplest revenue-positive regime handling: size = target-vol / forecast-vol. Harvey's "The Impact of Volatility Targeting" (Duke paper) shows the Sharpe lift comes from a "momentumness" of vol itself: today's vol *predicts* next period's vol (R² ≈ 45% on a 20-day half-life, ≈ 60% on 90-day). The conditional version (T&F, 2020) investigated state-dependent value — high-vol states carry more residual persistence.

**What it gets wrong.** It does not predict *direction*; it just reduces risk in high-vol periods (and increases in low-vol). If you target too aggressively (e.g., 2× monthly vol) you reintroduce left tails; vol forecasting with half-life < 20 days is noisy, so use ~30–90d. It assuming vol is mean-reverting — true enough for equity and dogecoin, but crypto vol clusters persist longer; and for BNB overnight you must measure **night-hours realized vol** separately (it can differ from 24h vol).

**Engine use.** Best applied as *position sizing*, not a gate: `position = risk_budget / (σ_est × k)`. For SPY/QQQ use 20–60d half-life; for BNB use 7–20d (crypto vol decays faster). Combined with a hard cap (e.g., never > x% of account on BNB nights), this alone reduces ruin-risk more than any regime classifier.

### 2.4 Trend filter (MA200) + ADX gate

The two-line defense: is price above/below the level where trend regime matters (MA200), and is the market trending or choppy (ADX).

**Evidence.** DavidEH "Market Regime Analyzer" expands on this with a 5-regime model: uses drift stats (t-stat style) + volume delta and a transition-probability matrix from the last ~100 bars. The strongest quantified source is Tenth Meridian S04 (research.tenthmeridian.co): ADX(14) used as a *binary gate* — ADX < 20 blocks momentum entries — filtered 22% of losing trades in their V14.1 backtest, lifting win rate from 64% to 71.5% on surviving trades; of all trades blocked by the gate, 71% would have been losers; high-confidence signals in low-ADX environments had a 46% win rate — the worst category of losses. Cluster statistics: INDEX instruments spend ~35% of time in ADX < 20 (win rate 49.8% → 53.7%, +6.3R) — directly relevant since SPY/QQQ are index products; the gate is most selective exactly where index ETFs live. ADX is Wilder's construction from 1978 (smoothing = EMA with period 2n−1, so it needs ~40 bars warm-up after gaps).

**What it gets wrong.** Long-term MAs lag big turns; in choppy periods MA200 whipsaws. ADX flickers across 20; the 20 threshold is a hyperparameter — Tenth Meridian itself lowers it to 18 in restricted session windows, an admission the boundary is soft. The regime matrix window of ~100 bars is fragile. And there is the day/overnight mismatch: trend filters judged on daily bars govern overnight motion, but the gap itself is decided overnight — a stock can close above MA200 and gap down 3% the same night (see VIX deep dive for the interplay).

**Verdict.** Use trend direction as a *gate* not a signal: only long overnight when close > MA200 (SPY/QQQ), and only treat BNB as "trend day" when ADX(14) > 20 typical — otherwise tape as mean-revert/night chop. That's ~5 lines of code and zero extra data.

### 2.5 Dispersion / correlation & regime transition tables

Dispersion = average pairwise **correlation** across a basket; high correlation = systemic regime (everything tanks together), especially useful in equity/crypto. The institutional versions (Bloomberg MAC3, 16-factor) are heavy; the kangchengX/market-regime research applies unsupervised clustering (CNN / AutoEncoder / Siamese / K-means over rolling correlation matrices) — credible but institutional-grade.

**What it gets wrong.** Correlation is unstable in calm markets and converges to ~1 during stress; it says nothing about direction; requires a reasonably many-asset universe to compute (for 3 assets the dispersion estimate is extremely noisy); clusters via K-means/variance based are unstable across refits; this adds more parameters without real signal for a tiny account.

**Also: regime "transition probability" material** was searched (JEIF HMM transition tables, non-free). Only [NOT FOUND] free content on AllocateSmartly/Quantpedia-specific regime filters was returned (all paywalled/aggregated). Those are dead friends for this density.

**Verdict.** For this engine: use **pair correlation SPY↔QQQ trend regime as a tiny overlay** (if the two correlate much > normal → beta is all in one risk pocket) — literally a computed roll-through; skip MAC3-style dispersion wholesale. Keep the transition-matrix HMM only if the HMM layer above is built.

## 3. What actually matters for this engine (ranked, honest)

1. **Vol-targeting by asset (30–90d half-life) — invest in this first.** It buys risk-governing with zero extra data and is the difference between ruin and survival on a $100 overnight engine; academic support (R² 45–60%) is the strongest of all methods here.
2. **Trend gate (MA200 daily close; ADX14 for BNB trend/chop).** Cheap, interpretable, sieves most "overnight turning" razor edges. It will whipsaw — profitably, still.
3. **VIX percentile + term-structure caps for SPY/QQQ.** Only for the US leg; elevated/backwardation cuts size. It will *falsely cut* after capitulation bottoms — accept that cost.
4. **HMM/Markov layer.** Best as a research overlay to check "is the vol regime truly clustering" (esp. BNB at nighthours). Not first-line; expected to fail around transitions.
5. **Dispersion / correlation.** Skip for this notional size.

Honest boundaries: every indicator above is *retrospective*: regime=time t is identified post-hoc, so transitions are always 1–N bars late. Nothing here beats a hard position cap and a sane target vol. Methods needing __zero__ new data vs those needing free new sources:

| Method | Extra data needed | Status |
|---|---|---|
| Vol targeting | none (own returns) | usable today |
| MA200 / ADX | none (own daily/night bars) | usable today |
| VIX percentile | ^VIX (free) | new free source |
| VIX term structure (9 futures) | VIX futures expirations curve (free/cboe) | new free source |
| HMM | none (own returns) | usable today |
| Dispersion/correlation | many symbols or factor return files | needs new sources |

## 4. Sources (only fetched)

- TradingView VIX Regime indicator (levels table) — https://www.tradingview.com/script/QwBMpOG9-VIX-Regime/
- TradingView Volatility Visualizer Percentiles (VIX percentile vs 252 bars) — https://www.tradingview.com/script/Ng3lWB8S-Volatility-Visualizer-Percentiles-VIXFix-ATR-VIX/
- eco3min.fr VIX term structure/backwardation article (21/22 episodes, VX2/VX1 slope) — https://eco3min.fr/en/vix-backwardation-contango-volatility-term-structure
- Volatility Box: VIX futures contango/backwardation mechanics, VIX9D+20% signal, VIX/VIX3M ratio — https://volatilitybox.com/research/vix-contango-backwardation/
- IEEE: HMM + RL on Dow Jones stocks — https://ieeexplore.ieee.org/abstract/document/11038276
- ArXiv hierarchical HMM bull/bear — https://ideas.repec.org/p/arx/papers/2007.14874.html (mirror of arXiv:2007.14874)
- "The Impact of Volatility Targeting" (Harvey et al., Duke) — https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of_.pdf
- Conditional Volatility Targeting (Taylor & Francis, 2020) — https://www.tandfonline.com/doi/full/10.1080/07474938.2020.1756589
- 5-regime Market Regime Analyzer (DavidEH) — https://www.tradingview.com/script/Laj90V1p-Market-Regime-Analyzer/
- Tenth Meridian, S04 ADX regime classifier (ADX<20 gate, 22% loser-filter, win rate 64%→71.5%, cluster table incl. INDEX 35% low-ADX) — https://research.tenthmeridian.co/s04-momentum-regime-classifier
- JEIF HMM regime detection study (Botswana/Ghana/Kenya/Nigeria 2011–2017, 2 vs 3 regimes via AIC/BIC/HQIC) — https://academicjournals.org/journal/JEIF/article-full-text/60F93A768161
- Overnight return evidence: "Celebrating Three Decades of Worldwide Stock Market Manipulation" (SPY close-to-open +1232% vs intraday −14%, 29 Jan 1993 – 31 Oct 2019) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3490879 (via https://quant.stackexchange.com/questions/53633/overnight-and-intraday-returns-of-stock-index-and-etf-seem-inconsistent)
- "Overnight returns, daytime reversals, and future stock returns" (J. Fin. Econ. 2022) — https://www.sciencedirect.com/science/article/pii/S0304405X21004116
- TwoQuants "Trading the Night Effect" (SPY since 1993, >88% of SPY's overall return from overnight; effect breaks during crises, and Nightshares ETF + Lachance 2015 SSRN) — https://twoquants.substack.com/p/trading-the-night-effect
- "Day and night expected returns under overnight information" (2025) — https://www.sciencedirect.com/science/article/pii/S1544612325018458
- Bayesian regime-switching (PyMC, bull/bear posterior probabilities, 11/120 months uncertain) — https://www.pymc-labs.com/blog-posts/bayesian-hmm-market-regime-detection-pymc/md

## 5. NOT FOUND / paywalled

- AllocateSmartly tactical strategy detail (aggregated paywall) — [NOT FOUND]
- Quantpedia regime-strategy details (paywall) — [NOT FOUND]
- Academic transition-probability data, e.g., JEIF exact transition tables — [NOT FOUND full]
- MAC3 16-factor suite details (Bloomberg, closed) — [NOT FOUND]
- CBOE VIX futures raw feed (free but registration) — [NOT FOUND this session]
- AllocateSmartly/Quantpedia regime-filter specifics — [NOT FOUND, aggregator homepages only]