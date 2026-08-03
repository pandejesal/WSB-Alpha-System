# WSB-Alpha-System: Autonomous Agentic Quant Firm

This is a fully automated, self-optimizing system running on a $100 micro-account. It uses natural language processing on retail sentiment data, combines it with institutional quantitative methods, and continually refines itself using an AI skill loop.

## The Tech Stack (Highlighting Zero-Cost)
* **LLM Engine:** Google Gemini 3.1 Pro (Zero-cost optimization via Google AI Studio).
* **Data Ingestion:** PRAW (Free Reddit API).
* **Execution:** Alpaca (Zero-commission fractional shares) & CCXT.

## The Architecture
* **Signal Generation:** FinBERT Sentiment + Smart Money Concepts (FVGs/Order Blocks) + Man AHL Trend Following.
* **Validation:** Timothy Masters' Monte Carlo Permutation Testing (Logarithmic).
* **Self-Learning:** The Gemini Agent Skill Loop (`skill_executor.py`) that generates hypotheses, tests them via the Sandbox Backtest Tool, and safely deploys optimized parameters.

## Setup Instructions

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and fill in the following values:
   * `ALPACA_API_KEY`: For zero-commission fractional share execution.
   * `GEMINI_API_KEY`: For the self-learning agent and LLM optimization loop.
   * `REDDIT_CLIENT_ID`: Your PRAW / Reddit App client ID.
   * `REDDIT_CLIENT_SECRET`: Your PRAW / Reddit App client secret.
     * **You MUST create a registered Reddit Developer App (type: 'script') to get OAuth credentials. Do not use unauthenticated requests, or you will be throttled to 10 requests per minute and your IP will be blocked.**
   * `TELEGRAM_BOT_TOKEN`: For system notifications and trade logging.

## Real Backtest Results (2020-2026)

The strategy was rigorously backtested from 2020 to 2026, evaluating the S&P 500 Adaptive Auto-Regime Switcher.
While the raw backtest reports extraordinary performance (achieving up to **+1,479.92%** total return), the statistical validation via Monte Carlo permutation tests indicates the strategy has not demonstrated it beats random noise:
* **In-sample Monte Carlo permutation p-value:** 0.1100 (11.0%)
* **Multi-year rolling Walk-forward permutation p-value:** 0.2150 (21.5%)

The true statistical performance currently fails to meet the strict viability thresholds (In-sample p-value > 1%, Walk-forward p-value > 5%). Please read `REAL_LIFE_VIABILITY.md` for full details.

## Risk Management & Failure Checks

### Technical and System Failures
* **Internet Drops:** A lost connection stops your program from getting price updates or sending stop-loss orders.
* **Server Crashes:** Software bugs or hardware freezes can leave open trades hanging without protection.
* **Latency Delays:** Slow data speeds mean your order arrives too late, missing the target price.

### Strategy and Data Errors
* **Over-Optimization:** Tuning a model too closely to past data (curve fitting) means it will fail in live markets.
* **Bad Data Quality:** Incorrect or delayed historical and live feeds create false buy or sell signals.
* **Ignoring Costs:** Forgetting about broker fees, taxes, and price slippage can turn a winning idea into a losing routine.

### Market and Execution Risks
* **Liquidity Shortages:** Sudden drops in buyers or sellers mean your large order cannot close at a fair price.
* **Changing Conditions:** An automated rule built for a quiet market will often break during sudden economic panic or high volatility.
