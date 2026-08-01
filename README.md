# WSB-Alpha-System: Autonomous Agentic Quant Firm

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Python Version](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🚀 Elevator Pitch

The **WSB-Alpha-System** has evolved far beyond a basic Reddit sentiment script. It is now a **Fully Autonomous, Self-Optimizing Quantitative Trading Firm** encapsulated within a single repository. By fusing unstructured retail social sentiment with institutional-grade risk management and technical confluence, the system identifies market inefficiencies, dynamically allocates capital, and executes trades with zero human intervention.

This system is an end-to-end autonomous framework. It doesn't just execute static rules—it constantly validates edge through rigorous Monte Carlo permutation testing, incubates new strategies in a paper-trading sandbox, and continuously improves its own hyperparameters using a Large Language Model (LLM) agent functioning as an AI Quantitative Researcher.

---

## 🏗️ High-Level Architecture (The Flow)

Data ingestion, signal generation, validation, and execution follow a strict, systematic pipeline designed to prevent look-ahead bias and protect capital.

1. **Sentiment Ingestion (FinBERT)** ➡️ Scrapes r/WallStreetBets to extract structured Bull/Bear sentiment scores using a financial-specific NLP model.
2. **Signal Generation (The Alpha Engine)** ➡️ Validates sentiment signals with Smart Money Concepts (SMC), Trend Following (Man AHL-style), and Counter-Trend ("The Fade") indicators.
3. **Statistical Validation (The Laboratory)** ➡️ Applies Monte Carlo Permutation Testing to ensure signals have a statistically significant P-Value (<0.01) before trading.
4. **Paper Incubation (The Sandbox)** ➡️ Strategies run in paper-trading mode until they prove empirical profitability and low drawdowns.
5. **Live Execution & Risk (The Hands)** ➡️ Universal Broker enforces a <1% global equity risk rule, tail-risk CVaR filters, and routes trades to exchange adapters (Alpaca/Crypto).
6. **Self-Optimization (The Brain)** ➡️ Every week, an LLM agent reviews the trade ledger and autonomously refines strategy parameters to adapt to changing market regimes.

---

## 🧠 Core Subsystems

### 1. The Alpha Engine (Signal Generation)
The system leverages multiple orthogonal alpha models to synthesize high-conviction trades:
* **FinBERT Sentiment Analysis:** Scrapes r/WallStreetBets Due Diligence posts and classifies text using FinBERT. Features a noise-reduction system to permanently blacklist false tickers (e.g., dictionary words like "GAP" or "FOR") to prevent API rate limits.
* **Smart Money Concepts (SMC):** The `order_blocks.py` module models institutional liquidity zones using Fair Value Gaps (FVG), ATR displacement criteria, and 5-bar fractal swing points.
* **Man AHL-Style Trend Following:** The `strategy_man_ahl.py` core engine uses multi-horizon momentum (5, 10, 21, 42 days) with volatility-scaled position sizing and dynamic holding periods.
* **"The Fade" Strategy:** A parallel mean-reversion engine (`src/alpha/fade_strategy.py`) that generates short signals when retail sentiment reaches extreme euphoria while technical momentum breaks down.
* **S&P 500 Adaptive Auto-Regime Switcher:** Evaluates the SPY macro regime (`src/alpha/macro_regime.py`) to auto-select strategy holding horizons (Short-Term, Mid-Long, or Long-Term).

### 2. The Laboratory (Statistical Validation)
No strategy touches live capital without surviving rigorous mathematical validation.
* **Monte Carlo Permutation Testing:** The `permutation_tester.py` module uses Timothy Masters' approach, destroying serial correlation while preserving logarithmic returns to calculate hard P-Values. If a strategy's success is based on historical noise ($p > 0.01$), it is strictly rejected.
* **Incubation Pipeline:** Managed by `incubation_manager.py`, new strategies start in an `INCUBATION` state. They are promoted to `LIVE` only after achieving strict risk-adjusted metrics in paper trading, or immediately demoted to `DEPRECATED` if they breach drawdown limits.

### 3. The Brain (Self-Optimization)
The system acts as its own Quant Researcher, actively learning from its mistakes.
* **LLM Auto-Optimization:** The `self_learning_agent.py` uses Anthropic's Claude 3.5 Sonnet to read the SQLite trade ledger (`trades.db`), analyzing Maximum Favorable Excursion (MFE), Maximum Adverse Excursion (MAE), PnL, and Drawdowns.

### 4. The Hands (Execution & Risk)
Institutional-grade risk management is enforced at the portfolio and order levels.
* **Dynamic Capital Allocation:** Uses Risk Parity sizing, OSQuant-inspired Conditional Value-at-Risk (CVaR) tail-risk filters, and ATR-based slippage modeling.
* **The Universal Broker Interceptor:** The `universal_broker.py` intercepts all incoming orders and strictly enforces a <1% global equity risk rule per trade before routing them.
* **Live Exchange Adapters:** Supports seamless routing to standard equity brokers via `live_alpaca_executor.py` or crypto perpetuals via `live_crypto_executor.py` (Bybit via CCXT).
* **Asynchronous Webhooks:** Provides live, emoji-formatted execution and alert monitoring directly to Telegram or Discord.

---

## 🗂️ Repository File Tree

```text
WSB-Alpha-System/
├── README.md                      # You are here
├── AUTOMATION.md                  # Cloud deployment & cron automation guide
├── PAPER_BROKER_SETUP.md          # Setup instructions for paper trading environments
├── REAL_LIFE_VIABILITY.md         # Market friction and slippage analysis
├── requirements.txt               # Pinned Python dependencies
├── .env.example                   # Template for API Keys and Secrets
│
├── wsb_alpha_system.py            # Data ingestion, FinBERT pipeline & sentiment rules
├── main_live.py                   # The Live Orchestrator (cron entrypoint)
├── universal_broker.py            # Global Risk Interceptor & Telegram Alerting
├── live_alpaca_executor.py        # Alpaca Equity Execution Adapter
├── live_crypto_executor.py        # CCXT Crypto Perpetuals Execution Adapter
├── risk_config.py                 # Hard-coded risk boundaries and circuit breakers
│
├── strategy_man_ahl.py            # Man AHL-style trend following momentum engine
├── order_blocks.py                # Smart Money Concepts & Institutional FVGs
├── indicators.py                  # Centralized vector math & technicals
│
├── permutation_tester.py          # Monte Carlo Validation Engine
├── run_historic_backtest.py       # Baseline sentiment backtester
├── run_man_ahl_backtest.py        # Institutional quantitative backtester
├── validation.py                  # P-Value constraint enforcement pipeline
├── incubation_manager.py          # State machine (INCUBATION -> LIVE -> DEPRECATED)
│
├── self_learning_agent.py         # Claude 3.5 LLM self-optimization script
├── self_improvement_agent.py      # Scientific method LLM strategy proposer
│
└── src/                           # Additional Subsystems
    ├── alpha/
    │   ├── fade_strategy.py       # Mean-reversion "The Fade" strategy
    │   └── macro_regime.py        # S&P 500 Adaptive Regime Filter
    └── execution/
        └── execution_adapter.py   # Standardized JSON schema execution bridge
```

---

## 💻 Prerequisites & Setup

### 1. Python Dependencies
The project is built on **Python 3.12**. Install all required dependencies using `pip`:
```bash
pip install -r requirements.txt
```

### 2. Required API Keys
Create a `.env` file in the root directory and populate the required API keys for full functionality:
* **Alpaca API:** `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` (For live/paper equity execution)
* **Anthropic API:** `ANTHROPIC_API_KEY` (Required for `self_learning_agent.py` optimizations using Claude 3.5 Sonnet)
* **Telegram/Discord Webhooks:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (For asynchronous trade monitoring)
* **Apify/Reddit API:** `APIFY_TOKEN` (For scraping historical/live Reddit data without strict rate limits)

---

## 🛠️ Usage Instructions

### 1. Run a Historic Backtest with the Permutation Tester
To execute a backtest and rigorously validate the statistical significance (P-Value) of the strategy via Monte Carlo simulations:
```bash
python run_historic_backtest.py
# Or to test the Man AHL engine specifically:
python run_man_ahl_backtest.py
```

### 2. Run the Live Orchestrator
To run the end-to-end live pipeline (Data Ingestion ➡️ Confluence ➡️ Risk Parity ➡️ Execution):
```bash
# Designed to be run as a daily cron job shortly before market close
python main_live.py
```

### 3. Trigger Weekly LLM Self-Optimization
```bash
# Designed to be run on weekends when markets are closed
python self_learning_agent.py
```

---

## ⚠️ Disclaimer
**Strictly for Educational and Research Purposes.**

This project is a quantitative research codebase. The trading algorithms, alpha engines, and strategies contained within this repository involve significant financial risk and **can result in total loss of capital**.
* Do not use this code to manage real money without thorough understanding and extensive paper-trading.
* Real-world frictions like slippage, spread, borrow fees, and API latency can severely impact simulated returns.
* Live trading mode requires a manual override (`LIVE_TRADING_ENABLED = True`) in `risk_config.py`. The creator of this repository is not responsible for any financial losses incurred from the use of this software.
