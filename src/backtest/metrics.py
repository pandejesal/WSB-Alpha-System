import numpy as np
import pandas as pd

def safe_sharpe(returns_series, periods=252):
    """
    Computes Sharpe ratio safely, guarding against near-zero standard deviation
    which causes astronomical results.
    """
    if isinstance(returns_series, list):
        returns_series = pd.Series(returns_series)
    elif not isinstance(returns_series, pd.Series):
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
    if isinstance(returns_series, list):
        returns_series = pd.Series(returns_series)
    elif not isinstance(returns_series, pd.Series):
        returns_series = pd.Series(returns_series)

    returns_series = returns_series.fillna(0)

    if len(returns_series) < 2:
        return 0.0

    downside_rets = returns_series[returns_series < 0]
    if len(downside_rets) == 0:
        return 0.0

    downside_std = downside_rets.std()
    if downside_std < 1e-12:
        return 0.0

    mean = returns_series.mean()
    return float((mean / downside_std) * np.sqrt(periods))
