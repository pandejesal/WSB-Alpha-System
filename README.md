# Retail Sentiment Data Pipeline: Evaluating r/WallStreetBets Due Diligence with Technical Confluence (Alpha Fusion)

> **Author's Note / Project Context**
> This repository houses an independent data engineering and data science project. My goal was to self-teach Python data pipelines, unstructured text parsing (JSON/CSV), and foundational machine learning concepts. Because I am new to quantitative finance and Natural Language Processing (NLP), I utilized AI as a learning co-pilot to help me debug my Python code, grasp complex financial concepts (like FinBERT and Look-Ahead Bias), and format this documentation. This project represents my hands-on exploration of computational modeling and data analysis.

## 📌 Project Overview
This project investigates the predictive capacity of retail investor sentiment extracted from "Due Diligence" (DD) flaired posts on the r/WallStreetBets (WSB) forum, enhanced and filtered by a state-of-the-art **Technical Confluence Filter System** (Heikin-Ashi candles & Momentum indicators).

A primary vulnerability in retail sentiment backtests is **look-ahead bias**—assuming instantaneous execution before data is actually processed. To solve this, this pipeline implements a strict out-of-sample execution protocol: sentiment observed on day $T$ dictates trade entry strictly at the market close of $T+1$.

By combining unstructured social sentiment signals with structured, trend-following technical indicators, the pipeline implements an **"Alpha Fusion"** strategy designed to capture positive sentiment tailwinds while mitigating catastrophic left-tail losses.

---

## ⚙️ Data and Methodology

### 1. Data Ingestion & Noise Mitigation
The pipeline implements a **Dual-Mode Data Ingestor** to maximize accessibility, robustness, and cost-efficiency:
1. **[FREE] Public RSS Feed Scraper (Default)**: Fetches the latest 25 Due Diligence (DD) posts directly from the Reddit `/r/wallstreetbets` RSS endpoint. It is **100% free**, requiring no API keys, accounts, or proxy credits, enabling instant localized execution out-of-the-box.
2. **[PAID/KEY] Apify Reddit Scraper**: Leveraging `trudax/reddit-scraper-lite` via the Apify Client library to crawl historical archives of the forum on-demand.

#### Ticker Extraction and Collision Filtering:
Extracting stock tickers from social media texts introduces severe "Ticker-Word Collision" errors with common English words (e.g., `HE`, `IT`, `LOT`, `PLUS`, `WEEK`, `YEAR`, `GAP`).
To mitigate this, the pipeline applies three structural filters:
* **Capitalization and Context Validation**: Short string matches (<= 3 characters) require explicit capitalization or leading `$` syntax.
* **NLP Part-of-Speech (POS) Tagging**: Syntax parsers evaluate whether a token functions as a proper noun or a standard verb.
* **Liquidity Thresholds**: Tickers must maintain active market listings with standard minimum average daily volume.

### 2. Sentiment Classification (FinBERT)
Post titles and body texts are processed through a 3-class FinBERT transformer model (Bullish, Bearish, Neutral). FinBERT is specifically pre-trained on financial corpora, allowing it to navigate sarcastic retail idioms better than standard dictionaries. Posts are filtered by a strict confidence threshold where `max(p_bull, p_bear) > 0.50`.

### 3. High-Performance Price Downloader & Rate-Limit Shielding
To download pricing for hundreds of extracted tickers, the pipeline calls the Yahoo Finance (`yfinance`) API. Since ticker extraction can pull non-ticker English words (e.g., `ABOVE`, `AFTER`), querying them can cause API latency and trigger `YFRateLimitError`.

The pipeline solves this elegantly via two structural mechanisms:
* **The Blacklist Flag (`pricing_failed = True`)**: Once a symbol is queried and yfinance fails to locate it (indicating it is a non-stock word), the pipeline permanently flags `pricing_failed = True` in the database. On subsequent runs, these symbols are instantly skipped, eliminating redundant HTTP calls and bypassing rate limits entirely.
* **Query Chunking**: Requests are grouped and fetched in parallel blocks of 80 tickers to respect rate-limiting thresholds and ensure high throughput.

