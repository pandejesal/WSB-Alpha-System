"""
🤖 Live Bybit Perpetual Broker Execution Template: Man AHL Multi-Horizon Momentum

This script is a production-ready template that automates daily execution
of our Man AHL Crypto Momentum strategy on Bybit USDT-Margined Perpetuals.
It securely fetches active signals for today, calculates risk-adjusted
position sizes (35% target risk, half-Kelly), and automatically submits Long/Short
market orders to paper or live Bybit perpetual accounts via ccxt.

Error handling explicitly catches ccxt.InsufficientFunds and ccxt.InvalidOrder,
gracefully scaling down or adjusting sizes if the exchange rejects our orders.

To run this in production, schedule this script to run daily at 00:01 UTC via cron:
$ python live_crypto_executor.py
"""

import os

import ccxt
import pandas as pd
from dotenv import load_dotenv
import risk_config
import json

from strategy_man_ahl import (
    calculate_momentum_score,
    calculate_target_position_sizes,
    calculate_volatility_and_atr,
    check_rebalance_required,
)

# Load environment variables
load_dotenv()

# ============================================================================
# BYBIT CONFIGURATION
# ============================================================================
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
USE_SANDBOX = not risk_config.LIVE_TRADING_ENABLED

TICKERS = ["BTC-USD", "ETH-USD", "SOL-USD"]
# Map yfinance-style tickers to Bybit Perpetual linear symbols
BYBIT_SYMBOLS = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "SOL-USD": "SOLUSDT"
}

# Target risk parameters matching backtest
TARGET_RISK = risk_config.MAX_POSITION_SIZE_PCT
HALF_KELLY = 0.5
LEVERAGE_CAP = 1.0 # Force leverage cap for safety
MIN_ORDER_SIZE = 10.0  # Bybit floor minimum position size $10

def init_bybit_exchange() -> ccxt.bybit:
    """
    Initializes Bybit linear perpetual connection via ccxt.
    """
    exchange_params = {
        'apiKey': BYBIT_API_KEY,
        'secret': BYBIT_API_SECRET,
        'options': {
            'defaultType': 'linear',  # Use linear USDT-margined perpetuals
        }
    }

    exchange = ccxt.bybit(exchange_params)
    if USE_SANDBOX:
        exchange.set_sandbox_mode(True)
        print("[*] Initializing Bybit in SANDBOX (testnet) mode.")
    else:
        print("[*] Initializing Bybit in PRODUCTION (live) mode.")
    return exchange

def fetch_account_equity(exchange: ccxt.bybit) -> float:
    """
    Fetches the total equity (wallet balance + unrealized PnL) of the USDT account.
    """
    try:
        balance = exchange.fetch_balance()
        # Get equity from USDT balance section
        usdt_info = balance.get('USDT', {})
        equity = float(usdt_info.get('equity', usdt_info.get('total', 0.0)))
        return equity
    except Exception as e:  # noqa: BLE001
        print(f"[!] Exception fetching account equity: {e}")
        return 0.0

def fetch_historical_ohlcv(exchange: ccxt.bybit, symbol: str, limit: int = 100) -> pd.DataFrame:
    """
    Fetches daily historical OHLCV data directly from Bybit exchange to calculate indicators.
    """
    try:
        # Fetch daily timeframe candles
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=limit)
        df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:  # noqa: BLE001
        print(f"[!] Exception fetching OHLCV for {symbol}: {e}")
        return pd.DataFrame()

def get_current_positions_and_scores(exchange: ccxt.bybit) -> tuple[dict, dict, dict]:
    """
    Fetch active scores, volatilities, and current positions on exchange.
    """
    current_positions = {t: 0.0 for t in TICKERS}
    today_scores = {}
    today_vols = {}

    # 1. Fetch current live positions
    try:
        positions = exchange.fetch_positions(symbols=list(BYBIT_SYMBOLS.values()))
        for pos in positions:
            symbol = pos.get('symbol')
            # Map Bybit linear symbol back to ticker
            ticker = None
            for tk, sym in BYBIT_SYMBOLS.items():
                if sym == symbol:
                    ticker = tk
                    break

            if ticker:
                size = float(pos.get('contracts', 0.0))
                price = float(pos.get('entryPrice', 0.0))
                side = pos.get('side', '').lower()

                # Position value in USDT
                position_val = size * price
                if side == 'short':
                    position_val = -position_val
                current_positions[ticker] = position_val
    except Exception as e:  # noqa: BLE001
        print(f"[!] Error fetching positions: {e}. Defaulting current positions to 0.")

    # 2. Fetch daily OHLCV and compute indicators
    for ticker in TICKERS:
        symbol = BYBIT_SYMBOLS[ticker]
        df = fetch_historical_ohlcv(exchange, symbol, limit=60)
        if not df.empty:
            df = calculate_volatility_and_atr(df)
            df["Momentum_Score"] = calculate_momentum_score(df["Close"])

            # Extract latest available daily close state
            latest_row = df.iloc[-1]
            today_scores[ticker] = float(latest_row["Momentum_Score"])
            today_vols[ticker] = float(latest_row["Vol_20d"])
        else:
            print(f" [!] Empty daily candles for {symbol}, skipping signal generation.")
            today_scores[ticker] = 0.0
            today_vols[ticker] = 0.50

    return current_positions, today_scores, today_vols

