# -*- coding: utf-8 -*-
"""
🤖 Live Alpaca Broker Execution Template: WSB Sentiment & Technical Confluence

This script is a production-ready example showing how to automate daily execution
of our sentiment confluence strategy using the Alpaca Trade API.
It extracts active signals for today, computes risk-parity position sizes,
and automatically submits Buy/Short market orders to paper or live accounts.

To run this in production, schedule this script to run daily at 3:55 PM EST via cron:
$ python live_alpaca_executor.py
"""

import os
import requests
import pandas as pd

# ============================================================================
# API CONFIGURATION
# ============================================================================
ALPACA_API_KEY_ID = os.getenv("ALPACA_API_KEY_ID", "MOCK_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "MOCK_SECRET_KEY")
# Use paper trading URL by default for safety
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY_ID,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    "Content-Type": "application/json"
}

# Target equity buying power percentage allocated to this system (e.g. 50%)
SYSTEM_ALLOCATION = 0.50

def get_account_equity() -> float:
    """
    Fetches the current account equity from Alpaca.
    """
    url = f"{ALPACA_BASE_URL}/v2/account"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return float(data.get("equity", 0.0))
        else:
            print(f"[!] Error fetching Alpaca account: {r.text}")
            return 0.0
    except Exception as e:
        print(f"[!] Exception calling Alpaca API: {e}")
        return 0.0

def place_market_order(symbol: str, qty: int, side: str):
    """
    Submits a market order to Alpaca.
    side can be 'buy' (bullish setups) or 'sell' (bearish setups / short).
    """
    url = f"{ALPACA_BASE_URL}/v2/orders"
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": "market",
        "time_in_force": "day"
    }
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if r.status_code == 200 or r.status_code == 201:
            order = r.json()
            print(f" -> ORDER SUBMITTED: {side.upper()} {qty} shares of {symbol} (Order ID: {order.get('id')})")
        else:
            print(f"[!] Order rejected for {symbol}: {r.text}")
    except Exception as e:
        print(f"[!] Exception placing order for {symbol}: {e}")

def main():
    print("=" * 60)
    print("ALPACA AUTOMATED LIVE/PAPER ORDER EXECUTOR")
    print("=" * 60)

    # 1. Fetch live account equity
    equity = get_account_equity()
    if equity <= 0:
        print("[!] No valid account equity found. Aborting execution.")
        return
    print(f"[*] Live Account Equity: ${equity:,.2f}")

    # 2. Read the latest aggregated signals from our CSV database
    csv_path = "wsb_factual_research_data.csv"
    if not os.path.exists(csv_path):
        print(f"[!] Could not locate database at {csv_path}. Run backtest or pipeline first.")
        return

    df = pd.read_csv(csv_path)

    # Get today's date or the latest post date in the file
    df["post_date"] = pd.to_datetime(df["post_date"])
    latest_date = df["post_date"].max()
    print(f"[*] Analyzing latest available signals for date: {latest_date.strftime('%Y-%m-%d')}")

    today_signals = df[df["post_date"] == latest_date]
    active_signals = today_signals[today_signals["confluence_triggered"] == True]  # noqa: E712

    if active_signals.empty:
        print("[*] No active confluence-triggered signals found for today. Cash preserved.")
        return

    print(f"[*] Located {len(active_signals)} active trade signals:")
    print(active_signals[["ticker", "sentiment_score", "risk_parity_weight"]].to_string(index=False))

    # Total dollar capital assigned to today's active signals
    capital_pool = equity * SYSTEM_ALLOCATION
    # Equal division per active signal, scaled by its individual risk parity weight
    base_allocation_per_trade = capital_pool / len(active_signals)

    # 3. Process each active signal and execute orders
    for _, signal in active_signals.iterrows():
        symbol = signal["ticker"]
        sentiment = signal["sentiment_score"]
        weight = float(signal.get("risk_parity_weight", 1.0))

        # Calculate dollar allocation scaled by risk-parity volatility unit
        dollar_allocation = base_allocation_per_trade * weight
        print(f"\n[*] Processing order for {symbol}:")
        print(f"   -> Risk-Parity Allocation Capital: ${dollar_allocation:,.2f}")

        # Fetch current asset market price to determine quantity
        ticker_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            r = requests.get(ticker_url, headers=headers, timeout=10)
            if r.status_code == 200:
                price_data = r.json()
                current_price = float(price_data["chart"]["result"][0]["meta"]["regularMarketPrice"])
            else:
                print(f"   [!] Failed to download market price for {symbol}, skipping trade.")
                continue
        except Exception as e:
            print(f"   [!] Error retrieving price for {symbol}: {e}, skipping.")
            continue

        qty = int(dollar_allocation / current_price)
        if qty <= 0:
            print(f"   [!] Price (${current_price:.2f}) exceeds trade capital, skipping.")
            continue

        print(f"   -> Current Stock Price: ${current_price:.2f}")
        print(f"   -> Target Share Quantity: {qty}")

        # Submit the order
        if sentiment > 0:
            place_market_order(symbol, qty, "buy")
        else:
            # Short-selling bearish setups if supported by the broker
            place_market_order(symbol, qty, "sell")

    print("\n" + "=" * 60)
    print("LIVE EXECUTION CYCLE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
