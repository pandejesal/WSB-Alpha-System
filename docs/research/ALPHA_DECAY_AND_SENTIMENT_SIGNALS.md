# Alpha Decay & NLP Sentiment Signals: Research Brief

**Date:** 2026-08-25  
**Purpose:** Inform hunt-factory strategy design, edge-gate parameters, and sentiment overlay spec for WSB-Alpha-System  
**Sources:** 20+ academic papers, industry reports, vendor analyses

---

## 1. Alpha Decay: How Fast Does Edge Erode?

### 1.1 Academic Estimates

| Source | Half-Life Estimate | Context |
|--------|-------------------|---------|
| INSEAD "Crowding and Factor Timing" (2024) | Not specified (structural) | Crowding has accelerated post-2015; factor crowding now largest alpha-decay driver |
| arxiv 2512.11913 "Disentangling Alpha Decay" (2025) | Hyperbolic: α(t) = K / (1 + λt) | Momentum shows clearest decay (R²=0.65); tightest decay curves for crowded factors |
| arxiv 2605.23905 "Alpha Decay as a Social Phenomenon" (2026) | **h(ϕ) = ln2 / [θ + δ(ϕ)]** | At ϕ≈0.7 (current AI adoption): **~18-month half-life**. Pre-AI was 5–7 years |
| Kulma & Meier (2024) via ZEW DP | Cited in multiple papers | α decays faster in crowded environments; log–log regime shift after 2015 |

**Key finding:** Alpha half-life has compressed from 5–7 years (pre-AI) to ~18 months at current adoption levels. Factor crowding (exposure correlation >0.30) now drives 35–60% of alpha degradation, up from 15–25% historically.

### 1.2 Crowding Effects on Decay

- **Pre-2015:** Individual alpha generation dominated; crowding was marginal
- **Post-2015:** Crowding drives 35–60% of alpha degradation (up from 15–25%)
- **Threshold:** Exposure correlation >0.30 → structural crowding regime
- **Speed:** Crowded factors half-life shrinks from 7 years to **6–18 months**
- **Asymmetry:** Crowded reversal → 1.7–1.8× higher crash probability (early-morning institutional selling is 8× larger during these events)
- **Concentration:** Alpha capture now concentrated in bottom 30% of assets by market cap (less crowded)
- **Causal link:** Crowding precedes reversal exits by one to two quarters

### 1.3 Decay as Social Process (New Model)

The 2026 paper (arxiv 2605.23905) introduces a novel framework treating alpha decay as an **information cascade** rather than purely statistical erosion:

- Decay modeled as social-diffusion, not market microstructure
- Competitive imitation across the financial network (not just arbitrage)
- Nonlinear diffusion dynamics interact with market microstructure
- Implication: **decay rate is itself a tradeable signal** — fast-decaying factors may be more crowded and thus prone to reversal

### 1.4 Implications for Hunt Factory

| Design Decision | Rationale |
|----------------|-----------|
| Edge-gate walk-forward window: **12–18 months max** | Matches current half-life; longer windows risk overfitting to stale edges |
| Factor crowding check mandatory | Reject any strategy whose signals correlate >0.30 with existing strategies |
| OOS holdout: **minimum 3 months** | Must capture decay within the half-life window |
| Re-evaluation cadence: **quarterly** | 18-month half-life means edges can flip in 2 quarters |
| Prefer less-crowded universes | Bottom 30% by market cap; avoid mega-cap factor overlap |
| Register decay parameters in registry.json | Track expected half-life per strategy family |

---

## 2. NLP Sentiment Signals: What Works

### 2.1 Institutional-Grade Sentiment (Earnings Calls)

**Paper:** "Leveraging Sentiment in Earnings Calls for Market Predictions" (arxiv 2604.13260)

- **Model:** FinBERT on 16,428 S&P 500 earnings call transcripts
- **OOS Spearman IC: 0.142** (robust across stratified splits)
- **Monthly L/S alpha: +2.03%** (5-factor adjusted, statistically significant)
- **Subsumes** traditional Loughran-McDonald dictionary approaches
- **Key insight:** Weak-form Efficient Market Hypothesis fails for textual information — markets exhibit **sluggish assimilation of soft information**
  - Price adjustment is **gradual** (not instantaneous)
  - Creates exploitable drift over days-to-weeks
  - Not fully priced even a month after release
