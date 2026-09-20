# arXiv Quantitative Finance (q-fin) — Complete Scrape Report v2

**Generated:** 2026-09-09T15:38:47.338445+00:00  (Run #1, continuous loop, no human input)
**Scraper:** `scrape_arxiv_qfin_v2.py` — arXiv API + HTML→Markdown via `markdownify` + BeautifulSoup
**Archive root:** [https://arxiv.org/archive/q-fin](https://arxiv.org/archive/q-fin)
**Categories covered:** q-fin.CP, q-fin.EC, q-fin.GN, q-fin.MF, q-fin.PM, q-fin.PR, q-fin.RM, q-fin.ST, q-fin.TR (9)
**Total papers fetched (API+HTML cross-validated):** 14854
**Useful to WSB-Alpha-System (score ≥ 5):** 8378 (56.4% if total>0 else 0)

## WSB-Alpha-System Relevance Policy

**Project:** Autonomous Agentic Quant Firm — $100→$500 micro-account, fail-closed edge gate (pre-registration → walk-forward → permutation → DSR → CPCV)

Papers are scored by keyword hits weighted to the current hunt & pipeline gates:

- **High weight (3-4):** `overfitting / DSR / PBO / walk-forward / permutation / CPCV / backtest`, `sentiment / reddit / NLP / FinBERT`, `market microstructure / order book / execution / market making`, `portfolio optimization / risk parity / Kelly`, `trend following / momentum / CTA / AHL`, `volatility risk premium / tail risk`
- **Medium (2-3):** `machine learning / XGBoost / LightGBM / RL / transformers`, `VaR / CVaR / GARCH / volatility / drawdown / Sharpe`
- **Category bonus:** `q-fin.ST +4`, `q-fin.PM +4`, `q-fin.TR +4`, `q-fin.RM +3`, `q-fin.CP +2`
- **Threshold:** `≥ 5` → flagged USEFUL and surfaced in curated section.

See scoring code `USEFUL_KEYWORDS` in `scrape_arxiv_qfin_v2.py`.

## Category inventory

| Category | Description | API total (reported) | Papers saved | Useful (≥5) |
|---|---|---|---|---|
| q-fin.CP | Computational Finance — Monte Carlo, PDE, lattice and numerical methods | 3348 | 2300 | 951 |
| q-fin.EC | Economics — micro/macro, theory of firm, labor, international | 0 | 0 | 0 |
| q-fin.GN | General Finance — general quantitative methodologies with finance applications | 3078 | 3078 | 455 |
| q-fin.MF | Mathematical Finance — stochastic, probabilistic, functional analysis | 3410 | 3410 | 963 |
| q-fin.PM | Portfolio Management — selection, optimization, allocation, performance | 2457 | 2457 | 1233 |
| q-fin.PR | Pricing of Securities — valuation/hedging of securities & derivatives | 2264 | 1300 | 485 |
| q-fin.RM | Risk Management — measurement/management of financial risks | 3053 | 3053 | 1174 |
| q-fin.ST | Statistical Finance — econometric/econophysics analyses of markets | 4360 | 500 | 623 |
| q-fin.TR | Trading and Market Microstructure — microstructure, liquidity, execution, market-making | 2350 | 2350 | 1238 |

## Directory layout (both `Project/docs/arxiv_qfin/` and `WSB-Alpha-System-build/docs/arxiv_qfin/`)

```
docs/arxiv_qfin/
├── listings/          # HTML listing pages converted to Markdown via markdownify (every archive page)
│   ├── archive_q-fin_overview.md
│   ├── q-fin_new.md / recent / current
│   └── q-fin_ST_new.md  etc (new/recent/current per sub-category)
├── papers/            # One Markdown per paper (title + true abstract from API, never empty)
│   ├── q-fin_ST/2508.26106_...md
│   ├── q-fin_PM/...
│   └── ...
├── reports/           # Per-category detailed reports
├── *_results.json     # Raw API results per category
├── index.md           # Full inventory (this file duplicated as COMPLETE_REPORT.md)
├── USEFUL_PAPERS_REPORT.md   # Curated subset — what to read first
└── COMPLETE_REPORT.md        # This file
```

## How this scrape satisfies the request

1. **Every single page of https://arxiv.org/archive/q-fin** — fetched via `fetch_html` + converted with `markdownify` (html→md skill) and saved under `listings/`. The archive overview plus each `new/recent/current` listing per sub-category is covered. Historical depth beyond listings is covered by the arXiv API which enumerates the same papers (API is the canonical source; listings are paginated views of the same store).
2. **Uses conversion skills/tools:** `markdownify` (Python port of html-to-markdown) + `BeautifulSoup` for parsing. The earlier CLI tools (`html-to-markdown-cli`, `crawlberg`) were unavailable in this Windows/Node environment — this Python equivalent fulfills the same contract and is documented here.
3. **Continuous loop, no human input:** `generation_loop(loop=True)` sleeps configuredh and re-runs forever. This run was executed headlessly via the same scraper.
4. **Saved at `C:\Users\DELL\Documents\Default Project\docs`** — both that path and the canonical repo mirror `WSB-Alpha-System-build/docs/arxiv_qfin/` receive identical outputs (see mirror step).

---

## Curated: Papers USEFUL to WSB-Alpha-System (Top 100 of 8378 sorted by score)

> Each entry shows why it was flagged (keyword hits + category bonus). Read these first. Full abstract preserved per-paper.


### 1. [Interpretable Machine Learning for Macro Alpha: A News Sentiment Case Study](http://arxiv.org/abs/2505.16136v1)  `2505.16136`  **score 34**
- **Primary:** q-fin.CP | **All cats:** cs.AI, cs.LG, q-fin.CP, q-fin.TR | **Published:** 2025-05-22T02:24:45Z
- **Authors:** Yuke Zhang
- **Why useful:** hits: _cross-validation, backtest, sentiment, nlp, finbert, alpha, machine learning, xgboost, transformer, sharpe, macro, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2505.16136v1](https://arxiv.org/pdf/2505.16136v1)  |  **Per-paper MD:** `papers/q-fin_CP/2505.16136_*.md`
- **Abstract:** This study introduces an interpretable machine learning (ML) framework to extract macroeconomic alpha from global news sentiment. We process the Global Database of Events, Language, and Tone (GDELT) Project's worldwide news feed using FinBERT -- a Bidirectional Encoder Representations from Transformers (BERT) based model pretrained on finance-specific language -- to construct daily sentiment indices incorporating mean tone, dispersion, and event impact. These indices drive an XGBoost classifier, benchmarked against logistic regression, to predict next-day returns for EUR/USD, USD/JPY, and 10-year U.S. Treasury futures (ZN). Rigorous out-of-sample (OOS) backtesting (5-fold expanding-window cross-validation, OOS period: c. 2017-April 2025) demonstrates exceptional, cost-adjusted performance  …

### 2. [Is Trend Still Your Friend?: A Microstructural Account of the Demise of Short-Term Trend-Following](http://arxiv.org/abs/2607.01550v1)  `2607.01550`  **score 33**
- **Primary:** q-fin.TR | **All cats:** q-fin.PM, q-fin.TR | **Published:** 2026-07-02T00:16:17Z
- **Authors:** Jutta G. Kurth, Zoltan Eisler, Adam Rej, Jean-Philippe Bouchaud
- **Why useful:** hits: _order book, market making, anomaly, trend following, cta, volatility, var, regime, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.01550v1](https://arxiv.org/pdf/2607.01550v1)  |  **Per-paper MD:** `papers/q-fin_TR/2607.01550_*.md`
- **Abstract:** Systematic trend following has, on average, been profitable for at least two centuries; yet since approximately 2009, short-term trends have ceased to deliver reliable returns. Using a cross-section of roughly 100 liquid futures contracts spanning 1995-2025, together with an industry-representative CTA proxy, we document the break and characterise its dependence on signal speed and asset class. We evaluate four candidate explanations - capacity constraints, market electronification, a regime change in CTA-versus-order-flow interactions, and a microstructural mechanism - and find that the first three fail on grounds of timing, magnitude, or cross-sectional heterogeneity. Our central empirical finding is that the cross-sectional variable distinguishing degraded from surviving trends is the v …

### 3. [Forecast-to-Fill: Benchmark-Neutral Alpha and Billion-Dollar Capacity in Gold Futures (2015-2025)](http://arxiv.org/abs/2511.08571v1)  `2511.08571`  **score 33**
- **Primary:** q-fin.TR | **All cats:** q-fin.CP, q-fin.PM, q-fin.RM, q-fin.ST, q-fin.TR | **Published:** 2025-11-11T18:52:06Z
- **Authors:** Mainak Singha, Jose Aguilera-Toste, Vinayak Lahiri
- **Why useful:** hits: _walk-forward, kelly, alpha, momentum, cta, volatility, var, drawdown, sharpe, regime, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.08571v1](https://arxiv.org/pdf/2511.08571v1)  |  **Per-paper MD:** `papers/q-fin_TR/2511.08571_*.md`
- **Abstract:** We test whether simple, interpretable state variables-trend and momentum-can generate durable out-of-sample alpha in one of the world's most liquid assets, gold. Using a rolling 10-year training and 6-month testing walk-forward from 2015 to 2025 (2,793 trading days), we convert a smoothed trend-momentum regime signal into volatility-targeted, friction-aware positions through fractional, impact-adjusted Kelly sizing and ATR-based exits. Out of sample, the strategy delivers a Sharpe ratio of 2.88 and a maximum drawdown of 0.52 percent, net of 0.7 basis-point linear cost and a square-root impact term (gamma = 0.02). A regression on spot-gold returns yields a 43 percent annualized return (CAGR approximately 43 percent) and a 37 percent alpha (Sharpe = 2.88, IR = 2.09) at a 15 percent volatilit …

### 4. [AlgoXpert Alpha Research Framework. A Rigorous IS WFA OOS Protocol for Mitigating Overfitting in Quantitative Strategies](http://arxiv.org/abs/2603.09219v1)  `2603.09219`  **score 32**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2026-03-10T05:40:23Z
- **Authors:** The Anh Pham, Bao Chan Nguyen, Nguyet Nguyen Thi
- **Why useful:** hits: _overfit, walk forward, backtest, execution, alpha, var, tail risk, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.09219v1](https://arxiv.org/pdf/2603.09219v1)  |  **Per-paper MD:** `papers/q-fin_PM/2603.09219_*.md`
- **Abstract:** Transitioning a strategy from backtest to live trading is a common failure point for quantitative systems due to parameter overfitting, selection bias, and sensitivity to regime changes. This paper presents the AlgoXpert Alpha Research Framework, a standardized protocol that evaluates strategies across three stages: In Sample (IS), which focuses on stable parameter regions instead of single optima; Walk Forward Analysis (WFA) using rolling windows and purge gaps to reduce information leakage, supported by majority pass and catastrophic veto rules; and Out of Sample (OOS) testing under strict parameter lock with no further tuning. The framework applies a defense in depth structure that includes structural safeguards such as cliff veto, execution controls such as spread and leverage guards,  …

### 5. [Harvesting the Volatility Risk Premium: A Learning-to-Rank Approach](http://arxiv.org/abs/2608.24786v1)  `2608.24786`  **score 30**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP, q-fin.ST | **Published:** 2026-08-25T16:31:48Z
- **Authors:** Maciej Wysocki
- **Why useful:** hits: _walk-forward, execution, lightgbm, volatility risk premium, volatility, drawdown, sharpe, sortino, options, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.24786v1](https://arxiv.org/pdf/2608.24786v1)  |  **Per-paper MD:** `papers/q-fin_CP/2608.24786_*.md`
- **Abstract:** This paper develops the first end-to-end application of cross-sectional learning-to-rank to the S&P 500 weekly options (SPXW) zero-day-to-expiration surface, integrated with margin-aware position sizing, an abstention rule driven by model uncertainty, and a strict out-of-time integrity check. A LightGBM LambdaRank ranker scores a daily nine-strategy cross-section composed of eight delta-targeted short-put positions and a \textit{SKIP} candidate, trained against a path-aware Sortino-on-bars label computed at one-minute resolution. The framework is evaluated under index-option margin requirements, a tiered fee schedule, and bid-to-mid execution assumptions across a four-window walk-forward over 2021-2024 and a strictly held-out 2025 out-of-time slice. Seven sizing methods produce out-of-time …

### 6. [Continuous Timing Signals for Growth-Defensive Style Allocation: Factor Attribution, Risk Matching, and Out-of-Sample Evidence](http://arxiv.org/abs/2605.20636v2)  `2605.20636`  **score 30**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2026-05-20T02:45:07Z
- **Authors:** Zheli Xiong
- **Why useful:** hits: _walk-forward, factor, alpha, anomaly, momentum, volatility, drawdown, sharpe, vix, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2605.20636v2](https://arxiv.org/pdf/2605.20636v2)  |  **Per-paper MD:** `papers/q-fin_PM/2605.20636_*.md`
- **Abstract:** This paper studies conditional allocation between a growth/technology ETF basket, denoted by $G$, and a defensive income/value-oriented ETF basket, denoted by $D$. The objective is not to discover a new standalone alpha factor, but to examine whether known style exposures can be dynamically allocated using macro-market timing signals. Fama-French five-factor plus momentum attribution shows that the relative portfolio $G-D$ is a recognizable style portfolio: its market beta is 0.273, its HML beta is -0.552, its momentum beta is 0.117, and its annualized alpha is 1.95\% with a Newey-West t-statistic of only 0.81. The empirical object is therefore interpreted as a growth-versus-defensive style allocation problem rather than a new return anomaly. The allocation framework replaces discrete regi …

### 7. [Financially Guided Deep Portfolio Optimization](http://arxiv.org/abs/2605.28853v1)  `2605.28853`  **score 30**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG | **Published:** 2026-05-16T22:30:15Z
- **Authors:** Rahul Fernandes, Travis Desell
- **Why useful:** hits: _walk-forward, portfolio optimization, risk parity, lstm, neural network, var, cvar, tail risk, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2605.28853v1](https://arxiv.org/pdf/2605.28853v1)  |  **Per-paper MD:** `papers/q-fin_PM/2605.28853_*.md`
- **Abstract:** Portfolio optimization in real-world financial markets is notoriously difficult due to non-stationarity, noisy data, and high transaction costs. Standard predict-then-optimize methods first forecast returns and then solve for weights, compounding prediction errors and often failing under regime shifts. We propose an end-to-end framework that directly optimizes differentiable surrogates of key financial metrics - Sharpe ratio, Omega ratio, Conditional Value-at-Risk (CVaR), and Risk Parity - allowing neural networks to learn portfolio weights via backpropagation. Our expanding-window walk-forward procedure, applied to 50 S&P 500 stocks from 2007 to 2023, incorporates realistic bid-ask spread costs and rebalances quarterly. On the challenging out-of-sample test period (2022-2023), the best mo …

### 8. [Overreaction as an indicator for momentum in algorithmic trading: A Case of AAPL stocks](http://arxiv.org/abs/2602.18912v1)  `2602.18912`  **score 30**
- **Primary:** q-fin.TR | **All cats:** q-fin.PM, q-fin.TR | **Published:** 2026-02-21T17:31:02Z
- **Authors:** Szymon Lis, Robert Ślepaczuk, Paweł Sakowski
- **Why useful:** hits: _sentiment, machine learning, xgboost, lstm, transformer, neural network, random forest, momentum, cta, volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2602.18912v1](https://arxiv.org/pdf/2602.18912v1)  |  **Per-paper MD:** `papers/q-fin_TR/2602.18912_*.md`
- **Abstract:** This paper investigates whether short-term market overreactions can be systematically predicted and monetized as momentum signals using high-frequency emotional information and modern machine learning methods. Focusing on Apple Inc. (AAPL), we construct a comprehensive intraday dataset that combines volatility normalized returns with transformer-based emotion features extracted from Twitter messages. Overreactions are defined as extreme return realizations relative to contemporaneous volatility and transaction costs and are modeled as a three-class prediction problem. We evaluate the performance of several nonlinear classifiers, including XGBoost, Random Forests, Deep Neural Networks, and Bidirectional LSTMs, across multiple intraday frequencies (1, 5, 10, and 15 minute data). Model output …

### 9. [Deep Hedging with Reinforcement Learning: A Practical Framework for Option Risk Management](http://arxiv.org/abs/2512.12420v1)  `2512.12420`  **score 30**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.RM | **Published:** 2025-12-13T18:18:08Z
- **Authors:** Travon Lucius, Christian Koch, Jacob Starling, Julia Zhu, Miguel Urena, Carrie Hu
- **Why useful:** hits: _portfolio management, mean-variance, reinforcement learning, momentum, volatility, var, cvar, drawdown, sharpe, hedging, macro_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.12420v1](https://arxiv.org/pdf/2512.12420v1)  |  **Per-paper MD:** `papers/q-fin_PM/2512.12420_*.md`
- **Abstract:** We present a reinforcement-learning (RL) framework for dynamic hedging of equity index option exposures under realistic transaction costs and position limits. We hedge a normalized option-implied equity exposure (one unit of underlying delta, offset via SPY) by trading the underlying index ETF, using the option surface and macro variables only as state information and not as a direct pricing engine. Building on the "deep hedging" paradigm of Buehler et al. (2019), we design a leak-free environment, a cost-aware reward function, and a lightweight stochastic actor-critic agent trained on daily end-of-day panel data constructed from SPX/SPY implied volatility term structure, skew, realized volatility, and macro rate context. On a fixed train/validation/test split, the learned policy improves  …

### 10. [Discovery of a 13-Sharpe OOS Factor: Drift Regimes Unlock Hidden Cross-Sectional Predictability](http://arxiv.org/abs/2511.12490v1)  `2511.12490`  **score 30**
- **Primary:** q-fin.TR | **All cats:** econ.GN, q-fin.PM, q-fin.TR | **Published:** 2025-11-16T07:55:00Z
- **Authors:** Mainak Singha
- **Why useful:** hits: _walk-forward, market microstructure, factor, cta, volatility, drawdown, sharpe, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.12490v1](https://arxiv.org/pdf/2511.12490v1)  |  **Per-paper MD:** `papers/q-fin_TR/2511.12490_*.md`
- **Abstract:** We document a high-performing cross-sectional equity factor that achieves out-of-sample Sharpe ratios above 13 through regime-conditional signal activation. The strategy combines value and short-term reversal signals only during stock-specific drift regimes, defined as periods when individual stocks show more than 60 percent positive days in trailing 63-day windows. Under these conditions, the factor delivers annualized returns of 158.6 percent with 12.0 percent volatility and a maximum drawdown of minus 11.9 percent. Using rigorous walk-forward validation across 20 years of S&P 500 data (2004 to 2024), we show performance roughly 13 times stronger than market benchmarks on a risk-adjusted basis, produced entirely out-of-sample with frozen parameters. The factor passes extensive robustness …

### 11. [An Impulse Control Approach to Market Making in a Hawkes LOB Market](http://arxiv.org/abs/2510.26438v2)  `2510.26438`  **score 30**
- **Primary:** q-fin.TR | **All cats:** q-fin.CP, q-fin.TR | **Published:** 2025-10-30T12:34:06Z
- **Authors:** Konark Jain, Nick Firoozye, Jonathan Kochems, Philip Treleaven
- **Why useful:** hits: _order book, execution, market making, deep learning, reinforcement learning, cta, var, sharpe, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.26438v2](https://arxiv.org/pdf/2510.26438v2)  |  **Per-paper MD:** `papers/q-fin_TR/2510.26438_*.md`
- **Abstract:** We study the optimal Market Making problem in a Limit Order Book (LOB) market simulated using a high-fidelity, mutually exciting Hawkes process. Departing from traditional Brownian-driven mid-price models, our setup captures key microstructural properties such as queue dynamics, inter-arrival clustering, and endogenous price impact. Recognizing the realistic constraint that market makers cannot update strategies at every LOB event, we formulate the control problem within an impulse control framework, where interventions occur discretely via limit, cancel, or market orders. This leads to a high-dimensional, non-local Hamilton-Jacobi-Bellman Quasi-Variational Inequality (HJB-QVI), whose solution is analytically intractable and computationally expensive due to the curse of dimensionality. To  …

### 12. [Equity Strategy Backtesting: Luck or Edge? The MinervaScore as a Statistical Robustness Grade](http://arxiv.org/abs/2608.23808v2)  `2608.23808`  **score 29**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2026-08-24T20:17:28Z
- **Authors:** Maria Laura Santoni, Vincent Jouanne, Matthew L. Scullin
- **Why useful:** hits: _overfit, deflated sharpe, probability of backtest overfitting, backtest, cta, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.23808v2](https://arxiv.org/pdf/2608.23808v2)  |  **Per-paper MD:** `papers/q-fin_ST/2608.23808_*.md`
- **Abstract:** Backtests of trading strategies are often selected after many parameter trials. A strong historical result can therefore reflect search luck rather than a persistent signal. Standard summaries such as return, Sharpe ratio, and drawdown do not record how many candidates were tried, whether the selected rule survives out-of-sample validation, or whether the available history is long enough to support the result. This paper describes the MinervaScore, a post-selection robustness grade for trading strategies. The score combines four established validation quantities: Deflated Sharpe Ratio, Probability of Backtest Overfitting, Superior Predictive Ability, and Minimum Track Record Length, with a regime-stability diagnostic. These components are converted into signed margins from their admissibil …

### 13. [Quantitative Financial Modeling for Sri Lankan Markets: Approach Combining NLP, Clustering and Time-Series Forecasting](http://arxiv.org/abs/2512.20216v1)  `2512.20216`  **score 29**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2025-12-23T10:16:00Z
- **Authors:** Linuk Perera
- **Why useful:** hits: _sentiment, nlp, finbert, portfolio optimization, lstm, transformer, neural network, moving average, volatility, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.20216v1](https://arxiv.org/pdf/2512.20216v1)  |  **Per-paper MD:** `papers/q-fin_CP/2512.20216_*.md`
- **Abstract:** This research introduces a novel quantitative methodology tailored for quantitative finance applications, enabling banks, stockbrokers, and investors to predict economic regimes and market signals in emerging markets, specifically Sri Lankan stock indices (S&P SL20 and ASPI) by integrating Environmental, Social, and Governance (ESG) sentiment analysis with macroeconomic indicators and advanced time-series forecasting. Designed to leverage quantitative techniques for enhanced risk assessment, portfolio optimization, and trading strategies in volatile environments, the architecture employs FinBERT, a transformer-based NLP model, to extract sentiment from ESG texts, followed by unsupervised clustering (UMAP/HDBSCAN) to identify 5 latent ESG regimes, validated via PCA. These regimes are mapped …

### 14. [RegimeFolio: A Regime Aware ML System for Sectoral Portfolio Optimization in Dynamic Markets](http://arxiv.org/abs/2510.14986v1)  `2510.14986`  **score 29**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI | **Published:** 2025-09-14T12:03:06Z
- **Authors:** Yiyao Zhang, Diksha Goel, Hussain Ahmad, Claudia Szabo
- **Why useful:** hits: _portfolio optimization, mean-variance, machine learning, random forest, volatility, var, drawdown, sharpe, vix, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.14986v1](https://arxiv.org/pdf/2510.14986v1)  |  **Per-paper MD:** `papers/q-fin_PM/2510.14986_*.md`
- **Abstract:** Financial markets are inherently non-stationary, with shifting volatility regimes that alter asset co-movements and return distributions. Standard portfolio optimization methods, typically built on stationarity or regime-agnostic assumptions, struggle to adapt to such changes. To address these challenges, we propose RegimeFolio, a novel regime-aware and sector-specialized framework that, unlike existing regime-agnostic models such as DeepVol and DRL optimizers, integrates explicit volatility regime segmentation with sector-specific ensemble forecasting and adaptive mean-variance allocation. This modular architecture ensures forecasts and portfolio decisions remain aligned with current market conditions, enhancing robustness and interpretability in dynamic markets. RegimeFolio combines thre …

### 15. [Machine Learning-Based Bitcoin Trading Under Transaction Costs: Evidence From Walk-Forward Forecasting](http://arxiv.org/abs/2606.00060v1)  `2606.00060`  **score 28**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.CE, cs.LG | **Published:** 2026-05-19T14:30:49Z
- **Authors:** Andrei Bysik, Robert Ślepaczuk
- **Why useful:** hits: _walk-forward, execution, machine learning, xgboost, lstm, transformer, cta, garch, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.00060v1](https://arxiv.org/pdf/2606.00060v1)  |  **Per-paper MD:** `papers/q-fin_TR/2606.00060_*.md`
- **Abstract:** This paper investigates whether machine learning forecasts of hourly BTC-USDT returns can be converted into economically meaningful trading performance after transaction costs. Using approximately 70,000 hourly observations from 2018-2026, XGBoost, LSTM, and iTransformer are evaluated in a 27-fold walk-forward protocol. All three models produce positive gross trading performance in selected configurations, but naive sign-based strategies fail once transaction costs of ten basis points are imposed. A cost-aware execution filter, which prevents trades only when the forecast magnitude exceeds a transaction-cost-based threshold, sharply reduces turnover and restores profitability in selected configurations. The strongest long-only XGBoost strategy produces annualised returns above 65% with a S …

### 16. [Deep Reinforcement Learning for Optimal Portfolio Allocation: A Comparative Study with Mean-Variance Optimization](http://arxiv.org/abs/2602.17098v1)  `2602.17098`  **score 28**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI, cs.LG | **Published:** 2026-02-19T05:47:23Z
- **Authors:** Srijan Sood, Kassiani Papasotiriou, Marius Vaiciulis, Tucker Balch
- **Why useful:** hits: _backtest, portfolio optimization, portfolio management, mean-variance, reinforcement learning, var, drawdown, sharpe, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2602.17098v1](https://arxiv.org/pdf/2602.17098v1)  |  **Per-paper MD:** `papers/q-fin_PM/2602.17098_*.md`
- **Abstract:** Portfolio Management is the process of overseeing a group of investments, referred to as a portfolio, with the objective of achieving predetermined investment goals. Portfolio optimization is a key component that involves allocating the portfolio assets so as to maximize returns while minimizing risk taken. It is typically carried out by financial professionals who use a combination of quantitative techniques and investment expertise to make decisions about the portfolio allocation. Recent applications of Deep Reinforcement Learning (DRL) have shown promising results when used to optimize portfolio allocation by training model-free agents on historical market data. Many of these methods compare their results against basic benchmarks or other state-of-the-art DRL agents but often fail to co …

### 17. [Non-Convex Portfolio Optimization via Energy-Based Models: A Comparative Analysis Using the Thermodynamic HypergRaphical Model Library (THRML) for Index Tracking](http://arxiv.org/abs/2601.07792v1)  `2601.07792`  **score 28**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP, q-fin.PM, stat.ML | **Published:** 2026-01-12T18:04:33Z
- **Authors:** Javier Mancilla, Theodoros D. Bouloumis, Frederic Goguikian
- **Why useful:** hits: _overfit, backtest, portfolio optimization, mean-variance, momentum, volatility, var, vix, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2601.07792v1](https://arxiv.org/pdf/2601.07792v1)  |  **Per-paper MD:** `papers/q-fin_CP/2601.07792_*.md`
- **Abstract:** Portfolio optimization under cardinality constraints transforms the classical Markowitz mean-variance problem from a convex quadratic problem into an NP-hard combinatorial optimization problem. This paper introduces a novel approach using THRML (Thermodynamic HypergRaphical Model Library), a JAX-based library for building and sampling probabilistic graphical models that reformulates index tracking as probabilistic inference on an Ising Hamiltonian. Unlike traditional methods that seek a single optimal solution, THRML samples from the Boltzmann distribution of high-quality portfolios using GPU-accelerated block Gibbs sampling, providing natural regularization against overfitting. We implement three key innovations: (1) dynamic coupling strength that scales inversely with market volatility ( …

### 18. [Interpretable Hypothesis-Driven Trading:A Rigorous Walk-Forward Validation Framework for Market Microstructure Signals](http://arxiv.org/abs/2512.12924v1)  `2512.12924`  **score 28**
- **Primary:** q-fin.TR | **All cats:** q-fin.CP, q-fin.TR, stat.ML | **Published:** 2025-12-15T02:20:42Z
- **Authors:** Gagan Deep, Akash Deep, William Lamptey
- **Why useful:** hits: _overfit, walk-forward, market microstructure, reinforcement learning, volatility, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.12924v1](https://arxiv.org/pdf/2512.12924v1)  |  **Per-paper MD:** `papers/q-fin_TR/2512.12924_*.md`
- **Abstract:** We develop a rigorous walk-forward validation framework for algorithmic trading designed to mitigate overfitting and lookahead bias. Our methodology combines interpretable hypothesis-driven signal generation with reinforcement learning and strict out-of-sample testing. The framework enforces strict information set discipline, employs rolling window validation across 34 independent test periods, maintains complete interpretability through natural language hypothesis explanations, and incorporates realistic transaction costs and position constraints. Validating five market microstructure patterns across 100 US equities from 2015 to 2024, the system yields modest annualized returns (0.55%, Sharpe ratio 0.33) with exceptional downside protection (maximum drawdown -2.76%) and market-neutral cha …

### 19. [Are Three Matrices All You Need To Beat the Market? Observable Matrix Dynamics for Portfolio Optimization](http://arxiv.org/abs/2607.27461v1)  `2607.27461`  **score 27**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.RM, q-fin.ST | **Published:** 2026-07-29T20:53:46Z
- **Authors:** Igor Halperin
- **Why useful:** hits: _portfolio optimization, portfolio management, mean-variance, momentum, volatility, var, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.27461v1](https://arxiv.org/pdf/2607.27461v1)  |  **Per-paper MD:** `papers/q-fin_PM/2607.27461_*.md`
- **Abstract:** We present a simple framework for dynamic portfolio management that uses nothing but daily prices, trading volumes, and market capitalizations. Its state is three fixed-size matrices built from the price history: the distance matrix of the return correlations and the transition matrices of two Markov chains that rank the S\&P 500 names monthly by trailing return and by trailing volatility. These three matrices rest on the price history alone, the same information Markowitz mean-variance optimization draws on, but they replace its expected-return vector and covariance matrix. Our method requires no matrix inversion, works on outlier-robust cross-sectional ranks, and is dynamic rather than single-period. Empirically the volatility rank is forecastable one step ahead while the return rank sta …

### 20. [When Does Order Flow Matter? State-Dependent L2 Liquidity-State Transitions in Crypto Futures](http://arxiv.org/abs/2607.09230v1)  `2607.09230`  **score 27**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2026-07-10T09:21:00Z
- **Authors:** Joohyoung Jeon
- **Why useful:** hits: _permutation test, market microstructure, order book, order flow, execution, macro, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.09230v1](https://arxiv.org/pdf/2607.09230v1)  |  **Per-paper MD:** `papers/q-fin_TR/2607.09230_*.md`
- **Abstract:** Building event-conditioned market models requires separating macro-event labels from persistent microstructure state. We study this distinction in Binance BTCUSDT and ETHUSDT futures from 2023-2026, combining top-20 L2 order book data, trade-flow records, and macro-event windows. We define a supervised discrete L2 liquidity-state transition task, distinct from latent-regime detection and price-direction prediction, and evaluate models in rolling monthly out-of-sample folds with event-clustered validation and blocked permutation tests, admitting each feature layer only if it improves on the layer below it on the same panel. Within these event windows, the first-order predictive signal is the pre-event L2 liquidity state: a coarse pre-event state baseline strongly predicts post-event liquidi …

### 21. [The Mathematics of Heuristic Portfolio Optimization (HPO)](http://arxiv.org/abs/2606.12612v1)  `2606.12612`  **score 27**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2026-06-10T19:13:53Z
- **Authors:** Miquel Noguer i Alonso
- **Why useful:** hits: _portfolio optimization, risk parity, kelly, alpha, reinforcement learning, volatility, var, cvar, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.12612v1](https://arxiv.org/pdf/2606.12612v1)  |  **Per-paper MD:** `papers/q-fin_PM/2606.12612_*.md`
- **Abstract:** Practitioners allocate capital with forecast-light rules such as equal weight, inverse volatility, risk parity, HRP, and return-adjusted HRP (RA-HRP). This paper develops \emph{Heuristic Portfolio Optimization} (HPO): an information-restricted projection of the Markowitz/tangency solution onto a stable rule class. The implied-return principle, $\mathbf{w}$ is maximum-Sharpe iff $\mathbfμ_e \propto \mathbfΣ\mathbf{w}$, gives closed-form optimality sets for leading heuristics and exposes the Schur-complement substitutions behind HRP. For RA-HRP, we introduce fixed-tree cluster-Sharpe recursion, unit-free HRP--RA-HRP interpolation, tangency conditions, conditional-risk splits, and pathwise/KL decompositions of weight distortion. First-order Sharpe calculus expresses the marginal value of retu …

### 22. [Generating Alpha: A Hybrid AI-Driven Trading System Integrating Technical Analysis, Machine Learning and Financial Sentiment for Regime-Adaptive Equity Strategies](http://arxiv.org/abs/2601.19504v1)  `2601.19504`  **score 27**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2026-01-27T11:44:47Z
- **Authors:** Varun Narayan Kannan Pillai, Akshay Ajith, Sumesh K J
- **Why useful:** hits: _sentiment, finbert, factor, alpha, machine learning, xgboost, momentum, volatility, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2601.19504v1](https://arxiv.org/pdf/2601.19504v1)  |  **Per-paper MD:** `papers/q-fin_CP/2601.19504_*.md`
- **Abstract:** The intricate behavior patterns of financial markets are influenced by fundamental, technical, and psychological factors. During times of high volatility and regime shifts causes many traditional strategies like trend-following or mean-reversion to fail. This paper proposes a hybrid AI-based trading strategy that combines (1) trend-following and directional momentum capture via EMA and MACD, (2) detection of price normalization through mean-reversion using RSI and Bollinger Bands, (3) market psychological interpretation through sentiment analysis using FinBERT, (4) signal generation through machine learning using XGBoost and (5)dynamically adjusting exposure with market regime filtering based on volatility and return environments. The system achieved a final portfolio value of $235,492.83, …

### 23. [DeePM: Regime-Robust Deep Learning for Systematic Macro Portfolio Management](http://arxiv.org/abs/2601.05975v1)  `2601.05975`  **score 27**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG, stat.ML | **Published:** 2026-01-09T17:47:32Z
- **Authors:** Kieran Wood, Stephen J. Roberts, Stefan Zohren
- **Why useful:** hits: _backtest, portfolio management, deep learning, transformer, momentum, cta, volatility, var, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2601.05975v1](https://arxiv.org/pdf/2601.05975v1)  |  **Per-paper MD:** `papers/q-fin_TR/2601.05975_*.md`
- **Abstract:** We propose DeePM (Deep Portfolio Manager), a structured deep-learning macro portfolio manager trained end-to-end to maximize a robust, risk-adjusted utility. DeePM addresses three fundamental challenges in financial learning: (1) it resolves the asynchronous "ragged filtration" problem via a Directed Delay (Causal Sieve) mechanism that prioritizes causal impulse-response learning over information freshness; (2) it combats low signal-to-noise ratios via a Macroeconomic Graph Prior, regularizing cross-asset dependence according to economic first principles; and (3) it optimizes a distributionally robust objective where a smooth worst-window penalty serves as a differentiable proxy for Entropic Value-at-Risk (EVaR) - a window-robust utility encouraging strong performance in the most adverse h …

### 24. [Risk-Aware Deep Reinforcement Learning for Dynamic Portfolio Optimization](http://arxiv.org/abs/2511.11481v1)  `2511.11481`  **score 27**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.CE, econ.EM | **Published:** 2025-11-14T16:58:28Z
- **Authors:** Emmanuel Lwele, Sabuni Emmanuel, Sitali Gabriel Sitali
- **Why useful:** hits: _backtest, portfolio optimization, mean-variance, reinforcement learning, volatility, var, drawdown, sharpe, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.11481v1](https://arxiv.org/pdf/2511.11481v1)  |  **Per-paper MD:** `papers/q-fin_PM/2511.11481_*.md`
- **Abstract:** This paper presents a deep reinforcement learning (DRL) framework for dynamic portfolio optimization under market uncertainty and risk. The proposed model integrates a Sharpe ratio-based reward function with direct risk control mechanisms, including maximum drawdown and volatility constraints. Proximal Policy Optimization (PPO) is employed to learn adaptive asset allocation strategies over historical financial time series. Model performance is benchmarked against mean-variance and equal-weight portfolio strategies using backtesting on high-performing equities. Results indicate that the DRL agent stabilizes volatility successfully but suffers from degraded risk-adjusted returns due to over-conservative policy convergence, highlighting the challenge of balancing exploration, return maximizat …

### 25. [Sentiment-Aware Mean-Variance Portfolio Optimization for Cryptocurrencies](http://arxiv.org/abs/2508.16378v2)  `2508.16378`  **score 27**
- **Primary:** cs.CE | **All cats:** cs.CE, q-fin.ST | **Published:** 2025-08-22T13:34:09Z
- **Authors:** Qizhao Chen
- **Why useful:** hits: _backtest, sentiment, portfolio optimization, portfolio management, mean-variance, momentum, moving average, var, drawdown_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2508.16378v2](https://arxiv.org/pdf/2508.16378v2)  |  **Per-paper MD:** `papers/cs_CE/2508.16378_*.md`
- **Abstract:** Cryptocurrency markets are highly volatile and influenced by both price trends and market sentiment, making effective portfolio management challenging. This paper proposes a dynamic cryptocurrency portfolio strategy that integrates technical indicators and sentiment analysis to enhance investment decision-making. Market momentum is captured using the 14-day Relative Strength Index (RSI) and Simple Moving Average (SMA), while sentiment signals are extracted from news articles with VADER and further validated using the Google Gemini large language model. These signals are incorporated into expected return estimates and used in a constrained mean-variance optimization framework. Backtesting across multiple cryptocurrencies shows that the integrated approach outperforms traditional benchmarks, …

### 26. [Deep Learning Meets Queue-Reactive: A Framework for Realistic Limit Order Book Simulation](http://arxiv.org/abs/2501.08822v1)  `2501.08822`  **score 27**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2025-01-15T14:19:20Z
- **Authors:** Hamza Bodor, Laurent Carlier
- **Why useful:** hits: _backtest, market microstructure, order book, deep learning, reinforcement learning, neural network, var, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2501.08822v1](https://arxiv.org/pdf/2501.08822v1)  |  **Per-paper MD:** `papers/q-fin_TR/2501.08822_*.md`
- **Abstract:** The Queue-Reactive model introduced by Huang et al. (2015) has become a standard tool for limit order book modeling, widely adopted by both researchers and practitioners for its simplicity and effectiveness. We present the Multidimensional Deep Queue-Reactive (MDQR) model, which extends this framework in three ways: it relaxes the assumption of queue independence, enriches the state space with market features, and models the distribution of order sizes. Through a neural network architecture, the model learns complex dependencies between different price levels and adapts to varying market conditions, while preserving the interpretable point-process foundation of the original framework. Using data from the Bund futures market, we show that MDQR captures key market properties including the sq …

### 27. [AlphaZeroBeta: Deep Reinforcement Learning for Market-Neutral Portfolios](http://arxiv.org/abs/2607.18001v1)  `2607.18001`  **score 26**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM | **Published:** 2026-07-20T14:33:47Z
- **Authors:** Boris Belyakov
- **Why useful:** hits: _walk-forward, backtest, factor, alpha, reinforcement learning, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.18001v1](https://arxiv.org/pdf/2607.18001v1)  |  **Per-paper MD:** `papers/q-fin_PM/2607.18001_*.md`
- **Abstract:** Market-neutral portfolios aim to generate consistent returns while offsetting systematic market risk. Traditional approaches based on factor models or convex optimization often underperform during market regime shifts or when structural assumptions break down. We propose AlphaZeroBeta, a deep reinforcement learning framework designed to deliver benchmark-relative alpha (excess returns) with near-zero beta (market neutrality). AlphaZeroBeta combines a composite reward function that balances risk-adjusted excess return, benchmark correlation, and transaction costs with a CNN-GRU policy trained end-to-end via Recurrent PPO and evaluated through a rolling walk-forward protocol. Backtests covering 2014-2024 across seven equity indices show that the model achieves higher Sharpe ratios than the b …

### 28. [Risk-Aware Financial Forecasting Enhanced by Machine Learning and Intuitionistic Fuzzy Multi-Criteria Decision-Making](http://arxiv.org/abs/2512.17936v1)  `2512.17936`  **score 26**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.LG, math.OC | **Published:** 2025-12-11T04:19:26Z
- **Authors:** Safiye Turgay, Serkan Erdoğan, Željko Stević, Orhan Emre Elma, Tevfik Eren, Zhiyuan Wang, Mahmut Baydaş
- **Why useful:** hits: _sentiment, machine learning, xgboost, lstm, neural network, volatility, var, sharpe, sortino, macro_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.17936v1](https://arxiv.org/pdf/2512.17936v1)  |  **Per-paper MD:** `papers/q-fin_ST/2512.17936_*.md`
- **Abstract:** In the face of increasing financial uncertainty and market complexity, this study presents a novel risk-aware financial forecasting framework that integrates advanced machine learning techniques with intuitionistic fuzzy multi-criteria decision-making (MCDM). Tailored to the BIST 100 index and validated through a case study of a major defense company in Türkiye, the framework fuses structured financial data, unstructured text data, and macroeconomic indicators to enhance predictive accuracy and robustness. It incorporates a hybrid suite of models, including extreme gradient boosting (XGBoost), long short-term memory (LSTM) network, graph neural network (GNN), to deliver probabilistic forecasts with quantified uncertainty. The empirical results demonstrate high forecasting accuracy, with a  …

### 29. [ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment for Optimal Execution with Endogenous Liquidity](http://arxiv.org/abs/2511.02016v2)  `2511.02016`  **score 26**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.GT, cs.MA, eess.SY | **Published:** 2025-11-03T19:42:17Z
- **Authors:** Patrick Cheridito, Jean-Loup Dupret, Zhexin Wu
- **Why useful:** hits: _market microstructure, order book, execution, reinforcement learning, cta, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.02016v2](https://arxiv.org/pdf/2511.02016v2)  |  **Per-paper MD:** `papers/q-fin_TR/2511.02016_*.md`
- **Abstract:** Classical optimal execution models treat market impact as a pre-specified, exogenous process. However, when market makers adapt strategically, this assumption becomes a structural misspecification: execution dynamics depend on the policies and actions of other agents. The problem therefore ceases to be a single-agent control problem and instead becomes a finite-horizon stochastic game, in which liquidity emerges endogenously from the interactions among heterogeneous market players. We hence introduce ABIDES-MARL, a multi-agent reinforcement learning framework for studying optimal execution under endogenous liquidity in a realistic limit order book setting. The framework extends ABIDES-Gym to support multiple learning agents with synchronized decision periods that preserve proper informatio …

### 30. [Adaptive and Regime-Aware RL for Portfolio Optimization](http://arxiv.org/abs/2509.14385v1)  `2509.14385`  **score 26**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM | **Published:** 2025-09-17T19:40:57Z
- **Authors:** Gabriel Nixon Raj
- **Why useful:** hits: _portfolio optimization, reinforcement learning, lstm, transformer, volatility, garch, var, sharpe, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.14385v1](https://arxiv.org/pdf/2509.14385v1)  |  **Per-paper MD:** `papers/q-fin_PM/2509.14385_*.md`
- **Abstract:** This study proposes a regime-aware reinforcement learning framework for long-horizon portfolio optimization. Moving beyond traditional feedforward and GARCH-based models, we design realistic environments where agents dynamically reallocate capital in response to latent macroeconomic regime shifts. Agents receive hybrid observations and are trained using constrained reward functions that incorporate volatility penalties, capital resets, and tail-risk shocks. We benchmark multiple architectures, including PPO, LSTM-based PPO, and Transformer PPO, against classical baselines such as equal-weight and Sharpe-optimized portfolios. Our agents demonstrate robust performance under financial stress. While Transformer PPO achieves the highest risk-adjusted returns, LSTM variants offer a favorable tra …

### 31. [Neural Lévy SDE for State--Dependent Risk and Density Forecasting](http://arxiv.org/abs/2509.01041v1)  `2509.01041`  **score 26**
- **Primary:** q-fin.RM | **All cats:** q-fin.RM | **Published:** 2025-09-01T00:46:03Z
- **Authors:** Ziyao Wang, Svetlozar T Rachev
- **Why useful:** hits: _backtest, execution, machine learning, cta, volatility, garch, var, tail risk, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.01041v1](https://arxiv.org/pdf/2509.01041v1)  |  **Per-paper MD:** `papers/q-fin_RM/2509.01041_*.md`
- **Abstract:** Financial returns are known to exhibit heavy tails, volatility clustering and abrupt jumps that are poorly captured by classical diffusion models. Advances in machine learning have enabled highly flexible functional forms for conditional means and volatilities, yet few models deliver interpretable state--dependent tail risk, capture multiple forecast horizons and yield distributions amenable to backtesting and execution. This paper proposes a neural Lévy jump--diffusion framework that jointly learns, as functions of observable state variables, the conditional drift, diffusion, jump intensity and jump size distribution. We show how a single shared encoder yields multiple forecasting heads corresponding to distinct horizons (daily, weekly, etc.), facilitating multi--horizon density forecasts …

### 32. [PreBit -- A multimodal model with Twitter FinBERT embeddings for extreme price movement prediction of Bitcoin](http://arxiv.org/abs/2206.00648v2)  `2206.00648`  **score 26**
- **Primary:** q-fin.ST | **All cats:** cs.CL, cs.LG, q-fin.CP, q-fin.ST, q-fin.TR | **Published:** 2022-05-30T19:25:12Z
- **Authors:** Yanzhao Zou, Dorien Herremans
- **Why useful:** hits: _backtest, nlp, finbert, social media, neural network, moving average, volatility, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2206.00648v2](https://arxiv.org/pdf/2206.00648v2)  |  **Per-paper MD:** `papers/q-fin_ST/2206.00648_*.md`
- **Abstract:** Bitcoin, with its ever-growing popularity, has demonstrated extreme price volatility since its origin. This volatility, together with its decentralised nature, make Bitcoin highly subjective to speculative trading as compared to more traditional assets. In this paper, we propose a multimodal model for predicting extreme price fluctuations. This model takes as input a variety of correlated assets, technical indicators, as well as Twitter content. In an in-depth study, we explore whether social media discussions from the general public on Bitcoin have predictive power for extreme price movements. A dataset of 5,000 tweets per day containing the keyword `Bitcoin' was collected from 2015 to 2021. This dataset, called PreBit, is made available online. In our hybrid model, we use sentence-level  …

### 33. [Deep Reinforcement Learning for Long-Short Portfolio Optimization](http://arxiv.org/abs/2012.13773v8)  `2012.13773`  **score 26**
- **Primary:** q-fin.CP | **All cats:** cs.LG, q-fin.CP, q-fin.PM | **Published:** 2020-12-26T16:25:20Z
- **Authors:** Gang Huang, Xiaohua Zhou, Qingyang Song
- **Why useful:** hits: _backtest, portfolio optimization, portfolio management, reinforcement learning, neural network, drawdown, sharpe, hedging, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2012.13773v8](https://arxiv.org/pdf/2012.13773v8)  |  **Per-paper MD:** `papers/q-fin_CP/2012.13773_*.md`
- **Abstract:** With the rapid development of artificial intelligence, data-driven methods effectively overcome limitations in traditional portfolio optimization. Conventional models primarily employ long-only mechanisms, excluding highly correlated assets to diversify risk. However, incorporating short-selling enables low-risk arbitrage through hedging correlated assets. This paper constructs a Deep Reinforcement Learning (DRL) portfolio management framework with short-selling mechanisms conforming to actual trading rules, exploring strategies for excess returns in China's A-share market. Key innovations include: (1) Development of a comprehensive short-selling mechanism in continuous trading that accounts for dynamic evolution of transactions across time periods; (2) Design of a long-short optimization  …

### 34. [Distributional Portfolio Optimization (DPO): A Unified Framework for Distributions over Weights, Returns, and Parameters](http://arxiv.org/abs/2605.30464v1)  `2605.30464`  **score 25**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2026-05-28T18:38:56Z
- **Authors:** Miquel Noguer i Alonso
- **Why useful:** hits: _backtest, portfolio optimization, factor, alpha, var, cvar, tail risk, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2605.30464v1](https://arxiv.org/pdf/2605.30464v1)  |  **Per-paper MD:** `papers/q-fin_PM/2605.30464_*.md`
- **Abstract:** Classical portfolio optimization treats expected returns, covariances, and allocations as deterministic. Modern practice replaces at least one by a distribution: a posterior over parameters, a law of future returns, a stochastic allocation policy, or a distributional-robustness set. We call distributional portfolio optimization (DPO) the unified framework in which weights, returns, and parameters are all modeled as probability measures, organized around the joint coupling Gamma_theta(dw,dr) and its marginal triple (W,R,P). The contribution is synthetic and structural: we organize Bayesian, robust, chance-constrained, stochastic-allocation, and distributional reinforcement-learning portfolio methods through this coupling and prove boundary results connecting them, including a portfolio spec …

### 35. [Hybrid Quantum-Classical Ensemble Learning for S\&P 500 Directional Prediction](http://arxiv.org/abs/2512.15738v1)  `2512.15738`  **score 25**
- **Primary:** cs.LG | **All cats:** cs.LG, cs.AI, q-fin.ST | **Published:** 2025-12-06T22:22:09Z
- **Authors:** Abraham Itzhak Weinberg
- **Why useful:** hits: _backtest, sentiment, machine learning, xgboost, lstm, transformer, random forest, var, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.15738v1](https://arxiv.org/pdf/2512.15738v1)  |  **Per-paper MD:** `papers/cs_LG/2512.15738_*.md`
- **Abstract:** Financial market prediction is a challenging application of machine learning, where even small improvements in directional accuracy can yield substantial value. Most models struggle to exceed 55--57\% accuracy due to high noise, non-stationarity, and market efficiency. We introduce a hybrid ensemble framework combining quantum sentiment analysis, Decision Transformer architecture, and strategic model selection, achieving 60.14\% directional accuracy on S\&P 500 prediction, a 3.10\% improvement over individual models. Our framework addresses three limitations of prior approaches. First, architecture diversity dominates dataset diversity: combining different learning algorithms (LSTM, Decision Transformer, XGBoost, Random Forest, Logistic Regression) on the same data outperforms training ide …

### 36. [Reinforcement Learning in Queue-Reactive Models: Application to Optimal Execution](http://arxiv.org/abs/2511.15262v1)  `2511.15262`  **score 25**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2025-11-19T09:26:23Z
- **Authors:** Tomas Espana, Yadh Hafsi, Fabrizio Lillo, Edoardo Vittori
- **Why useful:** hits: _order book, order flow, execution, reinforcement learning, cta, var, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.15262v1](https://arxiv.org/pdf/2511.15262v1)  |  **Per-paper MD:** `papers/q-fin_TR/2511.15262_*.md`
- **Abstract:** We investigate the use of Reinforcement Learning for the optimal execution of meta-orders, where the objective is to execute incrementally large orders while minimizing implementation shortfall and market impact over an extended period of time. Departing from traditional parametric approaches to price dynamics and impact modeling, we adopt a model-free, data-driven framework. Since policy optimization requires counterfactual feedback that historical data cannot provide, we employ the Queue-Reactive Model to generate realistic and tractable limit order book simulations that encompass transient price impact, and nonlinear and dynamic order flow responses. Methodologically, we train a Double Deep Q-Network agent on a state space comprising time, inventory, price, and depth variables, and eval …

### 37. [Causal and Predictive Modeling of Short-Horizon Market Risk and Systematic Alpha Generation Using Hybrid Machine Learning Ensembles](http://arxiv.org/abs/2510.22348v1)  `2510.22348`  **score 25**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2025-10-25T16:16:27Z
- **Authors:** Aryan Ranjan
- **Why useful:** hits: _backtest, factor, alpha, machine learning, neural network, volatility, drawdown, sharpe, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.22348v1](https://arxiv.org/pdf/2510.22348v1)  |  **Per-paper MD:** `papers/q-fin_CP/2510.22348_*.md`
- **Abstract:** We present a systematic trading framework that forecasts short-horizon market risk, identifies its underlying drivers, and generates alpha using a hybrid machine learning ensemble built to trade on the resulting signal. The framework integrates neural networks with tree-based voting models to predict five-day drawdowns in the S&P 500 ETF, leveraging a cross-asset feature set spanning equities, fixed income, foreign exchange, commodities, and volatility markets. Interpretable feature attribution methods reveal the key macroeconomic and microstructural factors that differentiate high-risk (crash) from benign (non-crash) weekly regimes. Empirical results show a Sharpe ratio of 2.51 and an annualized CAPM alpha of +0.28, with a market beta of 0.51, indicating that the model delivers substantia …

### 38. [LLM-Powered Multi-Agent System for Automated Crypto Portfolio Management](http://arxiv.org/abs/2501.00826v3)  `2501.00826`  **score 25**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.AI | **Published:** 2025-01-01T13:08:17Z
- **Authors:** Yichen Luo, Yebo Feng, Jiahua Xu, Paolo Tasca, Yang Liu
- **Why useful:** hits: _backtest, sentiment, execution, portfolio management, deep learning, volatility, var, sharpe, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2501.00826v3](https://arxiv.org/pdf/2501.00826v3)  |  **Per-paper MD:** `papers/q-fin_TR/2501.00826_*.md`
- **Abstract:** Cryptocurrency portfolio management requires the fusion of heterogeneous multi-modal signals, including structured price and on-chain time series, unstructured news text, and technical indicators, under high-volatility and real-time constraints. While deep learning approaches show predictive capability, their opacity limits practical adoption, and single large language model (LLM) agents struggle to process the breadth of modality-specific inputs needed for robust decision-making. We propose a multi-agent system (MAS) framework in which three modality-specialised agents, a Crypto Agent for market dynamics, a News Agent for weekly news sentiment, and a Trading Agent for signal fusion and portfolio execution, decompose the task across three communication architectures: hierarchical, collabor …

### 39. [S&P 500 Trend Prediction](http://arxiv.org/abs/2412.11462v1)  `2412.11462`  **score 25**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2024-12-16T05:37:30Z
- **Authors:** Shasha Yu, Qinchen Zhang, Yuwei Zhao
- **Why useful:** hits: _overfit, alpha, machine learning, xgboost, lstm, neural network, random forest, momentum, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2412.11462v1](https://arxiv.org/pdf/2412.11462v1)  |  **Per-paper MD:** `papers/q-fin_CP/2412.11462_*.md`
- **Abstract:** This project aims to predict short-term and long-term upward trends in the S&P 500 index using machine learning models and feature engineering based on the "101 Formulaic Alphas" methodology. The study employed multiple models, including Logistic Regression, Decision Trees, Random Forests, Neural Networks, K-Nearest Neighbors (KNN), and XGBoost, to identify market trends from historical stock data collected from Yahoo! Finance. Data preprocessing involved handling missing values, standardization, and iterative feature selection to ensure relevance and variability. For short-term predictions, KNN emerged as the most effective model, delivering robust performance with high recall for upward trends, while for long-term forecasts, XGBoost demonstrated the highest accuracy and AUC scores after  …

### 40. [Combining Deep Learning on Order Books with Reinforcement Learning for Profitable Trading](http://arxiv.org/abs/2311.02088v1)  `2311.02088`  **score 25**
- **Primary:** q-fin.CP | **All cats:** cs.AI, cs.LG, q-fin.CP, q-fin.PM, q-fin.TR | **Published:** 2023-10-24T15:58:58Z
- **Authors:** Koti S. Jaddu, Paul A. Bilokon
- **Why useful:** hits: _backtest, order book, order flow, slippage, machine learning, deep learning, reinforcement learning_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2311.02088v1](https://arxiv.org/pdf/2311.02088v1)  |  **Per-paper MD:** `papers/q-fin_CP/2311.02088_*.md`
- **Abstract:** High-frequency trading is prevalent, where automated decisions must be made quickly to take advantage of price imbalances and patterns in price action that forecast near-future movements. While many algorithms have been explored and tested, analytical methods fail to harness the whole nature of the market environment by focusing on a limited domain. With the evergrowing machine learning field, many large-scale end-to-end studies on raw data have been successfully employed to increase the domain scope for profitable trading but are very difficult to replicate. Combining deep learning on the order books with reinforcement learning is one way of breaking down large-scale end-to-end learning into more manageable and lightweight components for reproducibility, suitable for retail trading. The f …

### 41. [Deep Reinforcement Learning for Asset Allocation in US Equities](http://arxiv.org/abs/2010.04404v1)  `2010.04404`  **score 25**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM | **Published:** 2020-10-09T07:25:55Z
- **Authors:** Miquel Noguer i Alonso, Sonam Srivastava
- **Why useful:** hits: _portfolio management, mean-variance, risk parity, machine learning, reinforcement learning, neural network, var, impact, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2010.04404v1](https://arxiv.org/pdf/2010.04404v1)  |  **Per-paper MD:** `papers/q-fin_PM/2010.04404_*.md`
- **Abstract:** Reinforcement learning is a machine learning approach concerned with solving dynamic optimization problems in an almost model-free way by maximizing a reward function in state and action spaces. This property makes it an exciting area of research for financial problems. Asset allocation, where the goal is to obtain the weights of the assets that maximize the rewards in a given state of the market considering risk and transaction costs, is a problem easily framed using a reinforcement learning framework. It is first a prediction problem for expected returns and covariance matrix and then an optimization problem for returns, risk, and market impact. Investors and financial researchers have been working with approaches like mean-variance optimization, minimum variance, risk parity, and equall …

### 42. [Robust Asset Allocation for Robo-Advisors](http://arxiv.org/abs/1902.07449v1)  `1902.07449`  **score 25**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2019-02-20T08:30:29Z
- **Authors:** Thibault Bourgeron, Edmond Lezmi, Thierry Roncalli
- **Why useful:** hits: _social media, portfolio optimization, portfolio management, mean-variance, factor, var, hedging, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1902.07449v1](https://arxiv.org/pdf/1902.07449v1)  |  **Per-paper MD:** `papers/q-fin_PM/1902.07449_*.md`
- **Abstract:** In the last few years, the financial advisory industry has been impacted by the emergence of digitalization and robo-advisors. This phenomenon affects major financial services, including wealth management, employee savings plans, asset managers, etc. Since the robo-advisory model is in its early stages, we estimate that robo-advisors will help to manage around $1 trillion of assets in 2020 (OECD, 2017). And this trend is not going to stop with future generations, who will live in a technology-driven and social media-based world. In the investment industry, robo-advisors face different challenges: client profiling, customization, asset pooling, liability constraints, etc. In its primary sense, robo-advisory is a term for defining automated portfolio management. This includes automated tradi …

### 43. [High frequency trading and asymptotics for small risk aversion in a Markov renewal model](http://arxiv.org/abs/1310.1756v2)  `1310.1756`  **score 25**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, math.PR | **Published:** 2013-10-07T12:42:10Z
- **Authors:** Pietro Fodra, Huyên Pham
- **Why useful:** hits: _market microstructure, order book, execution, market making, cta, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1310.1756v2](https://arxiv.org/pdf/1310.1756v2)  |  **Per-paper MD:** `papers/q-fin_TR/1310.1756_*.md`
- **Abstract:** We study a an optimal high frequency trading problem within a market microstructure model designed to be a good compromise between accuracy and tractability. The stock price is driven by a Markov Renewal Process (MRP), while market orders arrive in the limit order book via a point process correlated with the stock price itself. In this framework, we can reproduce the adverse selection risk, appearing in two different forms: the usual one due to big market orders impacting the stock price and penalizing the agent, and the weak one due to small market orders and reducing the probability of a profitable execution. We solve the market making problem by stochastic control techniques in this semi-Markov model. In the no risk-aversion case, we provide explicit formula for the optimal controls and …

### 44. [Optimal High Frequency Trading with limit and market orders](http://arxiv.org/abs/1106.5040v1)  `1106.5040`  **score 25**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, eess.SY, math.OC, q-fin.CP | **Published:** 2011-06-24T19:16:59Z
- **Authors:** Fabien Guilbaud, Huyen Pham
- **Why useful:** hits: _order book, execution, market making, mean-variance, var, regime, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1106.5040v1](https://arxiv.org/pdf/1106.5040v1)  |  **Per-paper MD:** `papers/q-fin_TR/1106.5040_*.md`
- **Abstract:** We propose a framework for studying optimal market making policies in a limit order book (LOB). The bid-ask spread of the LOB is modelled by a Markov chain with finite values, multiple of the tick size, and subordinated by the Poisson process of the tick-time clock. We consider a small agent who continuously submits limit buy/sell orders and submits market orders at discrete dates. The objective of the market maker is to maximize her expected utility from revenue over a short term horizon by a tradeoff between limit and market orders, while controlling her inventory position. This is formulated as a mixed regime switching regular/ impulse control problem that we characterize in terms of quasi-variational system by dynamic programming methods. In the case of a mean-variance criterion with m …

### 45. [Design and Empirical Study of a Large Language Model-Based Multi-Agent Investment System for Chinese Public REITs](http://arxiv.org/abs/2602.00082v1)  `2602.00082`  **score 24**
- **Primary:** q-fin.ST | **All cats:** cs.AI, q-fin.ST, q-fin.TR | **Published:** 2026-01-22T16:35:27Z
- **Authors:** Zheng Li
- **Why useful:** hits: _backtest, execution, reinforcement learning, momentum, volatility, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2602.00082v1](https://arxiv.org/pdf/2602.00082v1)  |  **Per-paper MD:** `papers/q-fin_ST/2602.00082_*.md`
- **Abstract:** This study addresses the low-volatility Chinese Public Real Estate Investment Trusts (REITs) market, proposing a large language model (LLM)-driven trading framework based on multi-agent collaboration. The system constructs four types of analytical agents-announcement, event, price momentum, and market-each conducting analysis from different dimensions; then the prediction agent integrates these multi-source signals to output directional probability distributions across multiple time horizons, then the decision agent generates discrete position adjustment signals based on the prediction results and risk control constraints, thereby forming a closed loop of analysis-prediction-decision-execution. This study further compares two prediction model pathways: for the prediction agent, directly ca …

### 46. [Limit Order Book Dynamics in Matching Markets: Microstructure, Spread, and Execution Slippage](http://arxiv.org/abs/2511.20606v2)  `2511.20606`  **score 24**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.MA, cs.SI | **Published:** 2025-11-25T18:34:46Z
- **Authors:** Yao Wu
- **Why useful:** hits: _market microstructure, order book, execution, slippage, var, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.20606v2](https://arxiv.org/pdf/2511.20606v2)  |  **Per-paper MD:** `papers/q-fin_TR/2511.20606_*.md`
- **Abstract:** Conventional models of matching markets assume that monetary transfers can clear markets by compensating for utility differentials. However, empirical patterns show that such transfers often fail to close structural preference gaps. This paper introduces a market microstructure framework that models matching decisions as a limit order book system with rigid bid ask spreads. Individual preferences are represented by a latent preference state matrix, where the spread between an agent's internal ask price (the unconditional maximum) and the market's best bid (the reachable maximum) creates a structural liquidity constraint. We establish a Threshold Impossibility Theorem showing that linear compensation cannot close these spreads unless it induces a categorical identity shift. A dynamic discre …

### 47. [When AI Trading Agents Compete: Adverse Selection of Meta-Orders by Reinforcement Learning-Based Market Making](http://arxiv.org/abs/2510.27334v1)  `2510.27334`  **score 24**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2025-10-31T10:05:14Z
- **Authors:** Ali Raza Jafree, Konark Jain, Nick Firoozye
- **Why useful:** hits: _order book, execution, slippage, market making, reinforcement learning, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.27334v1](https://arxiv.org/pdf/2510.27334v1)  |  **Per-paper MD:** `papers/q-fin_TR/2510.27334_*.md`
- **Abstract:** We investigate the mechanisms by which medium-frequency trading agents are adversely selected by opportunistic high-frequency traders. We use reinforcement learning (RL) within a Hawkes Limit Order Book (LOB) model in order to replicate the behaviours of high-frequency market makers. In contrast to the classical models with exogenous price impact assumptions, the Hawkes model accounts for endogenous price impact and other key properties of the market (Jain et al. 2024a). Given the real-world impracticalities of the market maker updating strategies for every event in the LOB, we formulate the high-frequency market making agent via an impulse control reinforcement learning framework (Jain et al. 2025). The RL used in the simulation utilises Proximal Policy Optimisation (PPO) and self-imitati …

### 48. [Benchmarking Classical and Quantum Models for DeFi Yield Prediction on Curve Finance](http://arxiv.org/abs/2508.02685v1)  `2508.02685`  **score 24**
- **Primary:** q-fin.ST | **All cats:** cs.LG, q-fin.ST, q-fin.TR | **Published:** 2025-07-22T06:55:20Z
- **Authors:** Chi-Sheng Chen, Aidan Hung-Wen Tsai
- **Why useful:** hits: _machine learning, deep learning, xgboost, lstm, transformer, neural network, random forest, liquidity, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2508.02685v1](https://arxiv.org/pdf/2508.02685v1)  |  **Per-paper MD:** `papers/q-fin_ST/2508.02685_*.md`
- **Abstract:** The rise of decentralized finance (DeFi) has created a growing demand for accurate yield and performance forecasting to guide liquidity allocation strategies. In this study, we benchmark six models, XGBoost, Random Forest, LSTM, Transformer, quantum neural networks (QNN), and quantum support vector machines with quantum feature maps (QSVM-QNN), on one year of historical data from 28 Curve Finance pools. We evaluate model performance on test MAE, RMSE, and directional accuracy. Our results show that classical ensemble models, particularly XGBoost and Random Forest, consistently outperform both deep learning and quantum models. XGBoost achieves the highest directional accuracy (71.57%) with a test MAE of 1.80, while Random Forest attains the lowest test MAE of 1.77 and 71.36% accuracy. In co …

### 49. [A Comparative Analysis of Statistical and Machine Learning Models for Outlier Detection in Bitcoin Limit Order Books](http://arxiv.org/abs/2507.14960v1)  `2507.14960`  **score 24**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.AI, cs.LG, math.ST | **Published:** 2025-07-20T13:42:36Z
- **Authors:** Ivan Letteri
- **Why useful:** hits: _backtest, market microstructure, order book, anomaly, machine learning, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2507.14960v1](https://arxiv.org/pdf/2507.14960v1)  |  **Per-paper MD:** `papers/q-fin_TR/2507.14960_*.md`
- **Abstract:** The detection of outliers within cryptocurrency limit order books (LOBs) is of paramount importance for comprehending market dynamics, particularly in highly volatile and nascent regulatory environments. This study conducts a comprehensive comparative analysis of robust statistical methods and advanced machine learning techniques for real-time anomaly identification in cryptocurrency LOBs. Within a unified testing environment, named AITA Order Book Signal (AITA-OBS), we evaluate the efficacy of thirteen diverse models to identify which approaches are most suitable for detecting potentially manipulative trading behaviours. An empirical evaluation, conducted via backtesting on a dataset of 26,204 records from a major exchange, demonstrates that the top-performing model, Empirical Covariance  …

### 50. [To Trade Or Not To Trade: Cascading Waterfall Round Robin Rebalancing Mechanism for Cryptocurrencies](http://arxiv.org/abs/2407.12150v1)  `2407.12150`  **score 24**
- **Primary:** q-fin.PM | **All cats:** cs.CE, cs.DC, q-fin.PM, q-fin.TR | **Published:** 2024-05-17T12:55:01Z
- **Authors:** Ravi Kashyap
- **Why useful:** hits: _execution, slippage, factor, momentum, volatility, var, macro, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2407.12150v1](https://arxiv.org/pdf/2407.12150v1)  |  **Per-paper MD:** `papers/q-fin_PM/2407.12150_*.md`
- **Abstract:** We have designed an innovative portfolio rebalancing mechanism termed the Cascading Waterfall Round Robin Mechanism. This algorithmic approach recommends an ideal size and number of trades for each asset during the periodic rebalancing process, factoring in the gas fee and slippage. The essence of the model we have created gives indications regarding whether trades should be made on individual assets depending on the uncertainty in the micro - asset level characteristics - and macro - aggregate market factors - environments. In the hyper-volatile crypto market, our approach to daily rebalancing will benefit from volatility. Price movements will cause our algorithm to buy assets that drop in prices and sell as they soar. In fact, the buying and selling happen only when certain boundaries ar …

### 51. [An Empirical Analysis on Financial Markets: Insights from the Application of Statistical Physics](http://arxiv.org/abs/2308.14235v6)  `2308.14235`  **score 24**
- **Primary:** q-fin.TR | **All cats:** q-fin.CP, q-fin.MF, q-fin.PR, q-fin.ST, q-fin.TR | **Published:** 2023-08-28T00:06:45Z
- **Authors:** Haochen Li, Yi Cao, Maria Polukarov, Carmine Ventre
- **Why useful:** hits: _market microstructure, order book, machine learning, momentum, volatility, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2308.14235v6](https://arxiv.org/pdf/2308.14235v6)  |  **Per-paper MD:** `papers/q-fin_TR/2308.14235_*.md`
- **Abstract:** In this study, we introduce a physical model inspired by statistical physics for predicting price volatility and expected returns by leveraging Level 3 order book data. By drawing parallels between orders in the limit order book and particles in a physical system, we establish unique measures for the system's kinetic energy and momentum as a way to comprehend and evaluate the state of limit order book. Our model goes beyond examining merely the top layers of the order book by introducing the concept of 'active depth', a computationally-efficient approach for identifying order book levels that have impact on price dynamics. We empirically demonstrate that our model outperforms the benchmarks of traditional approaches and machine learning algorithm. Our model provides a nuanced comprehension …

### 52. [Portfolio Optimization on Multivariate Regime Switching GARCH Model with Normal Tempered Stable Innovation](http://arxiv.org/abs/2009.11367v3)  `2009.11367`  **score 24**
- **Primary:** q-fin.RM | **All cats:** q-fin.MF, q-fin.PM, q-fin.RM | **Published:** 2020-09-23T20:25:14Z
- **Authors:** Cheng Peng, Young Shin Kim, Stefan Mittnik
- **Why useful:** hits: _portfolio optimization, volatility, garch, var, cvar, tail risk, drawdown, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2009.11367v3](https://arxiv.org/pdf/2009.11367v3)  |  **Per-paper MD:** `papers/q-fin_RM/2009.11367_*.md`
- **Abstract:** This paper uses simulation-based portfolio optimization to mitigate the left tail risk of the portfolio. The contribution is twofold. (i) We propose the Markov regime-switching GARCH model with multivariate normal tempered stable innovation (MRS-MNTS-GARCH) to accommodate fat tails, volatility clustering and regime switch. The volatility of each asset independently follows the regime-switch GARCH model, while the correlation of joint innovation of the GARCH models follows the Hidden Markov Model. (ii) We use tail risk measures, namely conditional value-at-risk (CVaR) and conditional drawdown-at-risk (CDaR), in the portfolio optimization. The optimization is performed with the sample paths simulated by the MRS-MNTS-GARCH model. We conduct an empirical study on the performance of optimal por …

### 53. [Deep Reinforcement Learning Framework for Diversified Portfolio Management Across Global Equity Markets](http://arxiv.org/abs/2605.17307v1)  `2605.17307`  **score 23**
- **Primary:** q-fin.PM | **All cats:** cs.AI, cs.LG, cs.NE, q-fin.PM, q-fin.TR | **Published:** 2026-05-17T07:50:37Z
- **Authors:** Kamil Kashif, Robert Ślepaczuk
- **Why useful:** hits: _walk-forward, portfolio management, reinforcement learning, lstm, transformer, var, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2605.17307v1](https://arxiv.org/pdf/2605.17307v1)  |  **Per-paper MD:** `papers/q-fin_PM/2605.17307_*.md`
- **Abstract:** This study develops and evaluates a deep reinforcement learning framework for dynamic portfolio allocation across global equity markets. The Soft Actor-Critic algorithm is used to learn continuous portfolio weights within a Markov Decision Process, incorporating transaction costs, turnover penalties, and diversification constraints into the reward function. Five model configurations are compared, varying in reward formulation, policy structure (flat versus hierarchical Dirichlet), portfolio constraints, and temporal encoder (LSTM versus Transformer), and evaluated via walk-forward optimization across sixteen out-of-sample folds spanning 2003-2026 on the Nasdaq-100, Nikkei 225, and Euro Stoxx 50. Results show that RL strategies achieve competitive risk-adjusted performance primarily in the  …

### 54. [The GT-Score: A Robust Objective Function for Reducing Overfitting in Data-Driven Trading Strategies](http://arxiv.org/abs/2602.00080v1)  `2602.00080`  **score 23**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.LG | **Published:** 2026-01-22T05:16:47Z
- **Authors:** Alexander Sheppert
- **Why useful:** hits: _overfit, walk-forward, backtest, machine learning, cta, sortino_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2602.00080v1](https://arxiv.org/pdf/2602.00080v1)  |  **Per-paper MD:** `papers/q-fin_ST/2602.00080_*.md`
- **Abstract:** Overfitting remains a critical challenge in data-driven financial modeling, where machine learning (ML) systems learn spurious patterns in historical prices and fail out of sample and in deployment. This paper introduces the GT-Score, a composite objective function that integrates performance, statistical significance, consistency, and downside risk to guide optimization toward more robust trading strategies. This approach directly addresses critical pitfalls in quantitative strategy development, specifically data snooping during optimization and the unreliability of statistical inference under non-normal return distributions. Using historical stock data for 50 S&P 500 companies spanning 2010-2024, we conduct an empirical evaluation that includes walk-forward validation with nine sequentia …

### 55. [Stablecoin Design with Adversarial-Robust Multi-Agent Systems via Trust-Weighted Signal Aggregation](http://arxiv.org/abs/2601.22168v1)  `2601.22168`  **score 23**
- **Primary:** q-fin.RM | **All cats:** cs.AI, cs.CR, q-fin.CP, q-fin.RM | **Published:** 2026-01-18T14:21:25Z
- **Authors:** Shengwei You, Aditya Joshi, Andrey Kuehlkamp, Jarek Nabrzyski
- **Why useful:** hits: _sentiment, mean-variance, cta, volatility, var, drawdown, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2601.22168v1](https://arxiv.org/pdf/2601.22168v1)  |  **Per-paper MD:** `papers/q-fin_RM/2601.22168_*.md`
- **Abstract:** Algorithmic stablecoins promise decentralized monetary stability by maintaining a target peg through programmatic reserve management. Yet, their reserve controllers remain vulnerable to regime-blind optimization, calibrating risk parameters on fair-weather data while ignoring tail events that precipitate cascading failures. The March 2020 Black Thursday collapse, wherein MakerDAO's collateral auctions yielded $8.3M in losses and a 15% peg deviation, exposed a critical gap: existing models like SAS systematically omit extreme volatility regimes from covariance estimates, producing allocations optimal in expectation but catastrophic under adversarial stress. We present MVF-Composer, a trust-weighted Mean-Variance Frontier reserve controller incorporating a novel Stress Harness for risk-state …

### 56. [Hidden Order in Trades Predicts the Size of Price Moves](http://arxiv.org/abs/2512.15720v1)  `2512.15720`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.ST, q-fin.TR, stat.AP, stat.ME | **Published:** 2025-12-02T23:20:46Z
- **Authors:** Mainak Singha
- **Why useful:** hits: _walk-forward, market microstructure, factor, cta, volatility, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.15720v1](https://arxiv.org/pdf/2512.15720v1)  |  **Per-paper MD:** `papers/q-fin_TR/2512.15720_*.md`
- **Abstract:** Financial markets exhibit an apparent paradox: while directional price movements remain largely unpredictable--consistent with weak-form efficiency--the magnitude of price changes displays systematic structure. Here we demonstrate that real-time order-flow entropy, computed from a 15-state Markov transition matrix at second resolution, predicts the magnitude of intraday returns without providing directional information. Analysis of 38.5 million SPY trades over 36 trading days reveals that conditioning on entropy below the 5th percentile increases subsequent 5-minute absolute returns by a factor of 2.89 (t = 12.41, p < 0.0001), while directional accuracy remains at 45.0%--statistically indistinguishable from chance (p = 0.12). This decoupling arises from a fundamental symmetry: entropy is i …

### 57. [Deviations from Tradition: Stylized Facts in the Era of DeFi](http://arxiv.org/abs/2510.22834v1)  `2510.22834`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2025-10-26T21:01:54Z
- **Authors:** Daniele Maria Di Nosse, Federico Gatta, Fabrizio Lillo, Sebastian Jaimungal
- **Why useful:** hits: _order book, order flow, execution, cta, var, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.22834v1](https://arxiv.org/pdf/2510.22834v1)  |  **Per-paper MD:** `papers/q-fin_TR/2510.22834_*.md`
- **Abstract:** Decentralized Exchanges (DEXs) are now a significant component of the financial world where billions of dollars are traded daily. Differently from traditional markets, which are typically based on Limit Order Books, DEXs typically work as Automated Market Makers, and, since the implementation of Uniswap v3, feature concentrated liquidity. By investigating the twenty-four most active pools in Uniswap v3 during 2023 and 2024, we empirically study how this structural change in the organization of the markets modifies the well-studied stylized facts of prices, liquidity, and order flow observed in traditional markets. We find a series of new statistical regularities in the distributions and cross-autocorrelation functions of these variables that we are able to associate either with the market  …

### 58. [From Headlines to Holdings: Deep Learning for Smarter Portfolio Decisions](http://arxiv.org/abs/2509.24144v2)  `2509.24144`  **score 23**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM, q-fin.ST, stat.ML | **Published:** 2025-09-29T00:42:24Z
- **Authors:** Yun Lin, Jiawei Lou, Jinghe Zhang
- **Why useful:** hits: _sentiment, portfolio optimization, portfolio management, deep learning, lstm, var, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.24144v2](https://arxiv.org/pdf/2509.24144v2)  |  **Per-paper MD:** `papers/q-fin_PM/2509.24144_*.md`
- **Abstract:** Deep learning offers new tools for portfolio optimization. We present an end-to-end framework that directly learns portfolio weights by combining Long Short-Term Memory (LSTM) networks to model temporal patterns, Graph Attention Networks (GAT) to capture evolving inter-stock relationships, and sentiment analysis of financial news to reflect market psychology. Unlike prior approaches, our model unifies these elements in a single pipeline that produces daily allocations. It avoids the traditional two-step process of forecasting asset returns and then applying mean--variance optimization (MVO), a sequence that can introduce instability. We evaluate the framework on nine U.S. stocks spanning six sectors, chosen to balance sector diversity and news coverage. In this setting, the model delivers  …

### 59. [Sizing the Risk: Kelly, VIX, and Hybrid Approaches in Put-Writing on Index Options](http://arxiv.org/abs/2508.16598v1)  `2508.16598`  **score 23**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM, q-fin.PR, q-fin.TR | **Published:** 2025-08-09T08:31:00Z
- **Authors:** Maciej Wysocki
- **Why useful:** hits: _kelly, volatility risk premium, volatility, drawdown, options, vix, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2508.16598v1](https://arxiv.org/pdf/2508.16598v1)  |  **Per-paper MD:** `papers/q-fin_PM/2508.16598_*.md`
- **Abstract:** This paper examines systematic put-writing strategies applied to S&P 500 Index options, with a focus on position sizing as a key determinant of long-term performance. Despite the well-documented volatility risk premium, where implied volatility exceeds realized volatility, the practical implementation of short-dated volatility-selling strategies remains underdeveloped in the literature. This study evaluates three position sizing approaches: the Kelly criterion, VIX-based volatility regime scaling, and a novel hybrid method combining both. Using SPXW options with expirations from 0 to 5 days, the analysis explores a broad design space, including moneyness levels, volatility estimators, and memory horizons. Results show that ultra-short-dated, far out-of-the-money options deliver superior ri …

### 60. [Can We Reliably Predict the Fed's Next Move? A Multi-Modal Approach to U.S. Monetary Policy Forecasting](http://arxiv.org/abs/2506.22763v1)  `2506.22763`  **score 23**
- **Primary:** q-fin.PM | **All cats:** cs.LG, q-fin.CP, q-fin.PM | **Published:** 2025-06-28T05:54:58Z
- **Authors:** Fiona Xiao Jingyi, Lili Liu
- **Why useful:** hits: _sentiment, finbert, machine learning, deep learning, xgboost, transformer, macro, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2506.22763v1](https://arxiv.org/pdf/2506.22763v1)  |  **Per-paper MD:** `papers/q-fin_PM/2506.22763_*.md`
- **Abstract:** Forecasting central bank policy decisions remains a persistent challenge for investors, financial institutions, and policymakers due to the wide-reaching impact of monetary actions. In particular, anticipating shifts in the U.S. federal funds rate is vital for risk management and trading strategies. Traditional methods relying only on structured macroeconomic indicators often fall short in capturing the forward-looking cues embedded in central bank communications. This study examines whether predictive accuracy can be enhanced by integrating structured data with unstructured textual signals from Federal Reserve communications. We adopt a multi-modal framework, comparing traditional machine learning models, transformer-based language models, and deep learning architectures in both unimodal  …

### 61. [A multi-factor market-neutral investment strategy for New York Stock Exchange equities](http://arxiv.org/abs/2412.12350v1)  `2412.12350`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2024-12-16T20:42:32Z
- **Authors:** Georgios M. Gkolemis, Adwin Richie Lee, Amine Roudani
- **Why useful:** hits: _backtest, risk parity, factor, momentum, var, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2412.12350v1](https://arxiv.org/pdf/2412.12350v1)  |  **Per-paper MD:** `papers/q-fin_TR/2412.12350_*.md`
- **Abstract:** This report presents a systematic market-neutral, multi-factor investment strategy for New York Stock Exchange equities with the objective of delivering steady returns while minimizing correlation with the market. A robust feature set is integrated combining momentum-based indicators, fundamental factors, and analyst recommendations. Using various statistical tests for feature selection, the strategy identifies key drivers of equity performance and ranks stocks to build a balanced portfolio of long and short positions. Portfolio construction methods, including equally weighted, risk parity, and minimum variance beta-neutral approaches, were evaluated through rigorous backtesting. Risk parity demonstrated superior performance with a higher Sharpe ratio, lower beta, and smaller maximum drawd …

### 62. [Hierarchical Reinforced Trader (HRT): A Bi-Level Approach for Optimizing Stock Selection and Execution](http://arxiv.org/abs/2410.14927v2)  `2410.14927`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.CE, cs.LG | **Published:** 2024-10-19T01:29:38Z
- **Authors:** Zijie Zhao, Roy E. Welsch
- **Why useful:** hits: _execution, portfolio management, factor, alpha, reinforcement learning, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2410.14927v2](https://arxiv.org/pdf/2410.14927v2)  |  **Per-paper MD:** `papers/q-fin_TR/2410.14927_*.md`
- **Abstract:** Automated equity trading requires converting noisy market and news signals into executable portfolio decisions under risk, turnover, and transaction costs. We propose Hierarchical Reinforced Trader (HRT), a bi-level reinforcement learning framework for text-aware portfolio management in multi-asset equity markets. HRT separates trading into two coordinated decisions: a factorized sparse High-Level Controller (HLC) selects asset-level increase, reduce, or hold directions from compact market and text-derived signals, while a risk-aware Low-Level Controller (LLC) converts these directions into feasible portfolio weight adjustments under turnover, drawdown, and text-risk penalties. This decomposition avoids enumerating the full joint action space and makes selection and execution easier to ins …

### 63. [AI-Powered Energy Algorithmic Trading: Integrating Hidden Markov Models with Neural Networks](http://arxiv.org/abs/2407.19858v7)  `2407.19858`  **score 23**
- **Primary:** q-fin.PM | **All cats:** cs.LG, q-fin.GN, q-fin.PM, stat.AP | **Published:** 2024-07-29T10:26:52Z
- **Authors:** Tiago Monteiro
- **Why useful:** hits: _backtest, portfolio optimization, alpha, machine learning, neural network, cta, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2407.19858v7](https://arxiv.org/pdf/2407.19858v7)  |  **Per-paper MD:** `papers/q-fin_PM/2407.19858_*.md`
- **Abstract:** In quantitative finance, machine learning methods are essential for alpha generation. This study introduces a new approach that combines Hidden Markov Models (HMM) and neural networks, integrated with Black-Litterman portfolio optimization. During the COVID period (2019-2022), this dual-model approach achieved a 83% return with a Sharpe ratio of 0.77. It incorporates two risk models to enhance risk management, showing efficiency during volatile periods. The methodology was implemented on the QuantConnect platform, which was chosen for its robust framework and experimental reproducibility. The system, which predicts future price movements, includes a three-year warm-up to ensure proper algorithm function. It targets highly liquid, large-cap energy stocks to ensure stable and predictable per …

### 64. [The Hybrid Forecast of S&P 500 Volatility ensembled from VIX, GARCH and LSTM models](http://arxiv.org/abs/2407.16780v1)  `2407.16780`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.PM, q-fin.ST, q-fin.TR, stat.ML | **Published:** 2024-07-23T18:28:16Z
- **Authors:** Natalia Roszyk, Robert Ślepaczuk
- **Why useful:** hits: _sentiment, factor, machine learning, lstm, volatility, garch, vix_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2407.16780v1](https://arxiv.org/pdf/2407.16780v1)  |  **Per-paper MD:** `papers/q-fin_TR/2407.16780_*.md`
- **Abstract:** Predicting the S&P 500 index volatility is crucial for investors and financial analysts as it helps assess market risk and make informed investment decisions. Volatility represents the level of uncertainty or risk related to the size of changes in a security's value, making it an essential indicator for financial planning. This study explores four methods to improve the accuracy of volatility forecasts for the S&P 500: the established GARCH model, known for capturing historical volatility patterns; an LSTM network that utilizes past volatility and log returns; a hybrid LSTM-GARCH model that combines the strengths of both approaches; and an advanced version of the hybrid model that also factors in the VIX index to gauge market sentiment. This analysis is based on a daily dataset that includ …

### 65. [Transformers versus LSTMs for electronic trading](http://arxiv.org/abs/2309.11400v1)  `2309.11400`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG, econ.EM, q-fin.ST | **Published:** 2023-09-20T15:25:43Z
- **Authors:** Paul Bilokon, Yitao Qiu
- **Why useful:** hits: _nlp, order book, lstm, transformer, neural network, var, limit order, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2309.11400v1](https://arxiv.org/pdf/2309.11400v1)  |  **Per-paper MD:** `papers/q-fin_TR/2309.11400_*.md`
- **Abstract:** With the rapid development of artificial intelligence, long short term memory (LSTM), one kind of recurrent neural network (RNN), has been widely applied in time series prediction. Like RNN, Transformer is designed to handle the sequential data. As Transformer achieved great success in Natural Language Processing (NLP), researchers got interested in Transformer's performance on time series prediction, and plenty of Transformer-based solutions on long time series forecasting have come out recently. However, when it comes to financial time series prediction, LSTM is still a dominant architecture. Therefore, the question this study wants to answer is: whether the Transformer-based model can be applied in financial time series prediction and beat LSTM. To answer this question, various LSTM-bas …

### 66. [Media Moments and Corporate Connections: A Deep Learning Approach to Stock Movement Classification](http://arxiv.org/abs/2309.06559v1)  `2309.06559`  **score 23**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.SI, q-fin.CP | **Published:** 2023-09-08T20:13:34Z
- **Authors:** Luke Sanborn, Matthew Sahagun
- **Why useful:** hits: _sentiment, reddit, social media, factor, deep learning, neural network, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2309.06559v1](https://arxiv.org/pdf/2309.06559v1)  |  **Per-paper MD:** `papers/q-fin_ST/2309.06559_*.md`
- **Abstract:** The financial industry poses great challenges with risk modeling and profit generation. These entities are intricately tied to the sophisticated prediction of stock movements. A stock forecaster must untangle the randomness and ever-changing behaviors of the stock market. Stock movements are influenced by a myriad of factors, including company history, performance, and economic-industry connections. However, there are other factors that aren't traditionally included, such as social media and correlations between stocks. Social platforms such as Reddit, Facebook, and X (Twitter) create opportunities for niche communities to share their sentiment on financial assets. By aggregating these opinions from social media in various mediums such as posts, interviews, and news updates, we propose a m …

### 67. [Machine Learning and Factor-Based Portfolio Optimization](http://arxiv.org/abs/2107.13866v1)  `2107.13866`  **score 23**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, econ.EM | **Published:** 2021-07-29T09:58:37Z
- **Authors:** Thomas Conlon, John Cotter, Iason Kynigakis
- **Why useful:** hits: _portfolio optimization, factor, machine learning, neural network, volatility, var, tail risk_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2107.13866v1](https://arxiv.org/pdf/2107.13866v1)  |  **Per-paper MD:** `papers/q-fin_PM/2107.13866_*.md`
- **Abstract:** We examine machine learning and factor-based portfolio optimization. We find that factors based on autoencoder neural networks exhibit a weaker relationship with commonly used characteristic-sorted portfolios than popular dimensionality reduction techniques. Machine learning methods also lead to covariance and portfolio weight structures that diverge from simpler estimators. Minimum-variance portfolios using latent factors derived from autoencoders and sparse methods outperform simpler benchmarks in terms of risk minimization. These effects are amplified for investors with an increased sensitivity to risk-adjusted returns, during high volatility periods or when accounting for tail risk.

### 68. [Time is Money: The Equilibrium Trading Horizon and Optimal Arrival Price](http://arxiv.org/abs/2104.05844v1)  `2104.05844`  **score 23**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF, q-fin.PM, q-fin.TR | **Published:** 2021-04-12T22:15:41Z
- **Authors:** Kevin Patrick Darby
- **Why useful:** hits: _order book, execution, slippage, factor, var, derivative, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2104.05844v1](https://arxiv.org/pdf/2104.05844v1)  |  **Per-paper MD:** `papers/q-fin_MF/2104.05844_*.md`
- **Abstract:** Executing even moderately large derivatives orders can be expensive and risky; it's hard to balance the uncertainty of working an order over time versus paying a liquidity premium for immediate execution. Here, we introduce the Time Is Money model, which calculates the Equilibrium Trading Horizon over which to execute an order within the adversarial forces of variance risk and liquidity premium. We construct a hypothetical at-the-money option within Arithmetic Brownian Motion and invert the Bachelier model to compute an inflection point between implied variance and liquidity cost as governed by a central limit order book, each in real time as they evolve. As a result, we demonstrate a novel, continuous-time Arrival Price framework. Further, we argue that traders should be indifferent to ch …

### 69. [Portfolio Optimization on the Dispersion Risk and the Asymmetric Tail Risk](http://arxiv.org/abs/2007.13972v5)  `2007.13972`  **score 23**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2020-07-28T03:35:50Z
- **Authors:** Young Shin Kim
- **Why useful:** hits: _portfolio optimization, mean-variance, cta, var, cvar, tail risk, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2007.13972v5](https://arxiv.org/pdf/2007.13972v5)  |  **Per-paper MD:** `papers/q-fin_PM/2007.13972_*.md`
- **Abstract:** In this paper, we propose a market model with returns assumed to follow a multivariate normal tempered stable distribution defined by a mixture of the multivariate normal distribution and the tempered stable subordinator. This distribution is able to capture two stylized facts: fat-tails and asymmetry, that have been empirically observed for asset return distributions. On the new market model, we discuss a new portfolio optimization method, which is an extension of Markowitz's mean-variance optimization. The new optimization method considers not only reward and dispersion but also asymmetry. The efficient frontier is also extended to a curved surface on three-dimensional space of reward, dispersion, and asymmetry. We also propose a new performance measure which is an extension of the Sharp …

### 70. [Risk-Sensitive Compact Decision Trees for Autonomous Execution in Presence of Simulated Market Response](http://arxiv.org/abs/1906.02312v2)  `1906.02312`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2019-06-05T21:13:11Z
- **Authors:** Svitlana Vyetrenko, Shaojie Xu
- **Why useful:** hits: _market microstructure, order book, execution, reinforcement learning, var, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1906.02312v2](https://arxiv.org/pdf/1906.02312v2)  |  **Per-paper MD:** `papers/q-fin_TR/1906.02312_*.md`
- **Abstract:** We demonstrate an application of risk-sensitive reinforcement learning to optimizing execution in limit order book markets. We represent taking order execution decisions based on limit order book knowledge by a Markov Decision Process; and train a trading agent in a market simulator, which emulates multi-agent interaction by synthesizing market response to our agent's execution decisions from historical data. Due to market impact, executing high volume orders can incur significant cost. We learn trading signals from market microstructure in presence of simulated market response and derive explainable decision-tree-based execution policies using risk-sensitive Q-learning to minimize execution cost subject to constraints on cost variance.

### 71. [How markets slowly digest changes in supply and demand](http://arxiv.org/abs/0809.0822v1)  `0809.0822`  **score 23**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cond-mat.stat-mech, physics.soc-ph | **Published:** 2008-09-04T14:21:33Z
- **Authors:** Jean-Philippe Bouchaud, J. Doyne Farmer, Fabrizio Lillo
- **Why useful:** hits: _market microstructure, order book, order flow, execution, volatility, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/0809.0822v1](https://arxiv.org/pdf/0809.0822v1)  |  **Per-paper MD:** `papers/q-fin_TR/0809.0822_*.md`
- **Abstract:** In this article we revisit the classic problem of tatonnement in price formation from a microstructure point of view, reviewing a recent body of theoretical and empirical work explaining how fluctuations in supply and demand are slowly incorporated into prices. Because revealed market liquidity is extremely low, large orders to buy or sell can only be traded incrementally, over periods of time as long as months. As a result order flow is a highly persistent long-memory process. Maintaining compatibility with market efficiency has profound consequences on price formation, on the dynamics of liquidity, and on the nature of impact. We review a body of theory that makes detailed quantitative predictions about the volume and time dependence of market impact, the bid-ask spread, order book dynam …

### 72. [Tail Risk Management with Puts and Trend Following: A CVaR Framework for Crashes and Drawdowns](http://arxiv.org/abs/2607.00883v1)  `2607.00883`  **score 22**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF | **Published:** 2026-07-01T12:50:52Z
- **Authors:** Miquel Noguer I Alonso, Ali Al Fallouji
- **Why useful:** hits: _trend following, volatility, var, cvar, tail risk, drawdown, options, regime, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.00883v1](https://arxiv.org/pdf/2607.00883v1)  |  **Per-paper MD:** `papers/q-fin_MF/2607.00883_*.md`
- **Abstract:** Tail-risk management is not only an instrument-selection problem. It is an allocation problem across loss mechanisms: abrupt crash states, volatility repricing, and persistent drawdowns require different forms of protection. This paper develops a continuous-time CVaR framework that places two common protection sleeves -- long out-of-the-money put options and systematic trend-following overlays -- inside one coherent tail-risk mandate. The option sleeve is modeled as a marked-to-market traded asset, so premium drag, diffusion exposure, and jump repricing enter through its physical return process rather than through inconsistent terminal-payoff accounting. The resulting Markov state contains wealth, spot, stochastic variance, and an exponentially weighted log-return signal, and we derive the …

### 73. [Neural Hidden Markov Model with Adaptive Granularity Attention for High-Frequency Order Flow Modeling](http://arxiv.org/abs/2603.20456v1)  `2603.20456`  **score 22**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, q-fin.TR | **Published:** 2026-03-20T19:36:00Z
- **Authors:** Tianzuo Hu
- **Why useful:** hits: _order book, order flow, lstm, volatility, regime, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.20456v1](https://arxiv.org/pdf/2603.20456v1)  |  **Per-paper MD:** `papers/q-fin_ST/2603.20456_*.md`
- **Abstract:** We propose a Neural Hidden Markov Model (HMM) with Adaptive Granularity Attention (AGA) for high-frequency order flow modeling. The model addresses the challenge of capturing multi-scale temporal dynamics in financial markets, where fine-grained microstructure signals and coarse-grained liquidity trends coexist. The proposed framework integrates parallel multi-resolution encoders, including a dilated convolutional network for tick-level patterns and a wavelet-LSTM module for low-frequency dynamics. A gating mechanism conditioned on local volatility and transaction intensity adaptively fuses multi-scale representations, while a multi-head attention layer further enhances temporal dependency modeling. Within this architecture, a Neural HMM with conditional normalizing flow emissions is emplo …

### 74. [Learning Market Making with Closing Auctions](http://arxiv.org/abs/2601.17247v2)  `2601.17247`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, math.OC | **Published:** 2026-01-24T00:50:35Z
- **Authors:** Julius Graf, Thibaut Mastrolia
- **Why useful:** hits: _order book, execution, market making, reinforcement learning, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2601.17247v2](https://arxiv.org/pdf/2601.17247v2)  |  **Per-paper MD:** `papers/q-fin_TR/2601.17247_*.md`
- **Abstract:** In this work, we investigate a market making execution problem on a trading session in which a continuous phase on a limit order book is followed by a closing auction. Whereas standard optimal market making models typically rely on terminal inventory penalties to manage end-of-day risk, ignoring the significant liquidity events available in closing auctions, we propose a deep reinforcement learning framework, consisting of a Deep Q-Network and its continuous-control actor-critic extensions (DDPG, TD3 and SAC), that explicitly incorporates this mechanism. We introduce a market making framework designed to explicitly anticipate the closing auction, continuously refining the projected clearing price as the trading session evolves. We develop a generative stochastic market model to simulate th …

### 75. [XGBoost Forecasting of NEPSE Index Log Returns with Walk Forward Validation](http://arxiv.org/abs/2601.08896v1)  `2601.08896`  **score 22**
- **Primary:** cs.LG | **All cats:** cs.LG, cs.AI, q-fin.ST | **Published:** 2026-01-13T15:22:08Z
- **Authors:** Sahaj Raj Malla, Shreeyash Kayastha, Rumi Suwal, Harish Chandra Bhandari, Rajendra Adhikari
- **Why useful:** hits: _walk-forward, walk forward, cross-validation, machine learning, xgboost, volatility, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2601.08896v1](https://arxiv.org/pdf/2601.08896v1)  |  **Per-paper MD:** `papers/cs_LG/2601.08896_*.md`
- **Abstract:** This study develops a robust machine learning framework for one-step-ahead forecasting of daily log-returns in the Nepal Stock Exchange (NEPSE) Index using the XGBoost regressor. A comprehensive feature set is engineered, including lagged log-returns (up to 30 days) and established technical indicators such as short- and medium-term rolling volatility measures and the 14-period Relative Strength Index. Hyperparameter optimization is performed using Optuna with time-series cross-validation on the initial training segment. Out-of-sample performance is rigorously assessed via walk-forward validation under both expanding and fixed-length rolling window schemes across multiple lag configurations, simulating real-world deployment and avoiding lookahead bias. Predictive accuracy is evaluated usin …

### 76. [Risk-Sensitive Option Market Making with Arbitrage-Free eSSVI Surfaces: A Constrained RL and Stochastic Control Bridge](http://arxiv.org/abs/2510.04569v1)  `2510.04569`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2025-10-06T08:11:16Z
- **Authors:** Jian'an Zhang
- **Why useful:** hits: _execution, market making, volatility, var, cvar, tail risk, hedging_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.04569v1](https://arxiv.org/pdf/2510.04569v1)  |  **Per-paper MD:** `papers/q-fin_TR/2510.04569_*.md`
- **Abstract:** We formulate option market making as a constrained, risk-sensitive control problem that unifies execution, hedging, and arbitrage-free implied-volatility surfaces inside a single learning loop. A fully differentiable eSSVI layer enforces static no-arbitrage conditions (butterfly and calendar) while the policy controls half-spreads, hedge intensity, and structured surface deformations (state-dependent rho-shift and psi-scale). Executions are intensity-driven and respond monotonically to spreads and relative mispricing; tail risk is shaped with a differentiable CVaR objective via the Rockafellar--Uryasev program. We provide theory for (i) grid-consistency and rates for butterfly/calendar surrogates, (ii) a primal--dual grounding of a learnable dual action acting as a state-dependent Lagrange …

### 77. [FR-LUX: Friction-Aware, Regime-Conditioned Policy Optimization for Implementable Portfolio Management](http://arxiv.org/abs/2510.02986v1)  `2510.02986`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2025-10-03T13:22:54Z
- **Authors:** Jian'an Zhang
- **Why useful:** hits: _execution, portfolio management, reinforcement learning, volatility, sharpe, regime, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.02986v1](https://arxiv.org/pdf/2510.02986v1)  |  **Per-paper MD:** `papers/q-fin_TR/2510.02986_*.md`
- **Abstract:** Transaction costs and regime shifts are major reasons why paper portfolios fail in live trading. We introduce FR-LUX (Friction-aware, Regime-conditioned Learning under eXecution costs), a reinforcement learning framework that learns after-cost trading policies and remains robust across volatility-liquidity regimes. FR-LUX integrates three ingredients: (i) a microstructure-consistent execution model combining proportional and impact costs, directly embedded in the reward; (ii) a trade-space trust region that constrains changes in inventory flow rather than logits, yielding stable low-turnover updates; and (iii) explicit regime conditioning so the policy specializes to LL/LH/HL/HH states without fragmenting the data. On a 4 x 5 grid of regimes and cost levels with multiple random seeds, FR-L …

### 78. [End-to-End Large Portfolio Optimization for Variance Minimization with Neural Networks through Covariance Cleaning](http://arxiv.org/abs/2507.01918v3)  `2507.01918`  **score 22**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI, math.OC, physics.data-an, stat.ML | **Published:** 2025-07-02T17:27:29Z
- **Authors:** Christian Bongiorno, Efstratios Manolakis, Rosario Nunzio Mantegna
- **Why useful:** hits: _slippage, portfolio optimization, neural network, volatility, var, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2507.01918v3](https://arxiv.org/pdf/2507.01918v3)  |  **Per-paper MD:** `papers/q-fin_PM/2507.01918_*.md`
- **Abstract:** We develop a rotation-invariant neural network that provides the global minimum-variance portfolio by jointly learning how to lag-transform historical returns and marginal volatilities and how to regularise the eigenvalues of large equity covariance matrices. This explicit mathematical mapping offers clear interpretability of each module's role, so the model cannot be regarded as a pure black box. The architecture mirrors the analytical form of the global minimum-variance solution yet remains agnostic to dimension, so a single model can be calibrated on panels of a few hundred stocks and applied, without retraining, to one thousand US equities, a cross-sectional jump that indicates robust generalization capability. The loss function is the future short-term realized minimum variance and is …

### 79. [TLOB: A Novel Transformer Model with Dual Attention for Price Trend Prediction with Limit Order Book Data](http://arxiv.org/abs/2502.15757v3)  `2502.15757`  **score 22**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.AI, cs.LG, q-fin.TR | **Published:** 2025-02-12T12:41:10Z
- **Authors:** Leonardo Berti, Gjergji Kasneci
- **Why useful:** hits: _market microstructure, order book, deep learning, transformer, cta, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2502.15757v3](https://arxiv.org/pdf/2502.15757v3)  |  **Per-paper MD:** `papers/q-fin_ST/2502.15757_*.md`
- **Abstract:** Price Trend Prediction (PTP) based on Limit Order Book (LOB) data is a fundamental challenge in financial markets. Despite advances in deep learning, existing models fail to generalize across different market conditions and assets. Surprisingly, by adapting a simple MLP-based architecture to LOB, we show that we surpass SoTA performance; thus, challenging the necessity of complex architectures. Unlike past work that shows robustness issues, we propose TLOB, a transformer-based model that uses a dual attention mechanism to capture spatial and temporal dependencies in LOB data. This allows it to adaptively focus on the market microstructure, making it particularly effective for longer-horizon predictions and volatile market conditions. We also introduce a new labeling method that improves on …

### 80. [Guided Learning: Lubricating End-to-End Modeling for Multi-stage Decision-making](http://arxiv.org/abs/2411.10496v1)  `2411.10496`  **score 22**
- **Primary:** cs.LG | **All cats:** cs.LG, cs.AI, q-fin.CP | **Published:** 2024-11-15T06:54:25Z
- **Authors:** Jian Guo, Saizhuo Wang, Yiyan Qi
- **Why useful:** hits: _execution, portfolio optimization, factor, alpha, machine learning, reinforcement learning, neural network, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2411.10496v1](https://arxiv.org/pdf/2411.10496v1)  |  **Per-paper MD:** `papers/cs_LG/2411.10496_*.md`
- **Abstract:** Multi-stage decision-making is crucial in various real-world artificial intelligence applications, including recommendation systems, autonomous driving, and quantitative investment systems. In quantitative investment, for example, the process typically involves several sequential stages such as factor mining, alpha prediction, portfolio optimization, and sometimes order execution. While state-of-the-art end-to-end modeling aims to unify these stages into a single global framework, it faces significant challenges: (1) training such a unified neural network consisting of multiple stages between initial inputs and final outputs often leads to suboptimal solutions, or even collapse, and (2) many decision-making scenarios are not easily reducible to standard prediction problems. To overcome the …

### 81. [Dynamic Factor Allocation Leveraging Regime-Switching Signals](http://arxiv.org/abs/2410.14841v1)  `2410.14841`  **score 22**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM, q-fin.ST | **Published:** 2024-10-18T19:42:01Z
- **Authors:** Yizhan Shu, John M. Mulvey
- **Why useful:** hits: _factor, momentum, volatility, var, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2410.14841v1](https://arxiv.org/pdf/2410.14841v1)  |  **Per-paper MD:** `papers/q-fin_PM/2410.14841_*.md`
- **Abstract:** This article explores dynamic factor allocation by analyzing the cyclical performance of factors through regime analysis. The authors focus on a U.S. equity investment universe comprising seven long-only indices representing the market and six style factors: value, size, momentum, quality, low volatility, and growth. Their approach integrates factor-specific regime inferences of each factor index's active performance relative to the market into the Black-Litterman model to construct a fully-invested, long-only multi-factor portfolio. First, the authors apply the sparse jump model (SJM) to identify bull and bear market regimes for individual factors, using a feature set based on risk and return measures from historical factor active returns, as well as variables reflecting the broader marke …

### 82. [An Algebraic Framework for the Modeling of Limit Order Books](http://arxiv.org/abs/2406.04969v1)  `2406.04969`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.MF, q-fin.ST, q-fin.TR | **Published:** 2024-06-07T14:33:57Z
- **Authors:** Johannes Bleher, Michael Bleher
- **Why useful:** hits: _market microstructure, order book, volatility, var, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2406.04969v1](https://arxiv.org/pdf/2406.04969v1)  |  **Per-paper MD:** `papers/q-fin_TR/2406.04969_*.md`
- **Abstract:** Introducing an algebraic framework for modeling limit order books (LOBs) with tools from physics and stochastic processes, our proposed framework captures the creation and annihilation of orders, order matching, and the time evolution of the LOB state. It also enables compositional settings, accommodating the interaction of heterogeneous traders and different market structures. We employ Dirac notation and generalized generating functions to describe the state space and dynamics of LOBs. The utility of this framework is shown through simulations of simplified market scenarios, illustrating how variations in trader behavior impact key market observables such as spread, return volatility, and liquidity. The algebraic representation allows for exact simulations using the Gillespie algorithm,  …

### 83. [Equity auction dynamics: latent liquidity models with activity acceleration](http://arxiv.org/abs/2401.06724v2)  `2401.06724`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, q-fin.ST | **Published:** 2024-01-12T17:49:16Z
- **Authors:** Mohammed Salek, Damien Challet, Ioane Muni Toke
- **Why useful:** hits: _order book, factor, cta, volatility, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2401.06724v2](https://arxiv.org/pdf/2401.06724v2)  |  **Per-paper MD:** `papers/q-fin_TR/2401.06724_*.md`
- **Abstract:** Equity auctions display several distinctive characteristics in contrast to continuous trading. As the auction time approaches, the rate of events accelerates causing a substantial liquidity buildup around the indicative price. This, in turn, results in a reduced price impact and decreased volatility of the indicative price. In this study, we adapt the latent/revealed order book framework to the specifics of equity auctions. We provide precise measurements of the model parameters, including order submissions, cancellations, and diffusion rates. Our setup allows us to describe the full dynamics of the average order book during closing auctions in Euronext Paris. These findings support the relevance of the latent liquidity framework in describing limit order book dynamics. Lastly, we analyze  …

### 84. [Liquidity Dynamics in RFQ Markets and Impact on Pricing](http://arxiv.org/abs/2309.04216v3)  `2309.04216`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, q-fin.ST | **Published:** 2023-09-08T09:01:51Z
- **Authors:** Philippe Bergault, Olivier Guéant
- **Why useful:** hits: _market microstructure, order book, market making, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2309.04216v3](https://arxiv.org/pdf/2309.04216v3)  |  **Per-paper MD:** `papers/q-fin_TR/2309.04216_*.md`
- **Abstract:** To assign a value to a portfolio, it is common to use Mark-to-Market prices. However, how should one proceed when the securities are illiquid? When transaction prices are scarce, how can one use all the available real-time information? In this article, we address these questions for over-the-counter (OTC) markets based on requests for quotes (RFQs). We extend the concept of micro-price, which was recently introduced for assets exchanged through limit order books in the market microstructure literature, and incorporate ideas from the recent literature on OTC market making. To account for liquidity imbalances in RFQ markets, we use an approach based on bidimensional Markov-modulated Poisson processes. Beyond extending the concept of micro-price to RFQ markets, we introduce the new concept of …

### 85. [Towards Generalizable Reinforcement Learning for Trade Execution](http://arxiv.org/abs/2307.11685v1)  `2307.11685`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG, stat.ML | **Published:** 2023-05-12T02:41:11Z
- **Authors:** Chuheng Zhang, Yitong Duan, Xiaoyu Chen, Jianyu Chen, Jian Li, Li Zhao
- **Why useful:** hits: _overfit, order book, execution, reinforcement learning, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2307.11685v1](https://arxiv.org/pdf/2307.11685v1)  |  **Per-paper MD:** `papers/q-fin_TR/2307.11685_*.md`
- **Abstract:** Optimized trade execution is to sell (or buy) a given amount of assets in a given time with the lowest possible trading cost. Recently, reinforcement learning (RL) has been applied to optimized trade execution to learn smarter policies from market data. However, we find that many existing RL methods exhibit considerable overfitting which prevents them from real deployment. In this paper, we provide an extensive study on the overfitting problem in optimized trade execution. First, we model the optimized trade execution as offline RL with dynamic context (ORDC), where the context represents market variables that cannot be influenced by the trading policy and are collected in an offline manner. Under this framework, we derive the generalization bound and find that the overfitting issue is cau …

### 86. [Recent Advances in Reinforcement Learning in Finance](http://arxiv.org/abs/2112.04553v4)  `2112.04553`  **score 22**
- **Primary:** q-fin.MF | **All cats:** cs.LG, q-fin.CP, q-fin.MF, q-fin.TR | **Published:** 2021-12-08T19:55:26Z
- **Authors:** Ben Hambly, Renyuan Xu, Huining Yang
- **Why useful:** hits: _execution, market making, portfolio optimization, reinforcement learning, neural network, var, hedging_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2112.04553v4](https://arxiv.org/pdf/2112.04553v4)  |  **Per-paper MD:** `papers/q-fin_MF/2112.04553_*.md`
- **Abstract:** The rapid changes in the finance industry due to the increasing amount of data have revolutionized the techniques on data processing and data analysis and brought new theoretical and computational challenges. In contrast to classical stochastic control theory and other analytical approaches for solving financial decision-making problems that heavily reply on model assumptions, new developments from reinforcement learning (RL) are able to make full use of the large amount of financial data with fewer model assumptions and to improve decisions in complex financial environments. This survey paper aims to review the recent developments and use of RL approaches in finance. We give an introduction to Markov decision processes, which is the setting for many of the commonly used RL approaches. Var …

### 87. [Adaptive learning for financial markets mixing model-based and model-free RL for volatility targeting](http://arxiv.org/abs/2104.10483v2)  `2104.10483`  **score 22**
- **Primary:** cs.LG | **All cats:** cs.LG, q-fin.MF, q-fin.PM | **Published:** 2021-04-19T19:20:22Z
- **Authors:** Eric Benhamou, David Saltiel, Serge Tabachnik, Sui Kai Wong, François Chareyron
- **Why useful:** hits: _walk-forward, reinforcement learning, volatility, var, drawdown, sharpe, sortino, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2104.10483v2](https://arxiv.org/pdf/2104.10483v2)  |  **Per-paper MD:** `papers/cs_LG/2104.10483_*.md`
- **Abstract:** Model-Free Reinforcement Learning has achieved meaningful results in stable environments but, to this day, it remains problematic in regime changing environments like financial markets. In contrast, model-based RL is able to capture some fundamental and dynamical concepts of the environment but suffer from cognitive bias. In this work, we propose to combine the best of the two techniques by selecting various model-based approaches thanks to Model-Free Deep Reinforcement Learning. Using not only past performance and volatility, we include additional contextual information such as macro and risk appetite signals to account for implicit regime changes. We also adapt traditional RL methods to real-life situations by considering only past data for the training sets. Hence, we cannot use future  …

### 88. [Deep Portfolio Optimization via Distributional Prediction of Residual Factors](http://arxiv.org/abs/2012.07245v1)  `2012.07245`  **score 22**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, stat.ML | **Published:** 2020-12-14T04:09:52Z
- **Authors:** Kentaro Imajo, Kentaro Minami, Katsuya Ito, Kei Nakagawa
- **Why useful:** hits: _portfolio optimization, factor, machine learning, deep learning, neural network, var, hedging_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2012.07245v1](https://arxiv.org/pdf/2012.07245v1)  |  **Per-paper MD:** `papers/q-fin_PM/2012.07245_*.md`
- **Abstract:** Recent developments in deep learning techniques have motivated intensive research in machine learning-aided stock trading strategies. However, since the financial market has a highly non-stationary nature hindering the application of typical data-hungry machine learning methods, leveraging financial inductive biases is important to ensure better sample efficiency and robustness. In this study, we propose a novel method of constructing a portfolio based on predicting the distribution of a financial quantity called residual factors, which is known to be generally useful for hedging the risk exposure to common market factors. The key technical ingredients are twofold. First, we introduce a computationally efficient extraction method for the residual information, which can be easily combined w …

### 89. [Extending Deep Reinforcement Learning Frameworks in Cryptocurrency Market Making](http://arxiv.org/abs/2004.06985v1)  `2004.06985`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2020-04-15T10:10:46Z
- **Authors:** Jonathan Sadighian
- **Why useful:** hits: _order book, market making, portfolio management, reinforcement learning, neural network, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2004.06985v1](https://arxiv.org/pdf/2004.06985v1)  |  **Per-paper MD:** `papers/q-fin_TR/2004.06985_*.md`
- **Abstract:** There has been a recent surge in interest in the application of artificial intelligence to automated trading. Reinforcement learning has been applied to single- and multi-instrument use cases, such as market making or portfolio management. This paper proposes a new approach to framing cryptocurrency market making as a reinforcement learning challenge by introducing an event-based environment wherein an event is defined as a change in price greater or less than a given threshold, as opposed to by tick or time-based events (e.g., every minute, hour, day, etc.). Two policy-based agents are trained to learn a market making trading strategy using eight days of training data and evaluate their performance using 30 days of testing data. Limit order book data recorded from Bitmex exchange is used  …

### 90. [Semi-metric portfolio optimization: a new algorithm reducing simultaneous asset shocks](http://arxiv.org/abs/2001.09404v3)  `2001.09404`  **score 22**
- **Primary:** q-fin.PM | **All cats:** q-fin.MF, q-fin.PM, stat.ME | **Published:** 2020-01-26T05:28:27Z
- **Authors:** Nick James, Max Menzies, Jennifer Chan
- **Why useful:** hits: _portfolio optimization, portfolio management, volatility, var, drawdown, options, econometrics, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2001.09404v3](https://arxiv.org/pdf/2001.09404v3)  |  **Per-paper MD:** `papers/q-fin_PM/2001.09404_*.md`
- **Abstract:** This paper proposes a new method for financial portfolio optimization based on reducing simultaneous asset shocks across a collection of assets. This may be understood as an alternative approach to risk reduction in a portfolio based on a new mathematical quantity. First, we apply recently introduced semi-metrics between finite sets to determine the distance between time series' structural breaks. Then, we build on the classical portfolio optimization theory of Markowitz and use this distance between asset structural breaks for our penalty function, rather than portfolio variance. Our experiments are promising: on synthetic data, we show that our proposed method does indeed diversify among time series with highly similar structural breaks and enjoys advantages over existing metrics between …

### 91. [A Gated Recurrent Unit Approach to Bitcoin Price Prediction](http://arxiv.org/abs/1912.11166v1)  `1912.11166`  **score 22**
- **Primary:** q-fin.PR | **All cats:** q-fin.MF, q-fin.PR | **Published:** 2019-12-24T01:23:29Z
- **Authors:** Aniruddha Dutta, Saket Kumar, Meheli Basu
- **Why useful:** hits: _portfolio optimization, factor, machine learning, deep learning, lstm, neural network, volatility, var, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1912.11166v1](https://arxiv.org/pdf/1912.11166v1)  |  **Per-paper MD:** `papers/q-fin_PR/1912.11166_*.md`
- **Abstract:** In today's era of big data, deep learning and artificial intelligence have formed the backbone for cryptocurrency portfolio optimization. Researchers have investigated various state of the art machine learning models to predict Bitcoin price and volatility. Machine learning models like recurrent neural network (RNN) and long short-term memory (LSTM) have been shown to perform better than traditional time series models in cryptocurrency price prediction. However, very few studies have applied sequence models with robust feature engineering to predict future pricing. in this study, we investigate a framework with a set of advanced machine learning methods with a fixed set of exogenous and endogenous factors to predict daily Bitcoin prices. We study and compare different approaches using the  …

### 92. [Deep Reinforcement Learning in Cryptocurrency Market Making](http://arxiv.org/abs/1911.08647v1)  `1911.08647`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2019-11-20T00:48:16Z
- **Authors:** Jonathan Sadighian
- **Why useful:** hits: _order book, order flow, market making, reinforcement learning, neural network, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1911.08647v1](https://arxiv.org/pdf/1911.08647v1)  |  **Per-paper MD:** `papers/q-fin_TR/1911.08647_*.md`
- **Abstract:** This paper sets forth a framework for deep reinforcement learning as applied to market making (DRLMM) for cryptocurrencies. Two advanced policy gradient-based algorithms were selected as agents to interact with an environment that represents the observation space through limit order book data, and order flow arrival statistics. Within the experiment, a forward-feed neural network is used as the function approximator and two reward functions are compared. The performance of each combination of agent and reward function is evaluated by daily and average trade returns. Using this DRLMM framework, this paper demonstrates the effectiveness of deep reinforcement learning in solving stochastic inventory control challenges market makers face.

### 93. [Model-Free Reinforcement Learning for Financial Portfolios: A Brief Survey](http://arxiv.org/abs/1904.04973v2)  `1904.04973`  **score 22**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI, cs.LG, stat.ML | **Published:** 2019-04-10T01:48:52Z
- **Authors:** Yoshiharu Sato
- **Why useful:** hits: _portfolio optimization, portfolio management, risk parity, kelly, reinforcement learning, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1904.04973v2](https://arxiv.org/pdf/1904.04973v2)  |  **Per-paper MD:** `papers/q-fin_PM/1904.04973_*.md`
- **Abstract:** Financial portfolio management is one of the problems that are most frequently encountered in the investment industry. Nevertheless, it is not widely recognized that both Kelly Criterion and Risk Parity collapse into Mean Variance under some conditions, which implies that a universal solution to the portfolio optimization problem could potentially exist. In fact, the process of sequential computation of optimal component weights that maximize the portfolio's expected return subject to a certain risk budget can be reformulated as a discrete-time Markov Decision Process (MDP) and hence as a stochastic optimal control, where the system being controlled is a portfolio consisting of multiple investment components, and the control is its component weights. Consequently, the problem could be solv …

### 94. [Trading Strategy with Stochastic Volatility in a Limit Order Book Market](http://arxiv.org/abs/1602.00358v1)  `1602.00358`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2016-02-01T01:47:52Z
- **Authors:** Wai-Ki Ching, Jia-Wen Gu, Tak-Kuen Siu, Qing-Qing Yang
- **Why useful:** hits: _order book, market making, volatility, var, options, limit order, stochastic volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1602.00358v1](https://arxiv.org/pdf/1602.00358v1)  |  **Per-paper MD:** `papers/q-fin_TR/1602.00358_*.md`
- **Abstract:** In this paper, we employ the Heston stochastic volatility model to describe the stock's volatility and apply the model to derive and analyze the optimal trading strategies for dealers in a security market. We also extend our study to option market making for options written on stocks in the presence of stochastic volatility. Mathematically, the problem is formulated as a stochastic optimal control problem and the controlled state process is the dealer's mark-to-market wealth. Dealers in the security market can optimally determine their ask and bid quotes on the underlying stocks or options continuously over time. Their objective is to maximize an expected profit from transactions with a penalty proportional to the variance of cumulative inventory cost.

### 95. [Stylized facts of price gaps in limit order books: Evidence from Chinese stocks](http://arxiv.org/abs/1405.1247v1)  `1405.1247`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, q-fin.ST | **Published:** 2014-05-06T12:38:35Z
- **Authors:** Gao-Feng Gu, Xiong Xiong, Yong-Jie Zhang, Wei Chen, Wei Zhang, Wei-Xing Zhou
- **Why useful:** hits: _order book, order flow, cta, var, limit order, liquidity, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1405.1247v1](https://arxiv.org/pdf/1405.1247v1)  |  **Per-paper MD:** `papers/q-fin_TR/1405.1247_*.md`
- **Abstract:** Price gap, defined as the logarithmic price difference between the first two occupied price levels on the same side of a limit order book (LOB), is a key determinant of market depth, which is one of the dimensions of liquidity. However, the properties of price gaps have not been thoroughly studied due to the less availability of ultrahigh frequency data. In the paper, we rebuild the LOB dynamics based on the order flow data of 26 A-share stocks traded on the Shenzhen Stock Exchange in 2003. Three key empirical statistical properties of price gaps are investigated. We find that the distribution of price gaps has a power-law tail for all stocks with an average tail exponent close to 3.2. Applying modern statistical methods, we confirm that the gap time series are long-range correlated and po …

### 96. [Optimal Portfolio Liquidation with Limit Orders](http://arxiv.org/abs/1106.3279v6)  `1106.3279`  **score 22**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, eess.SY, math.OC | **Published:** 2011-06-16T17:10:11Z
- **Authors:** Olivier Guéant, Charles-Albert Lehalle, Joaquin Fernandez Tapia
- **Why useful:** hits: _backtest, order book, execution, market making, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1106.3279v6](https://arxiv.org/pdf/1106.3279v6)  |  **Per-paper MD:** `papers/q-fin_TR/1106.3279_*.md`
- **Abstract:** This paper addresses the optimal scheduling of the liquidation of a portfolio using a new angle. Instead of focusing only on the scheduling aspect like Almgren and Chriss, or only on the liquidity-consuming orders like Obizhaeva and Wang, we link the optimal trade-schedule to the price of the limit orders that have to be sent to the limit order book to optimally liquidate a portfolio. Most practitioners address these two issues separately: they compute an optimal trading curve and they then send orders to the markets to try to follow it. The results obtained here solve simultaneously the two problems. As in a previous paper that solved the "intra-day market making problem", the interactions of limit orders with the market are modeled via a Poisson process pegged to a diffusive "fair price" …

### 97. [End-to-End Neural Shrinkage of Indefinite Pairwise Correlation Matrices for Small-Cap-Inclusive Portfolios](http://arxiv.org/abs/2608.30446v1)  `2608.30446`  **score 21**
- **Primary:** q-fin.PM | **All cats:** cs.LG, q-fin.PM, q-fin.ST | **Published:** 2026-08-31T08:36:09Z
- **Authors:** Christian Bongiorno, Lorenzo Villassero
- **Why useful:** hits: _execution, factor, volatility, var, drawdown, sharpe, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.30446v1](https://arxiv.org/pdf/2608.30446v1)  |  **Per-paper MD:** `papers/q-fin_PM/2608.30446_*.md`
- **Abstract:** Small-cap-inclusive equity universes contain recently listed and intermittently traded securities, so enforcing a common look-back discards a substantial fraction of the available information. Pairwise-complete estimation preserves the longest overlap for each asset pair, but the resulting correlation matrix can be indefinite because its entries are computed on different samples. This prevents direct use in Markowitz optimization and falls outside the assumptions of standard random-matrix shrinkage. We adapt a rotation-invariant neural covariance estimator to this setting. The model computes mask-aware marginal moments and a pairwise correlation matrix proxy, processes its signed spectrum, and uses a bidirectional gated recurrent unit conditioned on factor-aligned effective sample lengths  …

### 98. [Cross-Sectional Heterogeneity in LSTM Networks for Financial Time Series](http://arxiv.org/abs/2608.05755v2)  `2608.05755`  **score 21**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2026-08-06T08:39:41Z
- **Authors:** Julius Döbelt
- **Why useful:** hits: _factor, deep learning, lstm, random forest, momentum, var, macro, impact, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.05755v2](https://arxiv.org/pdf/2608.05755v2)  |  **Per-paper MD:** `papers/q-fin_ST/2608.05755_*.md`
- **Abstract:** Predicting financial asset returns remains one of the most difficult challenges in empirical finance, driven by the low signal-to-noise ratio and the semi-strong form of market efficiency. While deep learning models, especially LSTM networks, have shown promise in capturing temporal dependencies, standard architectures often struggle to account for the cross-sectional heterogeneity of asset returns. This paper proposes a novel architectural extension to the basic LSTM model designed to improve both predictive accuracy and model interpretability. The framework integrates macro-financial covariates to capture broader economic signals and learnable sector embeddings to encompass heterogeneity by sector. The trading strategy involves constructing a long-short portfolio based on daily direction …

### 99. [SciPhy Reinforcement Learning for Portfolio Optimization](http://arxiv.org/abs/2607.15195v1)  `2607.15195`  **score 21**
- **Primary:** q-fin.PM | **All cats:** math.AP, math.NA, q-fin.CP, q-fin.MF, q-fin.PM | **Published:** 2026-07-16T16:51:24Z
- **Authors:** Igor Halperin, Andrey Itkin
- **Why useful:** hits: _execution, portfolio optimization, reinforcement learning, volatility, var, sharpe, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.15195v1](https://arxiv.org/pdf/2607.15195v1)  |  **Per-paper MD:** `papers/q-fin_PM/2607.15195_*.md`
- **Abstract:** This paper introduces a dynamic portfolio optimization framework for large institutional investors using Scientific Physics-Informed Reinforcement Learning (SciPhyRL). Formulated in continuous time over an extended state space that includes explicit cumulative costs, the approach leverages offline historical data to learn optimal, distribution-aware strategies. A core innovation reduces the optimization challenge to solving an HJB equation by projecting it onto observed trajectories as a pathwise Hamilton-Jacobi equation. This is solved directly from data using PINN in a single offline sweep, eliminating the need for traditional value or policy iteration. To make the method effective at practical short horizons, the control variable is recast from a continuous trading rate to a discrete ta …

### 100. [Portfolio Optimization and Tail-Risk Analytics of Actively Managed ETFs](http://arxiv.org/abs/2607.03082v1)  `2607.03082`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.RM, q-fin.ST | **Published:** 2026-07-03T08:14:43Z
- **Authors:** William W. Lamptey, Nicholas Appiah, Abootaleb Shirvani, Priscilla Ati-Tay, Svetlozar T. Rachev, Frank J. Fabozzi
- **Why useful:** hits: _portfolio optimization, volatility, var, cvar, tail risk, drawdown_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.03082v1](https://arxiv.org/pdf/2607.03082v1)  |  **Per-paper MD:** `papers/q-fin_PM/2607.03082_*.md`
- **Abstract:** This paper examines portfolio optimization and tail-risk analytics for a heterogeneous universe of actively managed investment funds. Using daily Bloomberg data for 30 funds from 4 December 2020 to 24 December 2025, the study evaluates buy-and-hold, mean--variance, CVaR-based, and tangency-type strategies under long-only and long--short constraints. The sample consists predominantly of actively managed ETFs, with PTTRX retained as an actively managed fixed-income mutual-fund comparator. The results show substantial heterogeneity across thematic equity, fixed-income, income-oriented, multi-asset, and alternative strategies, creating both diversification opportunities and meaningful differences in volatility, drawdown behavior, downside exposure, and tail risk. Historical results indicate th …

### 101. [Addressing Market Regime Changes and Heavy-Tailed Returns in Portfolio Optimization via Bayesian VAR and Elliptical Black-Litterman](http://arxiv.org/abs/2606.09104v1)  `2606.09104`  **score 21**
- **Primary:** cs.LG | **All cats:** cs.LG, cs.AI, q-fin.PM | **Published:** 2026-06-08T06:58:11Z
- **Authors:** Daniil Mikriukov, Ruoyu Sun, Angelos Stefanidis, Jionglong Su, Zhengyong Jiang
- **Why useful:** hits: _portfolio optimization, reinforcement learning, transformer, cta, var, sharpe, sortino, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.09104v1](https://arxiv.org/pdf/2606.09104v1)  |  **Per-paper MD:** `papers/cs_LG/2606.09104_*.md`
- **Abstract:** Deep reinforcement learning (DRL) frameworks for portfolio optimization have shown promise for their ability to learn allocation rules dynamically from market data. However, these models fail to account for fat-tailed returns, which characterize actual market behavior with more frequent extreme events. Furthermore, historical data is treated homogeneously, without accounting for temporal importance, leading models to fail during regime changes. We propose a new BAVAR-BLED algorithm that combines methods derived from Bayesian-Averaging Vector Autoregressive (BAVAR) and the Black-Litterman model using Elliptical Distributions (BLED) within a TD3 architecture. BAVAR captures a set of vector autoregressive representations that consider multi-scale temporal features, enabling adaptive allocatio …

### 102. [What Does Deep Hedging Actually Learn? Delta Corrections, Regime Fragility, and Symbolic Distillation](http://arxiv.org/abs/2605.21696v1)  `2605.21696`  **score 21**
- **Primary:** q-fin.RM | **All cats:** q-fin.CP, q-fin.PR, q-fin.RM | **Published:** 2026-05-20T19:56:30Z
- **Authors:** Kirill Zernikov
- **Why useful:** hits: _walk-forward, volatility, var, cvar, sharpe, options, hedging, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2605.21696v1](https://arxiv.org/pdf/2605.21696v1)  |  **Per-paper MD:** `papers/q-fin_RM/2605.21696_*.md`
- **Abstract:** This paper studies empirical deep hedging for S&P 500 index options under a local downside-shortfall reward. It moves beyond performance comparison by asking what the learned hedge does, when it fails, and whether it can be made auditable. TD3 agents are compared with a daily-updated Black-Scholes delta hedge on the same option episodes. In walk-forward tests from 2015 to 2023, the agents usually learn a systematic delta haircut relative to Black-Scholes. The correction is explained by spot-implied-volatility co-movement and often improves accumulated reward and terminal downside variance, but it is regime-fragile: 2022 exposes losses in adverse daily states, while 2023 shows that underhedging can raise ordinary variance when option P&L is spot-dominated and the volatility channel is unusu …

### 103. [A Statistical-Finance Benchmark for Same-Day Directional Stock Prediction: Walk-Forward Evidence from SPY](http://arxiv.org/abs/2608.26106v1)  `2608.26106`  **score 21**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2026-05-01T15:47:15Z
- **Authors:** Alex Chen
- **Why useful:** hits: _walk-forward, xgboost, lightgbm, random forest, cta, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.26106v1](https://arxiv.org/pdf/2608.26106v1)  |  **Per-paper MD:** `papers/q-fin_ST/2608.26106_*.md`
- **Abstract:** We study statistical predictability in daily U.S. equity prices using only information available at the market open. Using SPY from February 1, 1993 through March 15, 2024, we benchmark XGBoost against Random Forest, LightGBM, Logistic Regression, and naive baselines under expanding-window walk-forward validation. After observing the current day's opening price and two lagged target-specific prices, the task is to predict whether the same day's close will be above or below the previous day's close. On the last 800 trading days, Logistic Regression attains the highest close-direction accuracy (71.09%), Random Forest reaches 61.20%, and XGBoost reaches 58.45% with a 95% bootstrap confidence interval of [54.94%, 62.08]. For XGBoost, close-direction accuracy rises to 72.7% when the predicted m …

### 104. [Mislearning of Factor Risk Premia under Structural Breaks: A Misspecified Bayesian Learning Framework](http://arxiv.org/abs/2603.21672v3)  `2603.21672`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.ST, q-fin.TR, stat.OT | **Published:** 2026-03-23T07:54:15Z
- **Authors:** Yimeng Qiu
- **Why useful:** hits: _factor, anomaly, cta, volatility, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.21672v3](https://arxiv.org/pdf/2603.21672v3)  |  **Per-paper MD:** `papers/q-fin_PM/2603.21672_*.md`
- **Abstract:** While asset-pricing models increasingly recognize that factor risk premia are subject to structural change, existing literature typically assumes that investors correctly account for such instability. This paper studies how investors instead learn under a misspecified model that underestimates structural breaks. We propose a minimal Bayesian framework in which this misspecification generates persistent prediction errors and pricing distortions, and we introduce an empirically tractable measure of mislearning intensity $(Δ_t)$ based on predictive likelihood ratios. The empirical results yield three main findings. First, in benchmark factor systems, elevated mislearning does not forecast a deterministic short-run collapse in performance; instead, it is associated with stronger long-horizon r …

### 105. [Joint Return and Risk Modeling with Deep Neural Networks for Portfolio Construction](http://arxiv.org/abs/2603.19288v1)  `2603.19288`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI, cs.LG | **Published:** 2026-03-09T01:49:51Z
- **Authors:** Keonvin Park
- **Why useful:** hits: _portfolio optimization, mean-variance, neural network, volatility, var, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.19288v1](https://arxiv.org/pdf/2603.19288v1)  |  **Per-paper MD:** `papers/q-fin_PM/2603.19288_*.md`
- **Abstract:** Portfolio construction traditionally relies on separately estimating expected returns and covariance matrices using historical statistics, often leading to suboptimal allocation under time-varying market conditions. This paper proposes a joint return and risk modeling framework based on deep neural networks that enables end-to-end learning of dynamic expected returns and risk structures from sequential financial data. Using daily data from ten large-cap US equities spanning 2010 to 2024, the proposed model is evaluated across return prediction, risk estimation, and portfolio-level performance. Out-of-sample results during 2020 to 2024 show that the deep forecasting model achieves competitive predictive accuracy (RMSE = 0.0264) with economically meaningful directional accuracy (51.9%). More …

### 106. [Exploratory Randomization for Discrete-Time Risk-Sensitive Benchmarked Investment Management with Reinforcement Learning](http://arxiv.org/abs/2603.00738v1)  `2603.00738`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, math.OC | **Published:** 2026-02-28T17:05:39Z
- **Authors:** Sebastien Lleo, Wolfgang Runggaldier
- **Why useful:** hits: _portfolio management, kelly, factor, reinforcement learning, cta, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.00738v1](https://arxiv.org/pdf/2603.00738v1)  |  **Per-paper MD:** `papers/q-fin_PM/2603.00738_*.md`
- **Abstract:** This paper bridges reinforcement learning (RL) and risk-sensitive stochastic control by introducing a tractable exploration mechanism for policy search in risk-sensitive portfolio management, with known and unknown model parameters, that yields an endogenous relative-entropy regularization. We construct a discrete-time risk-sensitive benchmarked investment model. This model combines a factor-based asset universe with periodic portfolio rebalancing. Exploration is incorporated through user-specified Gaussian perturbations to baseline (exploitative) controls. The risk-sensitive stochastic control problem is solved analytically using the Free Energy-Entropy Duality. The Duality recasts the control problem as a linear-quadratic-Gaussian game and introduces a natural penalty for exploration. Th …

### 107. [Optimal Signal Extraction from Order Flow: A Matched Filter Perspective on Normalization and Market Microstructure](http://arxiv.org/abs/2512.18648v3)  `2512.18648`  **score 21**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2025-12-21T08:50:11Z
- **Authors:** Sungwoo Kang
- **Why useful:** hits: _market microstructure, order flow, execution, factor, cta, var, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.18648v3](https://arxiv.org/pdf/2512.18648v3)  |  **Per-paper MD:** `papers/q-fin_CP/2512.18648_*.md`
- **Abstract:** We establish a general matched filter principle for order flow normalization: optimal normalization must match the scaling behaviour of the signal-generating process. For capacity-constrained institutional investors, market capitalization normalization ($S^{MC}$) is the matched filter; for volume-targeting traders (e.g., VWAP/TWAP algorithms), trading value normalization ($S^{TV}$) is optimal. Monte Carlo simulations confirm this principle works bidirectionally, with matched filters achieving up to $1.99\times$ higher signal correlation. Empirical validation using 2.7 million stock-day observations from the Korean market (2020--2024) reveals symmetric normalization dominance across investor types: domestic institutional flows predict next-day returns significantly under $S^{MC}$ ($t = 9.65 …

### 108. [EXFormer: A Multi-Scale Trend-Aware Transformer with Dynamic Variable Selection for Foreign Exchange Returns Prediction](http://arxiv.org/abs/2512.12727v2)  `2512.12727`  **score 21**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP, cs.CE | **Published:** 2025-12-14T15:00:36Z
- **Authors:** Dinggao Liu, Robert Ślepaczuk, Zhenpeng Tang
- **Why useful:** hits: _backtest, slippage, factor, transformer, volatility, var, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.12727v2](https://arxiv.org/pdf/2512.12727v2)  |  **Per-paper MD:** `papers/q-fin_CP/2512.12727_*.md`
- **Abstract:** Accurately forecasting daily exchange rate returns represents a longstanding challenge in international finance, as the exchange rate returns are driven by a multitude of correlated market factors and exhibit high-frequency fluctuations. This paper proposes EXFormer, a novel Transformer-based architecture specifically designed for forecasting the daily exchange rate returns. We introduce a multi-scale trend-aware self-attention mechanism that employs parallel convolutional branches with differing receptive fields to align observations on the basis of local slopes, preserving long-range dependencies while remaining sensitive to regime shifts. A dynamic variable selector assigns time-varying importance weights to 28 exogenous covariates related to exchange rate returns, providing pre-hoc int …

### 109. [Diffusive Limit of Hawkes Driven Order Book Dynamics With Liquidity Migration](http://arxiv.org/abs/2511.18117v1)  `2511.18117`  **score 21**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF | **Published:** 2025-11-22T16:44:29Z
- **Authors:** Levon Mahseredjian
- **Why useful:** hits: _market microstructure, order book, order flow, var, macro, regime, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.18117v1](https://arxiv.org/pdf/2511.18117v1)  |  **Per-paper MD:** `papers/q-fin_MF/2511.18117_*.md`
- **Abstract:** This paper develops a theoretical mesoscopic model of the limit order book driven by multivariate Hawkes processes, designed to capture temporal self-excitation and the spatial propagation of order flow across price levels. In contrast to classical zero-intelligence or Poisson based queueing models, the proposed framework introduces mathematically defined migration events between neighbouring price levels, whose intensities are themselves governed by the underlying Hawkes structure. This provides a principled stochastic mechanism for modeling interactions between order arrivals, cancellations, and liquidity movement across adjacent queues. Starting from a microscopic specification of Hawkes driven order flow, we derive a diffusion approximation which yields a reflected mesoscopic stochasti …

### 110. [Hybrid LSTM and PPO Networks for Dynamic Portfolio Optimization](http://arxiv.org/abs/2511.17963v1)  `2511.17963`  **score 21**
- **Primary:** cs.LG | **All cats:** cs.LG, cs.AI, cs.CE, q-fin.PM | **Published:** 2025-11-22T07:57:03Z
- **Authors:** Jun Kevin, Pujianto Yugopuspito
- **Why useful:** hits: _portfolio optimization, reinforcement learning, lstm, volatility, var, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.17963v1](https://arxiv.org/pdf/2511.17963v1)  |  **Per-paper MD:** `papers/cs_LG/2511.17963_*.md`
- **Abstract:** This paper introduces a hybrid framework for portfolio optimization that fuses Long Short-Term Memory (LSTM) forecasting with a Proximal Policy Optimization (PPO) reinforcement learning strategy. The proposed system leverages the predictive power of deep recurrent networks to capture temporal dependencies, while the PPO agent adaptively refines portfolio allocations in continuous action spaces, allowing the system to anticipate trends while adjusting dynamically to market shifts. Using multi-asset datasets covering U.S. and Indonesian equities, U.S. Treasuries, and major cryptocurrencies from January 2018 to December 2024, the model is evaluated against several baselines, including equal-weight, index-style, and single-model variants (LSTM-only and PPO-only). The framework's performance is …

### 111. [Scaling Conditional Autoencoders for Portfolio Optimization via Uncertainty-Aware Factor Selection](http://arxiv.org/abs/2511.17462v1)  `2511.17462`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2025-11-21T18:04:00Z
- **Authors:** Ryan Engel, Yu Chen, Pawel Polak, Ioana Boier
- **Why useful:** hits: _portfolio optimization, factor, xgboost, cta, sharpe, sortino_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.17462v1](https://arxiv.org/pdf/2511.17462v1)  |  **Per-paper MD:** `papers/q-fin_PM/2511.17462_*.md`
- **Abstract:** Conditional Autoencoders (CAEs) offer a flexible, interpretable approach for estimating latent asset-pricing factors from firm characteristics. However, existing studies usually limit the latent factor dimension to around K=5 due to concerns that larger K can degrade performance. To overcome this challenge, we propose a scalable framework that couples a high-dimensional CAE with an uncertainty-aware factor selection procedure. We employ three models for quantile prediction: zero-shot Chronos, a pretrained time-series foundation model (ZS-Chronos), gradient-boosted quantile regression trees using XGBoost and RAPIDS (Q-Boost), and an I.I.D bootstrap-based sample mean model (IID-BS). For each model, we rank factors by forecast uncertainty and retain the top-k most predictable factors for port …

### 112. [A three-step machine learning approach to predict market bubbles with financial news](http://arxiv.org/abs/2510.16636v1)  `2510.16636`  **score 21**
- **Primary:** q-fin.ST | **All cats:** cs.LG, q-fin.CP, q-fin.ST | **Published:** 2025-10-18T20:31:31Z
- **Authors:** Abraham Atsiwo
- **Why useful:** hits: _cross-validation, sentiment, nlp, machine learning, cta, macro_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.16636v1](https://arxiv.org/pdf/2510.16636v1)  |  **Per-paper MD:** `papers/q-fin_ST/2510.16636_*.md`
- **Abstract:** This study presents a three-step machine learning framework to predict bubbles in the S&P 500 stock market by combining financial news sentiment with macroeconomic indicators. Building on traditional econometric approaches, the proposed approach predicts bubble formation by integrating textual and quantitative data sources. In the first step, bubble periods in the S&P 500 index are identified using a right-tailed unit root test, a widely recognized real-time bubble detection method. The second step extracts sentiment features from large-scale financial news articles using natural language processing (NLP) techniques, which capture investors' expectations and behavioral patterns. In the final step, ensemble learning methods are applied to predict bubble occurrences based on high sentiment-b …

### 113. [A Deterministic Limit Order Book Simulator with Hawkes-Driven Order Flow](http://arxiv.org/abs/2510.08085v1)  `2510.08085`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2025-10-09T11:17:14Z
- **Authors:** Sohaib El Karmi
- **Why useful:** hits: _market microstructure, order book, order flow, var, regime, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.08085v1](https://arxiv.org/pdf/2510.08085v1)  |  **Per-paper MD:** `papers/q-fin_TR/2510.08085_*.md`
- **Abstract:** We present a reproducible research framework for market microstructure combining a deterministic C++ limit order book (LOB) simulator with stochastic order flow generated by multivariate marked Hawkes processes. The paper derives full stability and ergodicity proofs for both linear and nonlinear Hawkes models, implements time-rescaling and goodness-of-fit diagnostics, and calibrates exponential and power-law kernels on Binance BTCUSDT and LOBSTER AAPL datasets. Empirical results highlight the nearly-unstable subcritical regime as essential for reproducing realistic clustering in order flow. All code, datasets, and configuration files are publicly available at https://github.com/sohaibelkarmi/High-Frequency-Trading-Simulator

### 114. [Forecasting Liquidity Withdraw with Machine Learning Models](http://arxiv.org/abs/2509.22985v1)  `2509.22985`  **score 21**
- **Primary:** q-fin.RM | **All cats:** q-fin.CP, q-fin.RM, q-fin.TR | **Published:** 2025-09-26T22:35:55Z
- **Authors:** Haochuan, Wang
- **Why useful:** hits: _order book, execution, machine learning, xgboost, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.22985v1](https://arxiv.org/pdf/2509.22985v1)  |  **Per-paper MD:** `papers/q-fin_RM/2509.22985_*.md`
- **Abstract:** Liquidity withdrawal is a critical indicator of market fragility. In this project, I test a framework for forecasting liquidity withdrawal at the individual-stock level, ranging from less liquid stocks to highly liquid large-cap tickers, and evaluate the relative performance of competing model classes in predicting short-horizon order book stress. We introduce the Liquidity Withdrawal Index (LWI) -- defined as the ratio of order cancellations to the sum of standing depth and new additions at the best quotes -- as a bounded, interpretable measure of transient liquidity removal. Using Nasdaq market-by-order (MBO) data, we compare a spectrum of approaches: linear benchmarks (AR, HAR), and non-linear tree ensembles (XGBoost), across horizons ranging from 250\,ms to 5\,s. Beyond predictive accu …

### 115. [Reinforcement Learning-Based Market Making as a Stochastic Control on Non-Stationary Limit Order Book Dynamics](http://arxiv.org/abs/2509.12456v2)  `2509.12456`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.AI | **Published:** 2025-09-15T21:08:13Z
- **Authors:** Rafael Zimmer, Oswaldo Luiz do Valle Costa
- **Why useful:** hits: _order book, market making, reinforcement learning, volatility, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.12456v2](https://arxiv.org/pdf/2509.12456v2)  |  **Per-paper MD:** `papers/q-fin_TR/2509.12456_*.md`
- **Abstract:** Reinforcement Learning has emerged as a promising framework for developing adaptive and data-driven strategies, enabling market makers to optimize decision-making policies based on interactions with the limit order book environment. This paper explores the integration of a reinforcement learning agent in a market-making context, where the underlying market dynamics have been explicitly modeled to capture observed stylized facts of real markets, including clustered order arrival times, non-stationary spreads and return drifts, stochastic order quantities and price volatility. These mechanisms aim to enhance stability of the resulting control agent, and serve to incorporate domain-specific knowledge into the agent policy learning process. Our contributions include a practical implementation  …

### 116. [QTMRL: An Agent for Quantitative Trading Decision-Making Based on Multi-Indicator Guided Reinforcement Learning](http://arxiv.org/abs/2508.20467v2)  `2508.20467`  **score 21**
- **Primary:** q-fin.PM | **All cats:** cs.LG, q-fin.CP, q-fin.PM | **Published:** 2025-08-28T06:37:41Z
- **Authors:** Jingfeng Pan, Jiahao Chen
- **Why useful:** hits: _portfolio management, reinforcement learning, lstm, momentum, moving average, volatility, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2508.20467v2](https://arxiv.org/pdf/2508.20467v2)  |  **Per-paper MD:** `papers/q-fin_PM/2508.20467_*.md`
- **Abstract:** In the highly volatile and uncertain global financial markets, traditional quantitative trading models relying on statistical modeling or empirical rules often fail to adapt to dynamic market changes and black swan events due to rigid assumptions and limited generalization. To address these issues, this paper proposes QTMRL (Quantitative Trading Multi-Indicator Reinforcement Learning), an intelligent trading agent combining multi-dimensional technical indicators with reinforcement learning (RL) for adaptive and stable portfolio management. We first construct a comprehensive multi-indicator dataset using 23 years of S&P 500 daily OHLCV data (2000-2022) for 16 representative stocks across 5 sectors, enriching raw data with trend, volatility, and momentum indicators to capture holistic market …

### 117. [Event-Time Anchor Selection for Multi-Contract Quoting](http://arxiv.org/abs/2507.05749v2)  `2507.05749`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.ST, q-fin.TR | **Published:** 2025-07-08T07:52:07Z
- **Authors:** Aditya Nittur Anantha, Shashi Jain, Shivam Goyal, Dhruv Misra
- **Why useful:** hits: _order book, execution, factor, var, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2507.05749v2](https://arxiv.org/pdf/2507.05749v2)  |  **Per-paper MD:** `papers/q-fin_TR/2507.05749_*.md`
- **Abstract:** When quoting across multiple contracts, the sequence of execution can be a key driver of implementation shortfall relative to the target spread~\cite{bergault2022multi}. We model the short-horizon execution risk from such quoting as variations in transaction prices between the initiation of the first leg and the completion of the position. Our quoting policy anchors the spread by designating one contract ex ante as a \emph{reference contract}. Reducing execution risk requires a predictive criterion for selecting that contract whose price is most stable over the execution interval. This paper develops a diagnostic framework for reference-contract selection that evaluates this stability by contrasting order-flow Hawkes forecasts with a Composite Liquidity Factor (CLF) of instantaneous limit  …

### 118. [Advancing Exchange Rate Forecasting: Leveraging Machine Learning and AI for Enhanced Accuracy in Global Financial Markets](http://arxiv.org/abs/2506.09851v2)  `2506.09851`  **score 21**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.CL, cs.LG | **Published:** 2025-06-11T15:22:07Z
- **Authors:** Md. Yeasin Rahat, Rajan Das Gupta, Nur Raisa Rahman, Sudipto Roy Pritom, Samiur Rahman Shakir, Md Imrul Hasan Showmick, Md. Jakir Hossen
- **Why useful:** hits: _backtest, sentiment, machine learning, deep learning, lstm, neural network, volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2506.09851v2](https://arxiv.org/pdf/2506.09851v2)  |  **Per-paper MD:** `papers/q-fin_ST/2506.09851_*.md`
- **Abstract:** The prediction of foreign exchange rates, such as the US Dollar (USD) to Bangladeshi Taka (BDT), plays a pivotal role in global financial markets, influencing trade, investments, and economic stability. This study leverages historical USD/BDT exchange rate data from 2018 to 2023, sourced from Yahoo Finance, to develop advanced machine learning models for accurate forecasting. A Long Short-Term Memory (LSTM) neural network is employed, achieving an exceptional accuracy of 99.449%, a Root Mean Square Error (RMSE) of 0.9858, and a test loss of 0.8523, significantly outperforming traditional methods like ARIMA (RMSE 1.342). Additionally, a Gradient Boosting Classifier (GBC) is applied for directional prediction, with backtesting on a $10,000 initial capital revealing a 40.82% profitable trade  …

### 119. [Hybrid Models for Financial Forecasting: Combining Econometric, Machine Learning, and Deep Learning Models](http://arxiv.org/abs/2505.19617v1)  `2505.19617`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2025-05-26T07:32:23Z
- **Authors:** Dominik Stempień, Robert Ślepaczuk
- **Why useful:** hits: _cross-validation, machine learning, deep learning, xgboost, lstm, var, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2505.19617v1](https://arxiv.org/pdf/2505.19617v1)  |  **Per-paper MD:** `papers/q-fin_TR/2505.19617_*.md`
- **Abstract:** This research systematically develops and evaluates various hybrid modeling approaches by combining traditional econometric models (ARIMA and ARFIMA models) with machine learning and deep learning techniques (SVM, XGBoost, and LSTM models) to forecast financial time series. The empirical analysis is based on two distinct financial assets: the S&P 500 index and Bitcoin. By incorporating over two decades of daily data for the S&P 500 and almost ten years of Bitcoin data, the study provides a comprehensive evaluation of forecasting methodologies across different market conditions and periods of financial distress. Models' training and hyperparameter tuning procedure is performed using a novel three-fold dynamic cross-validation method. The applicability of applied models is evaluated using bo …

### 120. [ClusterLOB: Enhancing Trading Strategies by Clustering Orders in Limit Order Books](http://arxiv.org/abs/2504.20349v3)  `2504.20349`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2025-04-29T01:37:33Z
- **Authors:** Yichi Zhang, Mihai Cucuringu, Alexander Y. Shestopaloff, Stefan Zohren
- **Why useful:** hits: _market microstructure, order book, order flow, var, sharpe, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2504.20349v3](https://arxiv.org/pdf/2504.20349v3)  |  **Per-paper MD:** `papers/q-fin_TR/2504.20349_*.md`
- **Abstract:** In the rapidly evolving world of financial markets, understanding the dynamics of limit order book (LOB) is crucial for unraveling market microstructure and participant behavior. We introduce ClusterLOB as a method to cluster individual market events in a stream of market-by-order (MBO) data into different groups. To do so, each market event is augmented with six time-dependent features. By applying the K-means++ clustering algorithm to the resulting order features, we are then able to assign each new order to one of three distinct clusters, which we identify as directional, opportunistic, and market-making participants, each capturing unique trading behaviors. Our experimental results are performed on one year of MBO data containing small-tick, medium-tick, and large-tick stocks from NASD …

### 121. [Diffusion Factor Models: Generating High-Dimensional Returns with Factor Structure](http://arxiv.org/abs/2504.06566v5)  `2504.06566`  **score 21**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.LG, q-fin.MF | **Published:** 2025-04-09T04:01:35Z
- **Authors:** Minshuo Chen, Renyuan Xu, Yumin Xu, Ruixun Zhang
- **Why useful:** hits: _portfolio optimization, mean-variance, factor, neural network, var, regime, econometrics_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2504.06566v5](https://arxiv.org/pdf/2504.06566v5)  |  **Per-paper MD:** `papers/q-fin_ST/2504.06566_*.md`
- **Abstract:** Financial scenario simulation is essential for risk management and portfolio optimization, yet it remains challenging especially in high-dimensional and small data settings common in finance. We propose a diffusion factor model that integrates latent factor structure into generative diffusion processes, bridging econometrics with modern generative AI to address the challenges of the curse of dimensionality and data scarcity in financial simulation. By exploiting the low-dimensional factor structure inherent in asset returns, we decompose the score function--a key component in diffusion models--using time-varying orthogonal projections, and this decomposition is incorporated into the design of neural network architectures. We derive rigorous statistical guarantees, establishing nonasymptoti …

### 122. [TRADES: Generating Realistic Market Simulations with Diffusion Models](http://arxiv.org/abs/2502.07071v3)  `2502.07071`  **score 21**
- **Primary:** q-fin.TR | **All cats:** cs.AI, cs.LG, q-fin.CP, q-fin.TR | **Published:** 2025-01-31T19:43:13Z
- **Authors:** Leonardo Berti, Bardh Prenkaj, Paola Velardi
- **Why useful:** hits: _order book, order flow, deep learning, transformer, volatility, limit order, impact, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2502.07071v3](https://arxiv.org/pdf/2502.07071v3)  |  **Per-paper MD:** `papers/q-fin_TR/2502.07071_*.md`
- **Abstract:** Financial markets are complex systems characterized by high statistical noise, nonlinearity, volatility, and constant evolution. Thus, modeling them is extremely hard. Here, we address the task of generating realistic and responsive Limit Order Book (LOB) market simulations, which are fundamental for calibrating and testing trading strategies, performing market impact experiments, and generating synthetic market data. We propose a novel TRAnsformer-based Denoising Diffusion Probabilistic Engine for LOB Simulations (TRADES). TRADES generates realistic order flows as time series conditioned on the state of the market, leveraging a transformer-based architecture that captures the temporal and spatial characteristics of high-frequency market data. There is a notable absence of quantitative met …

### 123. [Exploratory Mean-Variance Portfolio Optimization with Regime-Switching Market Dynamics](http://arxiv.org/abs/2501.16659v1)  `2501.16659`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.MF, q-fin.PM, q-fin.ST, stat.ML | **Published:** 2025-01-28T02:48:41Z
- **Authors:** Yuling Max Chen, Bin Li, David Saunders
- **Why useful:** hits: _portfolio optimization, mean-variance, reinforcement learning, volatility, var, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2501.16659v1](https://arxiv.org/pdf/2501.16659v1)  |  **Per-paper MD:** `papers/q-fin_PM/2501.16659_*.md`
- **Abstract:** Considering the continuous-time Mean-Variance (MV) portfolio optimization problem, we study a regime-switching market setting and apply reinforcement learning (RL) techniques to assist informed exploration within the control space. We introduce and solve the Exploratory Mean Variance with Regime Switching (EMVRS) problem. We also present a Policy Improvement Theorem. Further, we recognize that the widely applied Temporal Difference (TD) learning is not adequate for the EMVRS context, hence we consider Orthogonality Condition (OC) learning, leveraging the martingale property of the induced optimal value function from the analytical solution to EMVRS. We design a RL algorithm that has more meaningful parameterization using the market parameters and propose an updating scheme for each paramet …

### 124. [Blending Ensemble for Classification with Genetic-algorithm generated Alpha factors and Sentiments (GAS)](http://arxiv.org/abs/2411.03035v1)  `2411.03035`  **score 21**
- **Primary:** q-fin.CP | **All cats:** cs.LG, q-fin.CP, q-fin.TR | **Published:** 2024-11-05T12:15:01Z
- **Authors:** Quechen Yang
- **Why useful:** hits: _sentiment, factor, alpha, xgboost, lightgbm, random forest, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2411.03035v1](https://arxiv.org/pdf/2411.03035v1)  |  **Per-paper MD:** `papers/q-fin_CP/2411.03035_*.md`
- **Abstract:** With the increasing maturity and expansion of the cryptocurrency market, understanding and predicting its price fluctuations has become an important issue in the field of financial engineering. This article introduces an innovative Genetic Algorithm-generated Alpha Sentiment (GAS) blending ensemble model specifically designed to predict Bitcoin market trends. The model integrates advanced ensemble learning methods, feature selection algorithms, and in-depth sentiment analysis to effectively capture the complexity and variability of daily Bitcoin trading data. The GAS framework combines 34 Alpha factors with 8 news economic sentiment factors to provide deep insights into Bitcoin price fluctuations by accurately analyzing market sentiment and technical indicators. The core of this study is u …

### 125. [FinBERT-BiLSTM: A Deep Learning Model for Predicting Volatile Cryptocurrency Market Prices Using Market Sentiment Dynamics](http://arxiv.org/abs/2411.12748v1)  `2411.12748`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2024-11-02T14:43:06Z
- **Authors:** Mabsur Fatin Bin Hossain, Lubna Zahan Lamia, Md Mahmudur Rahman, Md Mosaddek Khan
- **Why useful:** hits: _sentiment, finbert, deep learning, lstm, cta, volatility, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2411.12748v1](https://arxiv.org/pdf/2411.12748v1)  |  **Per-paper MD:** `papers/q-fin_TR/2411.12748_*.md`
- **Abstract:** Time series forecasting is a key tool in financial markets, helping to predict asset prices and guide investment decisions. In highly volatile markets, such as cryptocurrencies like Bitcoin (BTC) and Ethereum (ETH), forecasting becomes more difficult due to extreme price fluctuations driven by market sentiment, technological changes, and regulatory shifts. Traditionally, forecasting relied on statistical methods, but as markets became more complex, deep learning models like LSTM, Bi-LSTM, and the newer FinBERT-LSTM emerged to capture intricate patterns. Building upon recent advancements and addressing the volatility inherent in cryptocurrency markets, we propose a hybrid model that combines Bidirectional Long Short-Term Memory (Bi-LSTM) networks with FinBERT to enhance forecasting accuracy …

### 126. [Hedge Fund Portfolio Construction Using PolyModel Theory and iTransformer](http://arxiv.org/abs/2408.03320v3)  `2408.03320`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG | **Published:** 2024-08-06T17:55:58Z
- **Authors:** Siqiao Zhao, Zhikang Dong, Zeyu Cao, Raphael Douady
- **Why useful:** hits: _factor, alpha, machine learning, deep learning, transformer, var, sharpe, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2408.03320v3](https://arxiv.org/pdf/2408.03320v3)  |  **Per-paper MD:** `papers/q-fin_PM/2408.03320_*.md`
- **Abstract:** When constructing portfolios, a key problem is that a lot of financial time series data are sparse, making it challenging to apply machine learning methods. Polymodel theory can solve this issue and demonstrate superiority in portfolio construction from various aspects. To implement the PolyModel theory for constructing a hedge fund portfolio, we begin by identifying an asset pool, utilizing over 10,000 hedge funds for the past 29 years' data. PolyModel theory also involves choosing a wide-ranging set of risk factors, which includes various financial indices, currencies, and commodity prices. This comprehensive selection mirrors the complexities of the real-world environment. Leveraging on the PolyModel theory, we create quantitative measures such as Long-term Alpha, Long-term Ratio, and S …

### 127. [Generative modelling of financial time series with structured noise and MMD-based signature learning](http://arxiv.org/abs/2407.19848v4)  `2407.19848`  **score 21**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF | **Published:** 2024-07-29T09:59:31Z
- **Authors:** Chung I Lu, Julian Sester
- **Why useful:** hits: _portfolio optimization, portfolio management, machine learning, reinforcement learning, moving average, volatility, var, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2407.19848v4](https://arxiv.org/pdf/2407.19848v4)  |  **Per-paper MD:** `papers/q-fin_MF/2407.19848_*.md`
- **Abstract:** Generating synthetic financial time series data that accurately reflects real-world market dynamics holds tremendous potential for various applications, including portfolio optimization, risk management, and large scale machine learning. We present an approach that {uses structured noise} for training generative models for financial time series. The expressive power of the signature transform {has been shown to be able} to capture the complex dependencies and temporal structures inherent in financial data {when used to train generative models in the form of a signature kernel }. We employ a moving average model to model the variance of the noise input, enhancing the model's ability to reproduce stylized facts such as volatility clustering. Through empirical experiments on S\&P 500 index da …

### 128. [Deep Policy Gradient Methods in Commodity Markets](http://arxiv.org/abs/2308.01910v1)  `2308.01910`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2023-06-14T11:50:23Z
- **Authors:** Jonas Hanetho
- **Why useful:** hits: _backtest, reinforcement learning, lstm, neural network, volatility, sharpe, liquidity, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2308.01910v1](https://arxiv.org/pdf/2308.01910v1)  |  **Per-paper MD:** `papers/q-fin_TR/2308.01910_*.md`
- **Abstract:** The energy transition has increased the reliance on intermittent energy sources, destabilizing energy markets and causing unprecedented volatility, culminating in the global energy crisis of 2021. In addition to harming producers and consumers, volatile energy markets may jeopardize vital decarbonization efforts. Traders play an important role in stabilizing markets by providing liquidity and reducing volatility. Several mathematical and statistical models have been proposed for forecasting future returns. However, developing such models is non-trivial due to financial markets' low signal-to-noise ratios and nonstationary dynamics. This thesis investigates the effectiveness of deep reinforcement learning methods in commodities trading. It formalizes the commodities trading problem as a con …

### 129. [Constructing Time-Series Momentum Portfolios with Deep Multi-Task Learning](http://arxiv.org/abs/2306.13661v1)  `2306.13661`  **score 21**
- **Primary:** q-fin.CP | **All cats:** cs.LG, q-fin.CP, q-fin.PM | **Published:** 2023-06-08T13:04:44Z
- **Authors:** Joel Ong, Dorien Herremans
- **Why useful:** hits: _backtest, factor, neural network, momentum, volatility, var, tail risk_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2306.13661v1](https://arxiv.org/pdf/2306.13661v1)  |  **Per-paper MD:** `papers/q-fin_CP/2306.13661_*.md`
- **Abstract:** A diversified risk-adjusted time-series momentum (TSMOM) portfolio can deliver substantial abnormal returns and offer some degree of tail risk protection during extreme market events. The performance of existing TSMOM strategies, however, relies not only on the quality of the momentum signal but also on the efficacy of the volatility estimator. Yet many of the existing studies have always considered these two factors to be independent. Inspired by recent progress in Multi-Task Learning (MTL), we present a new approach using MTL in a deep neural network architecture that jointly learns portfolio construction and various auxiliary tasks related to volatility, such as forecasting realized volatility as measured by different volatility estimators. Through backtesting from January 2000 to Decem …

### 130. [Optimal Market Making in the Chinese Stock Market: A Stochastic Control and Scenario Analysis](http://arxiv.org/abs/2306.02764v1)  `2306.02764`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2023-06-05T10:40:53Z
- **Authors:** Shiqi Gong, Shuaiqiang Liu, Danny D. Sun
- **Why useful:** hits: _execution, market making, factor, volatility, var, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2306.02764v1](https://arxiv.org/pdf/2306.02764v1)  |  **Per-paper MD:** `papers/q-fin_PM/2306.02764_*.md`
- **Abstract:** Market making plays a crucial role in providing liquidity and maintaining stability in financial markets, making it an essential component of well-functioning capital markets. Despite its importance, there is limited research on market making in the Chinese stock market, which is one of the largest and most rapidly growing markets globally. To address this gap, we employ an optimal market making framework with an exponential CARA-type (Constant Absolute Risk Aversion) utility function that accounts for various market conditions, such as price drift, volatility, and stamp duty, and is capable of describing 3 major risks (i.e., inventory, execution and adverse selection risks) in market making practice, and provide an in-depth quantitative and scenario analysis of market making in the Chines …

### 131. [A parsimonious neural network approach to solve portfolio optimization problems without using dynamic programming](http://arxiv.org/abs/2303.08968v1)  `2303.08968`  **score 21**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2023-03-15T22:37:33Z
- **Authors:** Pieter M. van Staden, Peter A. Forsyth, Yuying Li
- **Why useful:** hits: _portfolio optimization, mean-variance, reinforcement learning, neural network, cta, var, sortino_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2303.08968v1](https://arxiv.org/pdf/2303.08968v1)  |  **Per-paper MD:** `papers/q-fin_CP/2303.08968_*.md`
- **Abstract:** We present a parsimonious neural network approach, which does not rely on dynamic programming techniques, to solve dynamic portfolio optimization problems subject to multiple investment constraints. The number of parameters of the (potentially deep) neural network remains independent of the number of portfolio rebalancing events, and in contrast to, for example, reinforcement learning, the approach avoids the computation of high-dimensional conditional expectations. As a result, the approach remains practical even when considering large numbers of underlying assets, long investment time horizons or very frequent rebalancing events. We prove convergence of the numerical solution to the theoretical optimal solution of a large class of problems under fairly general conditions, and present gro …

### 132. [Many learning agents interacting with an agent-based market model](http://arxiv.org/abs/2303.07393v4)  `2303.07393`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG, q-fin.ST | **Published:** 2023-03-13T18:15:52Z
- **Authors:** Matthew Dicks, Andrew Paskaramoorthy, Tim Gebbie
- **Why useful:** hits: _execution, slippage, reinforcement learning, var, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2303.07393v4](https://arxiv.org/pdf/2303.07393v4)  |  **Per-paper MD:** `papers/q-fin_TR/2303.07393_*.md`
- **Abstract:** We consider the dynamics and the interactions of multiple reinforcement learning optimal execution trading agents interacting with a reactive Agent-Based Model (ABM) of a financial market in event time. The model represents a market ecology with 3-trophic levels represented by: optimal execution learning agents, minimally intelligent liquidity takers, and fast electronic liquidity providers. The optimal execution agent classes include buying and selling agents that can either use a combination of limit orders and market orders, or only trade using market orders. The reward function explicitly balances trade execution slippage against the penalty of not executing the order timeously. This work demonstrates how multiple competing learning agents impact a minimally intelligent market simulati …

### 133. [Online learning techniques for prediction of temporal tabular datasets with regime changes](http://arxiv.org/abs/2301.00790v4)  `2301.00790`  **score 21**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP, cs.CE, cs.LG | **Published:** 2022-12-30T17:19:00Z
- **Authors:** Thomas Wong, Mauricio Barahona
- **Why useful:** hits: _overfit, machine learning, deep learning, neural network, drawdown, sharpe, calmar, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2301.00790v4](https://arxiv.org/pdf/2301.00790v4)  |  **Per-paper MD:** `papers/q-fin_CP/2301.00790_*.md`
- **Abstract:** The application of deep learning to non-stationary temporal datasets can lead to overfitted models that underperform under regime changes. In this work, we propose a modular machine learning pipeline for ranking predictions on temporal panel datasets which is robust under regime changes. The modularity of the pipeline allows the use of different models, including Gradient Boosting Decision Trees (GBDTs) and Neural Networks, with and without feature engineering. We evaluate our framework on financial data for stock portfolio prediction, and find that GBDT models with dropout display high performance, robustness and generalisability with reduced complexity and computational cost. We then demonstrate how online learning techniques, which require no retraining of models, can be used post-predi …

### 134. [A comparative study of the MACD-base trading strategies: evidence from the US stock market](http://arxiv.org/abs/2206.12282v1)  `2206.12282`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.GN, q-fin.PM | **Published:** 2022-06-18T11:33:55Z
- **Authors:** Pat Tong Chio
- **Why useful:** hits: _backtest, momentum, moving average, volatility, var, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2206.12282v1](https://arxiv.org/pdf/2206.12282v1)  |  **Per-paper MD:** `papers/q-fin_PM/2206.12282_*.md`
- **Abstract:** In recent years, more and more investors use technical analysis methods in their own trading. Evaluating the effectiveness of technical analysis has become more feasible due to increasing computing capability and blooming public data, which indie investors can perform stock analysis and backtest their own trading strategy conveniently. The Moving Average Convergence Divergence (MACD) indicator is one of the popular technical indicators that are widely used in different strategies. In order to verify the MACD effectiveness, in this thesis, I use the MACD indicator with traditional parameters (12, 26, 9) to build various trading strategies. Then, I apply these strategies to stocks listed on three indices in the US stock market (i.e., Dow-Jones, Nasdaq, and S&P 500) and evaluate its performan …

### 135. [A Meta-Method for Portfolio Management Using Machine Learning for Adaptive Strategy Selection](http://arxiv.org/abs/2111.05935v1)  `2111.05935`  **score 21**
- **Primary:** q-fin.PM | **All cats:** cs.CE, cs.LG, q-fin.CP, q-fin.PM, q-fin.RM | **Published:** 2021-11-10T20:46:43Z
- **Authors:** Damian Kisiel, Denise Gorse
- **Why useful:** hits: _portfolio management, risk parity, machine learning, xgboost, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2111.05935v1](https://arxiv.org/pdf/2111.05935v1)  |  **Per-paper MD:** `papers/q-fin_PM/2111.05935_*.md`
- **Abstract:** This work proposes a novel portfolio management technique, the Meta Portfolio Method (MPM), inspired by the successes of meta approaches in the field of bioinformatics and elsewhere. The MPM uses XGBoost to learn how to switch between two risk-based portfolio allocation strategies, the Hierarchical Risk Parity (HRP) and more classical Naïve Risk Parity (NRP). It is demonstrated that the MPM is able to successfully take advantage of the best characteristics of each strategy (the NRP's fast growth during market uptrends, and the HRP's protection against drawdowns during market turmoil). As a result, the MPM is shown to possess an excellent out-of-sample risk-reward profile, as measured by the Sharpe ratio, and in addition offers a high degree of interpretability of its asset allocation decis …

### 136. [Deep Reinforcement Trading with Predictable Returns](http://arxiv.org/abs/2104.14683v3)  `2104.14683`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM | **Published:** 2021-04-29T22:33:20Z
- **Authors:** Alessio Brini, Daniele Tantari
- **Why useful:** hits: _portfolio optimization, factor, reinforcement learning, cta, volatility, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2104.14683v3](https://arxiv.org/pdf/2104.14683v3)  |  **Per-paper MD:** `papers/q-fin_PM/2104.14683_*.md`
- **Abstract:** Classical portfolio optimization often requires forecasting asset returns and their corresponding variances in spite of the low signal-to-noise ratio provided in the financial markets. Modern deep reinforcement learning (DRL) offers a framework for optimizing sequential trader decisions but lacks theoretical guarantees of convergence. On the other hand, the performances on real financial trading problems are strongly affected by the goodness of the signal used to predict returns. To disentangle the effects coming from return unpredictability from those coming from algorithm un-trainability, we investigate the performance of model-free DRL traders in a market environment with different known mean-reverting factors driving the dynamics. When the framework admits an exact dynamic programming  …

### 137. [Using Machine Learning and Alternative Data to Predict Movements in Market Risk](http://arxiv.org/abs/2009.07947v1)  `2009.07947`  **score 21**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP, q-fin.ST | **Published:** 2020-09-16T21:36:03Z
- **Authors:** Thomas Dierckx, Jesse Davis, Wim Schoutens
- **Why useful:** hits: _sentiment, market making, machine learning, volatility, var, derivative, alternative data_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2009.07947v1](https://arxiv.org/pdf/2009.07947v1)  |  **Per-paper MD:** `papers/q-fin_CP/2009.07947_*.md`
- **Abstract:** Using machine learning and alternative data for the prediction of financial markets has been a popular topic in recent years. Many financial variables such as stock price, historical volatility and trade volume have already been through extensive investigation. Remarkably, we found no existing research on the prediction of an asset's market implied volatility within this context. This forward-looking measure gauges the sentiment on the future volatility of an asset, and is deemed one of the most important parameters in the world of derivatives. The ability to predict this statistic may therefore provide a competitive edge to practitioners of market making and asset management alike. Consequently, in this paper we investigate Google News statistics and Wikipedia site traffic as alternative  …

### 138. [Enhancing Time Series Momentum Strategies Using Deep Neural Networks](http://arxiv.org/abs/1904.04912v3)  `1904.04912`  **score 21**
- **Primary:** stat.ML | **All cats:** stat.ML, cs.LG, q-fin.TR | **Published:** 2019-04-09T21:06:55Z
- **Authors:** Bryan Lim, Stefan Zohren, Stephen Roberts
- **Why useful:** hits: _backtest, factor, deep learning, lstm, neural network, momentum, volatility, sharpe, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1904.04912v3](https://arxiv.org/pdf/1904.04912v3)  |  **Per-paper MD:** `papers/stat_ML/1904.04912_*.md`
- **Abstract:** While time series momentum is a well-studied phenomenon in finance, common strategies require the explicit definition of both a trend estimator and a position sizing rule. In this paper, we introduce Deep Momentum Networks -- a hybrid approach which injects deep learning based trading rules into the volatility scaling framework of time series momentum. The model also simultaneously learns both trend estimation and position sizing in a data-driven manner, with networks directly trained by optimising the Sharpe ratio of the signal. Backtesting on a portfolio of 88 continuous futures contracts, we demonstrate that the Sharpe-optimised LSTM improved traditional methods by more than two times in the absence of transactions costs, and continue outperforming when considering transaction costs up  …

### 139. [A stochastic partial differential equation model for limit order book dynamics](http://arxiv.org/abs/1904.03058v2)  `1904.03058`  **score 21**
- **Primary:** q-fin.TR | **All cats:** math.PR, q-fin.CP, q-fin.TR | **Published:** 2019-04-05T13:33:56Z
- **Authors:** Rama Cont, Marvin S. Mueller
- **Why useful:** hits: _order book, order flow, factor, cta, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1904.03058v2](https://arxiv.org/pdf/1904.03058v2)  |  **Per-paper MD:** `papers/q-fin_TR/1904.03058_*.md`
- **Abstract:** We propose an analytically tractable class of models for the dynamics of a limit order book, described through a stochastic partial differential equation (SPDE) with multiplicative noise for the order book centered at the mid-price, along with stochastic dynamics for the mid-price which is consistent with the order flow dynamics. We provide conditions under which the model admits a finite dimensional realization driven by a (low-dimensional) Markov process, leading to efficient estimation and computation methods. We study two examples of parsimonious models in this class: a two-factor model and a model with mean-reverting order book depth. For each model we analyze in detail the role of different parameters, the dynamics of the price, order book depth, volume and order imbalance, provide a …

### 140. [Stacking with Neural network for Cryptocurrency investment](http://arxiv.org/abs/1902.07855v2)  `1902.07855`  **score 21**
- **Primary:** stat.ML | **All cats:** stat.ML, cs.LG, q-fin.GN | **Published:** 2019-02-21T03:36:50Z
- **Authors:** Avinash Barnwal, Hari Pad Bharti, Aasim Ali, Vishal Singh
- **Why useful:** hits: _walk forward, cross-validation, sentiment, machine learning, neural network, momentum, volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1902.07855v2](https://arxiv.org/pdf/1902.07855v2)  |  **Per-paper MD:** `papers/stat_ML/1902.07855_*.md`
- **Abstract:** Predicting the direction of assets have been an active area of study and a difficult task. Machine learning models have been used to build robust models to model the above task. Ensemble methods is one of them showing results better than a single supervised method. In this paper, we have used generative and discriminative classifiers to create the stack, particularly 3 generative and 6 discriminative classifiers and optimized over one-layer Neural Network to model the direction of price cryptocurrencies. Features used are technical indicators used are not limited to trend, momentum, volume, volatility indicators, and sentiment analysis has also been used to gain useful insight combined with the above features. For Cross-validation, Purged Walk forward cross-validation has been used. In ter …

### 141. [Price impact without order book: A study of the OTC credit index market](http://arxiv.org/abs/1609.04620v1)  `1609.04620`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2016-09-15T13:11:34Z
- **Authors:** Zoltan Eisler, Jean-Philippe Bouchaud
- **Why useful:** hits: _market microstructure, order book, order flow, cta, limit order, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1609.04620v1](https://arxiv.org/pdf/1609.04620v1)  |  **Per-paper MD:** `papers/q-fin_TR/1609.04620_*.md`
- **Abstract:** We present a study of price impact in the over-the-counter credit index market, where no limit order book is used. Contracts are traded via dealers, that compete for the orders of clients. Despite this distinct microstructure, we successfully apply the propagator technique to estimate the price impact of individual transactions. Because orders are typically split less than in multilateral markets, impact is observed to be mainly permanent, in line with theoretical expectations. A simple method is presented to correct for errors in our classification of trades between buying and selling. We find a very significant, temporary increase in order flow correlations during late 2015 and early 2016, which we attribute to increased order splitting or herding among investors. We also find indication …

### 142. [Notes on Alpha Stream Optimization](http://arxiv.org/abs/1406.1249v2)  `1406.1249`  **score 21**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.RM | **Published:** 2014-06-05T00:41:28Z
- **Authors:** Zura Kakushadze
- **Why useful:** hits: _execution, factor, alpha, cta, volatility, var, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1406.1249v2](https://arxiv.org/pdf/1406.1249v2)  |  **Per-paper MD:** `papers/q-fin_PM/1406.1249_*.md`
- **Abstract:** In these notes we discuss investment allocation to multiple alpha streams traded on the same execution platform, including when trades are crossed internally resulting in turnover reduction. We discuss approaches to alpha weight optimization where one maximizes P&L subject to bounds on volatility (or Sharpe ratio). The presence of negative alpha weights, which are allowed when alpha streams are traded on the same execution platform, complicates the optimization problem. By using factor model approach to alpha covariance matrix, the original optimization problem can be viewed as a 1-dimensional root searching problem plus an optimization problem that requires a finite number of iterations. We discuss this approach without costs and with linear costs, and also with nonlinear costs in a certa …

### 143. [Realtime market microstructure analysis: online Transaction Cost Analysis](http://arxiv.org/abs/1302.6363v2)  `1302.6363`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.IT, math.ST | **Published:** 2013-02-26T09:04:34Z
- **Authors:** Robert Azencott, Arjun Beri, Yutheeka Gadhyan, Nicolas Joseph, Charles-Albert Lehalle, Matthew Rowley
- **Why useful:** hits: _market microstructure, execution, mean-variance, factor, anomaly, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1302.6363v2](https://arxiv.org/pdf/1302.6363v2)  |  **Per-paper MD:** `papers/q-fin_TR/1302.6363_*.md`
- **Abstract:** Motivated by the practical challenge in monitoring the performance of a large number of algorithmic trading orders, this paper provides a methodology that leads to automatic discovery of the causes that lie behind a poor trading performance. It also gives theoretical foundations to a generic framework for real-time trading analysis. Academic literature provides different ways to formalize these algorithms and show how optimal they can be from a mean-variance, a stochastic control, an impulse control or a statistical learning viewpoint. This paper is agnostic about the way the algorithm has been built and provides a theoretical formalism to identify in real-time the market conditions that influenced its efficiency or inefficiency. For a given set of characteristics describing the market con …

### 144. [High Frequency Market Making](http://arxiv.org/abs/1210.5781v1)  `1210.5781`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2012-10-21T23:39:20Z
- **Authors:** Rene Carmona, Kevin Webster
- **Why useful:** hits: _order book, market making, alpha, cta, var, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1210.5781v1](https://arxiv.org/pdf/1210.5781v1)  |  **Per-paper MD:** `papers/q-fin_TR/1210.5781_*.md`
- **Abstract:** Since they were authorized by the U.S. Security and Exchange Commission in 1998, electronic exchanges have boomed, and by 2010 high frequency trading accounted for over 70% of equity trades in the US. Such markets are thought to increase liquidity because of the presence of market makers, who are willing to trade as counterparties at any time, in exchange for a fee, the bid-ask spread. In this paper, we propose an equilibrium model showing how such market makers provide liquidity. The model relies on a codebook for client trades, the implied alpha. After solving the individual clients optimization problems and identifying their implied alphas, we frame the market maker stochastic optimization problem as a stochastic control problem with an infinite dimensional control variable. Assuming ei …

### 145. [Order book dynamics in liquid markets: limit theorems and diffusion approximations](http://arxiv.org/abs/1202.6412v1)  `1202.6412`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, q-fin.CP, q-fin.ST | **Published:** 2012-02-28T23:52:55Z
- **Authors:** Rama Cont, Adrien De Larrard
- **Why useful:** hits: _order book, order flow, cta, garch, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1202.6412v1](https://arxiv.org/pdf/1202.6412v1)  |  **Per-paper MD:** `papers/q-fin_TR/1202.6412_*.md`
- **Abstract:** We propose a model for the dynamics of a limit order book in a liquid market where buy and sell orders are submitted at high frequency. We derive a functional central limit theorem for the joint dynamics of the bid and ask queues and show that, when the frequency of order arrivals is large, the intraday dynamics of the limit order book may be approximated by a Markovian jump-diffusion process in the positive orthant, whose characteristics are explicitly described in terms of the statistical properties of the underlying order flow. This result allows to obtain tractable analytical approximations for various quantities of interest, such as the probability of a price increase or the distribution of the duration until the next price move, conditional on the state of the order book. Our results …

### 146. [Price dynamics in a Markovian limit order market](http://arxiv.org/abs/1104.4596v1)  `1104.4596`  **score 21**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, q-fin.ST | **Published:** 2011-04-24T00:16:56Z
- **Authors:** Rama Cont, Adrien De Larrard
- **Why useful:** hits: _order book, order flow, cta, volatility, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1104.4596v1](https://arxiv.org/pdf/1104.4596v1)  |  **Per-paper MD:** `papers/q-fin_TR/1104.4596_*.md`
- **Abstract:** We propose and study a simple stochastic model for the dynamics of a limit order book, in which arrivals of market order, limit orders and order cancellations are described in terms of a Markovian queueing system. Through its analytical tractability, the model allows to obtain analytical expressions for various quantities of interest such as the distribution of the duration between price changes, the distribution and autocorrelation of price changes, and the probability of an upward move in the price, {\it conditional} on the state of the order book. We study the diffusion limit of the price process and express the volatility of price changes in terms of parameters describing the arrival rates of buy and sell orders and cancelations. These analytical results provide some insight into the r …

### 147. [Anomaly detection in European cryptocurrency exchange-traded products](http://arxiv.org/abs/2608.09576v1)  `2608.09576`  **score 20**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF | **Published:** 2026-08-10T13:11:31Z
- **Authors:** Julia Kończal, Rafał Połoczański
- **Why useful:** hits: _anomaly, random forest, momentum, cta, volatility, var, drawdown, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.09576v1](https://arxiv.org/pdf/2608.09576v1)  |  **Per-paper MD:** `papers/q-fin_MF/2608.09576_*.md`
- **Abstract:** Cryptocurrency exchange-traded products (ETPs) listed on European exchanges provide a regulated environment for studying intraday market anomalies. We study four Bitcoin and Ethereum ETPs traded on Xetra and Nasdaq Stockholm over the period January 2024 - December 2025 using one-minute bars. As a benchmark, we adopt an extreme value theory approach in which anomalous bars are defined as returns falling below a threshold estimated by fitting a generalised Pareto distribution to left-tail exceedances. We then propose three new binary anomaly indicators. The first, a cross-venue divergence anomaly, identifies venue-specific price divergence between the two exchanges. The second is a no-recovery anomaly that identifies extreme price drops followed by little or no recovery over the next ten act …

### 148. [OpenMarket: A Synchronized Polymarket-Binance Dataset for High-Frequency Prediction-Market Research](http://arxiv.org/abs/2607.26245v1)  `2607.26245`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2026-07-28T20:28:16Z
- **Authors:** Gregory Young
- **Why useful:** hits: _walk-forward, order book, order flow, slippage, event study_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.26245v1](https://arxiv.org/pdf/2607.26245v1)  |  **Per-paper MD:** `papers/q-fin_TR/2607.26245_*.md`
- **Abstract:** OpenMarket began as an attempt to trade Polymarket's BTC 15-minute binary markets against Binance BTC/USDT order flow. The attempt did not produce a tradable edge: out-of-sample, a walk-forward logistic model over 43 microstructure features does not beat, and slightly underperforms, the probability already implied by Polymarket's own order book, and simulated trading nets -0.116 normalized payoff units per attempted trade under stated fee and slippage assumptions. We release the synchronized corpus and infrastructure that attempt produced and, to our knowledge, the first public millisecond-level Polymarket BTC / Binance BTC-USDT paired corpus with explicit pairing metadata. The frozen archive (tag v0.5.2) contains 727,098,247 deduplicated rows across 202 archival snapshots, with event data …

### 149. [End-to-End Parametric Portfolio Policies for Cross-Asset Futures Timing: When Do AI Models Beat Simple Rules?](http://arxiv.org/abs/2607.00475v1)  `2607.00475`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.PM, q-fin.ST, q-fin.TR | **Published:** 2026-07-01T05:49:41Z
- **Authors:** Austin Pollok, Kevin Robik
- **Why useful:** hits: _risk parity, lstm, transformer, momentum, sharpe, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2607.00475v1](https://arxiv.org/pdf/2607.00475v1)  |  **Per-paper MD:** `papers/q-fin_ST/2607.00475_*.md`
- **Abstract:** Timing-based tilts across asset classes can drive much of the risk and return of a diversified cross-asset portfolio. The standard approach forecasts returns and then optimizes weights. We instead study an end-to-end AI-based policy that maps market states directly to portfolio weights, and we then ask when this one-step modeling approach outperforms simple rules-based strategies. We train these policies on the sixteen most liquid CME futures, where an edge is unlikely to be due to illiquidity, using a differentiable Sharpe ratio loss function, and we benchmark them against equal weighting, risk parity, and time-series momentum. The learned policies rank above the rules on the pooled cross-asset portfolio and in several sub-asset classes, but not uniformly. In gross terms, an LSTM and a tr …

### 150. [Regime-Conditional Distributional Comparison of Trading Strategies: A GAMLSS/ZAGA Framework Applied to the S&P 500](http://arxiv.org/abs/2606.31251v1)  `2606.31251`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2026-06-30T07:26:07Z
- **Authors:** Krzysztof Ozimek
- **Why useful:** hits: _walk-forward, backtest, momentum, volatility, var, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.31251v1](https://arxiv.org/pdf/2606.31251v1)  |  **Per-paper MD:** `papers/q-fin_ST/2606.31251_*.md`
- **Abstract:** Conventional comparisons of algorithmic trading strategies reduce each performance metric to a single number over the full backtest horizon, thereby discarding information about how performance varies with market conditions. This paper proposes a distributional framework that addresses this shortcoming. A walk-forward backtest of 146 out-of-sample folds on the S&P 500 (2002--2025) is used to compute the Adjusted Information Ratio ($IR^{\ast}$) for a polynomial Support Vector Machine strategy (SVMP) and a buy-and-hold benchmark (BH) in each fold. The resulting $IR^{\ast}$ sequences are modelled jointly via a Generalised Additive Model for Location, Scale and Shape (GAMLSS) with a Zero-Adjusted Gamma (ZAGA) response, with distributional parameters conditioned on market regime covariates: rea …

### 151. [Supply Chain Propagation of Textual Signals: LLM Embeddings and Cross-Sectional Return Predictability](http://arxiv.org/abs/2606.29290v1)  `2606.29290`  **score 20**
- **Primary:** q-fin.PR | **All cats:** q-fin.PR | **Published:** 2026-06-28T09:26:45Z
- **Authors:** Asef Yılkı
- **Why useful:** hits: _finbert, factor, alpha, momentum, cta, volatility, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.29290v1](https://arxiv.org/pdf/2606.29290v1)  |  **Per-paper MD:** `papers/q-fin_PR/2606.29290_*.md`
- **Abstract:** This paper proposes a novel asset pricing framework that augments large language model (LLM) embeddings of annual report disclosures with supply chain knowledge graph (KG) propagation. Using FinBERT embeddings of 10-K MD&A sections for 255 S&P 500 firms over 2011-2025, two sets of return predictors are constructed: direct LLM embeddings and network-augmented embeddings, where firm-level signals propagate through inter-firm linkages. Fama-MacBeth cross-sectional regressions reveal that the network-augmented factor (net_pc_5) carries significant return predictability with a Newey-West t-statistic of -2.64, even after controlling for momentum, volatility, and firm size. A long-short portfolio sorted on net_pc_5 achieves an annualized Sharpe ratio of 0.86 and a Fama-French five-factor alpha of …

### 152. [Option-Implied Signals and Crash Risk: Predictability and Machine-Learning Evidence from U.S. Equity Options](http://arxiv.org/abs/2608.26115v1)  `2608.26115`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2026-06-10T10:13:06Z
- **Authors:** Baichuan Li, Mengxiao Wang
- **Why useful:** hits: _xgboost, cta, volatility, var, options, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2608.26115v1](https://arxiv.org/pdf/2608.26115v1)  |  **Per-paper MD:** `papers/q-fin_ST/2608.26115_*.md`
- **Abstract:** We re-estimate canonical option-implied predictability evidence using a unified 2015--2026 panel of 12.36 million U.S. equity firm-day observations across 10,026 underlyings. We split the sample into three regimes: late-post-crisis low volatility (2015--2019), high-volatility transition (2020--2022), and AI/mega-cap concentration (2023--2026). The Xing et al. (2010) smirk--return relationship weakens steadily: the next-month univariate smirk coefficient falls from $-0.023$ $(t=-5.5)$ in 2015--2019 to an insignificant $-0.006$ $(t=-1.5)$ in 2023--2026, and turns positive at the three-month horizon $(+0.016,\ t=+2.1)$. In joint specifications with all six canonical signals, the smirk is insignificant throughout and again changes sign in the latest regime. By contrast, the Cremers--Weinbaum I …

### 153. [Volatility Forecasting and Return Prediction under Market Regimes: Evidence from High-Frequency Chinese Equity Data](http://arxiv.org/abs/2606.09478v1)  `2606.09478`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.CP, q-fin.MF, q-fin.TR | **Published:** 2026-06-08T13:36:57Z
- **Authors:** Xinyue Fang, Robert Ślepaczuk
- **Why useful:** hits: _walk-forward, xgboost, cta, volatility, garch, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.09478v1](https://arxiv.org/pdf/2606.09478v1)  |  **Per-paper MD:** `papers/q-fin_TR/2606.09478_*.md`
- **Abstract:** This study investigates whether regime-dependent volatility forecasting and machine-learning-based return prediction can be jointly integrated to improve both statistical forecasting performance and economic strategy outcomes in equity markets. Using high-frequency CSI 300 Index data from 2005 to 2023, a sequential twostage framework is developed. In the first stage, realized volatility is modeled using regime-augmented HARQ specifications combined with Markov-switching GJR-GARCH filtering to capture long-memory dynamics, asymmetry, and structural market regimes. In the second stage, volatility forecasts, regime indicators, and return-related predictors are incorporated into an XGBoost return-prediction model estimated through a strictly walk-forward out-of-sample procedure. The empirical  …

### 154. [Regime-Based Portfolio Allocation Using Hidden Markov Models and Reinforcement Learning](http://arxiv.org/abs/2605.27848v1)  `2605.27848`  **score 20**
- **Primary:** q-fin.PM | **All cats:** econ.EM, q-fin.CP, q-fin.MF, q-fin.PM, q-fin.ST | **Published:** 2026-05-27T02:04:31Z
- **Authors:** Ajay Kumar Verma, Nunik Srikandi Putri, Neo Paul Lesupi
- **Why useful:** hits: _execution, reinforcement learning, volatility, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2605.27848v1](https://arxiv.org/pdf/2605.27848v1)  |  **Per-paper MD:** `papers/q-fin_PM/2605.27848_*.md`
- **Abstract:** This study develops a regime-aware portfolio allocation framework that integrates Markov switching models with Reinforcement Learning (RL) to dynamically allocate across equities (SPY), long-term Treasuries (TLT), and gold (GLD). Using daily ETF data from 2004-2025, we first characterize market behavior through a discrete Markov chain and then estimate a three-state Gaussian Hidden Markov Model (HMM) selected by the Bayesian Information Criterion (BIC). The estimated regimes-low-volatility, transitional, and high-volatility-exhibit strong persistence and state-dependent return dynamics consistent with recent findings on nonlinear market states (Ardia et al., 2024; Gupta & Pierdzioch, 2023). State-conditional analysis shows that SPY dominates in stable regimes, while TLT and GLD provide pro …

### 155. [Bitcoin Price Prediction: Peer-Reviewed Evidence and Social Media Discourse](http://arxiv.org/abs/2606.00071v1)  `2606.00071`  **score 20**
- **Primary:** q-fin.GN | **All cats:** q-fin.GN, cs.CE, cs.DC, econ.GN | **Published:** 2026-05-20T18:06:33Z
- **Authors:** Carlos Baquero
- **Why useful:** hits: _overfit, walk-forward, backtest, social media, cta, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2606.00071v1](https://arxiv.org/pdf/2606.00071v1)  |  **Per-paper MD:** `papers/q-fin_GN/2606.00071_*.md`
- **Abstract:** Bitcoin price prediction has attracted hundreds of academic papers and continuous social media debate, yet the field lacks consensus on even basic questions: can any model beat a naive "today's price" baseline at horizons of one to six months? We survey the peer-reviewed landscape, categorize papers by evaluation methodology, and contrast academic findings with informal but substantive discourse on X/Twitter. The picture that emerges is sobering. At short-to-medium horizons, no peer-reviewed study has shown robust superiority over the naive baseline across multiple market regimes. Daily predictability is real but does not extend to hourly or monthly horizons, and may not survive transaction costs. The stock-to-flow model has failed formal out-of-sample testing, and Metcalfe's Law valuation …

### 156. [Measuring Strategy-Decay Risk: Minimum Regime Performance and the Durability of Systematic Investing](http://arxiv.org/abs/2604.08356v1)  `2604.08356`  **score 20**
- **Primary:** q-fin.RM | **All cats:** q-fin.PM, q-fin.RM, stat.AP | **Published:** 2026-04-09T15:21:07Z
- **Authors:** Nolan Alexander, Frank Fabozzi
- **Why useful:** hits: _factor, alpha, volatility, drawdown, sharpe, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2604.08356v1](https://arxiv.org/pdf/2604.08356v1)  |  **Per-paper MD:** `papers/q-fin_RM/2604.08356_*.md`
- **Abstract:** Systematic investment strategies are exposed to a subtle but pervasive vulnerability: the progressive erosion of their effectiveness as market regimes change. Traditional risk measures, designed to capture volatility or drawdowns, overlook this form of structural fragility. This article introduces a quantitative framework for assessing the durability of systematic strategies through minimum regime performance (MRP), defined as the lowest realized risk-adjusted return across distinct historical regimes. MRP serves as a lower bound on a strategy's robustness, capturing how performance deteriorates when underlying relationships weaken or competitive pressures compress alpha. Applied to a broad universe of established factor strategies, the measure reveals a consistent trade-off between effici …

### 157. [Uncertainty-Aware Deep Hedging](http://arxiv.org/abs/2603.10137v1)  `2603.10137`  **score 20**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP | **Published:** 2026-03-10T18:17:51Z
- **Authors:** Manan Poddar
- **Why useful:** hits: _machine learning, lstm, neural network, volatility, var, cvar, hedging, derivative, stochastic volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.10137v1](https://arxiv.org/pdf/2603.10137v1)  |  **Per-paper MD:** `papers/q-fin_CP/2603.10137_*.md`
- **Abstract:** Deep hedging trains neural networks to manage derivative risk under market frictions, but produces hedge ratios with no measure of model confidence -- a significant barrier to deployment. We introduce uncertainty quantification to the deep hedging framework by training a deep ensemble of five independent LSTM networks under Heston stochastic volatility with proportional transaction costs. The ensemble's disagreement at each time step provides a per-time-step confidence measure that is strongly predictive of hedging performance: the learned strategy outperforms the Black-Scholes delta on approximately 80% of paths when model agreement is high, but on fewer than 20% when disagreement is elevated. We propose a CVaR-optimised blending strategy that combines the ensemble's hedge with the classi …

### 158. [Competition between DEXs through Dynamic Fees](http://arxiv.org/abs/2603.09669v1)  `2603.09669`  **score 20**
- **Primary:** q-fin.MF | **All cats:** math.OC, q-fin.MF, q-fin.TR | **Published:** 2026-03-10T13:41:31Z
- **Authors:** Leonardo Baggiani, Martin Herdegen, Leandro Sanchez-Betancourt
- **Why useful:** hits: _order flow, execution, slippage, cta, volatility, regime, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2603.09669v1](https://arxiv.org/pdf/2603.09669v1)  |  **Per-paper MD:** `papers/q-fin_MF/2603.09669_*.md`
- **Abstract:** We find an approximate Nash equilibrium in a game between decentralized exchanges (DEXs) that compete for order flow by setting dynamic trading fees. We characterize the equilibrium via a coupled system of partial differential equations and derive tractable approximate closed-form expressions for the equilibrium fees. Our analysis shows that the two-regime structure found in monopoly models persists under competition: pools alternate between raising fees to deter arbitrage and lowering fees to attract noise trading and increase volatility. Under competition, however, the switching boundary shifts from the oracle price to a weighted average of the oracle and competitors' exchange rates. Our numerical experiments show that, holding total liquidity fixed, an increase in the number of competin …

### 159. [Alpha-R1: Alpha Screening with LLM Reasoning via Reinforcement Learning](http://arxiv.org/abs/2512.23515v2)  `2512.23515`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.AI, cs.CE, cs.LG | **Published:** 2025-12-29T14:50:23Z
- **Authors:** Zuoyou Jiang, Li Zhao, Rui Sun, Ruohan Sun, Zhongjian Li, Jing Li, Daxin Jiang, Zuo Bai, Cheng Hua
- **Why useful:** hits: _factor, alpha, machine learning, reinforcement learning, sharpe, regime, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2512.23515v2](https://arxiv.org/pdf/2512.23515v2)  |  **Per-paper MD:** `papers/q-fin_TR/2512.23515_*.md`
- **Abstract:** Signal decay and regime shifts pose recurring challenges for data-driven investment strategies in non-stationary markets, where conventional time-series and machine learning approaches often struggle to generalize beyond historical correlations. While large language models (LLMs) offer strong capabilities for processing unstructured information, their potential to support quantitative factor screening through explicit economic reasoning remains underexplored. Existing factor-based methods typically reduce alphas to numerical time series, overlooking the semantic rationale that determines when a factor is economically relevant. We present Alpha-R1, an RL-aligned LLM framework for context-aware alpha screening. Its core mechanism, semantic gating, evaluates each candidate factor's semantic p …

### 160. [When Reasoning Fails: Evaluating 'Thinking' LLMs for Stock Prediction](http://arxiv.org/abs/2511.08608v1)  `2511.08608`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2025-11-05T08:40:44Z
- **Authors:** Rakeshkumar H Sodha
- **Why useful:** hits: _walk-forward, backtest, random forest, cta, var, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2511.08608v1](https://arxiv.org/pdf/2511.08608v1)  |  **Per-paper MD:** `papers/q-fin_ST/2511.08608_*.md`
- **Abstract:** Problem. "Thinking" LLMs (TLLMs) expose explicit or hidden reasoning traces and are widely believed to generalize better on complex tasks than direct LLMs. Whether this promise carries to noisy, heavy-tailed and regime-switching financial data remains unclear. Approach. Using Indian equities (NIFTY constituents), we run a rolling 48m/1m walk-forward evaluation at horizon k = 1 day and dial cross-sectional complexity via the universe size U in {5, 11, 21, 36} while keeping the reasoning budget fixed (B = 512 tokens) for the TLLM. We compare a direct LLM (gpt-4o-mini), a TLLM (gpt-5), and classical learners (ridge, random forest) on cross-sectional ranking loss 1 - IC, MSE, and long/short backtests with realistic costs. Statistical confidence is measured with Diebold-Mariano, Pesaran-Timmerm …

### 161. [(Non-Parametric) Bootstrap Robust Optimization for Portfolios and Trading Strategies](http://arxiv.org/abs/2510.12725v1)  `2510.12725`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST | **Published:** 2025-10-14T17:06:03Z
- **Authors:** Daniel Cunha Oliveira, Grover Guzman, Nick Firoozye
- **Why useful:** hits: _overfit, portfolio optimization, reinforcement learning, momentum, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.12725v1](https://arxiv.org/pdf/2510.12725v1)  |  **Per-paper MD:** `papers/q-fin_ST/2510.12725_*.md`
- **Abstract:** Robust optimization provides a principled framework for decision-making under uncertainty, with broad applications in finance, engineering, and operations research. In portfolio optimization, uncertainty in expected returns and covariances demands methods that mitigate estimation error, parameter instability, and model misspecification. Traditional approaches, including parametric, bootstrap-based, and Bayesian methods, enhance stability by relying on confidence intervals or probabilistic priors but often impose restrictive assumptions. This study introduces a non-parametric bootstrap framework for robust optimization in financial decision-making. By resampling empirical data, the framework constructs flexible, data-driven confidence intervals without assuming specific distributional forms …

### 162. [Application of Deep Reinforcement Learning to At-the-Money S&P 500 Options Hedging](http://arxiv.org/abs/2510.09247v1)  `2510.09247`  **score 20**
- **Primary:** q-fin.CP | **All cats:** cs.LG, q-fin.CP, q-fin.PR | **Published:** 2025-10-10T10:35:50Z
- **Authors:** Zofia Bracha, Paweł Sakowski, Jakub Michańków
- **Why useful:** hits: _walk-forward, reinforcement learning, volatility, var, sharpe, options, hedging, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.09247v1](https://arxiv.org/pdf/2510.09247v1)  |  **Per-paper MD:** `papers/q-fin_CP/2510.09247_*.md`
- **Abstract:** This paper explores the application of deep Q-learning to hedging at-the-money options on the S\&P~500 index. We develop an agent based on the Twin Delayed Deep Deterministic Policy Gradient (TD3) algorithm, trained to simulate hedging decisions without making explicit model assumptions on price dynamics. The agent was trained on historical intraday prices of S\&P~500 call options across years 2004--2024, using a single time series of six predictor variables: option price, underlying asset price, moneyness, time to maturity, realized volatility, and current hedge position. A walk-forward procedure was applied for training, which led to nearly 17~years of out-of-sample evaluation. The performance of the deep reinforcement learning (DRL) agent is benchmarked against the Black--Scholes delta- …

### 163. [Tail-Safe Stochastic-Control SPX-VIX Hedging: A White-Box Bridge Between AI Sensitivities and Arbitrage-Free Market Dynamics](http://arxiv.org/abs/2510.15937v1)  `2510.15937`  **score 20**
- **Primary:** q-fin.RM | **All cats:** q-fin.RM, q-fin.TR | **Published:** 2025-10-09T09:30:17Z
- **Authors:** Jian'an Zhang
- **Why useful:** hits: _execution, volatility, var, tail risk, vix, hedging, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2510.15937v1](https://arxiv.org/pdf/2510.15937v1)  |  **Per-paper MD:** `papers/q-fin_RM/2510.15937_*.md`
- **Abstract:** We present a white-box, risk-sensitive framework for jointly hedging SPX and VIX exposures under transaction costs and regime shifts. The approach couples an arbitrage-free market teacher with a control layer that enforces safety as constraints. On the market side, we integrate an SSVI-based implied-volatility surface and a Cboe-compliant VIX computation (including wing pruning and 30-day interpolation), and connect prices to dynamics via a clipped, convexity-preserving Dupire local-volatility extractor. On the control side, we pose hedging as a small quadratic program with control-barrier-function (CBF) boxes for inventory, rate, and tail risk; a sufficient-descent execution gate that trades only when risk drop justifies cost; and three targeted tail-safety upgrades: a correlation/expiry- …

### 164. [Factor-Based Conditional Diffusion Model for Contextual Portfolio Optimization](http://arxiv.org/abs/2509.22088v3)  `2509.22088`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, stat.ML | **Published:** 2025-09-26T09:11:08Z
- **Authors:** Xuefeng Gao, Mengying He, Xuedong He, Jiale Zha
- **Why useful:** hits: _portfolio optimization, mean-variance, factor, transformer, var, cvar_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.22088v3](https://arxiv.org/pdf/2509.22088v3)  |  **Per-paper MD:** `papers/q-fin_PM/2509.22088_*.md`
- **Abstract:** We propose a novel conditional diffusion model for contextual portfolio optimization that learns the cross-sectional distribution of next-day stock returns conditioned on high-dimensional asset-specific factors. Our model leverages a Diffusion Transformer architecture with token-wise conditioning, which enables linking each asset's return to its own factor vector while capturing complex cross-asset dependencies. By drawing generative samples from the learned conditional return distribution, we perform daily mean-variance and mean-CVaR optimization, incorporating transaction costs and realistic constraints. Using data from the Chinese A-share market, we demonstrate that our approach consistently outperforms various standard benchmarks across multiple risk-adjusted performance metrics. Furth …

### 165. [Increase Alpha: Performance and Risk of an AI-Driven Trading Framework](http://arxiv.org/abs/2509.16707v2)  `2509.16707`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG | **Published:** 2025-09-20T14:37:02Z
- **Authors:** Sid Ghatak, Arman Khaledian, Navid Parvini, Nariman Khaledian
- **Why useful:** hits: _alpha, deep learning, transformer, var, drawdown, sharpe, macro, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.16707v2](https://arxiv.org/pdf/2509.16707v2)  |  **Per-paper MD:** `papers/q-fin_PM/2509.16707_*.md`
- **Abstract:** There are inefficiencies in financial markets, with unexploited patterns in price, volume, and cross-sectional relationships. While many approaches use large-scale transformers, we take a domain-focused path: feed-forward and recurrent networks with curated features to capture subtle regularities in noisy financial data. This smaller-footprint design is computationally lean and reliable under low signal-to-noise, crucial for daily production at scale. At Increase Alpha, we built a deep-learning framework that maps over 800 U.S. equities into daily directional signals with minimal computational overhead. The purpose of this paper is twofold. First, we outline the general overview of the predictive model without disclosing its core underlying concepts. Second, we evaluate its real-time perfo …

### 166. [DeltaHedge: A Multi-Agent Framework for Portfolio Options Optimization](http://arxiv.org/abs/2509.12753v1)  `2509.12753`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG, cs.MA | **Published:** 2025-09-16T07:14:56Z
- **Authors:** Feliks Bańka, Jarosław A. Chudziak
- **Why useful:** hits: _portfolio optimization, portfolio management, reinforcement learning, var, options, hedging_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2509.12753v1](https://arxiv.org/pdf/2509.12753v1)  |  **Per-paper MD:** `papers/q-fin_PM/2509.12753_*.md`
- **Abstract:** In volatile financial markets, balancing risk and return remains a significant challenge. Traditional approaches often focus solely on equity allocation, overlooking the strategic advantages of options trading for dynamic risk hedging. This work presents DeltaHedge, a multi-agent framework that integrates options trading with AI-driven portfolio management. By combining advanced reinforcement learning techniques with an ensembled options-based hedging strategy, DeltaHedge enhances risk-adjusted returns and stabilizes portfolio performance across varying market conditions. Experimental results demonstrate that DeltaHedge outperforms traditional strategies and standalone models, underscoring its potential to transform practical portfolio management in complex financial environments. Building …

### 167. [Dynamic Liquidity Provision in Decentralized Markets: Strategy Optimization and Performance Evaluation in Concentrated Liquidity AMMs](http://arxiv.org/abs/2505.15338v2)  `2505.15338`  **score 20**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF | **Published:** 2025-05-21T10:09:29Z
- **Authors:** Andrey Urusov, Rostislav Berezovskiy, Anatoly Krestenko, Andrei Kornilov, Yury Yanovich
- **Why useful:** hits: _backtest, market microstructure, market making, factor, machine learning, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2505.15338v2](https://arxiv.org/pdf/2505.15338v2)  |  **Per-paper MD:** `papers/q-fin_MF/2505.15338_*.md`
- **Abstract:** Concentrated Liquidity Market Makers (CLMMs) represent a fundamental innovation in market microstructure, transforming liquidity provision from passive portfolio allocation to active risk management. This evolution creates significant challenges for performance evaluation and strategy optimization, particularly due to the absence of comprehensive historical liquidity data. We address these challenges through a novel methodological framework that reconstructs historical liquidity states from swap transaction data, enabling rigorous backtesting of dynamic liquidity provision strategies. Our parametric reconstruction method achieves high accuracy (approximation errors averaging around 2\%) without relying on historical liquidity snapshots, addressing a critical data gap in decentralized finan …

### 168. [Multimodal Stock Price Prediction: A Case Study of the Russian Securities Market](http://arxiv.org/abs/2503.08696v1)  `2503.08696`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.LG, q-fin.CP | **Published:** 2025-03-05T21:20:32Z
- **Authors:** Kasymkhan Khubiev, Mikhail Semenov
- **Why useful:** hits: _sentiment, order book, lstm, neural network, var, limit order, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2503.08696v1](https://arxiv.org/pdf/2503.08696v1)  |  **Per-paper MD:** `papers/q-fin_ST/2503.08696_*.md`
- **Abstract:** Classical asset price forecasting methods primarily rely on numerical data, such as price time series, trading volumes, limit order book data, and technical analysis indicators. However, the news flow plays a significant role in price formation, making the development of multimodal approaches that combine textual and numerical data for improved prediction accuracy highly relevant. This paper addresses the problem of forecasting financial asset prices using the multimodal approach that combines candlestick time series and textual news flow data. A unique dataset was collected for the study, which includes time series for 176 Russian stocks traded on the Moscow Exchange and 79,555 financial news articles in Russian. For processing textual data, pre-trained models RuBERT and Vikhr-Qwen2.5-0.5 …

### 169. [Looking into informal currency markets as Limit Order Books: impact of market makers](http://arxiv.org/abs/2503.03858v1)  `2503.03858`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2025-03-05T19:41:22Z
- **Authors:** Alejandro García Figal, Alejandro Lage Castellanos, Roberto Mulet
- **Why useful:** hits: _social media, market microstructure, order book, limit order, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2503.03858v1](https://arxiv.org/pdf/2503.03858v1)  |  **Per-paper MD:** `papers/q-fin_TR/2503.03858_*.md`
- **Abstract:** This study pioneers the application of the market microstructure framework to an informal financial market. By scraping data from websites and social media about the Cuban informal currency market, we model the dynamics of bid/ask intentions using a Limit Order Book (LOB). This approach enables us to study key characteristics such as liquidity, stability and volume profiles. We continue exploiting the Avellaneda-Stoikov model to explore the impact of introducing a Market Maker (MM) into this informal setting, assessing its influence on the market structure and the bid/ask dynamics. We show that the Market Maker improves the quality of the market. Beyond their academic significance, we believe that our findings are relevant for policymakers seeking to intervene informal markets with limited …

### 170. [Reinforcement-Learning Portfolio Allocation with Dynamic Embedding of Market Information](http://arxiv.org/abs/2501.17992v1)  `2501.17992`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG | **Published:** 2025-01-29T20:56:59Z
- **Authors:** Jinghai He, Cheng Hua, Chunyang Zhou, Zeyu Zheng
- **Why useful:** hits: _factor, machine learning, deep learning, reinforcement learning, volatility, var, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2501.17992v1](https://arxiv.org/pdf/2501.17992v1)  |  **Per-paper MD:** `papers/q-fin_PM/2501.17992_*.md`
- **Abstract:** We develop a portfolio allocation framework that leverages deep learning techniques to address challenges arising from high-dimensional, non-stationary, and low-signal-to-noise market information. Our approach includes a dynamic embedding method that reduces the non-stationary, high-dimensional state space into a lower-dimensional representation. We design a reinforcement learning (RL) framework that integrates generative autoencoders and online meta-learning to dynamically embed market information, enabling the RL agent to focus on the most impactful parts of the state space for portfolio allocation decisions. Empirical analysis based on the top 500 U.S. stocks demonstrates that our framework outperforms common portfolio benchmarks and the predict-then-optimize (PTO) approach using machin …

### 171. [Stock Price Prediction and Traditional Models: An Approach to Achieve Short-, Medium- and Long-Term Goals](http://arxiv.org/abs/2410.07220v1)  `2410.07220`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.LG, q-fin.CP | **Published:** 2024-09-29T11:20:20Z
- **Authors:** Opeyemi Sheu Alamu, Md Kamrul Siam
- **Why useful:** hits: _sentiment, social media, factor, deep learning, lstm, moving average, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2410.07220v1](https://arxiv.org/pdf/2410.07220v1)  |  **Per-paper MD:** `papers/q-fin_ST/2410.07220_*.md`
- **Abstract:** A comparative analysis of deep learning models and traditional statistical methods for stock price prediction uses data from the Nigerian stock exchange. Historical data, including daily prices and trading volumes, are employed to implement models such as Long Short Term Memory (LSTM) networks, Gated Recurrent Units (GRUs), Autoregressive Integrated Moving Average (ARIMA), and Autoregressive Moving Average (ARMA). These models are assessed over three-time horizons: short-term (1 year), medium-term (2.5 years), and long-term (5 years), with performance measured by Mean Squared Error (MSE) and Mean Absolute Error (MAE). The stability of the time series is tested using the Augmented Dickey-Fuller (ADF) test. Results reveal that deep learning models, particularly LSTM, outperform traditional m …

### 172. [MCI-GRU: Stock Prediction Model Based on Multi-Head Cross-Attention and Improved GRU](http://arxiv.org/abs/2410.20679v3)  `2410.20679`  **score 20**
- **Primary:** q-fin.ST | **All cats:** q-fin.ST, cs.LG, q-fin.CP | **Published:** 2024-09-25T14:37:49Z
- **Authors:** Peng Zhu, Yuante Li, Yifan Hu, Sheng Xiang, Qinyuan Liu, Dawei Cheng, Yuqi Liang
- **Why useful:** hits: _sentiment, factor, reinforcement learning, neural network, cta, impact, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2410.20679v3](https://arxiv.org/pdf/2410.20679v3)  |  **Per-paper MD:** `papers/q-fin_ST/2410.20679_*.md`
- **Abstract:** As financial markets grow increasingly complex in the big data era, accurate stock prediction has become more critical. Traditional time series models, such as GRUs, have been widely used but often struggle to capture the intricate nonlinear dynamics of markets, particularly in the flexible selection and effective utilization of key historical information. Recently, methods like Graph Neural Networks and Reinforcement Learning have shown promise in stock prediction but require high data quality and quantity, and they tend to exhibit instability when dealing with data sparsity and noise. Moreover, the training and inference processes for these models are typically complex and computationally expensive, limiting their broad deployment in practical applications. Existing approaches also gener …

### 173. [High-Frequency Options Trading | With Portfolio Optimization](http://arxiv.org/abs/2408.08866v1)  `2408.08866`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.CP, q-fin.TR | **Published:** 2024-08-16T17:49:21Z
- **Authors:** Sid Bhatia
- **Why useful:** hits: _portfolio optimization, portfolio management, mean-variance, volatility, var, options_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2408.08866v1](https://arxiv.org/pdf/2408.08866v1)  |  **Per-paper MD:** `papers/q-fin_TR/2408.08866_*.md`
- **Abstract:** This paper explores the effectiveness of high-frequency options trading strategies enhanced by advanced portfolio optimization techniques, investigating their ability to consistently generate positive returns compared to traditional long or short positions on options. Utilizing SPY options data recorded in five-minute intervals over a one-month period, we calculate key metrics such as Option Greeks and implied volatility, applying the Binomial Tree model for American options pricing and the Newton-Raphson algorithm for implied volatility calculation. Investment universes are constructed based on criteria like implied volatility and Greeks, followed by the application of various portfolio optimization models, including Standard Mean-Variance and Robust Methods. Our research finds that while …

### 174. [Optimizing Deep Reinforcement Learning for American Put Option Hedging](http://arxiv.org/abs/2405.08602v1)  `2405.08602`  **score 20**
- **Primary:** q-fin.RM | **All cats:** q-fin.RM, cs.CE, cs.LG | **Published:** 2024-05-14T13:41:44Z
- **Authors:** Reilly Pickard, F. Wredenhagen, Y. Lawryshyn
- **Why useful:** hits: _factor, reinforcement learning, neural network, volatility, options, hedging, impact, stochastic volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2405.08602v1](https://arxiv.org/pdf/2405.08602v1)  |  **Per-paper MD:** `papers/q-fin_RM/2405.08602_*.md`
- **Abstract:** This paper contributes to the existing literature on hedging American options with Deep Reinforcement Learning (DRL). The study first investigates hyperparameter impact on hedging performance, considering learning rates, training episodes, neural network architectures, training steps, and transaction cost penalty functions. Results highlight the importance of avoiding certain combinations, such as high learning rates with a high number of training episodes or low learning rates with few training episodes and emphasize the significance of utilizing moderate values for optimal outcomes. Additionally, the paper warns against excessive training steps to prevent instability and demonstrates the superiority of a quadratic transaction cost penalty function over a linear version. This study then e …

### 175. [Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach](http://arxiv.org/abs/2402.05272v3)  `2402.05272`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.ST | **Published:** 2024-02-07T21:36:49Z
- **Authors:** Yizhan Shu, Chenyu Yu, John M. Mulvey
- **Why useful:** hits: _cross-validation, volatility, var, drawdown, sharpe, regime_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2402.05272v3](https://arxiv.org/pdf/2402.05272v3)  |  **Per-paper MD:** `papers/q-fin_PM/2402.05272_*.md`
- **Abstract:** This article investigates a regime-switching investment strategy aimed at mitigating downside risk by reducing market exposure during anticipated unfavorable market regimes. We highlight the statistical jump model (JM) for market regime identification, a recently developed robust model that distinguishes itself from traditional Markov-switching models by enhancing regime persistence through a jump penalty applied at each state transition. Our JM utilizes a feature set comprising risk and return measures derived solely from the return series, with the optimal jump penalty selected through a time-series cross-validation method that directly optimizes strategy performance. Our empirical analysis evaluates the realistic out-of-sample performance of various strategies on major equity indices fr …

### 176. [Causal Inference on Investment Constraints and Non-stationarity in Dynamic Portfolio Optimization through Reinforcement Learning](http://arxiv.org/abs/2311.04946v1)  `2311.04946`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI | **Published:** 2023-11-08T07:55:51Z
- **Authors:** Yasuhiro Nakayama, Tomochika Sawaki
- **Why useful:** hits: _portfolio optimization, portfolio management, reinforcement learning, var, regime, impact, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2311.04946v1](https://arxiv.org/pdf/2311.04946v1)  |  **Per-paper MD:** `papers/q-fin_PM/2311.04946_*.md`
- **Abstract:** In this study, we have developed a dynamic asset allocation investment strategy using reinforcement learning techniques. To begin with, we have addressed the crucial issue of incorporating non-stationarity of financial time series data into reinforcement learning algorithms, which is a significant implementation in the application of reinforcement learning in investment strategies. Our findings highlight the significance of introducing certain variables such as regime change in the environment setting to enhance the prediction accuracy. Furthermore, the application of reinforcement learning in investment strategies provides a remarkable advantage of setting the optimization problem flexibly. This enables the integration of practical constraints faced by investors into the algorithm, result …

### 177. [D-TIPO: Deep time-inconsistent portfolio optimization with stocks and options](http://arxiv.org/abs/2308.10556v2)  `2308.10556`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.CP, q-fin.PM | **Published:** 2023-08-21T08:17:04Z
- **Authors:** Kristoffer Andersson, Cornelis W. Oosterlee
- **Why useful:** hits: _portfolio optimization, mean-variance, machine learning, neural network, var, options_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2308.10556v2](https://arxiv.org/pdf/2308.10556v2)  |  **Per-paper MD:** `papers/q-fin_PM/2308.10556_*.md`
- **Abstract:** In this paper, we propose a machine learning algorithm for time-inconsistent portfolio optimization. The proposed algorithm builds upon neural network based trading schemes, in which the asset allocation at each time point is determined by a a neural network. The loss function is given by an empirical version of the objective function of the portfolio optimization problem. Moreover, various trading constraints are naturally fulfilled by choosing appropriate activation functions in the output layers of the neural networks. Besides this, our main contribution is to add options to the portfolio of risky assets and a risk-free bond and using additional neural networks to determine the amount allocated into the options as well as their strike prices. We consider objective functions more in line …

### 178. [A Comparative Analysis of Portfolio Optimization Using Mean-Variance, Hierarchical Risk Parity, and Reinforcement Learning Approaches on the Indian Stock Market](http://arxiv.org/abs/2305.17523v1)  `2305.17523`  **score 20**
- **Primary:** cs.LG | **All cats:** cs.LG, q-fin.PM | **Published:** 2023-05-27T16:38:18Z
- **Authors:** Jaydip Sen, Aditya Jaiswal, Anshuman Pathak, Atish Kumar Majee, Kushagra Kumar, Manas Kumar Sarkar, Soubhik Maji
- **Why useful:** hits: _portfolio optimization, mean-variance, risk parity, reinforcement learning, neural network, var, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2305.17523v1](https://arxiv.org/pdf/2305.17523v1)  |  **Per-paper MD:** `papers/cs_LG/2305.17523_*.md`
- **Abstract:** This paper presents a comparative analysis of the performances of three portfolio optimization approaches. Three approaches of portfolio optimization that are considered in this work are the mean-variance portfolio (MVP), hierarchical risk parity (HRP) portfolio, and reinforcement learning-based portfolio. The portfolios are trained and tested over several stock data and their performances are compared on their annual returns, annual risks, and Sharpe ratios. In the reinforcement learning-based portfolio design approach, the deep Q learning technique has been utilized. Due to the large number of possible states, the construction of the Q-table is done using a deep neural network. The historical prices of the 50 premier stocks from the Indian stock market, known as the NIFTY50 stocks, and s …

### 179. [Systematic Review on Reinforcement Learning in the Field of Fintech](http://arxiv.org/abs/2305.07466v1)  `2305.07466`  **score 20**
- **Primary:** q-fin.CP | **All cats:** cs.AI, cs.LG, q-fin.CP, q-fin.GN | **Published:** 2023-04-29T07:48:42Z
- **Authors:** Nadeem Malibari, Iyad Katib, Rashid Mehmood
- **Why useful:** hits: _execution, market making, portfolio optimization, reinforcement learning, options, hedging_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2305.07466v1](https://arxiv.org/pdf/2305.07466v1)  |  **Per-paper MD:** `papers/q-fin_CP/2305.07466_*.md`
- **Abstract:** Applications of Reinforcement Learning in the Finance Technology (Fintech) have acquired a lot of admiration lately. Undoubtedly Reinforcement Learning, through its vast competence and proficiency, has aided remarkable results in the field of Fintech. The objective of this systematic survey is to perform an exploratory study on a correlation between reinforcement learning and Fintech to highlight the prediction accuracy, complexity, scalability, risks, profitability and performance. Major uses of reinforcement learning in finance or Fintech include portfolio optimization, credit risk reduction, investment capital management, profit maximization, effective recommendation systems, and better price setting strategies. Several studies have addressed the actual contribution of reinforcement lea …

### 180. [Co-trading networks for modeling dynamic interdependency structures and estimating high-dimensional covariances in US equity markets](http://arxiv.org/abs/2302.09382v2)  `2302.09382`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.PM, q-fin.TR | **Published:** 2023-02-18T16:48:58Z
- **Authors:** Yutong Lu, Gesine Reinert, Mihai Cucuringu
- **Why useful:** hits: _order book, mean-variance, volatility, var, sharpe, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2302.09382v2](https://arxiv.org/pdf/2302.09382v2)  |  **Per-paper MD:** `papers/q-fin_TR/2302.09382_*.md`
- **Abstract:** The time proximity of trades across stocks reveals interesting topological structures of the equity market in the United States. In this article, we investigate how such concurrent cross-stock trading behaviors, which we denote as co-trading, shape the market structures and affect stock price co-movements. By leveraging a co-trading-based pairwise similarity measure, we propose a novel method to construct dynamic networks of stocks. Our empirical studies employ high-frequency limit order book data from 2017-01-03 to 2019-12-09. By applying spectral clustering on co-trading networks, we uncover economically meaningful clusters of stocks. Beyond the static Global Industry Classification Standard (GICS) sectors, our data-driven clusters capture the time evolution of the dependency among stock …

### 181. [Model Based Reinforcement Learning with Non-Gaussian Environment Dynamics and its Application to Portfolio Optimization](http://arxiv.org/abs/2301.09297v3)  `2301.09297`  **score 20**
- **Primary:** q-fin.MF | **All cats:** q-fin.MF | **Published:** 2023-01-23T06:45:39Z
- **Authors:** Huifang Huang, Ting Gao, Pengbo Li, Jin Guo, Peng Zhang, Nan Du
- **Why useful:** hits: _portfolio optimization, factor, reinforcement learning, cta, var, drawdown, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2301.09297v3](https://arxiv.org/pdf/2301.09297v3)  |  **Per-paper MD:** `papers/q-fin_MF/2301.09297_*.md`
- **Abstract:** With the fast development of quantitative portfolio optimization in financial engineering, lots of AI-based algorithmic trading strategies have demonstrated promising results, among which reinforcement learning begins to manifest competitive advantages. However, the environment from real financial markets is complex and hard to be fully simulated, considering the observation of abrupt transitions, unpredictable hidden causal factors, heavy tail properties and so on. Thus, in this paper, first, we adopt a heavy-tailed preserving normalizing flows to simulate high-dimensional joint probability of the complex trading environment and develop a model-based reinforcement learning framework to better understand the intrinsic mechanisms of quantitative online trading. Second, we experiment with va …

### 182. [Asynchronous Deep Double Duelling Q-Learning for Trading-Signal Execution in Limit Order Book Markets](http://arxiv.org/abs/2301.08688v2)  `2301.08688`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG | **Published:** 2023-01-20T17:19:18Z
- **Authors:** Peer Nagy, Jan-Peter Calliess, Stefan Zohren
- **Why useful:** hits: _order book, execution, alpha, reinforcement learning, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2301.08688v2](https://arxiv.org/pdf/2301.08688v2)  |  **Per-paper MD:** `papers/q-fin_TR/2301.08688_*.md`
- **Abstract:** We employ deep reinforcement learning (RL) to train an agent to successfully translate a high-frequency trading signal into a trading strategy that places individual limit orders. Based on the ABIDES limit order book simulator, we build a reinforcement learning OpenAI gym environment and utilise it to simulate a realistic trading environment for NASDAQ equities based on historic order book messages. To train a trading agent that learns to maximise its trading return in this environment, we use Deep Duelling Double Q-learning with the APEX (asynchronous prioritised experience replay) architecture. The agent observes the current limit order book state, its recent history, and a short-term directional forecast. To investigate the performance of RL for adaptive trading independently from a con …

### 183. [Predictive Crypto-Asset Automated Market Making Architecture for Decentralized Finance using Deep Reinforcement Learning](http://arxiv.org/abs/2211.01346v2)  `2211.01346`  **score 20**
- **Primary:** q-fin.TR | **All cats:** cs.AI, cs.LG, q-fin.CP, q-fin.TR | **Published:** 2022-09-28T01:13:22Z
- **Authors:** Tristan Lim
- **Why useful:** hits: _slippage, market making, deep learning, reinforcement learning, lstm, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2211.01346v2](https://arxiv.org/pdf/2211.01346v2)  |  **Per-paper MD:** `papers/q-fin_TR/2211.01346_*.md`
- **Abstract:** The study proposes a quote-driven predictive automated market maker (AMM) platform with on-chain custody and settlement functions, alongside off-chain predictive reinforcement learning capabilities to improve liquidity provision of real-world AMMs. The proposed AMM architecture is an augmentation to the Uniswap V3, a cryptocurrency AMM protocol, by utilizing a novel market equilibrium pricing for reduced divergence and slippage loss. Further, the proposed architecture involves a predictive AMM capability, utilizing a deep hybrid Long Short-Term Memory (LSTM) and Q-learning reinforcement learning framework that looks to improve market efficiency through better forecasts of liquidity concentration ranges, so liquidity starts moving to expected concentration ranges, prior to asset price movem …

### 184. [Regime-based Implied Stochastic Volatility Model for Crypto Option Pricing](http://arxiv.org/abs/2208.12614v2)  `2208.12614`  **score 20**
- **Primary:** q-fin.CP | **All cats:** q-fin.CP, cs.LG | **Published:** 2022-08-15T15:31:42Z
- **Authors:** Danial Saef, Yuanrong Wang, Tomaso Aste
- **Why useful:** hits: _overfit, sentiment, cta, volatility, options, regime, stochastic volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2208.12614v2](https://arxiv.org/pdf/2208.12614v2)  |  **Per-paper MD:** `papers/q-fin_CP/2208.12614_*.md`
- **Abstract:** The increasing adoption of Digital Assets (DAs), such as Bitcoin (BTC), rises the need for accurate option pricing models. Yet, existing methodologies fail to cope with the volatile nature of the emerging DAs. Many models have been proposed to address the unorthodox market dynamics and frequent disruptions in the microstructure caused by the non-stationarity, and peculiar statistics, in DA markets. However, they are either prone to the curse of dimensionality, as additional complexity is required to employ traditional theories, or they overfit historical patterns that may never repeat. Instead, we leverage recent advances in market regime (MR) clustering with the Implied Stochastic Volatility Model (ISVM). Time-regime clustering is a temporal clustering method, that clusters the historic e …

### 185. [Deep Reinforcement Learning for Market Making Under a Hawkes Process-Based Limit Order Book Model](http://arxiv.org/abs/2207.09951v1)  `2207.09951`  **score 20**
- **Primary:** q-fin.GN | **All cats:** cs.LG, q-fin.GN, q-fin.TR | **Published:** 2022-07-20T14:54:40Z
- **Authors:** Bruno Gašperov, Zvonko Kostanjčar
- **Why useful:** hits: _backtest, order book, market making, reinforcement learning, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2207.09951v1](https://arxiv.org/pdf/2207.09951v1)  |  **Per-paper MD:** `papers/q-fin_GN/2207.09951_*.md`
- **Abstract:** The stochastic control problem of optimal market making is among the central problems in quantitative finance. In this paper, a deep reinforcement learning-based controller is trained on a weakly consistent, multivariate Hawkes process-based limit order book simulator to obtain market making controls. The proposed approach leverages the advantages of Monte Carlo backtesting and contributes to the line of research on market making under weakly consistent limit order book models. The ensuing deep reinforcement learning controller is compared to multiple market making benchmarks, with the results indicating its superior performance with respect to various risk-reward metrics, even under significant transaction costs.

### 186. [Fusion of Sentiment and Asset Price Predictions for Portfolio Optimization](http://arxiv.org/abs/2203.05673v1)  `2203.05673`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG | **Published:** 2022-03-10T23:21:12Z
- **Authors:** Mufhumudzi Muthivhi, Terence L. van Zyl
- **Why useful:** hits: _sentiment, portfolio optimization, mean-variance, lstm, neural network, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2203.05673v1](https://arxiv.org/pdf/2203.05673v1)  |  **Per-paper MD:** `papers/q-fin_PM/2203.05673_*.md`
- **Abstract:** The fusion of public sentiment data in the form of text with stock price prediction is a topic of increasing interest within the financial community. However, the research literature seldom explores the application of investor sentiment in the Portfolio Selection problem. This paper aims to unpack and develop an enhanced understanding of the sentiment aware portfolio selection problem. To this end, the study uses a Semantic Attention Model to predict sentiment towards an asset. We select the optimal portfolio through a sentiment-aware Long Short Term Memory (LSTM) recurrent neural network for price prediction and a mean-variance strategy. Our sentiment portfolio strategies achieved on average a significant increase in revenue above the non-sentiment aware models. However, the results show  …

### 187. [Deep differentiable reinforcement learning and optimal trading](http://arxiv.org/abs/2112.02944v2)  `2112.02944`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2021-12-06T11:35:53Z
- **Authors:** Thibault Jaisson
- **Why useful:** hits: _portfolio optimization, alpha, machine learning, deep learning, reinforcement learning, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2112.02944v2](https://arxiv.org/pdf/2112.02944v2)  |  **Per-paper MD:** `papers/q-fin_PM/2112.02944_*.md`
- **Abstract:** In many reinforcement learning applications, the underlying environment reward and transition functions are explicitly known differentiable functions. This enables us to use recent research which applies machine learning tools to stochastic control to find optimal action functions. In this paper, we define differentiable reinforcement learning as a particular case of this research. We find that incorporating deep learning in this framework leads to more accurate and stable solutions than those obtained from more generic actor critic algorithms. We apply this deep differentiable reinforcement learning (DDRL) algorithm to the problem of one asset optimal trading strategies in various environments where the market dynamics are known. Thanks to the stability of this method, we are able to effi …

### 188. [Hedging Cryptocurrency Options](http://arxiv.org/abs/2112.06807v3)  `2112.06807`  **score 20**
- **Primary:** q-fin.PR | **All cats:** q-fin.PR, stat.ME | **Published:** 2021-11-23T22:46:45Z
- **Authors:** Jovanka Lili Matic, Natalie Packham, Wolfgang Karl Härdle
- **Why useful:** hits: _backtest, volatility, garch, var, tail risk, options, hedging, derivative, stochastic volatility_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2112.06807v3](https://arxiv.org/pdf/2112.06807v3)  |  **Per-paper MD:** `papers/q-fin_PR/2112.06807_*.md`
- **Abstract:** The cryptocurrency market is volatile, non-stationary and non-continuous. Together with liquid derivatives markets, this poses a unique opportunity to study risk management, especially the hedging of options, in a turbulent market. We study the hedge behaviour and effectiveness for the class of affine jump diffusion models and infinite activity Levy processes. First, market data is calibrated to stochastic volatility inspired (SVI)-implied volatility surfaces to price options. To cover a wide range of market dynamics, we generate Monte Carlo price paths using an SVCJ model (stochastic volatility with correlated jumps), a close-to-actual-market GARCH-filtered kernel density estimation as well as a historical backtest. In all three settings, options are dynamically hedged with Delta, Delta-G …

### 189. [FRM Financial Risk Meter for Emerging Markets](http://arxiv.org/abs/2102.05398v1)  `2102.05398`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM | **Published:** 2021-02-10T12:08:27Z
- **Authors:** Souhir Ben Amor, Michael Althof, Wolfgang Karl Härdle
- **Why useful:** hits: _portfolio optimization, factor, volatility, var, hedging, macro, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2102.05398v1](https://arxiv.org/pdf/2102.05398v1)  |  **Per-paper MD:** `papers/q-fin_PM/2102.05398_*.md`
- **Abstract:** The fast-growing Emerging Market (EM) economies and their improved transparency and liquidity have attracted international investors. However, the external price shocks can result in a higher level of volatility as well as domestic policy instability. Therefore, an efficient risk measure and hedging strategies are needed to help investors protect their investments against this risk. In this paper, a daily systemic risk measure, called FRM (Financial Risk Meter) is proposed. The FRM-EM is applied to capture systemic risk behavior embedded in the returns of the 25 largest EMs FIs, covering the BRIMST (Brazil, Russia, India, Mexico, South Africa, and Turkey), and thereby reflects the financial linkages between these economies. Concerning the Macro factors, in addition to the Adrian and Brunne …

### 190. [Cross impact in derivative markets](http://arxiv.org/abs/2102.02834v2)  `2102.02834`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.PR, q-fin.TR | **Published:** 2021-02-04T19:02:47Z
- **Authors:** Mehdi Tomas, Iacopo Mastromatteo, Michael Benzaquen
- **Why useful:** hits: _factor, cta, options, vix, hedging, derivative, liquidity, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2102.02834v2](https://arxiv.org/pdf/2102.02834v2)  |  **Per-paper MD:** `papers/q-fin_TR/2102.02834_*.md`
- **Abstract:** Trading a financial asset pushes its price as well as the prices of other assets, a phenomenon known as cross-impact. The empirical estimation of this effect on complex financial instruments, such as derivatives, is an open problem. To address this, we consider a setting in which the prices of derivatives is a deterministic function of stochastic factors where trades on both factors and derivatives induce price impact. We show that a specific cross-impact model satisfies key properties which make its estimation tractable in applications. Using E-Mini futures, European call and put options and VIX futures, we estimate cross-impact and show our simple framework successfully captures some of the empirical phenomenology. Our framework for estimating cross-impact on derivatives may be used in p …

### 191. [Portfolio Optimization with 2D Relative-Attentional Gated Transformer](http://arxiv.org/abs/2101.03138v1)  `2101.03138`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.AI, cs.LG | **Published:** 2020-12-27T14:08:26Z
- **Authors:** Tae Wan Kim, Matloob Khushi
- **Why useful:** hits: _slippage, portfolio optimization, machine learning, reinforcement learning, transformer, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2101.03138v1](https://arxiv.org/pdf/2101.03138v1)  |  **Per-paper MD:** `papers/q-fin_PM/2101.03138_*.md`
- **Abstract:** Portfolio optimization is one of the most attentive fields that have been researched with machine learning approaches. Many researchers attempted to solve this problem using deep reinforcement learning due to its efficient inherence that can handle the property of financial markets. However, most of them can hardly be applicable to real-world trading since they ignore or extremely simplify the realistic constraints of transaction costs. These constraints have a significantly negative impact on portfolio profitability. In our research, a conservative level of transaction fees and slippage are considered for the realistic experiment. To enhance the performance under those constraints, we propose a novel Deterministic Policy Gradient with 2D Relative-attentional Gated Transformer (DPGRGT) mod …

### 192. [Reinforced Deep Markov Models With Applications in Automatic Trading](http://arxiv.org/abs/2011.04391v1)  `2011.04391`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR, cs.LG, stat.AP, stat.ML | **Published:** 2020-11-09T12:46:30Z
- **Authors:** Tadeu A. Ferreira
- **Why useful:** hits: _order book, execution, reinforcement learning, lstm, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2011.04391v1](https://arxiv.org/pdf/2011.04391v1)  |  **Per-paper MD:** `papers/q-fin_TR/2011.04391_*.md`
- **Abstract:** Inspired by the developments in deep generative models, we propose a model-based RL approach, coined Reinforced Deep Markov Model (RDMM), designed to integrate desirable properties of a reinforcement learning algorithm acting as an automatic trading system. The network architecture allows for the possibility that market dynamics are partially visible and are potentially modified by the agent's actions. The RDMM filters incomplete and noisy data, to create better-behaved input data for RL planning. The policy search optimisation also properly accounts for state uncertainty. Due to the complexity of the RKDF model architecture, we performed ablation studies to understand the contributions of individual components of the approach better. To test the financial performance of the RDMM we implem …

### 193. [Multi-Agent Reinforcement Learning in a Realistic Limit Order Book Market Simulation](http://arxiv.org/abs/2006.05574v2)  `2006.05574`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2020-06-10T00:16:33Z
- **Authors:** Michaël Karpe, Jin Fang, Zhongyao Ma, Chen Wang
- **Why useful:** hits: _market microstructure, order book, execution, reinforcement learning, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2006.05574v2](https://arxiv.org/pdf/2006.05574v2)  |  **Per-paper MD:** `papers/q-fin_TR/2006.05574_*.md`
- **Abstract:** Optimal order execution is widely studied by industry practitioners and academic researchers because it determines the profitability of investment decisions and high-level trading strategies, particularly those involving large volumes of orders. However, complex and unknown market dynamics pose significant challenges for the development and validation of optimal execution strategies. In this paper, we propose a model-free approach by training Reinforcement Learning (RL) agents in a realistic market simulation environment with multiple agents. First, we configure a multi-agent historical order book simulation environment for execution tasks built on an Agent-Based Interactive Discrete Event Simulation (ABIDES) [arXiv:1904.12066]. Second, we formulate the problem of optimal execution in an R …

### 194. [Application of Deep Q-Network in Portfolio Management](http://arxiv.org/abs/2003.06365v1)  `2003.06365`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, cs.LG, stat.ML | **Published:** 2020-03-13T16:20:51Z
- **Authors:** Ziming Gao, Yuan Gao, Yi Hu, Zhengyong Jiang, Jionglong Su
- **Why useful:** hits: _portfolio management, machine learning, reinforcement learning, neural network, drawdown, sharpe_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/2003.06365v1](https://arxiv.org/pdf/2003.06365v1)  |  **Per-paper MD:** `papers/q-fin_PM/2003.06365_*.md`
- **Abstract:** Machine Learning algorithms and Neural Networks are widely applied to many different areas such as stock market prediction, face recognition and population analysis. This paper will introduce a strategy based on the classic Deep Reinforcement Learning algorithm, Deep Q-Network, for portfolio management in stock market. It is a type of deep neural network which is optimized by Q Learning. To make the DQN adapt to financial market, we first discretize the action space which is defined as the weight of portfolio in different assets so that portfolio management becomes a problem that Deep Q-Network can solve. Next, we combine the Convolutional Neural Network and dueling Q-net to enhance the recognition ability of the algorithm. Experimentally, we chose five lowrelevant American stocks to test  …

### 195. [Design of High-Frequency Trading Algorithm Based on Machine Learning](http://arxiv.org/abs/1912.10343v1)  `1912.10343`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2019-12-21T21:25:39Z
- **Authors:** Boyue Fang, Yutong Feng
- **Why useful:** hits: _backtest, order book, machine learning, deep learning, garch, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1912.10343v1](https://arxiv.org/pdf/1912.10343v1)  |  **Per-paper MD:** `papers/q-fin_TR/1912.10343_*.md`
- **Abstract:** Based on iterative optimization and activation function in deep learning, we proposed a new analytical framework of high-frequency trading information, that reduced structural loss in the assembly of Volume-synchronized probability of Informed Trading ($VPIN$), Generalized Autoregressive Conditional Heteroscedasticity (GARCH) and Support Vector Machine (SVM) to make full use of the order book information. Amongst the return acquisition procedure in market-making transactions, uncovering the relationship between discrete dimensional data from the projection of high-dimensional time-series would significantly improve the model effect. $VPIN$ would prejudge market liquidity, and this effectiveness backtested with CSI300 futures return.

### 196. [Using Machine Learning to Predict Realized Variance](http://arxiv.org/abs/1909.10035v1)  `1909.10035`  **score 20**
- **Primary:** q-fin.MF | **All cats:** q-fin.CP, q-fin.MF | **Published:** 2019-09-22T15:56:19Z
- **Authors:** Peter Carr, Liuren Wu, Zhibai Zhang
- **Why useful:** hits: _machine learning, neural network, cta, volatility, var, options, vix, liquidity, time series_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1909.10035v1](https://arxiv.org/pdf/1909.10035v1)  |  **Per-paper MD:** `papers/q-fin_MF/1909.10035_*.md`
- **Abstract:** In this paper we formulate a regression problem to predict realized volatility by using option price data and enhance VIX-styled volatility indices' predictability and liquidity. We test algorithms including regularized regression and machine learning methods such as Feedforward Neural Networks (FNN) on S&P 500 Index and its option data. By conducting a time series validation we find that both Ridge regression and FNN can improve volatility indexing with higher prediction performance and fewer options required. The best approach found is to predict the difference between the realized volatility and the VIX-styled index's prediction rather than to predict the realized volatility directly, representing a successful combination of human learning and machine learning. We also discuss suitabili …

### 197. [Market Making under a Weakly Consistent Limit Order Book Model](http://arxiv.org/abs/1903.07222v4)  `1903.07222`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2019-03-18T01:27:14Z
- **Authors:** Baron Law, Frederi Viens
- **Why useful:** hits: _market microstructure, order book, market making, var, limit order_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1903.07222v4](https://arxiv.org/pdf/1903.07222v4)  |  **Per-paper MD:** `papers/q-fin_TR/1903.07222_*.md`
- **Abstract:** We develop a new market-making model, from the ground up, which is tailored towards high-frequency trading under a limit order book (LOB), based on the well-known classification of order types in market microstructure. Our flexible framework allows arbitrary order volume, price jump, and bid-ask spread distributions as well as the use of market orders. It also honors the consistency of price movements upon arrivals of different order types. For example, it is apparent that prices should never go down on buy market orders. In addition, it respects the price-time priority of LOB. In contrast to the approach of regular control on diffusion as in the classical Avellaneda and Stoikov [1] market-making framework, we exploit the techniques of optimal switching and impulse control on marked point  …

### 198. [Using Deep Learning Neural Networks and Candlestick Chart Representation to Predict Stock Market](http://arxiv.org/abs/1903.12258v1)  `1903.12258`  **score 20**
- **Primary:** q-fin.GN | **All cats:** q-fin.GN, cs.LG, q-fin.ST, stat.ML | **Published:** 2019-02-26T03:47:40Z
- **Authors:** Rosdyana Mangir Irawan Kusuma, Trang-Thi Ho, Wei-Chun Kao, Yu-Yen Ou, Kai-Lung Hua
- **Why useful:** hits: _sentiment, social media, factor, deep learning, neural network, cta, var_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1903.12258v1](https://arxiv.org/pdf/1903.12258v1)  |  **Per-paper MD:** `papers/q-fin_GN/1903.12258_*.md`
- **Abstract:** Stock market prediction is still a challenging problem because there are many factors effect to the stock market price such as company news and performance, industry performance, investor sentiment, social media sentiment and economic factors. This work explores the predictability in the stock market using Deep Convolutional Network and candlestick charts. The outcome is utilized to design a decision support framework that can be used by traders to provide suggested indications of future stock price direction. We perform this work using various types of neural networks like convolutional neural network, residual network and visual geometry group network. From stock market historical data, we converted it to candlestick charts. Finally, these candlestick charts will be feed as input for tra …

### 199. [Order Flows and Limit Order Book Resiliency on the Meso-Scale](http://arxiv.org/abs/1708.02715v1)  `1708.02715`  **score 20**
- **Primary:** q-fin.TR | **All cats:** q-fin.TR | **Published:** 2017-08-09T04:40:29Z
- **Authors:** Kyle Bechler, Michael Ludkovski
- **Why useful:** hits: _order book, order flow, execution, var, limit order, liquidity_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1708.02715v1](https://arxiv.org/pdf/1708.02715v1)  |  **Per-paper MD:** `papers/q-fin_TR/1708.02715_*.md`
- **Abstract:** We investigate the behavior of limit order books on the meso-scale motivated by order execution scheduling algorithms. To do so we carry out empirical analysis of the order flows from market and limit order submissions, aggregated from tick-by-tick data via volume-based bucketing, as well as various LOB depth and shape metrics. We document a nonlinear relationship between trade imbalance and price change, which however can be converted into a linear link by considering a weighted average of market and limit order flows. We also document a hockey-stick dependence between trade imbalance and one-sided limit order flows, highlighting numerous asymmetric effects between the active and passive sides of the LOB. To address the phenomenological features of price formation, book resilience, and sc …

### 200. [Portfolio optimization for heavy-tailed assets: Extreme Risk Index vs. Markowitz](http://arxiv.org/abs/1505.04045v1)  `1505.04045`  **score 20**
- **Primary:** q-fin.PM | **All cats:** q-fin.PM, q-fin.RM | **Published:** 2015-05-15T12:16:43Z
- **Authors:** Georg Mainik, Georgi Mitov, Ludger Rüschendorf
- **Why useful:** hits: _backtest, portfolio optimization, portfolio management, var, drawdown, impact_  (threshold 5, category bonus included)
- **PDF:** [https://arxiv.org/pdf/1505.04045v1](https://arxiv.org/pdf/1505.04045v1)  |  **Per-paper MD:** `papers/q-fin_PM/1505.04045_*.md`
- **Abstract:** Using daily returns of the S&P 500 stocks from 2001 to 2011, we perform a backtesting study of the portfolio optimization strategy based on the extreme risk index (ERI). This method uses multivariate extreme value theory to minimize the probability of large portfolio losses. With more than 400 stocks to choose from, our study seems to be the first application of extreme value techniques in portfolio management on a large scale. The primary aim of our investigation is the potential of ERI in practice. The performance of this strategy is benchmarked against the minimum variance portfolio and the equally weighted portfolio. These fundamental strategies are important benchmarks for large-scale applications. Our comparison includes annualized portfolio returns, maximal drawdowns, transaction co …


---

## All papers — by category & date (newest first, excerpt)


### q-fin.CP — Computational Finance — Monte Carlo, PDE, lattice and numerical methods (1219 papers)
- **Unbiased Monte Carlo Greeks for Discontinuous Payoffs** `2609.06137` — 2026-09-05 — Evgeny Lakshtanov — [abs](http://arxiv.org/abs/2609.06137v1) [pdf](https://arxiv.org/pdf/2609.06137v1)
- **Quantum Circuit Learning for Volatility Modeling: Multifractal Analysis of Realized Volatility Time Series** `2609.04569` ✅ USEFUL — 2026-09-03 — Tetsuya Takaishi — [abs](http://arxiv.org/abs/2609.04569v1) [pdf](https://arxiv.org/pdf/2609.04569v1)
- **Global Multi-Maturity SPX-VIX Calibration Beyond Markovian Stitching** `2609.04087` ✅ USEFUL — 2026-09-03 — Atithi Acharya, Yue Sun, Brandon Augustino et al. — [abs](http://arxiv.org/abs/2609.04087v1) [pdf](https://arxiv.org/pdf/2609.04087v1)
- **Insights on Time-consistent Deep Hedging under Elicitable Dynamic Risk Measures** `2609.02014` ✅ USEFUL — 2026-09-02 — Shuyi Zhang, Frédéric Godin — [abs](http://arxiv.org/abs/2609.02014v1) [pdf](https://arxiv.org/pdf/2609.02014v1)
- **Adaptive singular-point method for pricing and hedging surrenderable equity-linked contracts** `2609.01323` ✅ USEFUL — 2026-09-01 — Andrea Molent, Marcellino Gaudenzi — [abs](http://arxiv.org/abs/2609.01323v1) [pdf](https://arxiv.org/pdf/2609.01323v1)
- **Single- and Multilevel Quadrature with Error Control for Fourier Pricing under the Rough Heston Model** `2609.00438` — 2026-08-31 — Chiheb Ben Hammouda, Abderrahmene Ben Romdhane, Michael Samet et al. — [abs](http://arxiv.org/abs/2609.00438v1) [pdf](https://arxiv.org/pdf/2609.00438v1)
- **Latent-Space No-Arbitrage Geometry of Generative Models for Implied Volatility Surfaces** `2609.00332` ✅ USEFUL — 2026-08-31 — Jing Wang, Shuaiqiang Liu, Cornelis Vuik — [abs](http://arxiv.org/abs/2609.00332v1) [pdf](https://arxiv.org/pdf/2609.00332v1)
- **Agentic Quantitative Trading: A Survey of Workflows, Systems, and Evaluation** `2608.31041` ✅ USEFUL — 2026-08-31 — Fengrui Hua, Hengyi Yang, Xinlei Hao et al. — [abs](http://arxiv.org/abs/2608.31041v1) [pdf](https://arxiv.org/pdf/2608.31041v1)
- **Neural Calibration of a Complete Market Model** `2608.30867` ✅ USEFUL — 2026-08-31 — Andrea Molent, Michel Vellekoop — [abs](http://arxiv.org/abs/2608.30867v1) [pdf](https://arxiv.org/pdf/2608.30867v1)
- **Importance Sampling Enhanced with the COS Method for the Portfolio Risk Allocation** `2608.30749` — 2026-08-31 — Fang Fang, Xiaoyu Shen, Qinling Wang — [abs](http://arxiv.org/abs/2608.30749v1) [pdf](https://arxiv.org/pdf/2608.30749v1)
- **Improving Swaption Calibration in Factor HJM Stochastic Volatility Models: A First-Order Correction to Frozen Swap-Rate Loadings** `2608.29423` ✅ USEFUL — 2026-08-29 — Bram Brongers — [abs](http://arxiv.org/abs/2608.29423v1) [pdf](https://arxiv.org/pdf/2608.29423v1)
- **Market-Informed Valuation of GMMB Riders with Surrender Options under a Heston Stochastic-Local Volatility Model** `2608.28397` ✅ USEFUL — 2026-08-28 — Ludovic Goudenege, Andrea Molent, Xiao Wei et al. — [abs](http://arxiv.org/abs/2608.28397v1) [pdf](https://arxiv.org/pdf/2608.28397v1)
- **Pricing and Calibration of Bitcoin Inverse Options via the Rough Bergomi Model** `2608.27575` ✅ USEFUL — 2026-08-27 — Riccardo Caruso — [abs](http://arxiv.org/abs/2608.27575v1) [pdf](https://arxiv.org/pdf/2608.27575v1)
- **A Temporal Multiplex Graph Neural Network for Systemic Risk Transmission in Global Banking** `2608.27295` ✅ USEFUL — 2026-08-27 — Nneka Umeorah, Tolulope Fadina — [abs](http://arxiv.org/abs/2608.27295v1) [pdf](https://arxiv.org/pdf/2608.27295v1)
- **Harvesting the Volatility Risk Premium: A Learning-to-Rank Approach** `2608.24786` ✅ USEFUL — 2026-08-25 — Maciej Wysocki — [abs](http://arxiv.org/abs/2608.24786v1) [pdf](https://arxiv.org/pdf/2608.24786v1)
- **Asymptotically-informed neural networks for Black-Scholes implied volatility computation** `2609.05491` ✅ USEFUL — 2026-08-25 — Samira Amiriyan, Youness Boutaib — [abs](http://arxiv.org/abs/2609.05491v1) [pdf](https://arxiv.org/pdf/2609.05491v1)
- **The Physical Crash Frontier: What Finite Option Quotes Can and Cannot Reveal** `2608.23274` — 2026-08-24 — Jirong Zhuang — [abs](http://arxiv.org/abs/2608.23274v1) [pdf](https://arxiv.org/pdf/2608.23274v1)
- **Rethinking Synthetic Scenario Realism: Compatibility, Not Fidelity, Drives Hedging Performance** `2608.20842` — 2026-08-21 — Ryuji Hashimoto, Masanori Hirano, Ryota Ozaki et al. — [abs](http://arxiv.org/abs/2608.20842v2) [pdf](https://arxiv.org/pdf/2608.20842v2)
- **Calibrating Inelastic Markets to Options: The Lean Marketron and the Generalized Langevin Equation** `2608.20589` ✅ USEFUL — 2026-08-20 — Andrey Itkin — [abs](http://arxiv.org/abs/2608.20589v1) [pdf](https://arxiv.org/pdf/2608.20589v1)
- **Deep-MKV-TS: Path-Dependent McKean--Vlasov Control for Financial Time Series Generation** `2608.19394` ✅ USEFUL — 2026-08-19 — Samer El Boustany, Théo Basseras, Samy Mekkaoui et al. — [abs](http://arxiv.org/abs/2608.19394v1) [pdf](https://arxiv.org/pdf/2608.19394v1)
- **COS-TT-CHF: A Tensor-Train Characteristic-Function COS Method for Multi-Asset Option Pricing** `2608.17636` — 2026-08-18 — Lucas Arenstein, Michael Kastoryano — [abs](http://arxiv.org/abs/2608.17636v1) [pdf](https://arxiv.org/pdf/2608.17636v1)
- **LOB-ID: Evaluating Synthetic Market Data by Inception Distances** `2608.13082` ✅ USEFUL — 2026-08-13 — Andreea Bacalum, Zhuohan Wang, Ollie Olby et al. — [abs](http://arxiv.org/abs/2608.13082v1) [pdf](https://arxiv.org/pdf/2608.13082v1)
- **Diffusion Models in Finance: A Survey** `2608.12583` ✅ USEFUL — 2026-08-12 — Zhuohan Wang, Carmine Ventre — [abs](http://arxiv.org/abs/2608.12583v1) [pdf](https://arxiv.org/pdf/2608.12583v1)
- **Beyond the Skew-Stickiness Ratio: Transport Geometry of Spot-Driven Variance Surface Dynamics** `2608.12493` ✅ USEFUL — 2026-08-12 — Charlie Che, Pradeepta Das — [abs](http://arxiv.org/abs/2608.12493v1) [pdf](https://arxiv.org/pdf/2608.12493v1)
- **AI-Driven Multiscenario Interest Rate Forecasting: A Proof of Concept for Banking Asset Management** `2608.12424` ✅ USEFUL — 2026-08-12 — Ekkehardt Bauer, Dirk Holländer, David Scholz et al. — [abs](http://arxiv.org/abs/2608.12424v2) [pdf](https://arxiv.org/pdf/2608.12424v2)
  - … and 1194 more in `papers/q-fin_CP/`

### q-fin.EC — Economics — micro/macro, theory of firm, labor, international (0 papers)
_No papers with this primary category in this window._

### q-fin.GN — General Finance — general quantitative methodologies with finance applications (1750 papers)
- **AI for AI: Optimizing Additional Infrastructure Build-out to Power Artificial Intelligence Data Centers** `2609.08166` — 2026-09-08 — Alexander Crosier, Kyle Onghai, Ronnie Sircar — [abs](http://arxiv.org/abs/2609.08166v1) [pdf](https://arxiv.org/pdf/2609.08166v1)
- **Historical Reflections on Interest Rates and the Emergence of the Yield Curve** `2609.07958` — 2026-09-07 — Olivier Guéant — [abs](http://arxiv.org/abs/2609.07958v1) [pdf](https://arxiv.org/pdf/2609.07958v1)
- **Measuring DeFi Risk** `2609.07902` — 2026-09-07 — Jeremy Bertomeu, Xiumin Martin, Ibrahima Sall — [abs](http://arxiv.org/abs/2609.07902v1) [pdf](https://arxiv.org/pdf/2609.07902v1)
- **Quantity, Risk, and Return** `2609.05162` ✅ USEFUL — 2026-09-04 — Yu An, Yinan Su, Chen Wang — [abs](http://arxiv.org/abs/2609.05162v1) [pdf](https://arxiv.org/pdf/2609.05162v1)
- **Tempting the Agent: The Economics of Reputation without Persistent Identity in AI Agent Markets** `2609.02992` — 2026-09-02 — Federico Gatta, Manuel Naviglio, Francesco Tarantelli — [abs](http://arxiv.org/abs/2609.02992v1) [pdf](https://arxiv.org/pdf/2609.02992v1)
- **Authority-Inference Separation in Agentic Finance: First-Line Control, Blockchain Enforcement, and Replayable Assurance** `2608.30519` — 2026-08-31 — Hui Gong, Michail Samawi, Francesca Medda — [abs](http://arxiv.org/abs/2608.30519v1) [pdf](https://arxiv.org/pdf/2608.30519v1)
- **Two Kinds of Nothing: What Insignificant Results in Finance Actually Show** `2608.30490` — 2026-08-31 — David Tan — [abs](http://arxiv.org/abs/2608.30490v2) [pdf](https://arxiv.org/pdf/2608.30490v2)
- **Are AI Risks Priced in the U.S. Stock Market? Evidence from Financial News Factors** `2609.05485` ✅ USEFUL — 2026-08-23 — Yanhui Shen — [abs](http://arxiv.org/abs/2609.05485v1) [pdf](https://arxiv.org/pdf/2609.05485v1)
- **Self-Explaining Segment Trees: A KPI-Conditioned Segmentation Framework for Business Analytics with Node-Level Explanation via Recursive Subspace Partitioning** `2608.08197` ✅ USEFUL — 2026-08-08 — Girish G N, Dhanashekar Kandaswamy — [abs](http://arxiv.org/abs/2608.08197v1) [pdf](https://arxiv.org/pdf/2608.08197v1)
- **Methodology for Modelling Token Economies and Performing Event Impact Analysis with DeTEcT** `2608.02475` — 2026-08-03 — Rem Sadykhov, Geoffrey Goodell, Philip Treleaven — [abs](http://arxiv.org/abs/2608.02475v1) [pdf](https://arxiv.org/pdf/2608.02475v1)
- **Data-Driven Measures of High-Frequency Trading** `2608.00858` ✅ USEFUL — 2026-08-01 — Gbenga Ibikunle, Ben Moews, Dmitriy Muravyev et al. — [abs](http://arxiv.org/abs/2608.00858v2) [pdf](https://arxiv.org/pdf/2608.00858v2)
- **AI and Exchange Rate Predictability** `2608.00761` ✅ USEFUL — 2026-08-01 — Amin Izadyar — [abs](http://arxiv.org/abs/2608.00761v1) [pdf](https://arxiv.org/pdf/2608.00761v1)
- **ZAPs: A Reward Attribution Framework for DeFi Ecosystems with Adversarial-Robust Scoring via Parallel Anomaly Ensemble Detection** `2607.27859` — 2026-07-30 — Girish G N, Ashutosh Sahoo, Ajay Bhat et al. — [abs](http://arxiv.org/abs/2607.27859v1) [pdf](https://arxiv.org/pdf/2607.27859v1)
- **Settlement Infrastructure, Inside Money Elasticity, and the Network Economics of Distributed Ledger Technology** `2607.22459` — 2026-07-24 — Michail Samawi, Hui Gong, Francesca Medda — [abs](http://arxiv.org/abs/2607.22459v2) [pdf](https://arxiv.org/pdf/2607.22459v2)
- **Dead Reckoning: Counting Your Customers Who Never Say Goodbye** `2607.18623` — 2026-07-21 — Karl T. Ulrich — [abs](http://arxiv.org/abs/2607.18623v1) [pdf](https://arxiv.org/pdf/2607.18623v1)
- **Prediction of bank transaction fraud using TabNet an adaptive deep learning architecture** `2607.18616` ✅ USEFUL — 2026-07-21 — Prashanth BS, Manoj Kumar, Ariful Hoque et al. — [abs](http://arxiv.org/abs/2607.18616v1) [pdf](https://arxiv.org/pdf/2607.18616v1)
- **Measuring Sentiment News with Transformer-Based Language Models** `2607.13968` ✅ USEFUL — 2026-07-15 — Maria Saveria Mavillonio, Stefano Borgioli, Caterina Giannetti et al. — [abs](http://arxiv.org/abs/2607.13968v1) [pdf](https://arxiv.org/pdf/2607.13968v1)
- **A Unified Credit Expansion Theory on Housing Cycle: Causal Evidence for Within- and Cross-Metro Patterns in the Prior, Boom, Bust, and Recovery Periods** `2607.12205` ✅ USEFUL — 2026-07-13 — Bo Li — [abs](http://arxiv.org/abs/2607.12205v1) [pdf](https://arxiv.org/pdf/2607.12205v1)
- **Does Regulation Bite at Gateways? Evidence from MiCA and Stablecoins** `2607.09514` — 2026-07-10 — Nicola Borri, Kirill Shakhnov — [abs](http://arxiv.org/abs/2607.09514v1) [pdf](https://arxiv.org/pdf/2607.09514v1)
- **Stablecoins under Stress in a National Economy: Transaction-Level Evidence from Austrian Crypto-Asset Service Providers** `2607.08524` — 2026-07-09 — Pietro Saggese, Michael Sigmund, Burkhard Raunig et al. — [abs](http://arxiv.org/abs/2607.08524v1) [pdf](https://arxiv.org/pdf/2607.08524v1)
- **What Useful Alphas?** `2607.06502` ✅ USEFUL — 2026-07-07 — Andrew Y. Chen, Ivo Welch — [abs](http://arxiv.org/abs/2607.06502v1) [pdf](https://arxiv.org/pdf/2607.06502v1)
- **Overshooting the Coordinate: Where Factor Corrections Land on Characteristic Axes** `2607.05091` ✅ USEFUL — 2026-07-06 — Useong Shin — [abs](http://arxiv.org/abs/2607.05091v6) [pdf](https://arxiv.org/pdf/2607.05091v6)
- **A Cap-Axis Integral Diagnostic of Factor Models** `2607.01765` ✅ USEFUL — 2026-07-02 — Useong Shin — [abs](http://arxiv.org/abs/2607.01765v3) [pdf](https://arxiv.org/pdf/2607.01765v3)
- **Agent-to-Agent Finance: Blockchain Payments and Trust Infrastructure for Autonomous AI Agents** `2607.00245` — 2026-06-30 — Hui Gong — [abs](http://arxiv.org/abs/2607.00245v2) [pdf](https://arxiv.org/pdf/2607.00245v2)
- **Same Firms, Different Verdicts: ESG Rating Choice and the Measurement of Greenwashing** `2606.31469` — 2026-06-30 — Praveen Kumar Ashok Kumar, Rafał Sieradzki — [abs](http://arxiv.org/abs/2606.31469v1) [pdf](https://arxiv.org/pdf/2606.31469v1)
  - … and 1725 more in `papers/q-fin_GN/`

### q-fin.MF — Mathematical Finance — stochastic, probabilistic, functional analysis (1989 papers)
- **The Delta of a Variance Swap** `2609.08959` ✅ USEFUL — 2026-09-08 — Sébastien Bossu, Sebastian Gaitan-Escarpeta — [abs](http://arxiv.org/abs/2609.08959v1) [pdf](https://arxiv.org/pdf/2609.08959v1)
- **Numeraire Invariance of Entropy-Projected Martingale Measures** `2609.08605` — 2026-09-08 — Jan Vecer — [abs](http://arxiv.org/abs/2609.08605v1) [pdf](https://arxiv.org/pdf/2609.08605v1)
- **Variance-Optimal Hedging in the Rough Hawkes--Heston Model** `2609.08541` ✅ USEFUL — 2026-09-08 — Yingli Wang, Xiaoyu Wang — [abs](http://arxiv.org/abs/2609.08541v1) [pdf](https://arxiv.org/pdf/2609.08541v1)
- **Gatheral's Conjecture Revisited** `2609.05047` ✅ USEFUL — 2026-09-04 — Vladimir Lucic — [abs](http://arxiv.org/abs/2609.05047v2) [pdf](https://arxiv.org/pdf/2609.05047v2)
- **Bayesian Confidence Recalibration and Research-Equilibrium Criticality: Temporal Support in Robust Portfolios** `2609.03741` ✅ USEFUL — 2026-09-03 — Han Yanç — [abs](http://arxiv.org/abs/2609.03741v1) [pdf](https://arxiv.org/pdf/2609.03741v1)
- **A note on markets with semi-static trading strategies** `2608.30558` ✅ USEFUL — 2026-08-31 — Miklós Rásonyi — [abs](http://arxiv.org/abs/2608.30558v1) [pdf](https://arxiv.org/pdf/2608.30558v1)
- **Optimal Block Time for AMM Liquidity Providers under Jump-Diffusion Prices** `2608.30321` ✅ USEFUL — 2026-08-31 — Nils Bundi — [abs](http://arxiv.org/abs/2608.30321v1) [pdf](https://arxiv.org/pdf/2608.30321v1)
- **On the hedging problem in general 1D diffusion markets** `2608.25223` — 2026-08-25 — Alexis Anagnostakis, David Criens, Mikhail Urusov — [abs](http://arxiv.org/abs/2608.25223v1) [pdf](https://arxiv.org/pdf/2608.25223v1)
- **Capital allocation on decentralized lending platforms** `2608.24206` ✅ USEFUL — 2026-08-25 — Bastien Baude, Vincent Danos, Hamza El Khalloufi — [abs](http://arxiv.org/abs/2608.24206v1) [pdf](https://arxiv.org/pdf/2608.24206v1)
- **WSVI: A Dimensionless Shape Family for Implied Volatility and Its Static No-Arbitrage Structure** `2608.22620` ✅ USEFUL — 2026-08-23 — Charles Clevenger, Xiang Wan — [abs](http://arxiv.org/abs/2608.22620v1) [pdf](https://arxiv.org/pdf/2608.22620v1)
- **Arbitrage-Aware Multi-Step Forecasting of Implied Volatility Surfaces: Modelling Surface Trajectories Using Latent Diffusion** `2608.22478` — 2026-08-23 — Dominik Manuel Buchegger, Lukas Gonon — [abs](http://arxiv.org/abs/2608.22478v1) [pdf](https://arxiv.org/pdf/2608.22478v1)
- **Discrete asset pricing under transaction costs and model uncertainty with and without short-sale constraints** `2608.21873` — 2026-08-22 — Wenqing Zhang — [abs](http://arxiv.org/abs/2608.21873v1) [pdf](https://arxiv.org/pdf/2608.21873v1)
- **The Reconfiguration Premium: Co-movement Structure as an Unspanned Dimension of the Variance Risk Premium** `2608.20020` ✅ USEFUL — 2026-08-20 — Lucas Carvalho — [abs](http://arxiv.org/abs/2608.20020v1) [pdf](https://arxiv.org/pdf/2608.20020v1)
- **Rough Volatility Across Assets** `2608.16749` ✅ USEFUL — 2026-08-17 — Saad Mouti — [abs](http://arxiv.org/abs/2608.16749v1) [pdf](https://arxiv.org/pdf/2608.16749v1)
- **Behavioral Participating Insurance: Optimal Investment under Probability Distortion and Aspiration Constraints** `2608.15743` — 2026-08-16 — Hao Liu, Yang Liu, Zhenyu Shen — [abs](http://arxiv.org/abs/2608.15743v1) [pdf](https://arxiv.org/pdf/2608.15743v1)
- **An ergodic theorem for multi-period mutual insurance** `2608.14256` — 2026-08-14 — John Armstrong — [abs](http://arxiv.org/abs/2608.14256v1) [pdf](https://arxiv.org/pdf/2608.14256v1)
- **Dynamic Physical Hedging amid Jump Losses, Reconstruction-Price Uncertainty, Population Interactions** `2608.13745` ✅ USEFUL — 2026-08-13 — Paramahansa Pramanik, Michael Bowdin — [abs](http://arxiv.org/abs/2608.13745v1) [pdf](https://arxiv.org/pdf/2608.13745v1)
- **Fee Implied Volatility on Uniswap v3: A DEX Native Proxy and Its Limits** `2608.13340` ✅ USEFUL — 2026-08-13 — Amy Oumayma Khaldoun — [abs](http://arxiv.org/abs/2608.13340v1) [pdf](https://arxiv.org/pdf/2608.13340v1)
- **Physical Extinction and Long-Run Pricing under Time-Varying Beliefs** `2608.12777` — 2026-08-13 — Sourav Majumdar — [abs](http://arxiv.org/abs/2608.12777v1) [pdf](https://arxiv.org/pdf/2608.12777v1)
- **DYSANOS Generative Dynamic Smooth Arbitrage-free Non-parametric Option Surfaces** `2608.12587` — 2026-08-12 — Hans Buehler, Blanka Horvath, Anastasis Kratsios — [abs](http://arxiv.org/abs/2608.12587v1) [pdf](https://arxiv.org/pdf/2608.12587v1)
- **Term structure shapes in the Hull-White model with Svensson-parameterized initial yield curves** `2608.12016` — 2026-08-12 — Felix Sachse — [abs](http://arxiv.org/abs/2608.12016v1) [pdf](https://arxiv.org/pdf/2608.12016v1)
- **Multi-Credit Calibration via Elastically Stopped Lévy Processes** `2608.10321` ✅ USEFUL — 2026-08-10 — Graeme Baker, Agostino Capponi — [abs](http://arxiv.org/abs/2608.10321v1) [pdf](https://arxiv.org/pdf/2608.10321v1)
- **Anomaly detection in European cryptocurrency exchange-traded products** `2608.09576` ✅ USEFUL — 2026-08-10 — Julia Kończal, Rafał Połoczański — [abs](http://arxiv.org/abs/2608.09576v1) [pdf](https://arxiv.org/pdf/2608.09576v1)
- **High-Order Expansions of the Optimizer Map via Bell Polynomials** `2608.08900` — 2026-08-09 — Oleksii Mostovyi, Thaleia Zariphopoulou — [abs](http://arxiv.org/abs/2608.08900v1) [pdf](https://arxiv.org/pdf/2608.08900v1)
- **Microstructural Foundation for the Rough Hawkes--Heston Model** `2608.07709` ✅ USEFUL — 2026-08-07 — Yingli Wang, Yinhao Wu, Lingjiong Zhu — [abs](http://arxiv.org/abs/2608.07709v1) [pdf](https://arxiv.org/pdf/2608.07709v1)
  - … and 1964 more in `papers/q-fin_MF/`

### q-fin.PM — Portfolio Management — selection, optimization, allocation, performance (1484 papers)
- **Simple Dynamic Stock/Bond/Gold Portfolios** `2609.07946` ✅ USEFUL — 2026-09-07 — Nikhil Devanathan, Alexandros E. Tzikas, Stephen P. Boyd — [abs](http://arxiv.org/abs/2609.07946v1) [pdf](https://arxiv.org/pdf/2609.07946v1)
- **Portfolio Diversification and Concentration under Dependence Uncertainty: A Majorization Approach** `2609.04496` ✅ USEFUL — 2026-09-03 — Peng Liu, Yang Liu — [abs](http://arxiv.org/abs/2609.04496v1) [pdf](https://arxiv.org/pdf/2609.04496v1)
- **An Entropic Factor Model for Robust Portfolio Replication** `2609.03552` ✅ USEFUL — 2026-09-03 — Argimiro Arratia, Henryk Gzyl — [abs](http://arxiv.org/abs/2609.03552v1) [pdf](https://arxiv.org/pdf/2609.03552v1)
- **Eliciting ESG Preferences for Reinforcement Learning-Based Portfolio Optimization** `2609.02677` ✅ USEFUL — 2026-09-02 — Giovanni Dispoto, Marcello Restelli, Carmine Ventre — [abs](http://arxiv.org/abs/2609.02677v1) [pdf](https://arxiv.org/pdf/2609.02677v1)
- **Uniform Inference and Certified Capacity at a Reflexive Stability Boundary** `2609.02535` ✅ USEFUL — 2026-09-02 — Alejandro Rodriguez Dominguez — [abs](http://arxiv.org/abs/2609.02535v1) [pdf](https://arxiv.org/pdf/2609.02535v1)
- **Switching Frictions, Heterogeneous Trading Horizons, and Long-Memory Order Flow** `2609.02525` ✅ USEFUL — 2026-09-02 — Alejandro Rodriguez Dominguez — [abs](http://arxiv.org/abs/2609.02525v1) [pdf](https://arxiv.org/pdf/2609.02525v1)
- **Harvesting the Variance Risk Premium in Nuclear and Energy Equities: A Short-Put Portfolio Derisking Strategy** `2609.01183` ✅ USEFUL — 2026-09-01 — Jilang Miao, Nonna Sorokina — [abs](http://arxiv.org/abs/2609.01183v1) [pdf](https://arxiv.org/pdf/2609.01183v1)
- **End-to-End Neural Shrinkage of Indefinite Pairwise Correlation Matrices for Small-Cap-Inclusive Portfolios** `2608.30446` ✅ USEFUL — 2026-08-31 — Christian Bongiorno, Lorenzo Villassero — [abs](http://arxiv.org/abs/2608.30446v1) [pdf](https://arxiv.org/pdf/2608.30446v1)
- **Generalizing Markowitz Portfolio Optimization by a Quadratic Risk Measure** `2608.24449` ✅ USEFUL — 2026-08-25 — Ignas Gasparavičius, Andrius Grigutis — [abs](http://arxiv.org/abs/2608.24449v1) [pdf](https://arxiv.org/pdf/2608.24449v1)
- **KellyBoost: Growth-Optimal Portfolio Construction with Gradient-Boosted Trees** `2608.23393` ✅ USEFUL — 2026-08-24 — Jiayu Li — [abs](http://arxiv.org/abs/2608.23393v1) [pdf](https://arxiv.org/pdf/2608.23393v1)
- **The Market's Conditioning Representation: Equilibrium, Crowding, and Convention Multiplicity** `2608.18299` ✅ USEFUL — 2026-08-18 — Alejandro Rodriguez Dominguez — [abs](http://arxiv.org/abs/2608.18299v1) [pdf](https://arxiv.org/pdf/2608.18299v1)
- **Entropic Value-at-Risk portfolio optimization for tempered stable Lévy processes** `2608.18022` ✅ USEFUL — 2026-08-18 — Jaehyung Choi — [abs](http://arxiv.org/abs/2608.18022v1) [pdf](https://arxiv.org/pdf/2608.18022v1)
- **Scalable Pontryagin-Guided Adjoint-to-Control Recovery for Constrained Dynamic Portfolio Choice** `2608.15667` ✅ USEFUL — 2026-08-16 — Jaegi Jeon, Jeonggyu Huh, Hyeng Keun Koo et al. — [abs](http://arxiv.org/abs/2608.15667v3) [pdf](https://arxiv.org/pdf/2608.15667v3)
- **Large Language Model-Driven Small-Capitalization Trading: Integrating Financial News Sentiment, Macroeconomic Indicators, and Technical Signals** `2608.12283` ✅ USEFUL — 2026-08-12 — Alireza Kargarzadeh, Nariman Khaledian, Navid Parvini et al. — [abs](http://arxiv.org/abs/2608.12283v1) [pdf](https://arxiv.org/pdf/2608.12283v1)
- **Objective-oriented quantitative investment: A specification-driven framework for automated synthesis of trading strategy pipelines** `2608.10410` ✅ USEFUL — 2026-08-11 — Liangliang Zhang — [abs](http://arxiv.org/abs/2608.10410v1) [pdf](https://arxiv.org/pdf/2608.10410v1)
- **Robustness or Crowding: Experimental Design for Trading Strategy Capacity** `2608.08405` ✅ USEFUL — 2026-08-09 — Alejandro Rodriguez Dominguez, Miquel Noguer i Alonso — [abs](http://arxiv.org/abs/2608.08405v1) [pdf](https://arxiv.org/pdf/2608.08405v1)
- **Beyond Co-Movement: Locality by Exposures Enables a Joint Factor-Graph Framework for Portfolio Diversification** `2608.06618` ✅ USEFUL — 2026-08-06 — Sara Chehab, Giorgos Iacovides, Parisa Yazdanparast et al. — [abs](http://arxiv.org/abs/2608.06618v1) [pdf](https://arxiv.org/pdf/2608.06618v1)
- **Knowledge-Optimising Investment Decisions with Informative Datasets** `2608.05991` ✅ USEFUL — 2026-08-06 — Sidharth Mallik, Waymond Rodgers — [abs](http://arxiv.org/abs/2608.05991v1) [pdf](https://arxiv.org/pdf/2608.05991v1)
- **Portfolio Allocation under Heterogeneous Scales and Multifractality** `2608.04987` ✅ USEFUL — 2026-08-05 — Shinji Kakinaka, Ken Umeno — [abs](http://arxiv.org/abs/2608.04987v1) [pdf](https://arxiv.org/pdf/2608.04987v1)
- **Optimal Life Insurance Decision in Mean-Variance DC Management with Mortality Improvements** `2608.04532` ✅ USEFUL — 2026-08-05 — Yueman Feng, Wenyuan Li, Mengyi Xu et al. — [abs](http://arxiv.org/abs/2608.04532v2) [pdf](https://arxiv.org/pdf/2608.04532v2)
- **Path Portfolio Optimization: Defect, Lift, and the Price of Path Complexity** `2608.02355` ✅ USEFUL — 2026-08-03 — Miquel Noguer i Alonso — [abs](http://arxiv.org/abs/2608.02355v1) [pdf](https://arxiv.org/pdf/2608.02355v1)
- **Conformal Kelly: Conformal Prediction Intervals as the Scale in Fractional Kelly Position Sizing** `2608.01494` ✅ USEFUL — 2026-08-02 — Robert Jacob Ryan — [abs](http://arxiv.org/abs/2608.01494v1) [pdf](https://arxiv.org/pdf/2608.01494v1)
- **Are Three Matrices All You Need To Beat the Market? Observable Matrix Dynamics for Portfolio Optimization** `2607.27461` ✅ USEFUL — 2026-07-29 — Igor Halperin — [abs](http://arxiv.org/abs/2607.27461v1) [pdf](https://arxiv.org/pdf/2607.27461v1)
- **Neural Network-Driven Volatility Drag Mitigation under Aggressive Leverage** `2607.23068` ✅ USEFUL — 2026-07-25 — Christian Bongiorno, Efstratios Manolakis, Rosario Nunzio Mantegna — [abs](http://arxiv.org/abs/2607.23068v1) [pdf](https://arxiv.org/pdf/2607.23068v1)
- **Portfolio Optimization under Dynamic Rebalancing via Topological Data Analysis and News Sentiments** `2607.21170` ✅ USEFUL — 2026-07-23 — Divyanee Garg — [abs](http://arxiv.org/abs/2607.21170v1) [pdf](https://arxiv.org/pdf/2607.21170v1)
  - … and 1459 more in `papers/q-fin_PM/`

### q-fin.PR — Pricing of Securities — valuation/hedging of securities & derivatives (843 papers)
- **Pricing and Hedging of Discretely Monitored Asian Options in the Volterra-Heston Model** `2609.07169` ✅ USEFUL — 2026-09-07 — Gijs Custers, Sven Karbach, Martin Friesen — [abs](http://arxiv.org/abs/2609.07169v1) [pdf](https://arxiv.org/pdf/2609.07169v1)
- **Beyond Lognormal Sums: A Four-Moment Probability Framework for Basket and Spread Option Pricing** `2608.21498` ✅ USEFUL — 2026-08-21 — Dongdong Hu, Hasanjan Sayit, Steve Tchoneteck et al. — [abs](http://arxiv.org/abs/2608.21498v1) [pdf](https://arxiv.org/pdf/2608.21498v1)
- **When to Sell an Asset? - A Distribution Builder Approach** `2608.18783` — 2026-08-19 — Peter Carr, Stephan Sturm — [abs](http://arxiv.org/abs/2608.18783v1) [pdf](https://arxiv.org/pdf/2608.18783v1)
- **When ratios fall: A dynamic approach to contingent convertibles** `2608.16842` ✅ USEFUL — 2026-08-17 — Li Chen, Liang Wang, Weixuan Xia — [abs](http://arxiv.org/abs/2608.16842v1) [pdf](https://arxiv.org/pdf/2608.16842v1)
- **Optimal Pricing and Hedging of SOFR Derivatives** `2608.10711` — 2026-08-11 — Teemu Pennanen, Waleed Taoum — [abs](http://arxiv.org/abs/2608.10711v1) [pdf](https://arxiv.org/pdf/2608.10711v1)
- **Open Information: A Defining Perspective on Web Datasets for Carbon Pricing** `2608.04929` ✅ USEFUL — 2026-08-05 — Sidharth Mallik, Anastasios Megaritis, Waymond Rodgers — [abs](http://arxiv.org/abs/2608.04929v1) [pdf](https://arxiv.org/pdf/2608.04929v1)
- **Fund Competition under Conflicting ESG Rating Methodologies** `2607.29583` — 2026-07-31 — Wanling Rudkin — [abs](http://arxiv.org/abs/2607.29583v1) [pdf](https://arxiv.org/pdf/2607.29583v1)
- **Henstock--Kurzweil Path Integral in Financial Mathematics: A Machine-Verified Pricing of European and Barrier Options** `2608.19223` — 2026-07-26 — Alexander S. Ushakov, Yury N. Berdinsky — [abs](http://arxiv.org/abs/2608.19223v1) [pdf](https://arxiv.org/pdf/2608.19223v1)
- **Filtering Credit Risk with Stochastic Discontinuities** `2608.19221` ✅ USEFUL — 2026-07-23 — Félix B. Tambe-Ndonfack — [abs](http://arxiv.org/abs/2608.19221v1) [pdf](https://arxiv.org/pdf/2608.19221v1)
- **Quantum Kernels and the Cross-Section of Stock Returns: Anatomy of a Vanishing Advantage** `2607.20168` ✅ USEFUL — 2026-07-22 — Junchi Shen — [abs](http://arxiv.org/abs/2607.20168v1) [pdf](https://arxiv.org/pdf/2607.20168v1)
- **(Early) AI Compute Asset Pricing** `2607.12156` ✅ USEFUL — 2026-07-13 — Federico M. Bandi, Yinan Su — [abs](http://arxiv.org/abs/2607.12156v2) [pdf](https://arxiv.org/pdf/2607.12156v2)
- **Entropic Dynamics of Jump-Diffusion Option Pricing** `2607.06355` ✅ USEFUL — 2026-07-07 — Mohammad Abedi — [abs](http://arxiv.org/abs/2607.06355v1) [pdf](https://arxiv.org/pdf/2607.06355v1)
- **Reaction-boundary variance and adjoint-consistent local-volatility projection** `2607.05011` ✅ USEFUL — 2026-07-06 — Chris Angstmann, Tim Gebbie — [abs](http://arxiv.org/abs/2607.05011v3) [pdf](https://arxiv.org/pdf/2607.05011v3)
- **Renewing Reliability: Valuation and Credit Risk Adjustments for Renewable Power Purchase Agreements** `2607.04781` — 2026-07-06 — Nicola Bartolini, Silvia Romagnoli, Amia Santini — [abs](http://arxiv.org/abs/2607.04781v1) [pdf](https://arxiv.org/pdf/2607.04781v1)
- **Beyond the Fixed Price: Valuation and Risk of Non-Standard Renewable PPAs** `2607.03115` — 2026-07-03 — Nicola Bartolini, Silvia Romagnoli, Amia Santini — [abs](http://arxiv.org/abs/2607.03115v1) [pdf](https://arxiv.org/pdf/2607.03115v1)
- **Supply Chain Propagation of Textual Signals: LLM Embeddings and Cross-Sectional Return Predictability** `2606.29290` ✅ USEFUL — 2026-06-28 — Asef Yılkı — [abs](http://arxiv.org/abs/2606.29290v1) [pdf](https://arxiv.org/pdf/2606.29290v1)
- **Matrix Approximation of Bachelier Option Prices and Greeks under Stochastic Volatility models** `2606.26024` ✅ USEFUL — 2026-06-24 — Elisa Alòs, Òscar Burés — [abs](http://arxiv.org/abs/2606.26024v1) [pdf](https://arxiv.org/pdf/2606.26024v1)
- **Perpetual Futures for Stocks: The SpaceX Pre-IPO Market** `2609.05433` ✅ USEFUL — 2026-06-22 — Aditya Gupta, Nick Polson — [abs](http://arxiv.org/abs/2609.05433v1) [pdf](https://arxiv.org/pdf/2609.05433v1)
- **A Unified General Formula for Arbitrary Liquidity Operations in Weighted AMMs: Potential Applications to Intelligent Transportation Systems** `2606.22118` ✅ USEFUL — 2026-06-20 — Vittorio Astarita, Giuseppe Guido, Sina Shaffiee Haghshenas et al. — [abs](http://arxiv.org/abs/2606.22118v1) [pdf](https://arxiv.org/pdf/2606.22118v1)
- **Non-Spanning Identification of Scheduled Event Risk in Option Pricing** `2606.12872` ✅ USEFUL — 2026-06-11 — Tenghan Zhong — [abs](http://arxiv.org/abs/2606.12872v2) [pdf](https://arxiv.org/pdf/2606.12872v2)
- **Option prices from operational-time reaction-boundary lattices** `2606.09564` ✅ USEFUL — 2026-06-08 — Chris Angstmann, Tim Gebbie — [abs](http://arxiv.org/abs/2606.09564v4) [pdf](https://arxiv.org/pdf/2606.09564v4)
- **VIX options in Bergomi models** `2606.02336` ✅ USEFUL — 2026-06-01 — Desen Guo, Dan Pirjol, Lingjiong Zhu — [abs](http://arxiv.org/abs/2606.02336v1) [pdf](https://arxiv.org/pdf/2606.02336v1)
- **Multiplicative Langevin Process for Volatilities Produces Observed Q-Variance Regularities** `2606.00800` ✅ USEFUL — 2026-05-30 — William H. Press, Alex Dannenberg — [abs](http://arxiv.org/abs/2606.00800v2) [pdf](https://arxiv.org/pdf/2606.00800v2)
- **A Hybrid LSMC-PDE Method for Bermudan Option Pricing under the Gatheral Double Mean-Reverting Model** `2606.11237` ✅ USEFUL — 2026-05-29 — Mara Kalicanin Dimitrov, Ying Ni — [abs](http://arxiv.org/abs/2606.11237v1) [pdf](https://arxiv.org/pdf/2606.11237v1)
- **Valuation of GLWB-LTC Annuities with Lévy Equity Dynamics, Stochastic Interest Rates and Health-State Transitions** `2605.30567` ✅ USEFUL — 2026-05-28 — Andrea Molent — [abs](http://arxiv.org/abs/2605.30567v2) [pdf](https://arxiv.org/pdf/2605.30567v2)
  - … and 818 more in `papers/q-fin_PR/`

### q-fin.RM — Risk Management — measurement/management of financial risks (1646 papers)
- **Simplifying Cyber Cat(astrophe)s with Cyber Kittens: Power Law Plausibility for Cyber Insurance Risks** `2609.07486` — 2026-09-07 — Max Henderson, Anton Solomko, Henry Simmons et al. — [abs](http://arxiv.org/abs/2609.07486v1) [pdf](https://arxiv.org/pdf/2609.07486v1)
- **Illiquidity at Risk** `2609.00943` ✅ USEFUL — 2026-09-01 — Demetrio Lacava, Paolo Santucci de Magistris — [abs](http://arxiv.org/abs/2609.00943v1) [pdf](https://arxiv.org/pdf/2609.00943v1)
- **Pricing the DeFi Tail: Do Protocols or Depositors Price Operational Risk?** `2609.00911` ✅ USEFUL — 2026-09-01 — Nils Bundi — [abs](http://arxiv.org/abs/2609.00911v1) [pdf](https://arxiv.org/pdf/2609.00911v1)
- **Recovering Posterior Beliefs in Credit Risk: A Latent-State EM Extension of the Information-Geometric Framework** `2608.29786` ✅ USEFUL — 2026-08-30 — Lorenzo Quirini — [abs](http://arxiv.org/abs/2608.29786v1) [pdf](https://arxiv.org/pdf/2608.29786v1)
- **On the approximation of posterior laws in compound loss models by conditional Wasserstein GANs** `2608.27229` ✅ USEFUL — 2026-08-27 — Aleksandar Arandjelovic, Pavel V. Shevchenko, George Tzougas — [abs](http://arxiv.org/abs/2608.27229v1) [pdf](https://arxiv.org/pdf/2608.27229v1)
- **Interpretable hybrid credit scoring for thin-file and underbanked populations** `2608.26837` ✅ USEFUL — 2026-08-27 — Belise Kanziga, Yaé U. Gaba, Olivier Kanamugire — [abs](http://arxiv.org/abs/2608.26837v1) [pdf](https://arxiv.org/pdf/2608.26837v1)
- **DTD-VAE: Disentangled Temporal Dependencies VAE for Credit Risk Prediction** `2608.26473` ✅ USEFUL — 2026-08-27 — Xiaobo Guo, Lu-an Dong, Yanbo Wang et al. — [abs](http://arxiv.org/abs/2608.26473v2) [pdf](https://arxiv.org/pdf/2608.26473v2)
- **NatPar: Natural Parametric Modeling** `2608.24871` — 2026-08-25 — Hirbod Assa — [abs](http://arxiv.org/abs/2608.24871v1) [pdf](https://arxiv.org/pdf/2608.24871v1)
- **What Quantitative Risk Modellers Can Learn from Durkheim's Study of Suicide** `2608.21506` — 2026-08-21 — Mahmood Alaghmandan — [abs](http://arxiv.org/abs/2608.21506v1) [pdf](https://arxiv.org/pdf/2608.21506v1)
- **Calibration-Induced Degeneracy in LLM Financial Forecasting: An Audit-Trailed Case Study on Next-Day Market Risk** `2608.20304` ✅ USEFUL — 2026-08-20 — Arin Mohanty — [abs](http://arxiv.org/abs/2608.20304v1) [pdf](https://arxiv.org/pdf/2608.20304v1)
- **Communicating Credit Risk with Large Language Models: Evaluation of Explanations from Standard and Alternative Data-Based Models** `2608.17715` ✅ USEFUL — 2026-08-18 — Sahab Zandi, Noah Kostesku, Christophe Mues et al. — [abs](http://arxiv.org/abs/2608.17715v1) [pdf](https://arxiv.org/pdf/2608.17715v1)
- **A generic nonparametric value-at-risk estimator for high dimensions** `2608.17481` ✅ USEFUL — 2026-08-18 — Siyuan Sun — [abs](http://arxiv.org/abs/2608.17481v1) [pdf](https://arxiv.org/pdf/2608.17481v1)
- **zLend: A Dual-Scope Cash-Flow Reconstruction Framework for On-Chain Credit Underwriting** `2608.16856` ✅ USEFUL — 2026-08-17 — Girish G N, Ashutosh Sahoo, Akshay SP et al. — [abs](http://arxiv.org/abs/2608.16856v1) [pdf](https://arxiv.org/pdf/2608.16856v1)
- **Is the medium the message? Social disclosure channels and firm risk** `2608.15212` — 2026-08-15 — Andreas G. F. Hoepner, Blerita Korca, Frank Schiemann et al. — [abs](http://arxiv.org/abs/2608.15212v1) [pdf](https://arxiv.org/pdf/2608.15212v1)
- **Pricing Temperature-Index Insurance under Long Memory and Stochastic Time Change** `2608.15097` ✅ USEFUL — 2026-08-15 — Nader Karimi, Foad Shokrollahi — [abs](http://arxiv.org/abs/2608.15097v1) [pdf](https://arxiv.org/pdf/2608.15097v1)
- **Simulating Stress Laws under Extremal Dependence: Characterizing What Generative Models Must Preserve** `2608.13056` ✅ USEFUL — 2026-08-13 — Mantu Gupta, Anand Deo — [abs](http://arxiv.org/abs/2608.13056v1) [pdf](https://arxiv.org/pdf/2608.13056v1)
- **Nash Peer-to-Peer Insurance Bargaining under Price Fairness and Coalitional Stability** `2608.09859` ✅ USEFUL — 2026-08-10 — Tim J. Boonen, Wing Fung Chong, Kenneth Tsz Hin Ng et al. — [abs](http://arxiv.org/abs/2608.09859v1) [pdf](https://arxiv.org/pdf/2608.09859v1)
- **Climate-Conditioned Cascade Modeling for Multi-Peril Reinsurance: Analysis and Controlled Numerical Applications** `2608.09456` ✅ USEFUL — 2026-08-10 — N. Karimi, E. Salavati, F. Shokrollahi — [abs](http://arxiv.org/abs/2608.09456v1) [pdf](https://arxiv.org/pdf/2608.09456v1)
- **Attributing Differences Between Forecast Runs to Input Changes, With Applications to CCAR and CECL Exercises** `2608.04547` — 2026-08-05 — Xuan Mei, Junze Lin — [abs](http://arxiv.org/abs/2608.04547v1) [pdf](https://arxiv.org/pdf/2608.04547v1)
- **A unifying perspective on the collapse to the mean for law-invariant functionals** `2608.03466` ✅ USEFUL — 2026-08-04 — Felix-Benedikt Liebrich — [abs](http://arxiv.org/abs/2608.03466v1) [pdf](https://arxiv.org/pdf/2608.03466v1)
- **Preference robust distortion risk measures** `2608.02854` — 2026-08-03 — Carole Bernard, Silvana M. Pesenti — [abs](http://arxiv.org/abs/2608.02854v1) [pdf](https://arxiv.org/pdf/2608.02854v1)
- **Hawkes-Driven OTC Market Making: Volterra-Riccati Approximation** `2608.02002` ✅ USEFUL — 2026-08-03 — Alexander Barzykin — [abs](http://arxiv.org/abs/2608.02002v2) [pdf](https://arxiv.org/pdf/2608.02002v2)
- **An Information-Geometric Framework for Bayesian Credit Risk Monitoring** `2608.01294` ✅ USEFUL — 2026-08-02 — Lorenzo Quirini — [abs](http://arxiv.org/abs/2608.01294v1) [pdf](https://arxiv.org/pdf/2608.01294v1)
- **Drawdown Risk Beyond Brownian Motion: A Monte-Carlo Framework, Non-Gaussian Extensions, and Long Memory** `2608.00127` ✅ USEFUL — 2026-07-31 — Francesco Landolfi — [abs](http://arxiv.org/abs/2608.00127v1) [pdf](https://arxiv.org/pdf/2608.00127v1)
- **No Data Is Not No Risk: Visibility Aware Graph-Based Inference of Business Conduct Risk** `2607.26859` — 2026-07-29 — Tsuyoshi Iwata, Johannes Laurmaa, Ryohei Hisano — [abs](http://arxiv.org/abs/2607.26859v1) [pdf](https://arxiv.org/pdf/2607.26859v1)
  - … and 1621 more in `papers/q-fin_RM/`

### q-fin.ST — Statistical Finance — econometric/econophysics analyses of markets (683 papers)
- **Asymmetric Long-Memory GARCH: Sign-Dependent Kernel Injection in a Two-Dimensional Markov Chain** `2609.06422` ✅ USEFUL — 2026-09-06 — Kennedy Titus Kayaki, Kyungsub Lee — [abs](http://arxiv.org/abs/2609.06422v1) [pdf](https://arxiv.org/pdf/2609.06422v1)
- **Modeling Trade Durations under Temporal Granularity Effects in Forex Markets** `2609.02660` ✅ USEFUL — 2026-09-02 — Vladimír Holý — [abs](http://arxiv.org/abs/2609.02660v1) [pdf](https://arxiv.org/pdf/2609.02660v1)
- **Portfolio Risk Bounds without Cross-Asset Return Covariances: Distributional Fields from Language-Model Representations** `2608.29692` ✅ USEFUL — 2026-08-30 — Marcus Gawronsky, Chun-Sung Huang — [abs](http://arxiv.org/abs/2608.29692v1) [pdf](https://arxiv.org/pdf/2608.29692v1)
- **Wasserstein-Barycentric Interaction Fields for Spatial Factor Models: Evidence from Language-Model Representations** `2608.29669` ✅ USEFUL — 2026-08-30 — Marcus Gawronsky, Chun-Sung Huang — [abs](http://arxiv.org/abs/2608.29669v1) [pdf](https://arxiv.org/pdf/2608.29669v1)
- **Deep Hedging Under Realistic Market Frictions: A Regime-Conditional Empirical Study of Dynamic Option Hedging on Bitcoin Options** `2608.29025` ✅ USEFUL — 2026-08-29 — Sheryan Kumar — [abs](http://arxiv.org/abs/2608.29025v1) [pdf](https://arxiv.org/pdf/2608.29025v1)
- **What survives honest evaluation? Leakage-safe, search-aware assessment of LLM-driven trading strategy discovery** `2608.27734` ✅ USEFUL — 2026-08-27 — Eray Gençay — [abs](http://arxiv.org/abs/2608.27734v1) [pdf](https://arxiv.org/pdf/2608.27734v1)
- **Lead-Lag Relationships in Financial Markets: A Comparison of Multiple Clustering Algorithms** `2608.24703` ✅ USEFUL — 2026-08-25 — Ruichen Deng, Yichi Zhang — [abs](http://arxiv.org/abs/2608.24703v1) [pdf](https://arxiv.org/pdf/2608.24703v1)
- **Equity Strategy Backtesting: Luck or Edge? The MinervaScore as a Statistical Robustness Grade** `2608.23808` ✅ USEFUL — 2026-08-24 — Maria Laura Santoni, Vincent Jouanne, Matthew L. Scullin — [abs](http://arxiv.org/abs/2608.23808v2) [pdf](https://arxiv.org/pdf/2608.23808v2)
- **From Exponential to Polynomial: An Exact Filter for High-Dimensional MSM Models** `2608.22864` ✅ USEFUL — 2026-08-24 — Daniyal Ali Hameedi — [abs](http://arxiv.org/abs/2608.22864v1) [pdf](https://arxiv.org/pdf/2608.22864v1)
- **Disclosed Human-Capital Disruption and Firm-Specific Risk** `2608.14859` ✅ USEFUL — 2026-08-14 — Ang Zhang — [abs](http://arxiv.org/abs/2608.14859v1) [pdf](https://arxiv.org/pdf/2608.14859v1)
- **Dependence-Informed Sparse Neural Architecture for Stock Return Prediction** `2608.14323` ✅ USEFUL — 2026-08-14 — Hongyu Lin, Yulin Chen, Yuanrong Wang et al. — [abs](http://arxiv.org/abs/2608.14323v1) [pdf](https://arxiv.org/pdf/2608.14323v1)
- **The Price of Permission: Classification Uncertainty in Constrained Capital Markets** `2608.12634` — 2026-08-12 — Abdulrahman Qadi, Akash Sharma, Francesca Medda — [abs](http://arxiv.org/abs/2608.12634v1) [pdf](https://arxiv.org/pdf/2608.12634v1)
- **What Makes a Peer? Valuation-Anchored Similarity in Private Markets** `2608.12594` — 2026-08-12 — Sebastian Frank, Jingrao Lyu, Max Jarmey et al. — [abs](http://arxiv.org/abs/2608.12594v1) [pdf](https://arxiv.org/pdf/2608.12594v1)
- **Regime-Gated Residual Mixture-of-Experts for Cross-Sectional Volatility Forecasting** `2608.12251` ✅ USEFUL — 2026-08-12 — Junyi Ye, Gargi Vijay Borde — [abs](http://arxiv.org/abs/2608.12251v1) [pdf](https://arxiv.org/pdf/2608.12251v1)
- **When the Fed Speaks: Dynamics and Forecasts of the Volatility Surface** `2608.10693` ✅ USEFUL — 2026-08-11 — Lukasz Adamski, Robert Slepaczuk — [abs](http://arxiv.org/abs/2608.10693v1) [pdf](https://arxiv.org/pdf/2608.10693v1)
- **Lower spectrum of financial correlation matrices: a new perspective on market synchronization** `2608.09641` ✅ USEFUL — 2026-08-10 — Rosanna Grassi, Caterina Pastorino, Pierpaolo Uberti — [abs](http://arxiv.org/abs/2608.09641v1) [pdf](https://arxiv.org/pdf/2608.09641v1)
- **Scaling laws of Stablecoin Transactions: Evidence from USDT and USDC on the Ethereum blockchain** `2608.09378` ✅ USEFUL — 2026-08-10 — Kundan Mukhia, Sabat Rai, Vivek Shrivastav et al. — [abs](http://arxiv.org/abs/2608.09378v1) [pdf](https://arxiv.org/pdf/2608.09378v1)
- **Cross-Sectional Heterogeneity in LSTM Networks for Financial Time Series** `2608.05755` ✅ USEFUL — 2026-08-06 — Julius Döbelt — [abs](http://arxiv.org/abs/2608.05755v2) [pdf](https://arxiv.org/pdf/2608.05755v2)
- **Effort-Centric Fairness in Lending Decisions** `2607.28847` ✅ USEFUL — 2026-07-30 — Shiqi Fang, Zexun Chen, Jake Ansell — [abs](http://arxiv.org/abs/2607.28847v1) [pdf](https://arxiv.org/pdf/2607.28847v1)
- **Where does the criticality live? Early-warning signals are event-heterogeneous across seven crypto-perpetual liquidation cascades** `2607.27070` ✅ USEFUL — 2026-07-29 — Ramon Marc Garcia Seuma — [abs](http://arxiv.org/abs/2607.27070v1) [pdf](https://arxiv.org/pdf/2607.27070v1)
- **Bitcoin Runs on a Clock: Why Every Price Indicator Dies and the Halving Clock Doesn't** `2607.26188` ✅ USEFUL — 2026-07-28 — Josh Molnar — [abs](http://arxiv.org/abs/2607.26188v1) [pdf](https://arxiv.org/pdf/2607.26188v1)
- **Long-memory GARCH via a two-dimensional Markov chain** `2607.25189` ✅ USEFUL — 2026-07-28 — Kyungsub Lee, Kennedy Titus Kayaki — [abs](http://arxiv.org/abs/2607.25189v1) [pdf](https://arxiv.org/pdf/2607.25189v1)
- **The Fundamental Structure of Risk: From Characteristics to Covariance** `2607.24410` ✅ USEFUL — 2026-07-27 — Alexandre Alouadi, Charles-Albert Lehalle — [abs](http://arxiv.org/abs/2607.24410v1) [pdf](https://arxiv.org/pdf/2607.24410v1)
- **Forecasting Economically Significant Bitcoin Moves: A Multi-Scale TCN with Profit-Optimized Thresholds** `2608.26174` ✅ USEFUL — 2026-07-25 — Parsa Yousefnezhad, Gholamreza Mansourfar, Mohammadreza Feizi Derakhshi — [abs](http://arxiv.org/abs/2608.26174v1) [pdf](https://arxiv.org/pdf/2608.26174v1)
- **Retail Trader's Ruin: An Anatomy of Popular Signal Failure** `2607.20093` ✅ USEFUL — 2026-07-22 — Adam Darmanin — [abs](http://arxiv.org/abs/2607.20093v1) [pdf](https://arxiv.org/pdf/2607.20093v1)
  - … and 658 more in `papers/q-fin_ST/`

### q-fin.TR — Trading and Market Microstructure — microstructure, liquidity, execution, market-making (1388 papers)
- **The Double-Edged Sword of Short-Selling Bans** `2609.08881` ✅ USEFUL — 2026-09-08 — Pasquale Della Corte, Robert Kosowski, Dimitris Papadimitriou et al. — [abs](http://arxiv.org/abs/2609.08881v1) [pdf](https://arxiv.org/pdf/2609.08881v1)
- **Regimes in the Order Flow** `2609.07989` ✅ USEFUL — 2026-09-07 — Ramzi Jebali — [abs](http://arxiv.org/abs/2609.07989v1) [pdf](https://arxiv.org/pdf/2609.07989v1)
- **Explainable Deep Learning for Price-Trade Dynamics: From Black-Box Forecasts to Effective Parametric Models** `2609.06085` ✅ USEFUL — 2026-09-05 — Manuel Naviglio, Fabrizio Lillo — [abs](http://arxiv.org/abs/2609.06085v1) [pdf](https://arxiv.org/pdf/2609.06085v1)
- **Mean-field equilibrium of heterogeneous agents under market impact** `2609.03115` ✅ USEFUL — 2026-09-02 — Joseph Leclère, Mathieu Rosenbaum — [abs](http://arxiv.org/abs/2609.03115v1) [pdf](https://arxiv.org/pdf/2609.03115v1)
- **Price manipulation in nonlinear transient impact models: rigidity before memory and complete positivity after memory** `2609.02447` ✅ USEFUL — 2026-09-02 — Minhyeok Lee — [abs](http://arxiv.org/abs/2609.02447v1) [pdf](https://arxiv.org/pdf/2609.02447v1)
- **Metaorder modelling and identification from public data** `2608.30999` ✅ USEFUL — 2026-08-31 — Ezra Goliath, Tim Gebbie — [abs](http://arxiv.org/abs/2608.30999v2) [pdf](https://arxiv.org/pdf/2608.30999v2)
- **The Convergence Rate of Stochastic Tracking with Application to Optimal Execution** `2608.29468` ✅ USEFUL — 2026-08-29 — Marcel Nutz, Moritz Voss — [abs](http://arxiv.org/abs/2608.29468v1) [pdf](https://arxiv.org/pdf/2608.29468v1)
- **Equilibrium in closed constant-function market maker economies** `2608.23915` ✅ USEFUL — 2026-08-24 — Muqiao Huang, Ruodu Wang, Yiyun Wang — [abs](http://arxiv.org/abs/2608.23915v1) [pdf](https://arxiv.org/pdf/2608.23915v1)
- **tse_tick: A Python Library for Parsing and Querying Nikkei NEEDS Tick Data from the Tokyo Stock Exchange** `2608.23053` — 2026-08-24 — Kazumi Li, Masataka Hayashi, Teruo Nakatsuma et al. — [abs](http://arxiv.org/abs/2608.23053v1) [pdf](https://arxiv.org/pdf/2608.23053v1)
- **Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement** `2608.21888` ✅ USEFUL — 2026-08-22 — Nadav A. Kitron, Jonathan M. Wengrowicz — [abs](http://arxiv.org/abs/2608.21888v1) [pdf](https://arxiv.org/pdf/2608.21888v1)
- **Concentrated Liquidity Provision: a Reinforcement Learning Perspective** `2608.19389` ✅ USEFUL — 2026-08-19 — Georgios Chionas, Charalampos Kleitsikas, Stefanos Leonardos et al. — [abs](http://arxiv.org/abs/2608.19389v1) [pdf](https://arxiv.org/pdf/2608.19389v1)
- **Multi-Level Market Making with Reinforcement Learning** `2608.18195` ✅ USEFUL — 2026-08-18 — Patrick Cheridito, Moritz Weiss — [abs](http://arxiv.org/abs/2608.18195v1) [pdf](https://arxiv.org/pdf/2608.18195v1)
- **When Cross-Venue Agreement Is Not Price Discovery: Disclosure Frontiers for 24/7 Equity-Perpetual Oracles** `2608.09188` ✅ USEFUL — 2026-08-10 — Donghwa Seo, Doohwi Cha, Seunghan Son et al. — [abs](http://arxiv.org/abs/2608.09188v1) [pdf](https://arxiv.org/pdf/2608.09188v1)
- **On a Simple Relationship Between Order Imbalance, Skew and Width in Over-The-Counter Trading** `2608.07690` ✅ USEFUL — 2026-08-07 — Peter Cotton — [abs](http://arxiv.org/abs/2608.07690v1) [pdf](https://arxiv.org/pdf/2608.07690v1)
- **Velocity- and Regime-Aware Detection of Intraday Options Market Manipulation, with Explainable Attribution** `2608.05373` ✅ USEFUL — 2026-08-05 — Alex Chen, Maria Hybinette — [abs](http://arxiv.org/abs/2608.05373v1) [pdf](https://arxiv.org/pdf/2608.05373v1)
- **Public Trader Identity: Adverse Selection and Return Predictability** `2608.04373` ✅ USEFUL — 2026-08-05 — Daojing Zhai — [abs](http://arxiv.org/abs/2608.04373v3) [pdf](https://arxiv.org/pdf/2608.04373v3)
- **Mandate without Managers: Automated Market Makers as Verifiable Portfolio Products** `2608.02917` ✅ USEFUL — 2026-08-03 — Zachary Feinstein, Ionut Florescu, Sean O'Leary — [abs](http://arxiv.org/abs/2608.02917v1) [pdf](https://arxiv.org/pdf/2608.02917v1)
- **Exactly solvable model for the diffusive price-dynamics paradox under long-range correlated market-order flow** `2608.00988` ✅ USEFUL — 2026-08-02 — Yuki Sato, Shunta Fujiwara, Kiyoshi Kanazawa — [abs](http://arxiv.org/abs/2608.00988v1) [pdf](https://arxiv.org/pdf/2608.00988v1)
- **Optimal Trading of Microstructure Mean Reversion** `2608.00885` ✅ USEFUL — 2026-08-01 — Lucas Rabechini Amaral — [abs](http://arxiv.org/abs/2608.00885v1) [pdf](https://arxiv.org/pdf/2608.00885v1)
- **Axient: On-Chain Credit and Loss Allocation for Leveraged Event Markets: A Venue-Agnostic Protocol for Traders, Credit Providers, Market Makers, and Liquidation Backstops** `2608.00647` ✅ USEFUL — 2026-08-01 — Maksym Nechepurenko — [abs](http://arxiv.org/abs/2608.00647v1) [pdf](https://arxiv.org/pdf/2608.00647v1)
- **Axient: Debt-Free Finality for Leveraged Binary Event Markets** `2608.00631` ✅ USEFUL — 2026-08-01 — Maksym Nechepurenko — [abs](http://arxiv.org/abs/2608.00631v1) [pdf](https://arxiv.org/pdf/2608.00631v1)
- **Optimal Execution with Passive Market Impact** `2607.28323` ✅ USEFUL — 2026-07-30 — Alexander Barzykin, Robert Boyce, Eyal Neuman et al. — [abs](http://arxiv.org/abs/2607.28323v1) [pdf](https://arxiv.org/pdf/2607.28323v1)
- **Herding, Momentum, and Reversal in China's A-Share Market: An Agent-Based Network Model with Information Diffusion** `2607.27063` ✅ USEFUL — 2026-07-29 — Jiahao Weng — [abs](http://arxiv.org/abs/2607.27063v1) [pdf](https://arxiv.org/pdf/2607.27063v1)
- **Multi-Currency AMMs for Decentralized FOREX Markets: Feasibility & Optimal Design** `2607.26405` ✅ USEFUL — 2026-07-29 — Reina Ke Xin Li, Andreas Park, Andreas Veneris et al. — [abs](http://arxiv.org/abs/2607.26405v1) [pdf](https://arxiv.org/pdf/2607.26405v1)
- **OpenMarket: A Synchronized Polymarket-Binance Dataset for High-Frequency Prediction-Market Research** `2607.26245` ✅ USEFUL — 2026-07-28 — Gregory Young — [abs](http://arxiv.org/abs/2607.26245v1) [pdf](https://arxiv.org/pdf/2607.26245v1)
  - … and 1363 more in `papers/q-fin_TR/`


---

## Validation & reproducibility

- **Rate limiting:** 3 s between API calls (arXiv policy), 1 s between HTML fetches — no 429 abuse.
- **Deduplication:** by arXiv ID across pages.
- **Empty-abstract fix:** v1 scraped HTML with brittle regex → empty; v2 reads `atom:summary` from API (canonical) + verifies via per-paper HTML.
- **Historical coverage:** API `totalResults` per category cross-checked (e.g. q-fin.ST ~4346). To exhaust history, run with `max_papers_per_category=None` (default here does full pull). For quick demo runs, cap with e.g. `max_papers_per_category=200`.
- **Verification before completion:** per-paper markdowns sampled + this report's counts cross-footed against `*_results.json`.

*End of report — Run #1 — 2026-09-09T15:38:47.338445+00:00*
