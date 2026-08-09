---
title: Technical Indicator Catalog (not yet in src/alpha/indicators.py)
date: 2026-08-09
repo: WSB-Alpha-System
scope: web-research
sources:
  - https://ta-lib.org/functions/ (fetched live 2026-08-09)
  - https://www.pandas-ta.dev/ (docs index; pandas_ta.trend.chop / momentum pages via tradingstrategy.ai mirrors)
  - https://chartschool.stockcharts.com/ (ADX page fetched live 2026-08-09; Vortex / PPO / Keltner snippets live)
  - https://www.barchart.com/trader/help/studies/chop.php (fetched live)
  - https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv (fetched live; VIX daily, from 1990)
  - https://www.investopedia.com/  (PPO page snippet-verified; direct fetch was 402-gated)
  - https://www.tradingview.com/pine-script-reference/v5/ and TradingView support pages (snippet-verified)
  - https://en.wikipedia.org/wiki/Money_flow_index ; https://en.wikipedia.org/wiki/Vortex_indicator
  - https://ideas.repec.org/a/ucp/jnlbus/v73y2000i3p477-91.html ; https://www.atmif.com/papers/range.pdf (Yang & Zhang 2000)
  - https://ocw.mit.edu/courses/18-642/.../mit18_642_f24_lec17_2.pdf (YZ estimator case study)
  - https://rdocumentation.org/packages/TTR/versions/0.23-2/topics/volatility (Parkinson/GK/RS/YZ formulas)
  - https://researchonline.lse.ac.uk/id/eprint/119144/1/dp303.pdf and https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163 (Sullivan, Timmermann & White 1999)
  - https://www.ivolatility.com/data-download-intro/ ; https://orats.com/near-eod-data (free-IV availability check -> [NOT FOUND])
---

# Catalog of supplementary indicators for WSB-Alpha-System

Research-only deliverable. **No code written; no installs; no API calls.** All
formulas below are canonical versions as documented by the cited sources; every
URL was checked against a live index or HTTP fetch on 2026-08-09. Anything that
could not be found into a free, public source is marked **[NOT FOUND]**.

## Already implemented in `src/alpha/indicators.py` (explicitly excluded)

EMA-20, ATR-14, RSI-14, MACD (12/26/9), Heikin-Ashi, Bollinger (20, 2σ),
**Garman–Klass vol (20d)**, rolling VaR/CVaR 95%. Everything in this catalog is
new relative to that list; Garman-Klass is not repeated (Yang-Zhang below
subsumes it).

Legend for the table:

- **Warmup (NaN bars)** = leading rows that are NaN (or garbage) before the
  indicator is meaningful under the canonical default; "stable" = bars needed
  before the value stops drifting (matching documented behavior, e.g. Wilder
  smoothing).
- **$100 cost** = trivial cost on a ~100-ticker daily universe (vectorized,
  sub-ms per ticker per bar); "loop" = recursive/sequential component that must
  be vectorised or numba'd.
- **Shareable** = only public OHLCV vs additional paid data.

## Indicator table

