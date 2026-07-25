# Retail Sentiment Data Pipeline: Evaluating r/WallStreetBets Due Diligence

> **Author's Note / Project Context**
> This repository houses an independent data engineering and data science project. My goal was to self-teach Python data pipelines, unstructured text parsing (JSON/CSV), and foundational machine learning concepts. Because I am new to quantitative finance and Natural Language Processing (NLP), I utilized AI (ChatGPT) as a learning co-pilot to help me debug my Python code, grasp complex financial concepts (like FinBERT and Look-Ahead Bias), and format this documentation. This project represents my hands-on exploration of computational modeling and data analysis.

## 📌 Project Overview
This project investigates the predictive capacity of retail investor sentiment extracted from "Due Diligence" (DD) flaired posts on the r/WallStreetBets (WSB) forum. 

A primary vulnerability in retail sentiment backtests is **look-ahead bias**—assuming instantaneous execution before data is actually processed. To solve this, this pipeline implements a strict out-of-sample execution protocol: sentiment observed on day $T$ dictates trade entry strictly at the market close of $T+1$.

Analyzing 180 unique ticker entities tracked in July 2026, the pipeline evaluates risk-adjusted forward performance against the SPY benchmark.

## ⚙️ Data and Methodology

### 1. Data Ingestion & Noise Mitigation
Textual data was scraped using a Python wrapper for Reddit (`trudax/reddit-scraper-lite`). Extracting stock tickers from social media texts introduces severe "Ticker-Word Collision" errors with common English words (e.g., `HE`, `IT`, `LOT`, `PLUS`, `WEEK`, `YEAR`, `GAP`). 
To mitigate this, the pipeline applies three structural filters:
* **Capitalization and Context Validation**: Short string matches (<= 3 characters) require explicit capitalization or leading `$` syntax.
* **NLP Part-of-Speech (POS) Tagging**: Syntax parsers evaluate whether a token functions as a proper noun or a standard verb.
* **Liquidity Thresholds**: Tickers must maintain active market listings with standard minimum average daily volume.

### 2. Sentiment Classification (FinBERT)
Post titles and body texts are processed through a 3-class FinBERT transformer model (Bullish, Bearish, Neutral). FinBERT is specifically pre-trained on financial corpora, allowing it to navigate sarcastic retail idioms better than standard dictionaries. Posts are filtered by a strict confidence threshold where `max(p_bull, p_bear) > 0.50`.

### 3. Mathematical Framework
For ticker $i$ on post day $t$, the pipeline calculates:
* **Raw Sentiment Score:** $S_{i,t} = Bullish_{i,t} - Bearish_{i,t}$
* **Oxford Volume Normalization:** $NS_{i,t} = S_{i,t} / (ForumTotalDD_t + \epsilon)$
* **Out-of-Sample Return (T+1 Close Entry):** $R_{i,t,d} = (P_{i, t+d} - P_{i, t+1}) / P_{i, t+1}$
* **Benchmark Excess Return (Alpha):** $\alpha_{i,t,d} = R_{i,t,d} - R_{SPY,t,d}$

---

## 📊 Empirical Results

### Sentiment and Return Summary
The table below summarizes the forward stock returns, benchmark returns, and benchmark-adjusted alpha across the dataset.

| Metric | Mean | Median | Std Dev | Min | Max |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Normalized Sentiment (NS) | 0.284 | 0.143 | 0.312 | -0.091 | 1.000 |
| 1-Day Stock Return | 0.08% | 0.11% | 3.42% | -25.00% | +10.65% |
| 1-Day SPY Return | 0.01% | 0.01% | 0.52% | -0.77% | +0.85% |
| **1-Day Alpha** | **+0.07%** | **+0.12%** | **3.38%** | **-24.23%** | **+0.21%** |
| 5-Day Stock Return | +0.01% | +0.82% | 8.91% | -50.00% | +35.21% |
| 5-Day SPY Return | +0.03% | +0.03% | 1.12% | -1.54% | +1.26% |
| **5-Day Alpha** | **-0.02%** | **+0.79%** | **8.85%** | **-48.46%** | **+36.76%** |

