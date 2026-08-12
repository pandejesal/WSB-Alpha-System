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
