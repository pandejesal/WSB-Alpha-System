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
   * `TELEGRAM_BOT_TOKEN`: For system notifications and trade logging.
