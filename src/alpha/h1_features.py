import pandas as pd
import numpy as np


def compute_regime_features(df: pd.DataFrame, normalization: str = "zscore") -> pd.DataFrame:
    """
    Computes features for HMM regime detection:
    - sma20_slope
    - sma50_slope
    - realized_vol_20d
    - rsi_14d
    - vix_level
    """
    out = pd.DataFrame(index=df.index)

    # Make sure we have the required columns
    # We expect 'Close' for price and 'VIX' or 'vix_level' if provided
    # Fallback to defaults if missing (for testing)
    close_series = df["Close"] if "Close" in df.columns else df.iloc[:, 0]

    # 1. SMA Slopes
    sma20 = close_series.rolling(window=20).mean()
    sma50 = close_series.rolling(window=50).mean()

    # Calculate slope as the percentage change over 5 days (or 1 day, let's do 1 day for responsiveness)
    out["sma20_slope"] = sma20.pct_change()
    out["sma50_slope"] = sma50.pct_change()

    # 2. Realized Volatility 20d (annualized)
    daily_returns = close_series.pct_change()
    out["realized_vol_20d"] = daily_returns.rolling(window=20).std() * np.sqrt(252)

    # 3. RSI 14d
    delta = close_series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    out["rsi_14d"] = 100 - (100 / (1 + rs))

    # 4. VIX level
    if "VIX" in df.columns:
        out["vix_level"] = df["VIX"]
    elif "vix_level" in df.columns:
        out["vix_level"] = df["vix_level"]
    else:
        # Fallback if VIX is missing (e.g. synthetic data)
        out["vix_level"] = out["realized_vol_20d"] * 100  # proxy

    # Forward fill then drop remaining NaNs
    out = out.ffill().dropna()

    # Normalization
    if normalization == "zscore":
        out = (out - out.mean()) / (out.std() + 1e-8)
    elif normalization == "minmax":
        out = (out - out.min()) / (out.max() - out.min() + 1e-8)

    return out