- **Superiority:** Outperforms lexicon-based approaches; modern LLMs > FinBERT > Bag-of-Words > Loughran-McDonald

### 2.2 Reddit/WSB Sentiment Signals

#### Positive Results

**ICE/Reddit 5-Year Quintile Backtest (2020–2025):**
- Universe: 480 large-cap US stocks, ~957M Reddit posts/comments
- **Q5 (most negative sentiment change) → Q1 (most positive): L/S CAGR 1.85%, Sharpe 0.39**
- Q5 (contrarian short) CAGR 5.15%, Sharpe 0.42 — consistently outperformed
- Positive L/S spread in **5 of 6 calendar years**
- Strongest in 2021, stable 2021–2024, weak 2025 (tariff volatility)
- **Practical:** Daily rebalancing, z-scored sentiment change, minimum 60 mentions/day

**WSB vs Investment Banks (Buz & de Melo, 2024):**
- 1.6M WSB posts over 3.5 years
- WSB average returns **compete with best investment banks**
- WSB outperformed almost all banks at detecting top-performing stocks
- Conclusion: WSB is a "freely accessible, valuable source of investment advice"

**BERTweet SVC Strategy (Goyal et al., 2025):**
- 2M+ Reddit comments, BERTweet model
- **Sentiment Volume Change (SVC)** metric: sentiment change × |comment volume change|
- SVC R²=0.1304 (after removing noise near origin, p<0.05)
- **2021: +84.4% over buy-and-hold; 2023: +70% over B&H**
- **2022 (bear market): mitigated losses by 4%** vs B&H

#### Negative/Contradictory Results

**ICCS 2025 (ChatGPT-annotated Reddit):**
- Fine-tuned RoBERTa on GME/AMC — sentiment **weakly correlated** with price
- **Volume of comments** and **Google Trends** were **stronger predictive signals** than sentiment
- Suggests: attention metrics > sentiment for meme stocks
- Bidirectional Granger causality: price drives discussion as much as discussion drives price

**Oxford "Is there good advice on WSB?" (2024):**
- **Overall WSB sentiment does NOT predict future returns** (except meme stocks GME/AMC)
- Activity **reactive** — large price changes precede forum activity
- DD posts: informative 2018–2020, **lost informativeness after 2021** (user influx degraded quality)
- Recommendation: "at best noise, at worst following it leads to worse performance"

**ZEW DP 25-040 (Controversy Effect):**
- Pre-announcement sentiment positively associated with CAR — **BUT only if uncontroversial**
- When sentiment sparks controversy (high peer-to-peer disagreement), association **turns negative**
- Mechanism: "normalizing behavior" — disagreement triggers corrective selling
- Implication: **controversy filter is essential** before using sentiment as signal

### 2.3 Synthesis: What Actually Works

| Signal Type | Predictive Power | Decay Rate | Practical for $100/mo? |
|-------------|-----------------|------------|----------------------|
| **FinBERT on earnings calls** | HIGH (IC=0.142, +2.03%/mo) | Gradual, weeks | Yes (transcripts free via SEC) |
| **Reddit SVC (sentiment × volume change)** | MEDIUM-HIGH (R²=0.13, +84% in 2021) | Days-to-weeks | Yes (Reddit API free) |
| **Reddit sentiment alone** | LOW-MEDIUM | Hours-to-days | Yes |
| **Comment volume / attention** | MEDIUM (surprisingly strong) | Hours | Yes |
| **Google Trends** | MEDIUM (stronger than sentiment) | Days | Yes (free) |
| **Controversy-adjusted sentiment** | MEDIUM-HIGH (conditional) | Days | Moderate (needs network analysis) |
| **DD post recommendations** | LOW (degraded post-2021) | Variable | Yes |
| **WSB institutional-quality DD** | MEDIUM (pre-2021 only) | Weeks | Yes |

### 2.4 Key Design Rules for Sentiment Overlay

