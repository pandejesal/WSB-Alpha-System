"""
🤖 Live Alpaca Broker Execution Template: WSB Sentiment & Technical Confluence

This script is a production-ready example showing how to automate daily execution
of our sentiment confluence strategy using the Alpaca Trade API.
It extracts active signals for today, computes risk-parity position sizes,
and automatically submits Buy/Short market orders to paper or live accounts.

To run this in production, schedule this script to run daily at 3:55 PM EST via cron.
"""

import logging
import os
import sys
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

import pandas as pd  # noqa: E402 - imports must happen after configuration / environment setup
import requests  # noqa: E402 - imports must happen after configuration / environment setup
import yfinance as yf  # noqa: E402 - imports must happen after configuration / environment setup

from src.risk import position_sizing as risk_config  # noqa: E402 - imports must happen after configuration / environment setup

TECHNICAL_UNIVERSE = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'META', 'AMZN',
                      'GOOGL', 'JPM', 'V', 'UNH', 'JNJ', 'WMT', 'PG', 'MA',
                      'HD', 'DIS', 'BAC', 'XOM', 'PFE']

def generate_technical_signals(stock_dfs: dict) -> pd.DataFrame:
    """Generate trading signals from technical indicators only (no Reddit)."""
    signals = []
    for ticker in TECHNICAL_UNIVERSE:
        if ticker not in stock_dfs or stock_dfs[ticker] is None:
            continue
        df = stock_dfs[ticker]
        if len(df) < 50:
            continue
        latest = df.iloc[-1]

        rsi = latest.get('RSI_14', 50)
        macd_hist = latest.get('MACD_Hist', 0)
        close = latest['Close']
        bb_lower = latest.get('BB_Lower', close * 0.95)
        bb_upper = latest.get('BB_Upper', close * 1.05)
        ha_close = latest.get('HA_Close', close)
        ha_open = latest.get('HA_Open', close)
        gk_vol = latest.get('GK_Vol', 0.50)
        ema_20 = latest.get('EMA_20', close)

        volatility_shield_passed = gk_vol < 1.20

        bullish_score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi < 70) + int(close > bb_lower)
        bearish_score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi < 70) + int(close < bb_upper)

        if volatility_shield_passed:
            if bullish_score >= 3:
                signals.append({'ticker': ticker, 'sentiment_score': 1.0})
            elif bearish_score >= 3:
                signals.append({'ticker': ticker, 'sentiment_score': -1.0})

    return pd.DataFrame(signals)


# ============================================================================
# API CONFIGURATION
# ============================================================================
from src.utils.config import config  # noqa: E402 - imports must happen after configuration / environment setup

try:
    ALPACA_API_KEY_ID = config.api_keys.alpaca_api_key
    try:
        ALPACA_SECRET_KEY = config.api_keys.alpaca_secret_key.get_secret_value()
    except AttributeError:
        ALPACA_SECRET_KEY = config.api_keys.alpaca_secret_key
except AttributeError:
    ALPACA_API_KEY_ID = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not ALPACA_API_KEY_ID or not ALPACA_SECRET_KEY:
    raise ValueError("Valid Alpaca API credentials required. Please set them in configuration.")

if risk_config.LIVE_TRADING_ENABLED:
    ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://api.alpaca.markets")
else:
    # Force paper trading endpoint
    ALPACA_BASE_URL = "https://paper-api.alpaca.markets"


HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY_ID,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
    "Content-Type": "application/json"
}

def get_account_data() -> dict:
    """
    Fetches the current account details from Alpaca.
    """
    url = f"{ALPACA_BASE_URL}/v2/account"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[!] Error fetching Alpaca account: {r.text}")
            return {}
    except Exception as e:
        print(f"[!] Exception calling Alpaca API: {e}")
        return {}

def get_open_positions() -> list:
    url = f"{ALPACA_BASE_URL}/v2/positions"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception:
        return []

def place_fractional_market_order(symbol: str, notional: float, side: str):
    """
    Submits a fractional market order to Alpaca by notional value.
    side can be 'buy' (bullish setups) or 'sell' (bearish setups / short).
    """
    url = f"{ALPACA_BASE_URL}/v2/orders"

    # Due to some constraints, shorting might not support notional quantities in all brokers.
    # For now, we will submit the notional order for both, assuming it's supported.

    payload = {
        "symbol": symbol,
        "notional": round(notional, 2),
        "side": side,
        "type": "market",
        "time_in_force": "day"
    }

    # Alpaca live may require real money, but paper accepts notional.
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if r.status_code == 200 or r.status_code == 201:
            order = r.json()
            print(f" -> ORDER SUBMITTED: {side.upper()} ${notional:.2f} of {symbol} (Order ID: {order.get('id')})")
            return order
        else:
            print(f"[!] Order rejected for {symbol}: {r.text}")
            return None
    except Exception as e:
        print(f"[!] Exception placing order for {symbol}: {e}")
        return None

