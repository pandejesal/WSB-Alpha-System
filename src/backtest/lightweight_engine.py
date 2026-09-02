"""
Lightweight Backtest Engine — pure pandas/numpy replacement for VectorBTEngine.

Replicates core VectorBTEngine behavior:
  - entries/exits from `signal` column (1=long, -1=short, 0=flat)
  - init_cash=100, fees=0.001, freq='1D'
  - returns dict: total_return, sharpe_ratio, max_drawdown, win_rate
"""

import numpy as np
import pandas as pd


def run_backtest(data: pd.DataFrame, strategy, init_cash: float = 100.0, fees: float = 0.001) -> dict:
    """
    Run a backtest using signals from a strategy object.

    Parameters
    ----------
    data : pd.DataFrame
        OHLCV data with columns: Open, High, Low, Close, Volume (and optionally Date).
        Index may be DatetimeIndex or RangeIndex.
    strategy : object
        Must have a `generate_signals(df) -> pd.DataFrame` method returning a copy
        with a `signal` column (1=long, -1=short, 0=flat).
    init_cash : float
        Initial cash amount (default 100).
    fees : float
        Transaction fee as fraction (default 0.001 = 0.1%).

    Returns
    -------
    dict with keys: total_return, sharpe_ratio, max_drawdown, win_rate, equity_curve
    """
    # Work on a copy
    df = data.copy()

    # Normalize column names to match expected format
    # Strategy may expect 'Close' (capitalized) but we should handle both
    if 'close' in df.columns and 'Close' not in df.columns:
        df = df.rename(columns={c: c.capitalize() for c in df.columns})

    # Ensure required columns exist
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Generate signals from strategy
    df = strategy.generate_signals(df)

    # Ensure signal column exists
    if 'signal' not in df.columns:
        raise ValueError("Strategy did not produce a 'signal' column")

    signal = df['signal'].fillna(0).astype(int)
    close = df['Close'].values
    n = len(close)

    # Build position series: signal indicates target position
    # 1 = long (buy next bar), -1 = short (short next bar), 0 = flat
    position = np.zeros(n, dtype=float)
    for i in range(n):
        if i == 0:
            position[i] = 0  # start flat
        else:
            position[i] = signal.iloc[i - 1]  # signal from previous bar

    # Calculate daily returns
    price_returns = np.zeros(n)
    for i in range(1, n):
        price_returns[i] = (close[i] - close[i - 1]) / close[i - 1]

    # Position changes (for fee calculation)
    position_change = np.abs(np.diff(position, prepend=0))

    # Strategy returns: position * price_return, minus fees on changes
    strategy_returns = np.zeros(n)
    for i in range(1, n):
        strategy_returns[i] = position[i - 1] * price_returns[i]  # PnL from holding
        strategy_returns[i] -= position_change[i] * fees  # fees on position changes

    # Equity curve
    equity = np.zeros(n)
    equity[0] = init_cash
    for i in range(1, n):
        equity[i] = equity[i - 1] * (1 + strategy_returns[i])

    # Calculate metrics
    total_return = (equity[-1] / equity[0]) - 1

    # Sharpe ratio (annualized, 252 trading days)
    daily_returns = strategy_returns[1:]
    if len(daily_returns) > 1 and np.std(daily_returns) > 1e-12:
        sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Max drawdown
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = float(np.min(drawdown))

    # Win rate
    winning_days = np.sum(daily_returns > 0)
    active_days = np.sum(daily_returns != 0)
    win_rate = winning_days / active_days if active_days > 0 else 0.0

    return {
        'total_return': float(total_return),
        'sharpe_ratio': float(sharpe),
        'max_drawdown': float(max_dd),
        'win_rate': float(win_rate),
        'equity_curve': equity.tolist(),
    }


def run_walk_forward(data: pd.DataFrame, strategy, train_window: int = 252, test_window: int = 63, fees: float = 0.001) -> dict:
    """
    Run walk-forward validation.

    Parameters
    ----------
    data : pd.DataFrame
        Full OHLCV dataset.
    strategy : object
        Strategy with generate_signals method.
    train_window : int
        Training window size in bars.
    test_window : int
        Test window size in bars.
    fees : float
        Transaction fee.

    Returns
    -------
    dict with aggregate metrics across all test windows.
    """
    n = len(data)
    all_returns = []

    start = 0
    while start + train_window + test_window <= n:
        # Test window (after train)
        test_start = start + train_window
        test_end = min(test_start + test_window, n)
        test_data = data.iloc[test_start:test_end]

        if len(test_data) < 2:
            break

        result = run_backtest(test_data, strategy, fees=fees)
        all_returns.extend(result.get('equity_curve', [1.0]))

        start += test_window  # rolling step

    if not all_returns:
        return {'total_return': 0, 'sharpe_ratio': 0, 'max_drawdown': 0, 'win_rate': 0}

    equity = np.array(all_returns)
    total_return = (equity[-1] / equity[0]) - 1 if equity[0] != 0 else 0

    daily_rets = np.diff(equity) / equity[:-1]
    if len(daily_rets) > 1 and np.std(daily_rets) > 1e-12:
        sharpe = (np.mean(daily_rets) / np.std(daily_rets)) * np.sqrt(252)
    else:
        sharpe = 0.0

    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_dd = float(np.min(drawdown))

    winning = np.sum(daily_rets > 0)
    active = np.sum(daily_rets != 0)
    win_rate = winning / active if active > 0 else 0.0

    return {
        'total_return': float(total_return),
        'sharpe_ratio': float(sharpe),
        'max_drawdown': float(max_dd),
        'win_rate': float(win_rate),
    }
