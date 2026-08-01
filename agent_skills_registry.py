import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
import functools
from google.genai import types

# ---------------------------------------------------------------------------
# SKILL: Fetch Microstructure
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=128)
def _fetch_yf_data(ticker: str, days: int) -> pd.DataFrame:
    # yfinance requires specific periods ('1mo', '3mo', '6mo', '1y', etc.)
    # We'll fetch '1y' to be safe and slice it down.
    df = yf.download(ticker, period="1y", progress=False)
    # yfinance sometimes returns MultiIndex columns if multiple tickers are passed
    # we just passed one, but handle just in case
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    # Slice the dataframe to exactly what we need (days + buffer for indicators)
    buffer = 30
    return df.tail(days + buffer).copy()

def skill_fetch_microstructure(ticker: str, days: int) -> dict:
    try:
        df = _fetch_yf_data(ticker, days)
        if df.empty:
            return {"error": f"No data found for {ticker}."}

        # Ensure we have required columns
        req_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in req_cols:
            if col not in df.columns:
                return {"error": f"Missing column {col} in data for {ticker}."}

        # Calculate 14-day ATR
        df['H-L'] = df['High'] - df['Low']
        df['H-C'] = np.abs(df['High'] - df['Close'].shift(1))
        df['L-C'] = np.abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()

        # Garman-Klass Volatility
        # sqrt( 0.5 * (ln(H/L))^2 - (2*ln(2)-1) * (ln(C/O))^2 )
        log_hl = np.log(df['High'] / df['Low'])
        log_co = np.log(df['Close'] / df['Open'])
        rs = 0.5 * log_hl**2 - (2 * np.log(2) - 1) * log_co**2
        # Avoid negative numbers inside sqrt due to floating point inaccuracies
        rs = np.maximum(rs, 0)
        df['Garman_Klass_Vol'] = np.sqrt(rs)

        # 5-bar liquidity sweep profile (recent lows/highs broken)
        df['Sweep_Low'] = df['Low'] < df['Low'].shift(1).rolling(5).min()
        df['Sweep_High'] = df['High'] > df['High'].shift(1).rolling(5).max()

        # Take the last 'days' rows
        recent_df = df.tail(days)

        return {
            "ticker": ticker,
            "latest_close": float(recent_df['Close'].iloc[-1]),
            "latest_atr": float(recent_df['ATR'].iloc[-1]),
            "avg_garman_klass_vol": float(recent_df['Garman_Klass_Vol'].mean()),
            "recent_liquidity_sweeps": {
                "low_sweeps": int(recent_df['Sweep_Low'].sum()),
                "high_sweeps": int(recent_df['Sweep_High'].sum())
            }
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# SKILL: Analyze Ledger MFE/MAE
# ---------------------------------------------------------------------------
def skill_analyze_ledger_mfe_mae() -> dict:
    try:
        conn = sqlite3.connect("trades.db")
        # Get the last 30 trades
        df = pd.read_sql_query("SELECT mfe_percent, mae_percent, pnl_percent FROM trades ORDER BY entry_time DESC LIMIT 30", conn)
        conn.close()

        if df.empty:
            return {"error": "No trades found in ledger."}

        avg_mfe = float(df['mfe_percent'].mean())
        avg_mae = float(df['mae_percent'].mean())
        avg_pnl = float(df['pnl_percent'].mean())
        win_rate = float((df['pnl_percent'] > 0).mean())

        return {
            "trades_analyzed": len(df),
            "avg_mfe_percent": avg_mfe,
            "avg_mae_percent": avg_mae,
            "avg_pnl_percent": avg_pnl,
            "win_rate": win_rate
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# SKILL: Run Sandbox Backtest
# ---------------------------------------------------------------------------
def skill_run_sandbox_backtest(cvar_threshold: float, stop_loss_atr: float, take_profit_atr: float) -> dict:
    try:
        # Fetch SPY for the backtest (standard proxy)
        df = _fetch_yf_data("SPY", 90) # fetch 90 days to simulate on 60 days

        if df.empty:
             return {"error": "Failed to fetch data for backtest."}

        # Calculate indicators
        # EMA fast (10) and slow (21)
        df['EMA_Fast'] = df['Close'].ewm(span=10, adjust=False).mean()
        df['EMA_Slow'] = df['Close'].ewm(span=21, adjust=False).mean()

        # MACD (12, 26, 9)
        df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']

        # ATR (14)
        df['H-L'] = df['High'] - df['Low']
        df['H-C'] = np.abs(df['High'] - df['Close'].shift(1))
        df['L-C'] = np.abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
        df['ATR'] = df['TR'].rolling(window=14).mean()

        # Daily returns for cVaR calculation
        df['Return'] = df['Close'].pct_change()

        # Take the last 60 days for actual backtest simulation
        bt_df = df.tail(60).copy()

        account_balance = 100.00
        max_risk = 1.00
        equity_curve = [account_balance]
        trades = []

        for i in range(len(bt_df)):
            if i < 20: continue # need some history for cVaR

            # Simple historical cVaR calculation (95% confidence)
            lookback = df['Return'].iloc[:df.index.get_loc(bt_df.index[i])]
            if len(lookback) < 20:
                continue

            var_95 = np.percentile(lookback.dropna(), 5)
            cvar_95 = lookback[lookback <= var_95].mean()

            # Reject trade if abs(cvar) > threshold
            if abs(cvar_95) > cvar_threshold:
                equity_curve.append(account_balance)
                continue

            # Entry logic: EMA crossover and MACD momentum
            ema_bullish = bt_df['EMA_Fast'].iloc[i] > bt_df['EMA_Slow'].iloc[i]
            macd_bullish = bt_df['MACD_Hist'].iloc[i] > 0

            if ema_bullish and macd_bullish:
                entry_price = float(bt_df['Close'].iloc[i])
                atr = float(bt_df['ATR'].iloc[i])

                # Position Sizing: Risk exactly $1.00
                qty = max_risk / (stop_loss_atr * atr)

                # Guardrail: Check purchasing power
                if (qty * entry_price) > account_balance:
                    qty = account_balance / entry_price

                # Simulate trade outcome (simplified next day resolution for sandbox)
                # In a real backtest this would walk forward
                if i + 1 < len(bt_df):
                    next_close = float(bt_df['Close'].iloc[i+1])
                    next_low = float(bt_df['Low'].iloc[i+1])
                    next_high = float(bt_df['High'].iloc[i+1])

                    stop_price = entry_price - (stop_loss_atr * atr)
                    tp_price = entry_price + (take_profit_atr * atr)

                    exit_price = next_close
                    pnl = 0.0

                    if next_low <= stop_price:
                        exit_price = stop_price
                    elif next_high >= tp_price:
                        exit_price = tp_price

                    pnl = (exit_price - entry_price) * qty
                    account_balance += pnl
                    trades.append(pnl)

            equity_curve.append(account_balance)

        if not trades:
            return {
                "sharpe_ratio": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "final_equity": round(account_balance, 2)
            }

        wins = [t for t in trades if t > 0]
        win_rate = len(wins) / len(trades)

        # Calculate Sharpe Ratio (simplified, assuming daily risk-free rate = 0)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        if np.std(returns) == 0:
            sharpe = 0.0
        else:
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)

        # Calculate Max Drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / peak
        max_dd = np.max(drawdown)

        return {
            "sharpe_ratio": round(sharpe, 4),
            "win_rate": round(win_rate, 4),
            "max_drawdown": round(max_dd, 4),
            "total_trades": len(trades),
            "final_equity": round(account_balance, 2)
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------------------------------------------------------------------
# GEMINI FUNCTION DECLARATIONS
# ---------------------------------------------------------------------------

fetch_microstructure_declaration = types.FunctionDeclaration(
    name="skill_fetch_microstructure",
    description="Fetches OHLCV data, calculates 14-day ATR, Garman-Klass Volatility, and a 5-bar liquidity sweep profile.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "ticker": types.Schema(
                type=types.Type.STRING,
                description="The stock ticker symbol (e.g. SPY)."
            ),
            "days": types.Schema(
                type=types.Type.INTEGER,
                description="Number of recent days to fetch microstructure data for."
            ),
        },
        required=["ticker", "days"]
    )
)