1. **Never use raw sentiment alone** — always pair with volume change (SVC) or attention metrics
2. **Apply controversy filter** — if Reddit discussion is controversial, invert or neutralize the signal
3. **Earnings call sentiment has longest alpha** — sluggish assimilation means multi-week drift is tradeable
4. **Comment volume ≥ 60/day minimum** — below this, signal is noise
5. **Attention metrics (comment count, Google Trends) beat sentiment** for meme/volatile names
6. **Decay is fast** — Reddit signals have 1–7 day half-life; earnings call sentiment lasts weeks-to-months
7. **Bidirectional causality** — price moves drive discussion as much as discussion drives price; always check for reverse causation in backtests

---

## 3. Alternative Data Landscape

### 3.1 Market Size and Adoption

| Metric | Value | Source |
|--------|-------|--------|
| Global alt-data market | **>US$15 billion** (2025) | Lowenstein Sandle 2025 Survey |
| Private fund managers using alt-data | **~90%** (up from 67% prior year) | Lowenstein Sandle 2025 |
| Budget allocation >$1M/year | **>2/3** of alt-data users | Lowenstein Sandle 2025 |
| Historical market size | US$11.6B (2023), US$13.7B (2024), US$16.8B (2025) | Fortune Business Insights |
| 2025 alt-data spend (est.) | US$8.4B | Research and Markets |

### 3.2 Cost Tiers

| Tier | Cost Range | Data Types | Our Feasibility |
|------|-----------|------------|----------------|
| **Institutional** | $150K–$1.5M/year | Satellite imagery, credit card transactions, IoT sensors, web scraping (Bloomberg, Eagle Alpha, Quandl) | No |
| **Mid-tier** | $10K–$150K/year | News sentiment APIs, social media analytics (RavenPack, Sentifi, StockTwits Pro) | Stretch |
| **Retail/Prosumer** | $0–$5K/year | yfinance, FRED, Reddit API, SEC EDGAR, Google Trends, Finviz | **Yes — our target** |
| **Free/Open** | $0 | Public data, NLP on free sources | **Yes — primary** |

### 3.3 What Institutional Players Actually Use

From the survey (241 qualified respondents):
- **94%** prefer alternatives to traditional financial data for investment insights
- **88%** view combining alt-data with traditional financial data as key to success
- **30%** of asset owners expanded budgets specifically for sustainability/climate-related alt-data
- Top use cases: due diligence, investment signals, risk management, thematic research

---

## 4. Retail Proxy Toolkit (Under $100/month)

### 4.1 Free Data Sources

| Source | Data Type | API/Access | Rate Limits |
|--------|-----------|------------|-------------|
| **yfinance** | Price, fundamentals, options chain | Python library | No formal limits (be gentle) |
| **FRED** | 800K+ economic time series | Free API key | 120 req/min |
| **SEC EDGAR** | 10-K, 10-Q, 8-K, insider filings | Full-text search API | 10 req/sec |
| **Reddit API** | WSB posts, comments, sentiment | OAuth (100 OOB apps) | 100 req/min |
| **FinViz** | Screeners, fundamentals, news | Web scraping or Elite ($29/mo) | Varies |
| **Google Trends** | Search volume index | pytrends library | Unofficial, rate-limited |
| **Alpha Vantage** | Price, fundamentals, news | Free tier: 25 req/day | 5 req/min free |
| **Polygon.io** | Real-time/delayed prices | Free tier: 5 req/min | Free tier limited |
| **Quiver Quant** | Government contracts, WSB, insider | Free tier available | Limited |
| **OpenInsider** | Insider trading (Form 4) | Free scraping | N/A |
| **Unusual Whales** | Options flow (summary) | Free tier | Limited |

### 4.2 NLP/Sentiment Tools (Free)

| Tool | Best For | Cost | Quality |
|------|---------|------|---------|
| **FinBERT** (ProsusAI) | Financial text sentiment | Free (HuggingFace) | HIGH for formal text |
| **BERTweet** (vinai) | Social media / WSB sentiment | Free (HuggingFace) | HIGH for informal text |
| **VADER** | Quick sentiment baseline | Free (pip install) | MEDIUM |
| **RoBERTa (fine-tuned)** | Custom domain adaptation | Free (HuggingFace) | HIGH after fine-tuning |
| **TextBlob** | Simple polarity/subjectivity | Free | LOW-MEDIUM |
| **spaCy + custom NER** | Entity extraction from news | Free | HIGH with customization |

