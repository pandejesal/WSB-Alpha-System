#!/usr/bin/env python3
"""
Paper trading sandbox script.
Downloads current day pricing, generates signals, tracks simulated portfolio,
and saves results/logs for the dashboard sandbox interface.
"""
import os
import json
import logging
import argparse
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Paper Trading Sandbox")
    parser.add_argument("--day", type=int, required=True, help="Current day of sandbox (1-5)")
    args = parser.parse_args()

    current_day = args.day

    try:
        from src.alpha.indicators import compute_indicators

        # Load Universe
        with open("config/universe.json") as f:
            universe = json.load(f).get("tickers", [])
        universe = list(dict.fromkeys(universe))

        # Download recent pricing (need some history for indicators)
        logger.info("Downloading pricing data...")
        end_date = pd.Timestamp.now()
        start_date = end_date - timedelta(days=90)

        from src.data.providers.chain import get_provider
        provider = get_provider()
        px_data = provider.fetch_ohlcv(universe, start_date=start_date.strftime('%Y-%m-%d'), end_date=end_date.strftime('%Y-%m-%d'))

        if px_data.empty:
            logger.warning("No pricing data available.")
            return

        # Transform flat provider dataframe back into the MultiIndex format expected by the rest of the script
        if 'Ticker' in px_data.columns:
            px_data = px_data.pivot(index='Date', columns='Ticker')

        signals = []
        current_prices = {}

        for ticker in universe:
            try:
                if isinstance(px_data.columns, pd.MultiIndex):
                    t_px = px_data.loc[:, (slice(None), ticker)].copy()
                    t_px.columns = t_px.columns.get_level_values(0)
                else:
                    if len(universe) == 1:
                        t_px = px_data.copy()
                    else:
                        continue

                t_px = t_px.dropna(subset=["Close", "Open", "High", "Low"])
                if len(t_px) < 20:
                    continue

                ind_df = compute_indicators(t_px)
                if ind_df is None or ind_df.empty:
                    continue

                # Use the last row for the current signal
                last_row = ind_df.iloc[-1]
                rsi = last_row.get('RSI_14', 50)
                macd_hist = last_row.get('MACD_Hist', 0)
                close = last_row['Close']
                bb_lower = last_row.get('BB_Lower', close * 0.95)
                bb_upper = last_row.get('BB_Upper', close * 1.05)
                ha_close = last_row.get('HA_Close', close)
                ha_open = last_row.get('HA_Open', close)
                gk_vol = last_row.get('GK_Vol', 0.50)
                ema_20 = last_row.get('EMA_20', close)

                current_prices[ticker] = float(close)

                vol_passed = gk_vol < 1.20
                bull_score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi < 70) + int(close > bb_lower)
                bear_score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi < 70) + int(close < bb_upper)

                if vol_passed:
                    if bull_score >= 3:
                        signals.append({"ticker": ticker, "direction": "buy", "entry_price": float(close), "confluence_score": bull_score})
                    elif bear_score >= 3:
                        signals.append({"ticker": ticker, "direction": "sell", "entry_price": float(close), "confluence_score": bear_score})
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")
                continue

        # Load or init state
        os.makedirs("docs/data", exist_ok=True)
        state_file = "docs/data/sandbox_state.json"
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                state = json.load(f)
        else:
            state = {"days_completed": 0, "last_run": None, "portfolio_value": 100.0, "trades": [], "realized_pnl": 0.0, "cash": 100.0}

        from src.risk.position_sizing import PositionSizer

        # Real Mark-to-Market tracking
        daily_pnl = 0.0
        open_trades = []
        realized_pnl_today = 0.0

        if state.get("trades"):
            # Update open trades P&L and handle exits based on simple holding period (e.g. max 5 days) or condition
            for trade in state["trades"]:
                if trade["ticker"] in current_prices:
                    current_price = current_prices[trade["ticker"]]
                    trade_days = current_day - trade.get("entry_day", current_day)

                    if trade["direction"] == "buy":
                        pnl = (current_price - trade["entry_price"]) * trade.get("quantity", 0)
                    else:
                        pnl = (trade["entry_price"] - current_price) * trade.get("quantity", 0)

                    # Exit logic: if held for 5 days or hitting a threshold, close it
                    if trade_days >= 5:
                        realized_pnl_today += pnl
                        # For long: we get back original capital plus pnl.
                        # For short: the cash allocated was qty * entry_price.
                        # The return to cash is the initial cash allocated + pnl.
                        state["cash"] += trade.get("quantity", 0) * trade["entry_price"] + pnl
                    else:
                        trade["unrealized_pnl"] = pnl
                        open_trades.append(trade)
                        daily_pnl += pnl

        state["trades"] = open_trades

        # Process new signals
        for sig in signals:
            if sig["ticker"] in current_prices:
                # Use PositionSizer for realistic sizing logic
                # Assumed metrics for sandbox
                win_rate = 0.55
                win_loss_ratio = 1.5
                confidence_score = 0.8
                stop_loss = sig["entry_price"] * 0.95 if sig["direction"] == "buy" else sig["entry_price"] * 1.05

                qty = PositionSizer.calculate_position_size(
                    account_equity=state["portfolio_value"],
                    current_price=sig["entry_price"],
                    stop_loss_price=stop_loss,
                    win_rate=win_rate,
                    win_loss_ratio=win_loss_ratio,
                    confidence_score=confidence_score
                )

                if qty > 0 and state["cash"] >= qty * sig["entry_price"]:
                    sig["quantity"] = qty
                    sig["entry_day"] = current_day
                    sig["unrealized_pnl"] = 0.0
                    state["cash"] -= qty * sig["entry_price"] # deduct notional size from cash
                    state["trades"].append(sig)

        state["realized_pnl"] = state.get("realized_pnl", 0.0) + realized_pnl_today

        # Total portfolio value = cash + value of open positions
        # Value of a long position is current_price * qty
        # Value of a short position is (entry_price * qty) + unrealized_pnl = (entry_price * qty) + (entry_price - current_price) * qty
        # Which is 2 * entry_price * qty - current_price * qty.
        # But a simpler mental model for margin is: portfolio = cash + initial margin allocated + total pnl.
        # Since cash was deducted by `qty * entry_price`, the margin held is exactly `qty * entry_price`.
        # So open position value = `qty * entry_price` + `unrealized_pnl`.
        open_positions_value = sum(
            (t.get("quantity", 0) * t["entry_price"]) + t.get("unrealized_pnl", 0.0)
            for t in state["trades"]
        )
        new_portfolio_value = state["cash"] + open_positions_value

        # Save signals log
        signal_log = {
            "day": current_day,
            "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "signals": signals,
            "portfolio_value": round(new_portfolio_value, 2),
            "trades_today": len(signals)
        }

        with open("docs/data/sandbox_signals.json", "w") as f:
            json.dump(signal_log, f, indent=2)

        # Update state
        state["days_completed"] = current_day
        state["last_run"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        state["portfolio_value"] = new_portfolio_value

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Sandbox day {current_day} complete. Value: {new_portfolio_value:.2f}")

    except Exception as e:
        logger.error(f"Sandbox run failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
