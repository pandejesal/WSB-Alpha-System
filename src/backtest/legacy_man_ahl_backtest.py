"""
Institutional Backtester for Man AHL Multi-Horizon Momentum Strategy.
Strictly handles a $50-$100 micro-account, dynamic leverage (3x), deleveraging breakers,
realistic costs (0.04% commission), and Almgren-Chriss variable slippage model.
Outputs professional institutional performance tear-sheet and metrics.
No look-ahead bias (signals generated on Day T, executed on Day T+1 Open).
"""

from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from src.alpha.man_ahl_legacy import (
    calculate_momentum_score,
    calculate_target_position_sizes,
    calculate_volatility_and_atr,
    check_rebalance_required,
)

# Configuration Parameters
TICKERS = ["BTC-USD", "ETH-USD", "SOL-USD"]
START_DATE = "2020-01-01"
END_DATE = "2026-07-29"
INITIAL_EQUITY = 100.0  # Micro-account starting capital
TARGET_RISK = 0.35      # 35% annualized volatility target
HALF_KELLY = 0.5        # Half-Kelly multiplier
LEVERAGE_CAP = 3.0      # Safe maximum cross-margin leverage (3x)
MIN_ORDER_SIZE = 10.0   # Exchange minimum size floor
COMMISSION_RATE = 0.0004 # Bybit base commission 0.04%
SLIPPAGE_BASE = 0.0005  # 0.05% base slippage
SLIPPAGE_VOL_COEFF = 0.1 # Coefficient for ATR percent variable slippage

def download_historical_data() -> dict:
    """
    Downloads historical daily pricing data for BTC-USD, ETH-USD, and SOL-USD from yfinance.
    """
    print(f"[*] Downloading daily prices for {TICKERS} from {START_DATE} to {END_DATE}...")
    data = {}
    for ticker in TICKERS:
        try:
            # Download with 60 days buffer to allow initial indicator warming up
            buffered_start = (datetime.strptime(START_DATE, "%Y-%m-%d") - timedelta(days=60)).strftime("%Y-%m-%d")  # noqa: DTZ007
            df = yf.download(ticker, start=buffered_start, end=END_DATE, progress=False, auto_adjust=True)
            if not df.empty:
                # Handle MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                # Calculate indicators and cleanup
                df = calculate_volatility_and_atr(df)
                df["Momentum_Score"] = calculate_momentum_score(df["Close"])
                # Filter to target test window
                df = df.loc[START_DATE:END_DATE]
                data[ticker] = df
                print(f" -> {ticker}: loaded {len(df)} rows.")
            else:
                print(f" [!] Warning: Empty dataset downloaded for {ticker}")
        except Exception as e:  # noqa: BLE001
            print(f" [!] Error fetching {ticker}: {e}")
    return data