### Negative Skewness and Left-Tail Risks
A critical quantitative finding is the divergence between mean and median performance:
* At the 5-day horizon, **median alpha reaches +0.79%**, while **mean alpha drops to -0.02%**. 
* This confirms **negative skewness**: most posts precede minor gains, but severe left-tail drops drag the expected mean return below zero.
* **Case Studies:** Bullish DD posts on July 7, 2026, targeting `GAP` (+10.52% 5d return) and `META` (+12.96% 5d return) generated strong positive alpha. Conversely, `SONG` on July 9, 2026, suffered a catastrophic 5-day drawdown of -50.00%, completely wiping out dozens of positive trades.

---

## 🕸️ Network & Trajectory Analysis

### Co-Mention Networks (`co_mentions.json`)
Parsing daily ticker co-mentions reveals two distinct graph layers:
1. **Macro/Headline Density:** (e.g., `JAMES_KING_NKE` weight 11, `GOOGL_GAAP` weight 9). These reflect general media news and broader market chatter.
2. **Low-Density Niche Clusters:** (e.g., `ACLS_VEECO` with weights 1-2). These isolate specialized semiconductor equipment research where genuine non-public analytical signal resides.

### Trajectory and Momentum Analysis
![Stock Trajectory](wsb_stock_trajectories.png)
*Above: Stock Trajectory (entity 'IT') showing pre-post momentum (T-10 to T=0) and T+9 truncation.*

Evaluation of relative asset trajectories from $T-10$ to $T+90$ demonstrates significant pre-post volatility (dipping to 94.1 at $T-8$, rallying to 101.8 at $T=0$). This confirms retail authors predominantly publish DD posts **after** observing large price moves (momentum chasing). 

---

## 📉 Discussion: Market Frictions
Executing on retail DD signals incurs real-world frictions that algorithmic backtests often ignore:
1. **Slippage & Bid-Ask Spreads:** WSB small/mid-cap stocks feature wide spreads. Round-trip slippage of 15 to 20 basis points easily eliminates the marginal +0.12% 1-day median alpha.
2. **Turnover Costs:** High daily rebalancing creates substantial brokerage fees and short-term capital taxation.
3. **Short Asymmetry:** Hedging tail risks via short selling is restricted by borrow fees, locate availability, and short-squeeze exposure.

## 💡 Conclusion
Under a strict out-of-sample $T+1$ execution model, WSB Due Diligence sentiment exhibits localized selection capacity in niche clusters. However, left-tail risk and transaction costs prevent transformation of this signal into net profitable alpha, confirming retail sentiment functions primarily as a lagging momentum indicator.

---

## 📚 References & Inspiration
* Araci, D. (2019). FinBERT: Financial sentiment analysis with pre-trained language models. *arXiv preprint arXiv:1908.10063*.
* De Long, J. B., Shleifer, A., Summers, L. H., & Waldmann, R. J. (1990). Noise trader risk in financial markets. *Journal of Political Economy, 98*(4), 703–738.
* Eaton, G. W., Green, T. C., Roseman, R., & Wu, B. (2021). Zero-commission trading and retail investors. *Journal of Financial Economics, 141*(1), 210–233.
* Oxford University Computational Social Science Group. (2021). WallStreetBets and the retail investor revolution. *Working Paper Series in Financial Economics*.
* LosingLoonies. (2026). *Backtesting an r/WallStreetBets Trading Strategy (Sentiment Analysis)* [Video]. YouTube. [Link](https://youtu.be/DVVVvlK2O_k)
* LosingLoonies. (2026). *I Created a Reddit Trading Bot (WallStreetBets)* [Video]. YouTube. [Link](https://youtu.be/RNScyMTq-wE)
* Yang, Y., Uy, M. C. S., & Huang, A. (2020). FinBERT: A large language model for financial NLP. In *Proceedings of the 1st ACM International Conference on AI in Finance* (pp. 1–8).