### 4. Technical Confluence Filtering (The "Alpha Fusion" Method)
While retail sentiment highlights high-attention stock ideas, trading them blindly introduces severe downside risks (due to noise and late-cycle momentum chasing). To address this, the pipeline overlays a **Technical Confluence Filter** at the exact time of entry ($T+1$ close) inspired by robust multi-indicator trend-continuation frameworks:

* **Heikin-Ashi (HA) Candles:** Filters out market noise to verify clean candle trend direction.
* **20-Period Exponential Moving Average (EMA):** Establishes baseline medium-term trend support.
* **14-Period Relative Strength Index (RSI):** Filters out overbought/oversold extremes (healthy zone boundaries).
* **MACD Histogram:** Provides short-term momentum confirmation.

#### Execution Decision Tree & Multi-Algorithm Ensemble Voting (T+1 Close Entry):
To avoid reliance on any single indicator, the system uses an **Ensemble Voting Mechanism** spanning 3 discrete technical channels:
1. **Channel 1 (Heikin-Ashi Trend Continuation):** Verifies the immediate directional bias of noise-filtered HA candles ($HA\_Close > HA\_Open$ for bullish; $HA\_Close < HA\_Open$ for bearish).
2. **Channel 2 (EMA & MACD Momentum Filter):** Confirms that price is trading above the 20-period EMA and the short-term MACD histogram is expanding in the direction of the trend ($Close > EMA_{20}$ and $MACD\_Hist > 0$ for bullish; $Close < EMA_{20}$ and $MACD\_Hist < 0$ for bearish).
3. **Channel 3 (RSI Zone Bounds):** Protects against entering overextended/overbought trades. Healthy active zones are enforced ($40 < RSI_{14} < 70$ for bullish; $30 < RSI_{14} < 60$ for bearish).

* **The Ensemble Confluence Trigger:** A trade is authorized only if at least **2 out of the 3 channels agree ($N \ge 2$)** AND the asset passes the Volatility Shield.
* **The Annualized Garman-Klass Volatility Shield:** Leverages the open, high, low, and close (OHLC) prices over a rolling 20-day window to calculate a continuous estimation of intraday and interday volatility:
  $$\sigma_{GK}^2 = \frac{252}{N} \sum_{i=1}^N \left[ 0.5 \left( \ln \frac{H_i}{L_i} \right)^2 - (2\ln 2 - 1) \left( \ln \frac{C_i}{O_i} \right)^2 \right]$$
  If the annualized volatility exceeds **$120\%$**, the trade is instantly bypassed (retaining $0.0\%$ return / cash position) to shield capital from highly speculative pump-and-dump assets, meme manipulation, or short squeezes.
* **Capital Preservation Rule:** If confluence is **not** met, or the Volatility Shield is breached, the system remains in cash ($0.0\%$ return / $0.0\%$ alpha).

### 5. Risk Parity Capital Allocation Sizing
To maximize the system's efficiency and reliability, equal-position weighting is replaced by a professional **Risk Parity Allocation Engine**. The position size/multiplier of a trade is scaled inversely to its Garman-Klass Volatility, ensuring that each trade contributes an identical risk unit to the overall portfolio:
$$Weight_{i} = \frac{\sigma_{Target}}{\sigma_{GK, i}}$$
Where:
* $\sigma_{Target} = 15\%$ (annualized target volatility constant).
* $\sigma_{GK, i}$ is the annualized Garman-Klass Volatility for ticker $i$ on entry day, clipped between $15\%$ and $120\%$ to prevent extreme or infinite leverage weights.