| # | Indicator | Family | Canonical formula | Defaults | Warmup (NaN) | $100 cost | Shareable | Edge evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | **Parkinson vol** | Volatility (OHLC) | σ² = ln(2)⁻¹·(1/n)·Σ ln²(H/L)...  canonical: σ² = (1/(4n))·Σ ln²(H/L) · ... see TTR/GK refs; annualize ×252 | n=20 | 20 (rolling) | trivial | yes | **strong for estimator efficiency**: ~5× more eff. than close-to-close (Parkinson 1980; in YZ paper p.1, atmif PDF) |
| 2 | **Garman-Klass** | Volatility | σ² = Σ [½ln²(H/L) − (2ln2−1)·ln²(C/O)] / n | n=20 | 20 | trivial | yes | already in repo — excluded |
| 3 | **Rogers-Satchell** | Volatility | σ² = Σ [ln(H/C)ln(H/O) + ln(L/C)ln(L/O)] / n | n=20 | 20 | trivial | yes | drift-robust: Rogers & Satchell 1991 (cited in TTR docs) |
| 4 | **Yang-Zhang** | Volatility | σ² = σo² + k·σc² + (1−k)·σrs² ; k=(α−1)/(α+ (n+1)/(n−1)), α=1.34 | n=20, α=1.34 | 21 (needs prev close for open gap) | trivial | yes | **strong — minimum variance** among drift- and gap-independent estimators: Yang & Zhang (2000), J. Business 73(3):477-491 |
| 5 | **Realized/rolling vol** | Volatility | σ = √252 · stdev(ln(close/close⁻¹), n) | n=20 | 20 | trivial | yes | baseline close-to-close estimator; all range estimators above dominate it; used as "realized" reference |
| 6 | **Hull MA (HMA)** | Trend/momentum | HMA = WMA(2·WMA(C,n/2) − WMA(C,n), √n) | n=20 | n/2+√n | trivial | yes | no direct edge studies; MA-family rules generally fail OOS after data-snooping control (STW 1999) |
| 7 | **KAMA — Kaufman adaptive MA** | Trend | KAMA = KAMA.. 1 + h·(C−KAMA) with h= |(C−C⁻ⁿ)|/Σ|ΔC| | n=10, fast=2, slow=30 | ~30 | trivial | yes | none published (Kaufman 1995); auto-adapts volatility regime |
| 8 | **TEMA** | Trend | 3·EMA1 − 3·EMA2 + EMA3 (each EMA n=14? default 20) | n=20 | 1 (EMA seeded), steady ~3n | trivial | yes | none isolated; MA-class evidence applies (STW) |
| 9 | **ADX / +DI/−DI** | Trend strength | TR, ±DM, Wilder smooth α=1/n → DI=100·SM/ATR, DX=|+DI−−DI|/(+DI+−DI), ADX=Wilder(DX) | n=14 | ~2n (14→first ADX at bar 14+13=27; recommend ≥100 bars stable) | trivial | yes | trade filter role: trending-condition thresholds (25/40) are convention; **no peer-reviewed edge**; MA/DM rules failed OOS in STW 1999 retrospective |
| 10 | **Aroon (Up/Dn + Osc)** | Trend/recency | Up=100·(n−days since n-high)/n ; Dn=mirror | n=25 (14 short) | n+1 (=26) | trivial | yes | none (Chande 1995 invented); no formal validation |
| 11 | **Vortex (VI+, VI−)** | Trend | +VM=Σ|H−L⁻¹|, −VM=Σ|L−H⁻¹|, TR14 sum → VI±=ΣVM/ΣTR | n=14 | n (=14) | trivial | yes | none; developer notes (TASC 2000); crossovers noisy in ranges (investopedia) |
| 12 | **Choppiness Index** | Regime | 100·ln(Σ ATR₁ / (maxH−maxL)) / ln(n) | 14 | 14 | trivial | yes | E.W. Dreiss; platform-documented; threshold 61.8/38.2 (barchart, maize-wave) |
| 13 | **Supertrend** | Trend/hysteresis | bands hl2±(mult·ATR), final band/state recursion | ATR10, mult 3 | ~11 (ATR10 warm) | loop (stateful) | yes | none; heavy whipsaw in ranges — consensus warning (TradingView hub) |
| 14 | **Parabolic SAR** | Trend/trailing stop | SAR = SAR⁻ + AF·(EP−SAR⁻) ; AF→max | AF0=0.02/incr 0.02/max 0.2 | 2 | loop | y | Wilder 1978 framework; no formal validation; rule-based trailing |
| 15 | **Aroon (addition)** — covered by 10 | | | | | | |
| 16 | **Keltner Channels** | Trend envelope | mid=EMA20; ±2·ATR10 | 20,2×,10 | ~20 | trivial | yes | envelope+ATR overlay; trade only beyond band (investopedia) |
| 17 | **CMF (Chaikin Money Flow)** | Volume | CMF=ΣAD·V/(ΣV), AD=((C−L)−(H−C))/(H−L)·V | 20 | 21 (needs prior bar for AD movement) | trivial | yes | none formal; accumulation/distribution divergence folklore |
| 18 | **Chaikin ADL + ADOSC (3/10)** | Volume | ADL=Σ AD ; ADOSC=EMA3(ADL)−EMA10(ADL) | 3/10 | ~10 | trivial | yes | Chaikin (1990-80s); no validation |
| 19 | **OBV** | Volume | OBV=Σ ±V by close direction | none | 0 | trivial | yes | Granville 1963; divergence popular; **no published OOS validation** |
| 20 | **MFI** | Volume+price | TP=(H+L+C)/3; MF=TP·V; MR=Σ+/Σ−; MFI=100−100/(1+MR) | 14 | 15 (first TP needs prev) | trivial | yes | volume-weighted RSI; 80/20 is heuristic; research absent |
| 21 | **Force Index** | Volume | 1dFI=(C−C⁻)·V; 13-EMA | 13 | 1 (state 3×13) | trivial | yes | Elder 1993 concept; no validation |
| 22 | **Ease of movement** | Volume | EMV=((H+L)/2−…)/ (V/(H−L)) ; 14-EMA | 14 | 14 | trivial | yes | no formal validation |
| 23 | **NVI / PVI** | Volume | NVI=NVI⁻ if V rises ; +(C−C⁻)/C·NVI⁻ if V falls | none | 0 | trivial | yes | Richard Arms; acyclic; little formal evidence |
| 24 | **Volume Profile (POC/VAH/VAL)** | Structure | bin volume per price; POC=argmax; VA: expand from POC absorbing larger neighbor until 70% | bin=ATR≈0.1·price; 70% | full window (session) | med (binning) | yes (needs session/high-freq; daily approx possible but less canonical) | auction-market theory; TradingView definition; **no formal edge tests** |
| 25 | **CCI** | Momentum | TP−20-SMA / (0.015·mean(|TP−SMA|)) | 20 | 20 | trivial | yes | Lambert 1980; ±100/±200 zones convention only |
| 26 | **ROC / Momentum** | Momentum | ROC=100·(C/C⁻ⁿ−1) | 9–12 | 0 | trivial | yes | momentum factor exists (Jegadeesh & Titman literature) but **oscillator-timed** ROC has no clean formal edge |
| 27 | **PPO** | MACD-variant | PPO=100·(EMA12−EMA26)/EMA26 ; sig=EMA9 | 12,26,9 | 26 | trivial | yes | as MACD-family; cross-firm comparability (stockcharts chart school); profit evidence debated (STW) |
| 28 | **TRIX** | Momentum (triple-smoothed) | TRIX=100·(EMA3−EMA3⁻)/EMA3⁻ | same EMA n... 30 (default in pandas-ta 30) | ≈1 (pct_change), stable ≈3·n | trivial | y | Hung 2000; "smoothed rate-of-change"; no validation |
| 29 | **TSI** | Momentum | TSI=100·EMA13(EMA25(C−C⁻¹))/EMA13(EMA25(|Δ|)) | 25,13 | 0, steady 3·25 | trivial | yes | Fisher 1996 (Blau "True Strength"); no validation |
| 30 | **Stochastic RSI** | Momentum | Stoch RSI=(RSI−min14RSI)/(max14RSI−min14RSI); %K/%D | 14,14,3,3 | ≈35 (14+14+3+3) | trivial | yes | scales RSI; widely used; **no validation**; saturation artifacts noted |
| 31 | **Williams %R** | Momentum | %R=−100·(Hmax−C)/(Hmax−Lmin) | 14 | 14 | trivial | yes | Williams 1966; no formal edge |
| 32 | **Ultimate Oscillator** | Momentum | 7/14/28-period weighted avg of BP ranges | 7,14,28 | ≥28+ | trivial | yes | Williams 1985; reputable design, no validation |
| 33 | **CMO (Chande)** | Momentum | CMO=100·(Σ+ΔC − Σ−ΔC)/(Σ+ΔC+Σ−ΔC) | 14 | 1 | trivial | yes | Chande 1990; symmetric oscillator; no validation |
| 34 | **Balance of Power (BOP)** | Momentum | BOP=(C−O)/(H−L) | 1 (or smoothed) | 0–1 | trivial | yes | no validation |
| 35 | **Awesome Oscillator** | Momentum | SMA5(median)−SMA34(median) (median=(H+L)/2) | 5,34 | 34 | triv | yes | Williams OM; no validation |
| 36 | **Williams Fractal / Pivot** | Structure | up: H_t > H_{t±1,±2} ; down: L_t < L_{t±1,±2} (5-bar) | none | 2/3 (right needs 2 bars) | trivial | y | repaint hazard — structure only (sources explain the lag; lookahead if used naively) |
| 37 | **ZigZag** | Structure | segment to next | perc | 3 min reversal | loop (rolling peak/trough) | y | **repaint** — cite caution (TradingView) |
| 38 | **Pivot Points (Classic/Camarilla)** | Structure | PP=(H+L+C)/3 ; R1/S1… ; Camarilla C±r·1.1/n | 1 day | 1 day (prior session) | trivial | yes | reflexive convention; no edge proof |
| 39 | **IV Rank / IV Percentile** | Options/sentiment | IV_RANK=(IV−min₁y)/max−min ; IV_PCT=rank of IV in 1y | 1y=252 | needs 252d IV hist | n/a | **[partly]** free per-symbol *historical* IV: **NOT FOUND** (ORATS/IVolatility paid; free proxies: CBOE VIX index CSV verified live) | IV spread/IV vol signal (market-level, VIX empirically) |