### 4.3 Recommended Stack for WSB-Alpha-System

**Monthly cost: ~$0–30**

```
Data Layer (free):
├── yfinance         → price + fundamentals
├── FRED API         → macro regime signals  
├── Reddit API       → WSB sentiment + volume
├── SEC EDGAR        → earnings transcripts, insider
├── Google Trends    → attention proxy
└── FinViz (free)    → screener + news

NLP Layer (free):
├── FinBERT          → earnings call sentiment
├── BERTweet         → Reddit/social sentiment  
├── SVC metric       → sentiment × volume change
└── Controversy filter → network disagreement detection

Signal Layer:
├── Attention metrics (comment count, search volume)
├── Sentiment change (z-scored daily)
├── Insider cluster buying/selling
└── Macro regime overlay (FRED-based)
```

---

## 5. Factor Crowding and Decay Implications

### 5.1 Crowding Detection Methods

From INSEAD (2024) and arxiv 2512.11913:

| Method | What It Detects | Threshold |
|--------|----------------|-----------|
| **Exposure correlation matrix** | Positional overlap across strategies | >0.30 = structural crowding |
| **Factor return correlation** | Co-movement in factor returns | High positive = crowded |
| **Fund flow analysis** | Capital chasing same factors | Concentrated flows = risk |
| **Institutional order imbalance** | Early-morning selling pressure | 8× larger in crowded reversals |
| **Short interest concentration** | Crowded short positions | High = squeeze risk |
| **Alternative data usage rates** | Same signals, many users | Survey-based, lagging |

### 5.2 Implications for Strategy Design

1. **Diversify signal types, not just assets** — same signal across many assets = factor crowding
2. **Prefer idiosyncratic signals** — company-specific events (earnings, insider activity) less crowded than factor bets
3. **Track strategy correlation** — if new strategy correlates >0.30 with existing, reject or combine
4. **Monitor crowded reversal risk** — when factor is crowded, add reversal detection
5. **Counter-cyclical contrarianism** — buy fear, sell greed; contrarianism underperforms short-term but outperforms long-term (INSEAD finding)

---

## 6. Actionable Recommendations for WSB-Alpha-System

### 6.1 Hunt Factory Edge-Gate Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Walk-forward window | 12–18 months | Matches alpha half-life |
| OOS holdout | 3+ months minimum | Must capture decay within half-life |
| Crowding check | Required | Reject if exposure corr >0.30 |
| Permutation test | Required | Min 100 permutations |
| Deflated Sharpe | Required | Account for multiple testing |
| Decay monitoring | Quarterly re-evaluation | Track half-life per strategy |
| Universe preference | Bottom 30% market cap | Less crowded |
| Strategy correlation | <0.30 with existing | Factor diversification |

### 6.2 Sentiment Overlay Spec (YAML Template)

```yaml
id: sentiment-overlay-v1
name: WSB Sentiment Overlay
type: overlay
inputs:
  - source: reddit_api
    subreddit: wallstreetbets
    metrics: [sentiment_change, comment_volume, controversy_score]
  - source: google_trends  
    metrics: [search_volume_change]
  - source: sec_edgar
    metrics: [earnings_sentiment_finbert]
filters:
  min_mentions_per_day: 60
  controversy_threshold: 0.5  # invert signal if above
  attention_gate: comment_volume > 2σ
signals:
  primary: sentiment_volume_change  # SVC metric
  secondary: attention_zscore
  tertiary: earnings_drift
combining_method: weighted_average
weights:
  primary: 0.5
  secondary: 0.3
  tertiary: 0.2
decay_estimate:
  half_life_days: 3  # Reddit signals
  re_evaluate: quarterly
risk_budget:
  max_position_pct: 2.0
  max_sector_exposure: 20.0
  correlation_cap: 0.30  # vs existing strategies
```

### 6.3 Implementation Priority

