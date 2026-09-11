import numpy as np
import pandas as pd


def safe_sharpe(returns_series, periods=252):
    """
    Computes Sharpe ratio safely, guarding against near-zero standard deviation
    which causes astronomical results.
    """
    if isinstance(returns_series, list) or not isinstance(returns_series, pd.Series):
        returns_series = pd.Series(returns_series)

    returns_series = returns_series.fillna(0)

    if len(returns_series) < 2:
        return 0.0

    std = returns_series.std()
    if std < 1e-12:
        return 0.0

    mean = returns_series.mean()
    return float((mean / std) * np.sqrt(periods))

def safe_sortino(returns_series, periods=252):
    """
    Computes Sortino ratio safely.
    """
    if isinstance(returns_series, list) or not isinstance(returns_series, pd.Series):
        returns_series = pd.Series(returns_series)

    returns_series = returns_series.fillna(0)

    if len(returns_series) < 2:
        return 0.0

    downside_diff = returns_series.clip(upper=0.0)
    downside_std = np.sqrt(np.mean(downside_diff ** 2))
    if downside_std < 1e-12:
        return 0.0

    mean = returns_series.mean()
    return float((mean / downside_std) * np.sqrt(periods))


# W12: Vol-regime overlay proxy (daily vol-of-vol, VIX read-only tagging)
# Daily vol-of-vol: 20d realized vol vs 60d median. No intraday feed.
# Scale: vol <0.8*median -> 1.5x, vol >1.4*median -> 0.5x (or flat 0.5x), else 1.0.
# VIX is read-only for regime labeling (low<15, normal 15-25, high 25-35, extreme>35),
# never used to scale positions. Proxy captures 40-60% of realized variance
# concentration per Barndorff-Nielsen; cannot capture intraday gap risk.
def vol_regime_scale(close: pd.Series, vol_window: int = 20,
                     median_window: int = 60,
                     low_thresh: float = 0.8, high_thresh: float = 1.4,
                     low_scale: float = 1.5, high_scale: float = 0.5) -> pd.Series:
    """Daily vol-of-vol overlay scale. Pure daily OHLCV, no intraday."""
    try:
        ret = close.pct_change()
        vol = ret.rolling(int(vol_window)).std()
        vol_med = vol.rolling(int(median_window)).median()
        ratio = vol / vol_med.replace(0, np.nan)
        scale = pd.Series(1.0, index=close.index)
        scale[ratio < low_thresh] = low_scale
        scale[ratio > high_thresh] = high_scale
        return scale.fillna(1.0)
    except Exception:  # noqa: BLE001
        return pd.Series(1.0, index=close.index)


def vix_regime_tag(vix_close: pd.Series) -> pd.Series:
    """Read-only VIX regime tagging. No position scaling, tagging only."""
    try:
        bins = [0, 15, 25, 35, 1e9]
        labels = ["low", "normal", "high", "extreme"]
        return pd.cut(vix_close, bins=bins, labels=labels)
    except Exception:  # noqa: BLE001
        return pd.Series("normal", index=vix_close.index)
