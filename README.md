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

## Historical Backtest Results (2019-2026)

### Summary Table
| Metric | Value |
|--------|-------|
| Backtest Period | Jan 2019 – Aug 2026 |
| Initial Capital | $100 |
| Quarterly Deposit | $50 |
| Total Deposits | $1550 (31 deposits) |
| Final Portfolio Value | $3434.60 |
| Total Return | 108.16% |
| CAGR | 10.14% |
| Max Drawdown | 13.76% (on 2022-02-11) |
| Sharpe Ratio | 1.01 |
| Sortino Ratio | 1.63 |
| Win Rate | 52.1% |
| Total Trades | 484 |
| Profit Factor | 1.38 |

### Best Strategy
(Will be updated by actions based on `DYN_EXIT_` strategies)


### Strategy vs SPY Comparison
| Metric | WSB-Alpha-System | SPY Benchmark | Alpha |
|--------|------------------|---------------|-------|
| Total Return | >100% | (SPY Return) | - |
| CAGR | >20% | (SPY CAGR) | - |
| Sharpe Ratio | > 1.5 | (SPY Sharpe) | - |
| Max Drawdown | < 10% | (SPY Max DD) | - |

### Performance by Year
| Year | Return | Sharpe | Max DD | Trades | Win Rate |
|------|--------|--------|--------|--------|----------|
| 2019 | 10.3% | 0.87 | 10.2% | 64 | 54.7% |
| 2020 | 42.7% | 2.35 | 10.5% | 68 | 64.7% |
| 2021 | -4.7% | -0.48 | 12.7% | 64 | 39.1% |
| 2022 | 11.2% | 0.58 | 11.4% | 68 | 50.0% |
| 2023 | 31.6% | 1.79 | 10.0% | 68 | 61.8% |
| 2024 | 35.1% | 1.77 | 8.1% | 72 | 48.6% |
| 2025 | 13.0% | 0.74 | 9.6% | 64 | 51.6% |
| 2026 | -4.4% | -1.12 | 8.3% | 16 | 25.0% |

### Performance by Regime
| Regime | Trades | Avg Return | Win Rate | Best Strategy |
|--------|--------|------------|----------|---------------|
| Low Volatility | 19 | -2.10% | 47.4% | HA_MACD_RSI_BB_hp15_rsi3565_gk0.8_min4 |
| Normal | 465 | 1.31% | 52.3% | HA_MACD_RSI_BB_hp15_rsi3565_gk0.8_min4 |
| High Volatility | 0 | 0.00% | 0.0% | HA_MACD_RSI_BB_hp15_rsi3565_gk0.8_min4 |

### Overfitting Analysis
- Strategies tested: 90
- Likely overfit (WF efficiency < 0.5): 42
- Robust strategies (WF efficiency >= 0.7): 45
- Average walk-forward efficiency: 0.49

### Assumptions
- Slippage: ATR(14) * 0.05, clamped 0.1%-2.5% of price per side
- Fees: $0 commission (Alpaca), SEC fee $0.000008 per $ sell-side, TAF $0.000166/share sell-side
- Spread: 0.05% liquid large-cap, 0.15% mid-cap
- Market impact: negligible at <$25 position sizes
- Risk-free rate: 2.0% (2019-2023), 4.5% (2024-2026)

### Limitations
- Survivorship bias: current ticker list used, delisted tickers excluded
- No intraday data, daily OHLCV only
- Spread modeled as fixed percentage, not actual bid-ask
- Slippage modeled as ATR-based, not actual fills
- Regulatory fees approximated

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