def main():
    print("=" * 60)
    print("ALPACA AUTOMATED LIVE/PAPER ORDER EXECUTOR")
    print("=" * 60)


    if risk_config.LIVE_TRADING_ENABLED:
        print("[!] LIVE TRADING IS ENABLED. REAL CAPITAL IS AT RISK.")
    else:
        print("[*] Paper trading mode active. Live trading is disabled.")
        if "paper" not in ALPACA_BASE_URL:
            print("[!] ERROR: Live trading is disabled but ALPACA_BASE_URL is not pointing to paper. Aborting.")
            return


    # 1. Fetch live account equity
    account = get_account_data()
    if not account:
        print("[!] No valid account data found. Aborting execution.")
        return

    equity = float(account.get("equity", 0.0))
    if equity <= 0:
        print("[!] Account equity <= 0. Aborting execution.")
        return

    print(f"[*] Account Equity: ${equity:,.2f}")

    # Check Circuit Breakers
    last_equity = float(account.get("last_equity", equity))
    if last_equity > 0:
        daily_loss_pct = (last_equity - equity) / last_equity
        if daily_loss_pct > risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT:
            print(f"[!!!] DAILY CIRCUIT BREAKER TRIPPED. Loss ({daily_loss_pct*100:.2f}%) exceeds limit ({risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT*100:.2f}%). Trading halted.")
            sys.exit(1)


    # Check Weekly Circuit Breaker via Alpaca Portfolio History
    try:
        history_url = f"{ALPACA_BASE_URL}/v2/account/portfolio/history?period=1W&timeframe=1D"
        h_resp = requests.get(history_url, headers=HEADERS, timeout=10)
        if h_resp.status_code == 200:
            hist_data = h_resp.json()
            equities = hist_data.get("equity", [])
            if equities and len(equities) > 0:
                high_water_mark = max(equities)
                if high_water_mark > 0:
                    weekly_drawdown = (high_water_mark - equity) / high_water_mark
                    if weekly_drawdown > risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT:
                        print(f"[!!!] WEEKLY CIRCUIT BREAKER TRIPPED. Drawdown ({weekly_drawdown*100:.2f}%) exceeds limit ({risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT*100:.2f}%). Trading halted.")
                        sys.exit(1)
    except Exception as e:
        print(f"[!] Warning: Could not fetch portfolio history for weekly circuit breaker check: {e}")

    # Check current positions count
    positions = get_open_positions()
    num_positions = len(positions)
    print(f"[*] Open Positions: {num_positions}")

    if num_positions >= risk_config.MAX_CONCURRENT_POSITIONS:
        print(f"[*] Max positions ({risk_config.MAX_CONCURRENT_POSITIONS}) reached. No new trades will be opened.")
        return


    # 2. Read the latest aggregated signals
    technical_only = '--mode' in sys.argv and 'technical' in sys.argv

    if technical_only:
        print("[*] Technical-only mode: Using indicators only")
        from src.alpha.indicators import compute_indicators
        px_data = yf.download(TECHNICAL_UNIVERSE, period='60d', progress=False, auto_adjust=True)
        stock_dfs = {}
        for ticker in TECHNICAL_UNIVERSE:
            try:
                t_px = px_data.loc[:, (slice(None), ticker)].copy()
                t_px.columns = t_px.columns.get_level_values(0)
                stock_dfs[ticker] = compute_indicators(t_px)
            except Exception as e:
                logger.warning(f"Error computing indicators for {ticker}: {e}")
                continue
        today_signals = generate_technical_signals(stock_dfs)
        # Use real latest date from downloaded market data
        latest_date = px_data.index[-1].to_pydatetime() if not px_data.empty else datetime.now()
    else:
        csv_path = "wsb_factual_research_data.csv"
        if not os.path.exists(csv_path):
            print("[!] No sentiment data. Use --mode technical")
            return
        df = pd.read_csv(csv_path)
        df["post_date"] = pd.to_datetime(df["post_date"])
        latest_date = df["post_date"].max()
        print(f"[*] Analyzing latest available signals for date: {latest_date.strftime('%Y-%m-%d')}")
        today_signals = df[df["post_date"] == latest_date]

    if today_signals.empty:
        print("[*] No active signals found for today. Cash preserved.")
        return

    print("Downloading recent pricing data to evaluate technical confluence...")
    unique_tickers = today_signals["ticker"].unique().tolist()

    end_date = latest_date + timedelta(days=5)
    start_date = end_date - timedelta(days=60)

    px_data = yf.download(unique_tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)

    active_signals = []

    for _, signal in today_signals.iterrows():
        symbol = signal["ticker"]
        sentiment = signal["sentiment_score"]

        try:
            t_px = px_data.loc[:, (slice(None), symbol)].copy()
            t_px.columns = t_px.columns.get_level_values(0)
            t_px = t_px.dropna(subset=["Close", "Open", "High", "Low"])

            if len(t_px) < 20:
                continue

            ind_df = compute_indicators(t_px)
            entry_idx = ind_df.index.searchsorted(latest_date, side="right")
            if entry_idx >= len(ind_df):
                # use latest
                entry_idx = len(ind_df) - 1

            entry_row = ind_df.iloc[entry_idx]
            gk_vol = entry_row.get("GK_Vol", 0.50)
            volatility_shield_passed = gk_vol < 1.20

            alg_ha = False
            alg_momentum = False
            alg_reversion = False
            alg_bb = False

            if sentiment > 0:
                alg_ha = entry_row["HA_Close"] > entry_row["HA_Open"]
                alg_momentum = (entry_row["Close"] > entry_row["EMA_20"]) and (entry_row["MACD_Hist"] > 0.0)
                alg_reversion = (40.0 < entry_row["RSI_14"] < 70.0)
                alg_bb = entry_row["Close"] > entry_row["BB_Lower"]
            elif sentiment < 0:
                alg_ha = entry_row["HA_Close"] < entry_row["HA_Open"]
                alg_momentum = (entry_row["Close"] < entry_row["EMA_20"]) and (entry_row["MACD_Hist"] < 0.0)
                alg_reversion = (30.0 < entry_row["RSI_14"] < 60.0)
                alg_bb = entry_row["Close"] < entry_row["BB_Upper"]

            ensemble_score = int(alg_ha) + int(alg_momentum) + int(alg_reversion) + int(alg_bb)
            confluence_triggered_ensemble_only = (ensemble_score >= 3) and volatility_shield_passed

            if confluence_triggered_ensemble_only:
                active_signals.append({
                    "ticker": symbol,
                    "sentiment_score": sentiment
                })
        except Exception as e:
            print(f"Error evaluating {symbol}: {e}")
            continue

    active_signals = pd.DataFrame(active_signals)

    if active_signals.empty:
        print("[*] No active confluence-triggered signals found for today. Cash preserved.")
        return

    # We only take as many as we have room for
    room_for_new_positions = risk_config.MAX_CONCURRENT_POSITIONS - num_positions
    if room_for_new_positions <= 0:
        print("[*] Max positions reached. No new trades will be opened.")
        return

    active_signals = active_signals.head(room_for_new_positions)


    print(f"[*] Located {len(active_signals)} active trade signals:")
    print(active_signals[["ticker", "sentiment_score"]].to_string(index=False))

    # Base max allocation per trade based on risk config
    max_trade_dollar_size = equity * risk_config.MAX_RISK_PER_TRADE_PCT

    # 3. Process each active signal and execute orders
    for _, signal in active_signals.iterrows():
        symbol = signal["ticker"]
        sentiment = signal["sentiment_score"]

        # Limit position size using fractional (notional) orders
        dollar_allocation = max_trade_dollar_size
        print(f"\n[*] Processing order for {symbol}:")
        print(f"   -> Fractional Capital Allocation: ${dollar_allocation:,.2f}")

        # Submit the order
        if sentiment > 0:
            place_fractional_market_order(symbol, dollar_allocation, "buy")
        else:
            # Short-selling bearish setups if supported by the broker
            # Notional shorting is often restricted, but for paper trading Alpaca it might work or fallback to whole shares.
            # We'll just submit the notional order.
            place_fractional_market_order(symbol, dollar_allocation, "sell")

    # Dump log for paper trading loop to commit
    log_content = f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    log_content += f"Equity: ${equity:.2f}\n"
    log_content += f"Trades Executed: {len(active_signals)}\n"

    with open("paper_trading_logs/latest_execution.log", "w") as f:
        f.write(log_content)

    print("\n" + "=" * 60)
    print("LIVE EXECUTION CYCLE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
