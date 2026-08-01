import pandas as pd
import numpy as np

def compute_indicators(df):
    if len(df) < 20:
        return None
    df = df.copy()

    # 20 EMA
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()

    # 14 ATR (Average True Range)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR_14'] = true_range.rolling(14).mean()

    # 14 RSI
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["RSI_14"] = 100 - (100 / (1 + rs))

    # MACD
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # Heikin-Ashi
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha_open = np.zeros(len(df))
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + df["HA_Close"].iloc[i-1]) / 2.0
    df["HA_Open"] = ha_open
    df["HA_High"] = df[["High", "HA_Open", "HA_Close"]].max(axis=1)
    df["HA_Low"] = df[["Low", "HA_Open", "HA_Close"]].min(axis=1)

    # Bollinger Bands
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    df["BB_Std"] = df["Close"].rolling(window=20).std().fillna(1e-4)
    df["BB_Upper"] = df["BB_Middle"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2.0 * df["BB_Std"]
    df["BB_Middle"] = df["BB_Middle"].fillna(df["Close"])
    df["BB_Upper"] = df["BB_Upper"].fillna(df["Close"] * 1.05)
    df["BB_Lower"] = df["BB_Lower"].fillna(df["Close"] * 0.95)

    # Garman-Klass Volatility
    safe_high = df["High"].replace(0, 0.01)
    safe_low = df["Low"].replace(0, 0.01)
    safe_close = df["Close"].replace(0, 0.01)
    safe_open = df["Open"].replace(0, 0.01)

    log_hl = np.log(safe_high / safe_low)
    log_co = np.log(safe_close / safe_open)
    gk_element = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk_variance = gk_element.rolling(window=20).mean()
    gk_variance = gk_variance.clip(lower=1e-10)
    df["GK_Vol"] = np.sqrt(252 * gk_variance)
    first_valid = df["GK_Vol"].dropna().iloc[0] if len(df["GK_Vol"].dropna()) > 0 else 0.50
    df["GK_Vol"] = df["GK_Vol"].fillna(first_valid)

    # VaR and CVaR (Rolling 20-day 95%)
    daily_pct_returns = df["Close"].pct_change().fillna(0)
    rolling_var = []
    rolling_cvar = []
    for i in range(len(df)):
        if i < 20:
            rolling_var.append(0.02)
            rolling_cvar.append(0.04)
        else:
            window_rets = daily_pct_returns.iloc[i-19:i+1]
            sorted_rets = np.sort(window_rets.values)
            var_idx = max(0, int(0.05 * len(sorted_rets)) - 1) if len(sorted_rets) == 20 else int(0.05 * len(sorted_rets))
            var_val = -sorted_rets[var_idx] if var_idx < len(sorted_rets) else 0.02
            losses_below_var = sorted_rets[:var_idx+1]
            cvar_val = -losses_below_var.mean() if len(losses_below_var) > 0 else 0.04
            rolling_var.append(max(var_val, 0.0))
            rolling_cvar.append(max(cvar_val, 0.0))

    df["VaR_95"] = rolling_var
    df["CVaR_95"] = rolling_cvar
    return df

def compute_regime_returns(ind_df, spy_close, entry_idx, entry_px, spy_entry_px, sentiment_score, holding_days):
    target_regime_idx = entry_idx + holding_days

    # Calculate slippage based on ATR at entry
    atr_val = ind_df["ATR_14"].iloc[entry_idx] if "ATR_14" in ind_df.columns and not pd.isna(ind_df["ATR_14"].iloc[entry_idx]) else entry_px * 0.01

    # Base slippage is 5% of 14-day ATR
    raw_slippage = atr_val * 0.05

    # Clamp slippage between 0.1% and 2.5% of stock price
    min_slippage = entry_px * 0.001
    max_slippage = entry_px * 0.025
    slippage_penalty = max(min_slippage, min(max_slippage, raw_slippage))

    # Apply penalty adversely to entry price
    if sentiment_score > 0:
        actual_entry_px = entry_px + slippage_penalty
    else:
        actual_entry_px = entry_px - slippage_penalty

    if target_regime_idx < len(ind_df):
        regime_exit_date = ind_df.index[target_regime_idx]
        regime_exit_px = ind_df["Close"].iloc[target_regime_idx]
        regime_spy_exit_px = spy_close.loc[regime_exit_date] if regime_exit_date in spy_close.index else spy_close.iloc[min(spy_close.index.searchsorted(regime_exit_date, side="left"), len(spy_close)-1)]

        # Apply slippage on exit as well
        if sentiment_score > 0:
            actual_exit_px = regime_exit_px - slippage_penalty
        else:
            actual_exit_px = regime_exit_px + slippage_penalty

        regime_stock_ret = (actual_exit_px - actual_entry_px) / actual_entry_px if sentiment_score > 0 else (actual_entry_px - actual_exit_px) / actual_entry_px
        regime_spy_ret = (regime_spy_exit_px - spy_entry_px) / spy_entry_px if sentiment_score > 0 else (spy_entry_px - regime_spy_exit_px) / spy_entry_px
    else:
        # Fallback if history ends before holding period exits
        regime_exit_px = ind_df["Close"].iloc[-1]

        # Apply slippage on exit
        if sentiment_score > 0:
            actual_exit_px = regime_exit_px - slippage_penalty
        else:
            actual_exit_px = regime_exit_px + slippage_penalty

        regime_stock_ret = (actual_exit_px - actual_entry_px) / actual_entry_px if sentiment_score > 0 else (actual_entry_px - actual_exit_px) / actual_entry_px
        regime_spy_ret = (spy_close.iloc[-1] - spy_entry_px) / spy_entry_px if sentiment_score > 0 else (spy_entry_px - spy_close.iloc[-1]) / spy_entry_px

    return regime_stock_ret, regime_spy_ret