def run_backtest():
    print("=" * 70)
    print("RUNNING INSTITUTIONAL MAN AHL BACKTEST & PERFORMANCE TEARDOWN")
    print("=" * 70)

    data = download_historical_data()
    if not data:
        print("[!] No pricing data downloaded. Aborting backtest.")
        return

    # Standardize index dates across all loaded tickers
    common_dates = sorted(set.intersection(*(set(df.index) for df in data.values())))
    print(f"[*] Identified {len(common_dates)} overlapping trading days in the backtest.")

    # Portfolio State variables
    equity = INITIAL_EQUITY
    peak_equity = INITIAL_EQUITY
    equity_curve = []
    dates_list = []

    current_positions = {ticker: 0.0 for ticker in TICKERS} # Signed dollar exposures (long > 0, short < 0)
    prev_scores = {ticker: 0.0 for ticker in TICKERS}
    days_since_last_rebalance = {ticker: 999 for ticker in TICKERS}
    entry_prices = {ticker: None for ticker in TICKERS}
    entry_directions = {ticker: 0 for ticker in TICKERS}
    closed_trade_returns = []

    # Performance tracking metrics
    trades_executed = 0
    total_commission_paid = 0.0
    total_slippage_paid = 0.0
    consecutive_losses = 0
    max_consecutive_losses = 0

    daily_returns_list = []

    # Active Drawdown flags
    current_target_risk = TARGET_RISK
    halt_trading = False

    # Rebalance simulation day-by-day
    for i in range(len(common_dates) - 1):
        today = common_dates[i]
        next_day = common_dates[i + 1]

        # Increment holding days counter
        for ticker in TICKERS:
            days_since_last_rebalance[ticker] += 1

        # 1. Update positions value based on the close-to-close change
        daily_pnl = 0.0
        for ticker in TICKERS:
            if current_positions[ticker] != 0:
                today_close = data[ticker].loc[today, "Close"]
                prev_close = data[ticker].shift(1).loc[today, "Close"] if today != common_dates[0] else today_close

                # Check for single index or series
                if isinstance(today_close, pd.Series):
                    today_close = today_close.iloc[0]
                if isinstance(prev_close, pd.Series):
                    prev_close = prev_close.iloc[0]

                # Close-to-close return on position
                daily_asset_return = (today_close - prev_close) / prev_close if prev_close > 0 else 0.0

                # signed position determines long/short PnL
                pos_pnl = current_positions[ticker] * daily_asset_return
                daily_pnl += pos_pnl

                # Update current dollar position value as equity/price changes
                current_positions[ticker] *= (1.0 + daily_asset_return)

        # Apply daily P&L to total equity
        prev_equity = equity
        equity += daily_pnl
        equity_curve.append(equity)
        dates_list.append(today)

        # Calculate daily portfolio return
        daily_return = (equity - prev_equity) / prev_equity if prev_equity > 0 else 0.0
        daily_returns_list.append(daily_return)

        # 2. Track Drawdown and trigger Circuit Breaker deleveraging
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity

        # Drawdown Breakers
        if halt_trading:
            # Check portfolio 20-day volatility
            if len(daily_returns_list) >= 20:
                rolling_vol = np.std(daily_returns_list[-20:]) * np.sqrt(365)
                # Since we are in cash, rolling vol will decay to 0. Resume trading once it falls below 5%
                if rolling_vol < 0.05:
                    print(f" [*] Volatility Circuit Breaker Cleared on {today.strftime('%Y-%m-%d')} (Rolling Vol: {rolling_vol:.2%}). Resetting peak equity to {equity:.2f} and resuming standard trading.")
                    halt_trading = False
                    peak_equity = equity  # Reset peak to allow recovery
                    current_target_risk = TARGET_RISK
            # Ensure positions remain closed while halted
            for ticker in TICKERS:
                current_positions[ticker] = 0.0
            current_target_risk = 0.0
        elif drawdown >= 0.20:
            # 20% drawdown: Halt all new entries and close all open positions
            if not halt_trading:
                print(f" [!] CIRCUIT BREAKER TRIGGERED: 20% Drawdown breached on {today.strftime('%Y-%m-%d')} ({drawdown:.2%}). Halting entries and closing positions.")
            halt_trading = True
            for ticker in TICKERS:
                if current_positions[ticker] != 0:
                    # Close the position
                    close_val = abs(current_positions[ticker])
                    # Costs
                    commission = close_val * COMMISSION_RATE
                    atr_pct = data[ticker].loc[today, "ATR_pct"]
                    if isinstance(atr_pct, pd.Series):
                        atr_pct = atr_pct.iloc[0]
                    slippage_rate = SLIPPAGE_BASE + (SLIPPAGE_VOL_COEFF * atr_pct)
                    slippage = close_val * slippage_rate

                    equity -= (commission + slippage)
                    total_commission_paid += commission
                    total_slippage_paid += slippage

                    # Track trade return on liquidation
                    p_entry = entry_prices[ticker]
                    curr_dir = entry_directions[ticker]
                    if p_entry is not None and curr_dir != 0:
                        today_close = data[ticker].loc[today, "Close"]
                        if isinstance(today_close, pd.Series):
                            today_close = today_close.iloc[0]
                        t_ret = (today_close - p_entry) / p_entry * curr_dir
                        closed_trade_returns.append(t_ret)
                    entry_prices[ticker] = None
                    entry_directions[ticker] = 0

                    current_positions[ticker] = 0.0
                    trades_executed += 1
            current_target_risk = 0.0
        elif drawdown >= 0.15:
            # 15% drawdown: Halve Target Risk
            if current_target_risk == TARGET_RISK:
                print(f" [!] RISK ALERT: 15% Drawdown breached on {today.strftime('%Y-%m-%d')} ({drawdown:.2%}). Halving Target_Risk.")
                current_target_risk = TARGET_RISK * 0.5
        else:
            current_target_risk = TARGET_RISK

        # 3. Signals Generation (End of Day T Close)
        today_scores = {}
        today_vols = {}
        for ticker in TICKERS:
            score = data[ticker].loc[today, "Momentum_Score"]
            vol = data[ticker].loc[today, "Vol_20d"]
            if isinstance(score, pd.Series):
                score = score.iloc[0]
            if isinstance(vol, pd.Series):
                vol = vol.iloc[0]
            today_scores[ticker] = score
            today_vols[ticker] = vol

        # 4. Position Sizing
        if halt_trading:
            target_sizes = {ticker: 0.0 for ticker in TICKERS}
        else:
            target_sizes = calculate_target_position_sizes(
                scores=today_scores,
                volatilities=today_vols,
                equity=equity,
                target_risk=current_target_risk,
                half_kelly=HALF_KELLY,
                leverage_cap=LEVERAGE_CAP,
                min_order_size=MIN_ORDER_SIZE
            )

        # 5. Check Rebalance Requirements
        rebalance_required = check_rebalance_required(
            current_positions=current_positions,
            target_sizes=target_sizes,
            scores=today_scores,
            prev_scores=prev_scores,
            min_change=MIN_ORDER_SIZE
        )

        # Enforce minimum holding/rebalancing period of 15 days for minor size adjustments
        for ticker in TICKERS:
            if rebalance_required[ticker]:
                curr_pos = current_positions[ticker]
                target_size = target_sizes[ticker]
                score = today_scores[ticker]
                prev_score = prev_scores.get(ticker, 0.0)

                sign_flip = (np.sign(score) * np.sign(prev_score) < 0)
                exit_pos = (curr_pos != 0.0 and target_size == 0.0)
                entry = (curr_pos == 0.0 and target_size != 0.0)

                if not (sign_flip or exit_pos or entry) and (days_since_last_rebalance[ticker] < 15):
                    # This is a same-direction size adjustment (scaling up/down)
                    rebalance_required[ticker] = False

        # 6. Execute Trades on Day T+1 OPEN
        for ticker, required in rebalance_required.items():
            if required:
                next_open = data[ticker].loc[next_day, "Open"]
                if isinstance(next_open, pd.Series):
                    next_open = next_open.iloc[0]

                target_size = target_sizes[ticker]
                current_pos = current_positions[ticker]

                # Reset days since last rebalance on actual trade
                days_since_last_rebalance[ticker] = 0

                # Size of trade executed
                trade_size = abs(target_size - current_pos)

                # Execute Market Order
                atr_pct = data[ticker].loc[today, "ATR_pct"]
                if isinstance(atr_pct, pd.Series):
                    atr_pct = atr_pct.iloc[0]
                slippage_rate = SLIPPAGE_BASE + (SLIPPAGE_VOL_COEFF * atr_pct)

                # Compute frictional cost
                commission = trade_size * COMMISSION_RATE
                slippage = trade_size * slippage_rate

                # Charge friction to equity
                friction = commission + slippage
                equity -= friction
                total_commission_paid += commission
                total_slippage_paid += slippage

                # Log trade PnL tracking for consecutive losses
                np.sign(target_size - current_pos)
                # Estimate PnL from old position to new position
                if current_pos != 0:
                    trade_pnl = current_pos * ((next_open - data[ticker].loc[today, "Close"]) / data[ticker].loc[today, "Close"])
                    if trade_pnl < 0:
                        consecutive_losses += 1
                        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                    else:
                        consecutive_losses = 0

                # Track segment returns for trade-level win rate
                target_dir = int(np.sign(target_size))
                curr_dir = entry_directions[ticker]

                # If we are changing direction or closing, close previous segment
                if (curr_dir != 0) and (target_dir != curr_dir or target_dir == 0):
                    p_entry = entry_prices[ticker]
                    if p_entry is not None:
                        t_ret = (next_open - p_entry) / p_entry * curr_dir
                        closed_trade_returns.append(t_ret)
                    entry_prices[ticker] = None
                    entry_directions[ticker] = 0

                # If we are opening a new segment
                if (target_dir != 0) and (curr_dir == 0 or target_dir != curr_dir):
                    entry_prices[ticker] = next_open
                    entry_directions[ticker] = target_dir

                if trades_executed < 15:
                    print(f"[DEBUG TRADE] {today.strftime('%Y-%m-%d')} {ticker}: CurrPos={current_pos:.2f}, TargetSize={target_size:.2f}, SizeChange={trade_size:.2f}, Score={today_scores[ticker]}, PrevScore={prev_scores.get(ticker, 0)}")

                # Set position dollar exposure at open of next day
                current_positions[ticker] = target_size
                trades_executed += 1

        # Update previous scores
        prev_scores = today_scores.copy()

    # Append the final day equity state
    final_day = common_dates[-1]
    equity_curve.append(equity)
    dates_list.append(final_day)

    # Compile performance results
    returns_series = pd.Series(daily_returns_list, index=common_dates[:-1])
    equity_series = pd.Series(equity_curve, index=common_dates)

    total_days = (common_dates[-1] - common_dates[0]).days
    years = total_days / 365.25
    cagr = (equity / INITIAL_EQUITY) ** (1 / years) - 1 if years > 0 else 0.0

    # Drawdown metrics
    peaks = equity_series.cummax()
    drawdowns = (peaks - equity_series) / peaks
    max_dd = drawdowns.max()

    # Sharpe Ratio (Risk-free rate = 4%)
    rf_daily = 0.04 / 365.0
    excess_returns = returns_series - rf_daily
    sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(365)) if excess_returns.std() > 0 else 0.0

    # Win Rate (percentage of round-trip trade returns that are positive)
    # Trend-following relies on positive skew, so expect lower win rates but higher gains on positive days
    trade_win_rate = 0.0
    if len(closed_trade_returns) > 0:
        trade_win_rate = sum(1 for r in closed_trade_returns if r > 0) / len(closed_trade_returns)

    daily_win_rate = (returns_series > 0).sum() / len(returns_series) if len(returns_series) > 0 else 0.0

    print("\n" + "=" * 70)
    print("INSTITUTIONAL PERFORMANCE TEARDOWN REPORT")
    print("=" * 70)
    print(f"Start Date:                      {common_dates[0].strftime('%Y-%m-%d')}")
    print(f"End Date:                        {common_dates[-1].strftime('%Y-%m-%d')}")
    print(f"Total Trading Days:              {len(common_dates)}")
    print(f"Initial Account Balance:         ${INITIAL_EQUITY:.2f}")
    print(f"Ending Account Balance:          ${equity:.2f}")
    print(f"Total Profit/Loss:               ${(equity - INITIAL_EQUITY):.2f} ({(equity / INITIAL_EQUITY - 1.0):.2%})")
    print("-" * 70)
    print(f"CAGR (Compound Annual Growth):   {cagr:.2%}")
    print(f"Max Drawdown (Aiming for <15%):  {max_dd:.2%}")
    print(f"Sharpe Ratio (Rf=4%, SR>0.75?):  {sharpe:.4f}")
    print(f"Trade Win Rate (Expect ~30%):    {trade_win_rate:.2%}")
    print(f"Daily Positive Return Rate:      {daily_win_rate:.2%}")
    print(f"Trade Count (Statistical Sign):  {trades_executed}")
    print(f"Max Consecutive Loss Series:     {max_consecutive_losses}")
    print(f"Total Commission Expense:        ${total_commission_paid:.4f}")
    print(f"Total Slippage Friction Paid:    ${total_slippage_paid:.4f}")
    print("=" * 70)
    print("[*] Note: Trend-following strategies naturally rely on positive skewness")
    print("    (small frequent losses balanced by large, long-term trends) rather than")
    print("    a high win rate. Micro-accounts require strict drawdown controls and")
    print("    low turnover to survive this friction, which our circuit breakers enable!")
    print("=" * 70)

    # Generate Equity Plot
    plt.figure(figsize=(12, 6))
    plt.plot(equity_series.index, equity_series.values, label="Man AHL Multi-Horizon Portfolio Equity", color="blue", linewidth=1.8)
    plt.axhline(y=INITIAL_EQUITY, color="gray", linestyle="--", linewidth=0.8, label="Initial Capital")
    plt.title("Man AHL Systematic Crypto Momentum Strategy: Compounding Growth Curve ($50-$100 Balance)", fontsize=13, fontweight="bold")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Equity ($)")
    plt.legend(loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig("man_ahl_backtest_equity.png", dpi=300)
    print("[*] Backtest equity plot successfully outputted to: man_ahl_backtest_equity.png")

if __name__ == "__main__":
    run_backtest()
