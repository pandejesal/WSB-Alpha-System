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
        px_data = yf.download(universe, start=start_date, end=end_date, progress=False, auto_adjust=True)

        if px_data.empty:
            logger.warning("No pricing data available.")
            return

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
            state = {"days_completed": 0, "last_run": None, "portfolio_value": 100.0, "trades": []}

        # Simulate execution
        # For simplicity, if we hold positions, we would update their value here.
        # Here we just apply a mock P&L based on signals if any.
        daily_pnl = 0
        if state.get("trades"):
            # Mock update open trades P&L (in a real scenario, use actual prices)
            for trade in state["trades"]:
                if trade["ticker"] in current_prices:
                    if trade["direction"] == "buy":
                        pnl = (current_prices[trade["ticker"]] - trade["entry_price"])
                    else:
                        pnl = (trade["entry_price"] - current_prices[trade["ticker"]])
                    # Add to daily pnl (mocking closing the trade for simplicity in this sandbox)
                    daily_pnl += pnl * 0.1 # scaled down

        new_portfolio_value = state["portfolio_value"] + daily_pnl

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
        state["trades"].extend(signals)

        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        logger.info(f"Sandbox day {current_day} complete. Value: {new_portfolio_value}")

    except Exception as e:
        logger.error(f"Sandbox run failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
