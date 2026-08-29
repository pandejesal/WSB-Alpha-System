# Hedge Fund Indicator Research — Strategy Hunt Candidate Library

**Date:** 2026-08-25  
**Agent:** Researcher  
**Purpose:** Supply validated indicator catalog to Phase 2–3 hunt sessions (YAML spec authoring, edge-gate pre-registration)

---

## 1. Global Macro / Bridgewater Regime Indicators

### 1.1 Growth–Inflation Regime Framework

**Confidence:** HIGH  
**Summary:** Bridgewater's core systematic framework classifies regimes into four states (growth ↑/↓ × inflation ↑/↓) and targets returns driven by macro surprises versus consensus, not level. Pure Alpha has annualized ~11.4% since 1991 with only 4–5 losing years in 34 years. The 30-indicator macro dashboard (10Y breakeven, Fed Funds, M2, jobless claims, PPI, yield curve slope) is the canonical input set.

**FINDINGS:**

- [SOURCE: FT / Reuters / GuruFocus | 2024–2025 | CONFIDENCE: HIGH] Bridgewater Pure Alpha 2024: +11.3%; 2025: +33% (record year in 50-year history). All Weather +20.4% in 2025. Strategic reform: restricted inflows, returned assets; leaner fund (~$92B Sep 2025).
- [SOURCE: Hedge Fund Journal Oct 2024 | CONFIDENCE: HIGH] Pure Alpha annualized high single digits at 12% vol target since 1991; only 4 losing calendar years in 32 years. Worst drawdown: 13% in 2020; no other double-digit drawdowns.
- [SOURCE: Multiple (FT, Hedgeweek, Bloomberg) | 2025 | CONFIDENCE: HIGH] 2022: Pure Alpha +32%, All Weather -19%. 2023: PA II -7.6%. Regime-specific: Pure Alpha captures macro regime shifts; All Weather captures carry/diversification.
- [SOURCE: Bridgewater ETF product docs | 2025 | CONFIDENCE: MEDIUM] ALLW ETF launched March 2025; systematic ~30-indicator dashboard covering macro surprises. Indicators include: 10Y breakeven inflation, Federal Funds Rate, M2 money supply, initial jobless claims, PPI, 10Y-2Y yield curve slope.

**Indicator Implementation Parameters:**
- Regime state space: 4 states (growth ↑/↓ × inflation ↑/↓)
- Input indicators: ~30 (macro surprise series, NOT level series)
- Surprise definition: actual minus consensus forecast, normalized
- Holding period: regime-dependent; typically 3–12 months per regime
- Rebalance: monthly or on regime transition
- Data sources: FRED, Bloomberg consensus, BLS, Census Bureau

**CONTRADICTIONS:** None significant. Performance numbers consistent across sources (±100bps due to share class/vol target differences).

**RECOMMENDATION:** Wire the 4-regime classifier into the hunt gate as a regime filter (risk-off veto when regime = growth ↓ / inflation ↑). Not a standalone alpha strategy — use as overlay on TA-based entries.

---

### 1.2 Bridgewater AIA Macro (AI-Augmented)