analyze_ledger_declaration = types.FunctionDeclaration(
    name="skill_analyze_ledger_mfe_mae",
    description="Connects to the SQLite trades.db and calculates the average MFE and MAE of the last 30 trades.",
)

run_sandbox_backtest_declaration = types.FunctionDeclaration(
    name="skill_run_sandbox_backtest",
    description="Runs a fast, vectorized backtest on the last 60 days of data using proposed parameters. Enforces $100 starting equity and maximum $1.00 risk per trade.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "cvar_threshold": types.Schema(
                type=types.Type.NUMBER,
                description="The cVaR threshold to reject trades (e.g., 0.15)."
            ),
            "stop_loss_atr": types.Schema(
                type=types.Type.NUMBER,
                description="The ATR multiplier for the stop loss (e.g., 1.5)."
            ),
            "take_profit_atr": types.Schema(
                type=types.Type.NUMBER,
                description="The ATR multiplier for the take profit (e.g., 2.0)."
            ),
        },
        required=["cvar_threshold", "stop_loss_atr", "take_profit_atr"]
    )
)

skills_tool = types.Tool(
    function_declarations=[
        fetch_microstructure_declaration,
        analyze_ledger_declaration,
        run_sandbox_backtest_declaration
    ]
)

# Registry mapping
skills_registry = {
    "skill_fetch_microstructure": skill_fetch_microstructure,
    "skill_analyze_ledger_mfe_mae": skill_analyze_ledger_mfe_mae,
    "skill_run_sandbox_backtest": skill_run_sandbox_backtest
}