| Priority | Task | Why |
|----------|------|-----|
| **P0** | Wire FinBERT for earnings calls | Highest alpha, longest decay, free |
| **P0** | Build SVC metric from Reddit API | Proven +84% over B&H in 2021 |
| **P1** | Add controversy filter | Prevents signal inversion |
| **P1** | Google Trends attention proxy | Simple, strong, free |
| **P2** | Insider cluster detection (SEC EDGAR) | Low correlation to sentiment |
| **P2** | Macro regime overlay (FRED) | Risk-off gating |
| **P3** | Options flow (Unusual Whales free tier) | Complementary signal |

---

## 7. Key Caveats and Risks

1. **Survivorship bias in alt-data** — vendors overstate performance; always check methodology
2. **Capacity limits** — retail-grade signals may not survive at institutional scale (not our problem yet)
3. **Reddit API degradation** — API access increasingly restricted; have fallback (web scraping)
4. **Sentiment model drift** — WSB slang evolves rapidly; fine-tune models quarterly
5. **Transaction costs** — ICE backtest assumed 0 bps; daily rebalancing has real costs
6. **Regime dependency** — sentiment signals strongest in trending markets, weak in range-bound (2025 tariff period underperformed)
7. **Bidirectional causality** — price moves drive discussion; must test for reverse Granger causation

---

## Appendix: Source References

| ID | Source | Title | URL |
|----|--------|-------|-----|
| 1 | INSEAD (2024) | Crowding and Factor Timing | https://www.insead.edu/faculty-research/research-institute/finance-governance/crowding-factor-timing |
| 2 | arxiv 2512.11913 | Disentangling Alpha Decay in Financial Markets (2025) | https://arxiv.org/abs/2512.11913 |
| 3 | arxiv 2605.23905 | Alpha Decay as a Social Phenomenon in Modern Financial Markets (2026) | https://arxiv.org/abs/2605.23905 |
| 4 | arxiv 2604.13260 | Leveraging Sentiment in Earnings Calls for Market Predictions (2026) | https://arxiv.org/abs/2604.13260 |
| 5 | ICE (2026) | Backtesting a Reddit-derived Strategy Using ICE Signals and Sentiment Data | https://www.ice.com/insights/backtesting-a-reddit-derived-strategy-using-ice-signals-and-sentiment-data |
| 6 | Buz & de Melo (2024) | Democratisation of Retail Trading: Reddit WSB vs Investment Bank Analysts | https://ideas.repec.org/a/taf/tjbaxx/v7y2024i4p256-272.html |
| 7 | Goyal et al. (2025) | Leveraging Social Media Sentiment for Predictive Investment Decisions (BERTweet/SVC) | https://arxiv.org/pdf/2508.02089 |
| 8 | ICCS (2025) | Predicting Stock Prices with ChatGPT-Annotated Reddit Sentiment | https://www.iccs-meeting.org/archive/iccs2025/papers/159090292.pdf |
| 9 | ZEW DP 25-040 | Social Media Attention and Reddit Earnings Announcement Returns | https://www.zew.de/fileadmin/FTP/dp/dp25040.pdf |
| 10 | Oxford (2024) | Is There Good Investment Advice on r/wallstreetbets? | https://ora.ox.ac.uk/objects/uuid:6f3c53d3-f0d6-4232-b3cf-bf1696b200f9 |
| 11 | ScienceDirect (2024) | Social Media Attention and Retail Investor Behavior (WSB HPR: -8.5%) | https://www.sciencedirect.com/science/article/pii/S1057521924006537 |
| 12 | Springer (2024) | One-Way Ticket to the Moon? NLP-Based Meme Stock Analysis | https://link.springer.com/article/10.1007/s13278-024-01273-2 |
| 13 | Lowenstein Sandle (2025) | Alternative Data Trends: Hedge Fund Survey | https://www.lowenstein.com/news-insights/alternative-data-trends-hedge-fund-survey |
| 14 | Tender Alpha (2024) | The Alternative Data Market: 2024 Figures Overview | https://www.tenderalpha.com/the-alternative-data-market-an-overview-new-figures-as-of-2024/ |
| 15 | Fortune Business Insights | Alternative Data Market Size Report | https://www.fortunebusinessinsights.com/alternative-data-market-108738 |

---

*Document generated by Research Agent. Review before integrating into strategy specs.*