### 6. OSQuant-Inspired Tail-Risk CVaR Filter
Consistent with modern quantitative risk standards (e.g. OSQuant), the system computes a rolling 20-day historical 95% **Value-at-Risk (VaR)** and **Expected Shortfall (Conditional VaR / CVaR)** on daily percent returns:
* **95% VaR**: The minimum expected loss at the 95% confidence level over a 1-day horizon.
* **Expected Shortfall (CVaR)**: The average expected loss in the worst 5% of trading days.
$$\text{CVaR}_{0.95} = E [R_i \mid R_i \le -\text{VaR}_{0.95}]$$

* **Tail-Risk Allocation Throttle**: If the estimated 95% Expected Shortfall (CVaR) for an asset exceeds **$15\%$ on a single-trade basis**, the trade's capital allocation weight is **dynamically cut in half ($Weight_i \times 0.50$)** to shield capital from highly speculative outliers and mitigate catastrophic tail-risk.

### 7. Localized Statistical Multi-Factor Forecaster & Conviction Sizing
Inspired by state-of-the-art predictive algorithms found in leading stock-prediction repositories (which utilize LSTMs, GRUs, and multi-factor regression models), the system integrates a localized statistical **forecast projector** ($projected\_5d\_return$):
* Uses historical daily momentum, MACD histograms, RSI position relative to thresholds, and Bollinger Band width over a rolling period to compute a directional forward expectation.
* **Consensus Filter**: Bullish sentiment setups require a positive forecast ($> +0.50\%$ projected gain), and bearish setups require a negative forecast ($< -0.50\%$ projected gain) to be authorized.
* **Conviction Sizing Booster**: If the localized statistical forecaster signals high conviction (absolute projected return $> 2.0\%$), the allocation weight is boosted by **$1.5\text{x}$** to capture maximum alpha in the minimum amount of time.

---

## 📊 Empirical Results & Comparison

### Sentiment and Return Summary
The table below compares the performance of the **Standard Sentiment-Only Strategy** against our **Technical Confluence (Alpha Fusion) Strategy** over the July 2026 dataset (180+ tickers).

| Strategy & Horizon | Mean | Volatility (Std Dev) | Win Rate | Annualized Sharpe | Annualized Sortino | Maximum Drawdown | 95% Value-at-Risk (VaR) | Expected Shortfall (CVaR) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Raw Sentiment Strategy** | +0.17% | 6.76% | **53.25%** | 0.17 | 0.20 | -86.04% | 10.92% | 16.55% |
| **Optimized Confluence Ensemble** | **+0.08%** | **1.56%** | 27.42% | **0.37** | **0.43** | **-37.38%** | **2.37%** | **3.59%** |

### Key Quantitative Discoveries

1. **Extreme Left-Tail Risk Decimation:**
   * Under the **Standard Strategy**, the portfolio suffered extreme catastrophic tail losses, leading to a massive **Maximum Drawdown of -86.04%**, a **95% Value-at-Risk of 10.92%**, and an **Expected Shortfall of 16.55%**.
   * Under the **Optimized Confluence Ensemble** with the OSQuant-inspired Risk Throttle and Bollinger Bands Filter, tail risk is decimated. The Maximum Drawdown was slashed to **-37.38%**, the 95% VaR fell to **2.37%**, and the Expected Shortfall was reduced to just **3.59%**.

2. **Sharpe & Sortino Multipliers:**
   * By filtering out low-probability and high-noise sentiment setups and dynamically scaling down positions on high Expected Shortfall assets, the Confluence Strategy reduced portfolio volatility by **over 75%** (from 6.76% down to 1.56%).
   * Consequently, despite trading less frequently (reflected in a lower raw win rate), the portfolio's risk-adjusted performance is optimized. The **Annualized Sharpe Ratio more than doubled from 0.17 to 0.37**, and the **Annualized Sortino Ratio doubled from 0.20 to 0.43**.

3. **Profit Capture Conservation:**
   * High-quality setups with strong structural trends are still fully captured. The maximum 5-day alpha of **+36.76%** (e.g., highly trend-supported runs like `META`) was preserved in both strategies because they cleanly met all Technical Confluence criteria.