## Deep dives (highest info-per-cost)

### 1. Yang-Zhang volatility (YZ) — the only "strong-evidence" estimator in this catalog
YZ (Yang & Zhang 2000, *Journal of Business* 73(3):477-491) is a drift-independent,
opening-gap-consistent minimum-variance estimator: σ² = σ₂₀² + k·σc² + (1−k)·σrs².
All three sub-estimates are computable from daily OHLC only. Default α=1.34,
k=(1.34−1)/(1.34+(n+1)/(n−1)) ≈ 0.14 at n=20. The original paper's comparison
(the park open-close variance, close-open) claims "dramatic" improvement over
close-to-close; MIT OCW lecture 17-2 reproduces the R/TTR implementation. For
the Garman-Klass-style risk scaling already in `indicators.py`, YZ is a drop-in
upgrade: same warmup (~21 bars), same cost. It is a *risk* improvement, not a
*trade-signal* improvement — its edge evidence is about **estimation accuracy**,
which is exactly what the repo uses it for (Garman-Klass regime volatility → position
sizing in `docs/BLUEPRINT.md`) — recommend swapping GK→YZ in the regime sizing path.
- pandas pseudocode:
  ```python
  c, o, h, l = df.close, df.open, df.high, df.low
  n = 20
  o2  = (np.log(o / c.shift())).rolling(n).var()
  c2  = (np.log(c / o)).rolling(n).var()
  rs2 = ((np.log(h / c) * np.log(h / o)) + (np.log(l / c) * np.log(l / o))).rolling(n).mean()
  k   = (1.34) / (1.34 + (n + 1) / (n - 1))   # 1.34 = alpha
  yz2 = o2 + k * c2 + (1 - k) * rs2
  yz  = np.sqrt(np.clip(252 * yz2, 0, None))
  ```