def execute_bybit_order(exchange: ccxt.bybit, symbol: str, target_size: float, current_pos: float):
    """
    Submits market orders to reach the target dollar size.
    Gracefully handles ccxt.InsufficientFunds and ccxt.InvalidOrder exceptions.
    """
    # Linear contracts require quantity in asset units (e.g. BTC contracts, SOL contracts)
    # Fetch current ticker price to convert dollar target into quantity
    try:
        ticker_info = exchange.fetch_ticker(symbol)
        last_price = float(ticker_info.get('last', 0.0))
        if last_price <= 0:
            print(f"  [!] Invalid market price for {symbol}: {last_price}. Skipping order.")
            return
    except Exception as e:  # noqa: BLE001
        print(f"  [!] Failed to download current price for {symbol}: {e}. Skipping.")
        return

    # Calculate desired quantity
    _target_qty = abs(target_size) / last_price
    _current_qty = abs(current_pos) / last_price

    # Check side: long or short

    # Determine order action
    # For perpetual linear, we submit BUY order to open long or close short,
    # and SELL order to open short or close long.
    # To keep code clean and general, we calculate net quantity difference:
    net_qty = target_size / last_price - current_pos / last_price

    if abs(net_qty) * last_price < 1.0:
        print(f"  [*] Net order size too small (${abs(net_qty)*last_price:.2f}), skipping.")
        return

    side = 'buy' if net_qty > 0 else 'sell'
    qty = abs(net_qty)

    print("  [*] Preparing to submit Market Order:")
    print(f"      -> Symbol:         {symbol}")
    print(f"      -> Action:         {side.upper()}")
    print(f"      -> Dollar Size:    ${abs(net_qty) * last_price:.2f}")
    print(f"      -> Quantity:       {qty:.5f}")

    try:
        # Submit the order
        order = exchange.create_market_order(symbol, side, qty)
        print(f"  [+] ORDER SUCCESSFUL! Order ID: {order.get('id')}")
    except ccxt.InsufficientFunds as e:
        print(f"  [!] ccxt.InsufficientFunds caught: {e}")
        print("      Attempting graceful size recovery: Halving order size and retrying...")
        try:
            half_qty = qty * 0.5
            if half_qty * last_price >= MIN_ORDER_SIZE:
                order = exchange.create_market_order(symbol, side, half_qty)
                print(f"      [+] RECOVERY SUCCESSFUL! Halved Order ID: {order.get('id')}")
            else:
                print("      [!] Recovered size falls below exchange minimum ($10). Aborting order.")
        except Exception as err:  # noqa: BLE001
            print(f"      [!] Recovery attempt failed: {err}")
    except ccxt.InvalidOrder as e:
        print(f"  [!] ccxt.InvalidOrder caught: {e}")
        print("      Attempting size normalization to minimum floor limit ($10) and retrying...")
        try:
            min_floor_qty = MIN_ORDER_SIZE / last_price
            order = exchange.create_market_order(symbol, side, min_floor_qty)
            print(f"      [+] RECOVERY SUCCESSFUL! Normalized Order ID: {order.get('id')}")
        except Exception as err:  # noqa: BLE001
            print(f"      [!] Recovery attempt failed: {err}")
    except Exception as e:  # noqa: BLE001
        print(f"  [!] Uncaught broker exception placing order: {e}")