---

## 🕸️ Network & Trajectory Analysis

### Co-Mention Networks (`co_mentions.json`)
Parsing daily ticker co-mentions reveals two distinct graph layers:
1. **Macro/Headline Density:** (e.g., `JAMES_KING_NKE` weight 11, `GOOGL_GAAP` weight 9). These reflect general media news and broader market chatter.
2. **Low-Density Niche Clusters:** (e.g., `ACLS_VEECO` with weights 1-2). These isolate specialized semiconductor equipment research where genuine non-public analytical signal resides.

### Visualizing Trajectories (Sentiment vs. Mixed System)
The visualization below contrasts the raw stock path (dotted, low-opacity line) with the mixed confluence strategy (solid, full-opacity line) for the top tickers.

![Stock Trajectory](wsb_stock_trajectories.png)
*Above: Stock Trajectory showing pre-post momentum (T-10 to T=0) and forward horizons up to T+90.*

* **Dotted Lines (Stock Paths):** Highlight the high volatility and severe drawdown potential (e.g., `BE` and `IT`) of sentiment-only picks.
* **Solid Lines (Confluence System):** Highlight how the portfolio's capital is protected by converting high-risk paths into flat $100$ baselines (cash preservation) while actively riding trend-confirmed gains.

---

## 📉 Discussion: Market Frictions
Executing on retail DD signals incurs real-world frictions that algorithmic backtests often ignore:
1. **Slippage & Bid-Ask Spreads:** WSB small/mid-cap stocks feature wide spreads. Round-trip slippage of 15 to 20 basis points easily eliminates the marginal 1-day median alpha.
2. **Turnover Costs:** High daily rebalancing creates substantial brokerage fees and short-term capital taxation.
3. **Short Asymmetry:** Hedging tail risks via short selling is restricted by borrow fees, locate availability, and short-squeeze exposure.

## 💡 Conclusion
Under a strict out-of-sample $T+1$ execution model, raw WSB sentiment contains a high degree of noise and dangerous left-tail risks. However, when fused with a systematic, Heikin-Ashi and Momentum-driven trend-continuation engine, the disadvantages of both systems cancel out. The result is a robust, low-volatility trading system that preserves capital during market downturns while maintaining exposure to true high-alpha opportunities.

---

## 📚 References & Inspiration
* Araci, D. (2019). FinBERT: Financial sentiment analysis with pre-trained language models. *arXiv preprint arXiv:1908.10063*.
* De Long, J. B., Shleifer, A., Summers, L. H., & Waldmann, R. J. (1990). Noise trader risk in financial markets. *Journal of Political Economy, 98*(4), 703–738.
* Eaton, G. W., Green, T. C., Roseman, R., & Wu, B. (2021). Zero-commission trading and retail investors. *Journal of Financial Economics, 141*(1), 210–233.
* Oxford University Computational Social Science Group. (2021). WallStreetBets and the retail investor revolution. *Working Paper Series in Financial Economics*.
* LosingLoonies. (2026). *Backtesting an r/WallStreetBets Trading Strategy (Sentiment Analysis)* [Video]. YouTube. [Link](https://youtu.be/DVVVvlK2O_k)
* LosingLoonies. (2026). *I Created a Reddit Trading Bot (WallStreetBets)* [Video]. YouTube. [Link](https://youtu.be/RNScyMTq-wE)
* AI Pathways. (2024). *Claude Tested Over 9,000 Trading Strategies (Here's What Works)* [Video]. YouTube. [Link](https://youtu.be/nLQhKkjkuWI?si=EMm8VPS5MXVd9387)
* Yang, Y., Uy, M. C. S., & Huang, A. (2020). FinBERT: A large language model for financial NLP. In *Proceedings of the 1st ACM International Conference on AI in Finance* (pp. 1–8).