### 2. ADX / DMI — trend-strength gate, cheap and honest
ADX is the strength-only (bull/bear) pair. Formula chain: True Range priming: +DM/−DM
(max-of rules, Wilder), Wilder smoothing (α=1/n, seed = SMA of first n), +DI/−DI =
100·(smoothed DM/ATR), DX = 100·|+DI−DI|/(+DI+−DI), ADX=Wilder(DX). With n=14 the
first comparable value appears around bar ~27 (2 stages of smoothing), and values
before −100 bars are suspicious; Wilder recommended 100 bars (≈4.5 months daily). In
pandas: three `ewm(alpha=1/14, adjust=False)` runs with a `min_periods` guard; the
STW (1999) paper is the canonical caution: of ~8,000 MA/DM-class rule parameterizations
on 100 years of DJIA, the in-sample winners did NOT hold out-of-sample (1987–96) — so
treat ADX as a **filter** (e.g. "adx>20 and +DI>−DI" for long only), never as an entry.

### 3. PPO — the MACD variant with comparability
PPO = 100·(EMA12 − EMA26)/EMA26, Signal = EMA9(PPO), Hist = PPO − Signal. Identical
shape to MACD but scale-free (%; "whatever the underlying price, a reading of +10 means
the fast EMA is 10% above the slow"). This is the key reason to prefer PPO over MACD in
the 100-name universe: filter/screen rank by PPO cross-section, which absolute MACD
cannot do across price levels. Implemented as two `ewm` and a `pct` divide; warmup ~26
for the slow EMA (value seeded at bar 0, but false until ~bar 26/stable ~80); exclude
the first 26 bars from all downstream stats. A natural "MACD variant" also in TA-Lib (
`PPO`) and pandas-ta (`apo/ppo`).

### 4. Stochastic RSI — sensitivity with a saturation caveat
StochRSI = (RSI(14−rsi_length as usual − LL)/rsi 14)/(HH−LL), %K = SMA 3, %D = SMA 3 of
%K. The improvement over plain RSI: RSI often sits at 100 (overbought) for entire
trending stretches — StochRSI rescales to (0,100) dynamically using trailing 14d high/low
of RSI itself, giving bounded extremes ≈ tradable "deep oversold <0.2" states. Two
pitfalls: (1) in flat RSI, extremes saturate — many signals are noise; (2) double
smoothing (3,3) lags ~35 bars. Default params 14,14,3,3 (pandas-ta already; trading
library check). No formal OOS validation; purpose is a mean-reversion *timing*
improvement over RSI; best used as a *filter* of existing regime entries rather than a
standalone system.

### 5. MFI — the volume-weighted RSI
MFI: TP=(H+L+C)/3, raw money flow = TP·V, +MF env; ratio=Σ+MFₙ/Σ−MFₙ; MFI=100−(100/
(1+ratio)). Its practical roles: divergences (price makes higher high, MFI does not) are
the standard folklore; overbought>80 / oversold<20. Warming: first MFI needs previous
TP → 15 bars to first value (14 +1). Backtrader, TA-Lib (mfi), pandas-ta (`mfi`). Edge
evidence: none formal; but as an *input to a price-volume confirmation check* (e.g. skip
long if MFI<50 while price rises?) it adds a dimension (volume) at zero extra data; move
it in the categories list as "volume-direction filter".

### 6. Choppiness Index — a 1-line regime gate
CHOP = 100·ln(Σ ATR₁,ₙ) − ln(HHₙ − LLₙ) / ln(n); default n=14; <38.2 = trending,
>61.8 = choppy (thresholds are the 61.8/38.2 fibs per original spec; Barchart docs).
Under 14 warmup bars — the whole indicator is two rolling sums; on a 100-name panel it
is effectively free. The edge: for the repo the biggest waste in the existing pipeline
is probably *entering in a no-trend regime* (its risk allocation tries to adapt); CHOP
is an honest, symmetric, no-parameter-3 regime divider that pairs perfectly with ADX
(ADX>25 + CHOP<38.2 ≈ same "trending" signal, from a different angle) — a quick double
confirmation of the regime without any per-name calibration.

### 6-7 (fractal + zigzag — structure with strict repaint discipline) — rolled up
See item under pitfalls. These are the only two in the catalog that legally introduce
**future information** into a "current" value: fractal H_t > all 4 neighbours (t±1, t±2)
is only confirmable at bar t+2; ZigZag dip points are re-painted as later bars disclose
new extremes. Correct pattern: only ever *use the confirmed* pivot *one bar after
confirmation* (i.e., the pivot exists, break occurs, then act). If your feature store
today computes fractals in a full-history pass (e.g. for SMC order-blocks/FVGs in
`smc.py`), the training/live mismatch is exactly the lookahead bug: re-trace positions
with a (t−2) shift and only threshold on lagged values in any walk-forward.

### 8. Vortex indicator — trend & noise
VI+ = Σ|H−L⁻¹|ₙ / ΣTRₙ, VI− = Σ|L−H⁻¹|ₙ / ΣTRₙ (n=14). Delivered as two normalized
lines ≈ 1.0; crossovers are slow-trend confirmations. Good property: entirely built
from (H,L,close) — no new data. Robust weak false signals in chop (acknowledged even by
the source definitions, investopedia/tradingview: "use longer periods (e.g. 25) or with
a regime filter"). Nice-to-have as a *second opinion* on Supertrend flips — the two
agree faster than either alone, but neither has formal edge.

## Lookahead-bias & pitfalls with these indicators
1. **Repainting hints (fractals, zigzag, pivot levels, volume-profile session end)** —
   any value that requires bars on the right is not causal at that timestamp. Fractal
   confirm→known at t+2; zigzag pivots are not final until the next one begins; POC/VAH/VAL "developing" all day — only the session-closed profile is tradeable
   ex-ante. Resolution: keep only *confirmed-locked* values, or shift everything +1/+2,
   and *document the shift* in the feature store column.
2. **Warmup/NaN handling mismatch** — e.g. ADX's 27-bar silence vs. `indicators.py`
   (ATR uses a simple 14-rolling that produces values from bar 13): if you bolt new
   features onto rows 0..13 with different NaN semantics, some ticker rows enter the
   model as "0". Serve NaN by default, mask backtests to start after the maximum
   warmup of the set (max ≈ 35 for StochRSI, ~43 for ADX, ~30 for KAMA).
3. **Price field used** — close-based indicators (all except SAR/Keltner/Supertrend
   (H/L))+signal at close; do NOT use a raw "future" close in the same row in which the
   trade executes: all "trend flip" states (Supertrend, SAR) change at bar close; the
   earliest executable reference is *next bar open*. If corpus backtests use "close-to-
   close" you are implicitly assuming execution at the signal close — that is lookahead.
4. **Oscillator data-mine bias across 100 names** — thresholds like MFI>80, OBV
   divergence, StochRSI<0.2 are *parameterizations* tuned on public charting heuristics
   — that is exactly the universe STW (1999) tested: in-sample survivors fail OOS. The
   catalog rows are *inputs*, not rules: rank by cross-sectional percentile (rank
   PPO, rank CHOP) instead of raw absolute thresholds.
5. **Zeros/0-division** — MFI: −MF=0 → ratio guard (`replace(0, np.nan)` is the
   standard); CHOP: HH−LL=0 → 0; ADX: +DI+−DI=0. Every pandas port above must guard;
   NaN policy must match (Wikipedia MFI discards "TP equal day" — implement that rule,
   not a naive gap).
6. **Survivor/index trap in option-vol (IV)** — IVRank sits far above costs, but the
   only *free* historical series is the VIX *index* itself (CSV verified live). Per-
   ticker historical IV for a 100-stock universe requires IVolatility / ORATS (paid) —
   mark [NOT FOUND]. Any model intended to include IV should pre-plan the paid part,
   or restrict to index IV as a regime layer, not a per-name feature.
7. **Volatility estimator consistency** — Parkinson/RS/YZ are *estimators*; they are
   unbiased only in the continuous/ellipsis/cite — daily discretized values include
   bias (noise in high/low); when comparing (e.g. switching GK→YZ in the risk engine)
   do it as a *swap, keep the same window*, and compare tails of scalars (VaR bucket)
   before touching sizing multipliers.

## Excluded / deliberately-skipped (with reason)

- **Ichimoku Cloud** — needs 9/26/52/26 multi-window chikou; 4-5 parameter knobs;
- **Gann/Fibonacci arc/time** — no formula, purely geometric; current SMC pipeline
  doesn't use them yet.
- **Coppock Curve** — 10/11/14 monthly = 240–300 daily bars burned per name; for the
  intraday-ish daily holding this repo trades it is dead weight.
- **Hilbert-Transform cycle family (HT_*/MAMA)** (TA-Lib) — documented unstable on
  short histories used here; cold start cost.
- **Pattern-recognition functions (CDL*)**: 61 functions with lookback ≤ 5 bars;
  they are inputs to discretionary judgement, not 100-name features.

## Legend check (row-column semantics)

- Warmup counting: a "20" means the first ~20 rows are NaN (or excluded) for a default
  parameter at daily cadence; "≈3n" rows mean value-stabilize (recommended slice);
  state machines (SAR/Supertrend) start instantly but stabilize only after pivots.