def main():
    STATE_FILE = 'crypto_state.json'
    if USE_SANDBOX == False and risk_config.LIVE_TRADING_ENABLED == False:
        print("[!] ERROR: LIVE_TRADING_ENABLED is False but sandbox is false. Aborting for safety.")
        return

    print("=" * 60)
    print("BYBIT SYSTEMATIC CRYPTO MOMENTUM EXECUTIVE CYCLE")
    print("=" * 60)

    # 1. Initialize exchange connection
    if not BYBIT_API_KEY or not BYBIT_API_SECRET:
        print("[!] Missing BYBIT_API_KEY or BYBIT_API_SECRET in environment. Aborting.")
        return

    exchange = init_bybit_exchange()

    # 2. Fetch live account equity
    equity = fetch_account_equity(exchange)
    if equity <= 0:
        print("[!] No valid wallet balance found on Bybit. Aborting execution.")
        return
    print(f"[*] Total Portfolio Account Equity: ${equity:,.2f}")

    # 3. Fetch active positions, scores, and volatilities
    print("[*] Retrieving live positions, daily close candles, and volatilities...")
    current_positions, today_scores, today_vols = get_current_positions_and_scores(exchange)





    # Fetch circuit breaker state / high water mark
    # For crypto, since we don't have alpaca's 1-week API endpoint easily, we track equity in state.
    state_equity = equity
    high_water_mark = equity
    last_equity = equity
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state_data = json.load(f)
                last_equity = state_data.get("last_equity", equity)
                high_water_mark = state_data.get("high_water_mark", equity)
        except Exception:
            pass

    # Update high water mark
    if equity > high_water_mark:
        high_water_mark = equity

    # Check Circuit Breakers
    if last_equity > 0:
        daily_loss_pct = (last_equity - equity) / last_equity
        if daily_loss_pct > risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT:
            print(f"[!!!] DAILY CIRCUIT BREAKER TRIPPED. Loss ({daily_loss_pct*100:.2f}%) exceeds limit ({risk_config.DAILY_LOSS_CIRCUIT_BREAKER_PCT*100:.2f}%). Trading halted.")
            return

    if high_water_mark > 0:
        weekly_drawdown = (high_water_mark - equity) / high_water_mark
        if weekly_drawdown > risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT:
            print(f"[!!!] WEEKLY/MAX CIRCUIT BREAKER TRIPPED. Drawdown ({weekly_drawdown*100:.2f}%) exceeds limit ({risk_config.WEEKLY_LOSS_CIRCUIT_BREAKER_PCT*100:.2f}%). Trading halted.")
            return

    active_pos_count = sum(1 for p in current_positions.values() if abs(p) > 0)
    if active_pos_count >= risk_config.MAX_CONCURRENT_POSITIONS:
        print(f"[*] Max positions ({risk_config.MAX_CONCURRENT_POSITIONS}) reached or exceeded.")

    print("\n[*] Current Live Positions (Dollar Values):")
    for ticker, pos in current_positions.items():
        print(f"  -> {ticker}: ${pos:,.2f}")

    print("\n[*] Momentum Signals Generated Today:")
    for ticker, score in today_scores.items():
        print(f"  -> {ticker}: Score={score:.1f}, Vol_20d={today_vols[ticker]:.2%}")

    # 4. Sizing Calculations
    print("\n[*] Running Target Size Optimizer...")
    target_sizes = calculate_target_position_sizes(
        scores=today_scores,
        volatilities=today_vols,
        equity=equity,
        target_risk=TARGET_RISK,
        half_kelly=HALF_KELLY,
        leverage_cap=LEVERAGE_CAP,
        min_order_size=MIN_ORDER_SIZE
    )

    print("\n[*] Target Portfolio Sizing Optimized:")
    for ticker, size in target_sizes.items():
         print(f"  -> {ticker}: Target Size = ${size:,.2f}")

    # 5. Check Rebalance Requirements
    # Note: We track yesterday's score from the session/config if available.
    # In live execution, we can use 0 or load historical score from previous run.
    # To be conservative, we pass today's score as previous score if it's the first run,
    # or let the rebalance engine analyze size drifts.


    prev_scores = {ticker: 0.0 for ticker in TICKERS}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "scores" in loaded:
                    prev_scores = loaded["scores"]
                elif isinstance(loaded, dict):
                    prev_scores = loaded # fallback for old schema
        except Exception:
            pass

    rebalance_required = check_rebalance_required(
        current_positions=current_positions,
        target_sizes=target_sizes,
        scores=today_scores,
        prev_scores=prev_scores,
        min_change=MIN_ORDER_SIZE
    )

    # 6. Execute Orders on exchange
    print("\n[*] Executing required portfolio adjustments:")
    for ticker, required in rebalance_required.items():
        symbol = BYBIT_SYMBOLS[ticker]
        current_pos = current_positions[ticker]
        target_size = target_sizes[ticker]

        if required:
            print(f"\n[*] Rebalancing {ticker}:")
            execute_bybit_order(exchange, symbol, target_size, current_pos)
        else:
            print(f"  -> {ticker}: Stay at current position (${current_pos:.2f}), drift is within tolerance.")

    # Save today's state and scores for next run
    try:
        state_out = {
            "scores": today_scores,
            "last_equity": equity,
            "high_water_mark": equity if 'high_water_mark' not in locals() else max(equity, high_water_mark)
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state_out, f)
    except Exception as e:
        print(f"Error saving state: {e}")

    print("\n" + "=" * 60)
    print("LIVE EXECUTIVE CYCLE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()