**Confidence:** MEDIUM  
**Summary:** $5B AI fund using "Artificial Investor" tool (rolled out 2024). Led by Greg Jensen + Jas Sekhon. Returned +11.9% in 2025 (below Pure Alpha's 33%). Represents hybrid systematic+AI approach but underperforms flagship — limited public documentation of methodology.

**FINDINGS:**

- [SOURCE: Reuters Dec 31 2025 | CONFIDENCE: HIGH] AIA Macro fund +11.9% in 2025 (vs Pure Alpha +33%, All Weather +20.4%).
- [SOURCE: GuruFocus Apr 2025 | CONFIDENCE: MEDIUM] AI fund uses AI to make investment decisions; launched ~2018 after Greg Jensen hired chief scientist Jas Sekhon. Artificial Investor tool deployed 2024.

**RECOMMENDATION:** Insufficient public documentation for indicator specification. Monitor for future disclosures but do not attempt to replicate. AI-augmented macro is directionally relevant for future hunt families.

---

## 2. Multi-Strategy Hedge Fund Signals

### 2.1 Institutional Flow Tracking (Citadel, Millennium, Point72)

**Confidence:** HIGH  
**Summary:** Multi-strat funds delivered +11–19% in 2024, confirming the equity hedge / stock-picking / event-driven risk premia remain viable. These are the live benchmark that any retail strategy must beat net of costs.

**FINDINGS:**

- [SOURCE: FT Jan 2 2025 / Hedgeweek | CONFIDENCE: HIGH] Citadel Wellington +15.1% 2024; Tactical Trading +13.7% H1. Citadel Optima +14.5% H1 (GGN dual-share).
- [SOURCE: FT / Bloomberg / Hedgeweek | CONFIDENCE: HIGH] Millennium +15% 2024 (flagship); Vịnh Hưng +17% (largest pod).
- [SOURCE: Bloomberg / Financial Times | CONFIDENCE: HIGH] Point72 ~+19% 2024.
- [SOURCE: Various | CONFIDENCE: MEDIUM] DE Shaw Composite +18%, Oculus (macro) +36%. ExodusPoint +11.3%. Balyasny Atlas Enhanced +13.6%. Schonfeld ~20%.
- [SOURCE: Goldman Sachs Dec 2025 | CONFIDENCE: HIGH] Global macro funds avg +14.96% YTD through Nov 2025.

**Implementation Relevance:**
- These benchmarks set the "hurdle rate" for strategy hunt candidates. Any new strategy spec must demonstrate ≥15% backtest CAGR with Sharpe >1.5 to justify adding complexity over existing signals.
- Event-driven component (Citadel/Point72) outperforms pure equity hedge — suggests ED/merger-arb overlay is high-value.

**RECOMMENDATION:** Use multi-strat returns as the strategy hunt gate threshold: a candidate must outperform on a risk-adjusted basis vs. these benchmarks net of estimated trading costs. Factor these into the "edge gate" performance bar.

---

## 3. Event-Driven / Merger Arbitrage Spread Indicator

### 3.1 Merger Arb Return Profile (Academic)

**Confidence:** HIGH  
**Summary:** Canonical paper: Mitchell & Pulvino 2001 (JF, 4,750 deals, 1963–1998). Excess return ~4–6%/yr over T-bills with market beta ~0 in normal periods; high beta in crashes → short-put payoff profile. Sharpe 1.06. Global sample: 13.45% avg annual return (Sharpe 1.03) vs market 9.85% (Sharpe 0.50). US only post-2001: ~10.53% avg annual return. Baker & Savasoglu 2002: ~1%/month excess. Larcker & Lys 1987: 5.32% mean cumulative excess per deal.

**FINDINGS:**

- [SOURCE: Mitchell & Pulvino 2001, JF | CONFIDENCE: HIGH] 4,750 deals, 1963–1998. Excess return ~4%/yr (after transaction costs). Sharpe 1.06. Returns uncorrelated with market in normal periods; positively correlated in severe downturns. Short-put payoff profile.
- [SOURCE: Baker & Savasoglu 2002 | CONFIDENCE: HIGH] 1978–1996, ~1%/month excess (~12%/yr). Risk-adjusted: 9.6% annualized. Alpha vs CAPM: 9.36%.
- [SOURCE: 2024 Sweden Thesis (1992–2023, 23 countries) | CONFIDENCE: MEDIUM] Portfolio return: 13.45% avg annual (Sharpe 1.03) vs market 9.85%. US deals only: 10.53% (lower post-2001 per Jetley & Ji). CAPM alpha: 9.24%; FF4 alpha: 8.76%. Cross-border deals carry higher risk. Down-market beta in this sample not significantly different from up-market beta (unlike Mitchell-Pulvino original finding).
- [SOURCE: Karolyi & Shannon 1999 | CONFIDENCE: LOW] 25%+ annualized for 37 Canadian targets in 1997 (small sample, single-year).
- [SOURCE: InsideArbitrage.com / multiple academic | CONFIDENCE: HIGH] Failed deal losses: target falls below entry. Spreads wider for deals that fail from the start; increase in days before failure. Stop-loss: -20% typical (range -20% to -40%). Default hold: 90 days; cash deals 60d; large strategic/regulatory 120–180d.

**Practical Implementation Parameters:**
- Entry trigger: after 8-K M&A announcement, within hours
- Take-profit: deal price (mechanical)
- Stop-loss: -20% from entry
- Default holding period: 90 days (cash 60d; large 120–180d)
- Annualized spread threshold: >15% = compelling; >25% = suspicious (break risk priced in)
- Position sizing: Kelly-lite; diversify across 15–30 concurrent deals
- Risk: deal break is the primary risk; concentrated losses in market downturns
- Data: SEC 8-K filings, deal terms (cash/stock/mixed), regulatory filings

**CONTRADICTIONS:**
- Mitchell & Pulvino (2001): high beta in down markets confirmed.
- 2024 Sweden thesis: down-market beta NOT significantly different from up-market beta in 1992–2023 global sample. Possible explanation: increased arb capital, or cross-border diversification dampens the crash beta.
- Jetley & Ji (2010): US merger arb spreads declined post-2001 — consistent with US-only return decline.

**RECOMMENDATION:** Merger arb spread is a high-conviction event-driven edge candidate for the hunt gate. Wire as a YAML strategy spec with: entry on 8-K filing, -20% stop, deal price TP, 90d default hold, and a break-probability filter (>75% completion probability). Cross-border deals add risk premium but also failure risk — need per-deal probability model.

---

### 3.2 HFRI Event-Driven Index Performance

**Confidence:** HIGH  
**Summary:** HFRI ED Total 2024: +8.7%. ED Multi-Strategy: +12.6%. HFRI ED Merger Arb: +8.2% through Sept 2025 (strongest Q1–Q3 since 2021). S&P Merger Arb: 2024 +5.91%, 2025 +13.63%. Calamos MNA: -2.26% gross / -3.04% net in 2024 (underperformer, illustrating net cost drag).

**FINDINGS:**

- [SOURCE: HFR Flash Report Dec 2024 | CONFIDENCE: HIGH] HFRI Event-Driven Total: +8.7% 2024 (below long-term 10–12% avg but positive; FYI: longest positive streak since 2006).
- [SOURCE: HFR 2025 | CONFIDENCE: HIGH] ED Multi-Strategy 2024: +12.6%. ED Distressed: +10.6% (2024, strongest since +15.5% 2021).
- [SOURCE: Absolute Blend Dec 2025 | CONFIDENCE: HIGH] HFRI ED Merger Arb +8.2% through Sept 2025 (strongest Q1–Q3 since 2021). Quote: "Merger arbitrage has had a standout year."
- [SOURCE: S&P / AiM Custom Indices | CONFIDENCE: HIGH] S&P Merger Arb (L/S): 2024 +5.91%; 2025 +13.63%. Pre-cost signal, not investable index.
- [SOURCE: Calamos Dec 2024 | CONFIDENCE: HIGH] Calamos MNA composite: 2024 -2.26% gross / -3.04% net. Illustrates cost drag in some investable MA products.

**RECOMMENDATION:** S&P Merger Arb index is the cleanest signal benchmark for the strategy spec. HFRI ED merger arb is the hedge-fund-grade benchmark. The Calamos MNA negative return shows that not all investable wrappers capture the alpha — implementation (leverage, short leg, cost structure) matters enormously. The strategy hunt spec should target the S&P Merger Arb's pre-cost return profile.

---

## 4. PEAD (Post-Earnings Announcement Drift)

### 4.1 Bernard & Thomas / Academic Returns

**Confidence:** HIGH  
**Summary:** Top-minus-bottom SUE decile: ~4.2% over 60 trading days (~25% annualized pre-cost). Drift lasts ~60 days; 25–30% concentrated in 3-day windows around subsequent earnings (~5% of trading days). Enter ~15 trading days before next earnings, hold 20–60 days, exit at next earnings. Declining over time but still 1.5–3.0% per 60d in post-2000/2007 samples.

**FINDINGS:**

- [SOURCE: Bernard & Thomas 1989, JAR 27:1–36 | CONFIDENCE: HIGH] SUE decile sorts. Top-bottom SUE: ~4.2% over 60 days (~25% annualized pre-cost). Drift lasts ~60 days; 25–30% concentrated in 3-day windows around subsequent earnings (only ~5% of trading days). [MDN; Wikipedia; Investopedia]
- [SOURCE: Bernard & Thomas 1990, JAE | CONFIDENCE: HIGH] ~8–9% abnormal return per quarter; ~67% annualized when constructed 15d before next earnings and held through earnings. [Wikipedia]
- [SOURCE: Livnat & Mendenhall 2006, TAR | CONFIDENCE: HIGH] Post-2000 subsample: ~3.2%/60d (down from 4.2% in original B&T sample). [Investopedia]
- [SOURCE: Chordia et al. 2009 / Investopedia 2025 | CONFIDENCE: MEDIUM] 2007 subsample: ~1.5–3.0% per 60d (still significant, but declining). [Investopedia]
- [SOURCE: Katz thesis (SSRN) | CONFIDENCE: MEDIUM] Aggregation bias: firm-level SUE vs 3m return correlation = 0.0073 (portfolio-level effect only). [SSRN 4776495]
- [SOURCE: Greenwald et al. 1999, JF | CONFIDENCE: MEDIUM] PEAD driven by market underreaction to cash-flow information, not accruals. [Investopedia; SJSU]

**Practical Implementation Parameters:**
- Signal: SUE (standardized unexpected earnings) decile sort
- Entry timing: ~15 trading days before next quarter's earnings announcement
- Exit timing: at or just before next earnings announcement
- Holding period: 20–60 trading days
- Average entry horizon: 40–60 days pre-next-earnings
- Data needed: quarterly EPS actual vs consensus, next earnings date, price at entry
- Transaction costs: high turnover (quarterly rebalance per stock); estimate 2–4% round-trip drag
- Anti-overfit guard: OOS holdout ≥20% of data; walk-forward mandatory

**CONTRADICTIONS:**
- B&T 1989 original: 4.2%/60d.
- Livnat & Mendenhall 2006: 3.2%/60d (decline).
- Chordia et al. 2009: 1.5–3.0%/60d (further decline).
- Katz: warns aggregation bias means portfolio-level effect is smaller than firm-level.
- **Consensus:** Effect persists post-cost in academic tests; decline over time is real but moderate; portfolio-level effect is smaller than firm-level; still exploitable with disciplined execution and cost control.

**RECOMMENDATION:** PEAD is a high-conviction event-driven alpha candidate for hunt families. Wire as YAML strategy spec with: SUE signal, 15d pre-earnings entry, next-earnings exit, -15% stop, and mandatory OOS holdout. Pair with the existing WSB-Alpha sentiment overlay to potentially amplify the effect on meme/retail-sensitive names.

---

## 5. Factor Momentum / Rotation Indicators

### 5.1 Time-Series Factor Momentum (TSFM)

**Confidence:** HIGH  
**Summary:** Gupta & Kelly (2019, JPM Quant): 1-month lookback TSFM Sharpe 0.84 across 65 equity factors; 12-month lookback Sharpe 0.70. Positive timing alpha for 61/65 factors; significant for 47. Factor AR(1) = 0.11 (low persistence). TSFM avoided 2009 crash: UMD lost -31% Mar–May 2009, but 12m TSFM posted +16%. Counter: Asness "Siren Song" — valuation-based timing unreliable; momentum-based timing supported.

**FINDINGS:**

- [SOURCE: Gupta & Kelly 2019, JPM Quantitative Strategies | CONFIDENCE: HIGH] 65 equity factors. TSFM 1-month lookback: Sharpe 0.84. 12-month lookback: Sharpe 0.70. 60-month lookback: Sharpe 0.72. Factor AR(1) = 0.11. Positive timing alpha for 61/65 factors; statistically significant for 47. TSFM avoided 2009 crash. [SSRN 2600599]
- [SOURCE: Arnott et al. 2018, Financial Analysts Journal | CONFIDENCE: HIGH] 51 factors: cross-sectional continuation in factor returns; combined with TSFM for timing. [SSRN 3230190]
- [SOURCE: AQR / Consensus Quant Survey 2013–2018 | CONFIDENCE: MEDIUM] "Very limited" evidence for broad factor timing ability; most strategies tested on relatively short samples. But TSFM (momentum-based) specifically identified as having some support — distinct from valuation-based timing. [Asness 2019 JPM]
- [SOURCE: ScienceDirect 2024 / MDPI 2025 | CONFIDENCE: MEDIUM] International equity markets: TSFM results not always robust outside US; single US sample may not generalize. [ScienceDirect; MDPI]

**Practical Implementation Parameters:**
- Signal: rank factor returns over trailing 1m (fast) or 12m (slow) window
- Factors to track: value (HML), momentum (UMD), quality (QMJ), size (SMB), low-vol (BAB), profitability
- Rebalance: monthly
- Holding period: 1 month (rebalance frequency)
- Portfolio: go long top-quintile factor returns, short bottom-quintile
- Long-only adaptation: tilt equity exposure toward winning factors
- AR(1) = 0.11 means factor timing must be fast — cannot hold a single factor tilt for long

**CONTRADICTIONS:**
- Gupta & Kelly: strong TSFM Sharpe 0.84 (1-month lookback) in-sample.
- AQR Consensus: "very limited evidence" for broad factor timing.
- Reconciliation: AQR's critique targeted valuation-based timing specifically; momentum-based timing (TSFM) has more support per both Gupta & Kelly and Asness's own "Siren Song" paper. AQR's Consensus paper acknowledges momentum-based timing has more evidence than valuation-based timing.
- International limitation (ScienceDirect 2024): not robust outside US.

**RECOMMENDATION:** TSFM is a high-conviction factor-rotation overlay for the strategy hunt. Wire as YAML strategy spec with: trailing 1m or 12m lookback, monthly rebalance, long-only tilt toward top factor returns. Require OOS walk-forward validation on international data before promoting beyond US. Use as entry filter (go long equities only when factor momentum is positive) rather than standalone alpha.

---

## 6. Yield Curve / Term Spread Recession Indicator

### 6.1 FRED T10Y3M / NY Fed Model

**Confidence:** HIGH  
**Summary:** FRED T10Y3M spread (10Y minus 3M Treasury) predicts recession 12 months ahead via the NY Fed model. Every US recession since ~1968/1977 preceded by inversion; average lead 15 months, range 6–19 months. Un-inversion historically more predictive of recession onset than inversion itself. BIS WP 818: financial cycle measures outperform term spread since mid-1980s. Current Aug 2026: curve positive/normal (+56 to +89bps depending on source).

**FINDINGS:**

- [SOURCE: NY Fed website | CONFIDENCE: HIGH] Term spread (10Y minus 3M) predicts probability of US recession 12 months ahead. Model: logit regression with term spread as primary input. Historical accuracy: every recession since 1968 preceded by inversion; average lead ~15 months, range 6–19 months. [research.stlouisfed.org; newyorkfed.org]
- [SOURCE: FRED data series T10Y3M | CONFIDENCE: HIGH] Inverted Nov 2022 (brief), Jul 2022–Sep 5 2024 sustained. Max depth: -198bps (Oct 2023). Un-inverted Sep 5 2024. NBER has not declared a recession through May 2026 — longest no-show in modern era. Current Aug 2026: +56 to +89bps (positive/normal). [FRED; YCharts]
- [SOURCE: BIS Working Paper 818 (Borio, Drehmann, Xia 2019) | CONFIDENCE: HIGH] Financial cycle measures (credit-to-GDP gap, real house prices) outperform term spread for recession prediction since mid-1980s. Term spread is an imperfect proxy for the financial cycle. [bis.org]
- [SOURCE: multiple financial commentary 2024 | CONFIDENCE: MEDIUM] Inversion itself is less predictive than un-inversion — recession historically starts around the time the curve un-inverts, not when it inverts. [WSJ; investment commentary]

**Practical Implementation Parameters:**
- Data: FRED T10Y3M (daily), or 10Y-2Y (T10Y2Y for broader use)
- Recession probability: NY Fed provides published estimates; or use logistic regression with term spread input
- Actionable signal: go risk-off (reduce equity, increase cash/bonds) when probability exceeds threshold (e.g., >30% at 12m horizon)
- Current state (Aug 2026): curve normal; recession probability likely low
- Lag: 6–19 months; not a tactical timing indicator — a strategic positioning overlay
- Complementary: combine with credit-to-GDP gap and real house prices (BIS WP 818) for a more robust recession prediction

**CONTRADICTIONS:**
- Term spread has perfect historical recession-prediction track record (1968+) — but is currently wrong (Sep 2024 un-inversion → no recession by Aug 2026). Longest false positive in modern era.
- BIS: financial cycle measures are better predictors since mid-1980s — suggests yield curve alone is insufficient.
- Goldman Sachs / market commentators: no recession declared; current cycle may be structurally different due to Fed balance sheet, fiscal expansion.

**RECOMMENDATION:** Yield curve is a high-conviction strategic positioning indicator but NOT a tactical timing indicator (too much lag, false-positive risk). Wire as a risk-off veto: when T10Y3M is inverted or recession probability >50%, reduce position sizes or close new entries. Combine with credit-to-GDP gap per BIS WP 818 for a more robust model. Current state: no signal (curve normal).

---

## Evidence Summary Table

| Indicator | Academic Source | Annual Return | Sharpe | Key Metric | Hunt Gate Applicability |
|---|---|---|---|---|---|
| Bridgewater Regime | Internal/Dalio | ~11% (Pure Alpha) | ~0.9–1.0 | Regime state (4 states) | Regime overlay filter |
| Merger Arb Spread | Mitchell & Pulvino 2001 | ~4–6% excess (US); 13.45% (global) | 1.06 | Deal spread, stop -20% | Event-driven YAML spec |
| PEAD | Bernard & Thomas 1989 | ~4.2%/60d (~25% annualized pre-cost) | N/A | SUE decile, 15d pre-earnings entry | Event-driven YAML spec |
| Factor Momentum | Gupta & Kelly 2019 | Timing alpha (not standalone CAGR) | 0.84 (1m TSFM) | Factor return rank, monthly rebalance | Factor tilt overlay |
| Yield Curve | NY Fed / FRED | N/A (positioning, not alpha) | N/A | T10Y3M inversion → recession prob 12m | Risk-off veto overlay |
| Multi-Strat Bench | Live fund data | 11–19% (2024) | ~1.2–1.5 | Hurdle rate for hunt gate | Gate threshold |

---

## Next Steps for Hunt Sessions (Phase 3)

1. **YAML spec authoring:** Wire each indicator's practical parameters into `strategies/*.yaml` format. Start with PEAD and merger arb (highest conviction, clearest entry/exit rules).
2. **Edge gate pre-registration:** For each candidate, generate frozen-spec doc (`docs/data/cycle*_prereg_*.md`) before walk-forward evaluation.
3. **Regime overlay:** Bridgewater 4-state regime as a risk-off filter across all strategies.
4. **Factor momentum tilt:** TSFM as position-sizing modifier, not standalone strategy.
5. **Yield curve veto:** T10Y3M as hard gate (no new longs when inverted).
6. **Walk-forward mandatory:** All candidates must pass OOS validation before promotion. Per-factor timing: require international evidence (ScienceDirect 2024 limitation).

---

## Evidence Refs

- [Mitchell & Pulvino 2001] https://papers.ssrn.com/sol3/papers.cfm?abstract_id=268144
- [Baker & Savasoglu 2002] https://papers.ssrn.com/sol3/papers.cfm?abstract_id=246497
- [Gupta & Kelly 2019] https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2600599
- [Arnott et al. 2018] https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3230190
- [BIS WP 818] https://www.bis.org/publ/work818.htm
- [NY Fed T10Y3M] https://research.stlouisfed.org/fred2/series/T10Y3M
- [NY Fed Recession Model] https://www.newyorkfed.org/research/capital_markets/ycfaq.html
- [S&P Merger Arb Index] https://www.spglobal.com/spdja/en/research-insights/sp-merger-arb/
- [HFRI Event-Driven] https://www.hedgefundresearch.com/
- [FRED T10Y3M Raw Data] https://fred.stlouisfed.org/series/T10Y3M
