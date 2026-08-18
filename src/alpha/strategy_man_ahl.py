import logging

import numpy as np
import pandas as pd

from src.alpha.base_strategy import BaseStrategy


class ManAHLStrategy(BaseStrategy):
    def __init__(self, windows=None, vol_window=63):
        if windows is None:
            windows = [5, 10, 21, 42]
        self.windows = windows
        self.vol_window = vol_window
        self.logger = logging.getLogger(__name__)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < max(self.windows) + self.vol_window:
            self.logger.warning("Not enough data to compute Man AHL signals.")
            df['signal'] = 0
            return df

        df['returns'] = df['Close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=self.vol_window).std() * np.sqrt(252)
        df['volatility'] = df['volatility'].replace(0, np.nan).bfill()

        signals_components = []
        for w in self.windows:
            momentum = df['Close'] / df['Close'].shift(w) - 1
            normalized_momentum = momentum / df['volatility']
            signals_components.append(normalized_momentum)

        combined_signal_raw = sum(signals_components) / len(self.windows)
        df['raw_signal'] = combined_signal_raw

        df['signal'] = 0
        df.loc[df['raw_signal'] > 0.1, 'signal'] = 1
        df.loc[df['raw_signal'] < -0.1, 'signal'] = -1

        df['signal'] = df['signal'].ewm(span=14).mean()
        df['signal'] = np.sign(df['signal']).fillna(0).astype(int)
        return df
"""
Core Man AHL Multi-Horizon Momentum Strategy Quantitative Engine.
Provides functions for signal calculation, volatility scaling, ATR, position sizing,
drawdown tracking, and risk management.
"""

import pandas as pd


def calculate_momentum_score(close_series: pd.Series) -> pd.Series:
    """
    Calculate daily momentum score using exactly 4 lookback windows: 5, 10, 21, and 42 days.
    Score = sign(Close[today] - Close[5 days ago]) +
            sign(Close[today] - Close[10 days ago]) +
            sign(Close[today] - Close[21 days ago]) +
            sign(Close[today] - Close[42 days ago])
    We apply a 14-day Exponential Moving Average (EWM) to the close prices before calculating
    the lookback differences to filter out high-frequency noise and prevent excessive whipsaw.
    """
    score = pd.Series(0.0, index=close_series.index)
    smoothed_close = close_series.ewm(span=14, adjust=False).mean()
    for lookback in [5, 10, 21, 42]:
        diff = smoothed_close - smoothed_close.shift(lookback)
        score += np.sign(diff).fillna(0.0)
    return score

def calculate_volatility_and_atr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate annualized volatility and ATR percentage over a rolling 20-day window.
    For crypto, we assume 365 trading days in a year.
    ATR percentage = ATR_20 / Close.
    """
    df = df.copy()

    # Annualized standard deviation of daily percentage returns
    daily_returns = df["Close"].pct_change().fillna(0.0)
    # Using 365 days for crypto
    df["Vol_20d"] = daily_returns.rolling(window=20).std() * np.sqrt(365)
    # Floor volatility to avoid division by zero or extreme scaling
    df["Vol_20d"] = df["Vol_20d"].clip(lower=1e-4)

    # ATR 20
    high_low = df["High"] - df["Low"]
    high_close_prev = (df["High"] - df["Close"].shift(1)).abs()
    low_close_prev = (df["Low"] - df["Close"].shift(1)).abs()

    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    df["ATR_20"] = tr.rolling(window=20).mean()
    # Handle NaNs at start
    df["ATR_20"] = df["ATR_20"].bfill().fillna(0.0)

    df["ATR_pct"] = df["ATR_20"] / df["Close"]
    df["ATR_pct"] = df["ATR_pct"].fillna(0.0)

    return df

def calculate_target_position_sizes(
    scores: dict,
    volatilities: dict,
    equity: float,
    target_risk: float,
    half_kelly: float = 0.5,
    leverage_cap: float = 3.0,
    min_order_size: float = 10.0,
    strong_signal_threshold: float = 2.0
) -> dict:
    """
    Calculate volatility-scaled and risk-targeted position sizes.
    Scores: dict of {ticker: score}
    Volatilities: dict of {ticker: vol}
    Equity: current portfolio equity
    Target_Risk: target volatility (35%)
    Half_Kelly: Kelly fraction (0.5)
    Leverage_Cap: Max gross leverage (3x)
    """
    theoretical_sizes = {}
    for ticker, score in scores.items():
        if score == 0:
            theoretical_sizes[ticker] = 0.0
            continue
        vol = volatilities.get(ticker, 0.5)

        # Conviction-Based Sizing Booster (Dynamic Growth Engine)
        # Max score is 4.0 or -4.0 (confluence of all 4 lookbacks)
        conviction_multiplier = 1.0
        if abs(score) == 4.0:
            conviction_multiplier = 2.0  # Safe aggressive sizing for $100 -> $500 target

        # Target Position Size = Half-Kelly * (Score * Account_Equity * Target_Risk) / Volatility * Conviction
        theoretical = half_kelly * (score * equity * target_risk) / vol * conviction_multiplier
        theoretical_sizes[ticker] = theoretical

    # Filter strong signals & apply floor of $10
    floored_sizes = {}
    active_candidates = []
    for ticker, size in theoretical_sizes.items():
        abs_size = abs(size)
        score = scores.get(ticker, 0.0)
        if abs_size > 0:
            if abs_size < min_order_size:
                if abs(score) >= strong_signal_threshold:
                    floored_sizes[ticker] = np.sign(size) * min_order_size
                    active_candidates.append(ticker)
                else:
                    floored_sizes[ticker] = 0.0
            else:
                floored_sizes[ticker] = size
                active_candidates.append(ticker)
        else:
            floored_sizes[ticker] = 0.0

    # Prioritize candidates if we exceed the leverage budget
    max_allowed_exposure = equity * leverage_cap
    max_positions = int(max_allowed_exposure // min_order_size)

    # Sort candidates by: (absolute score DESC, volatility ASC)
    def sort_key(ticker):
        score = scores.get(ticker, 0.0)
        vol = volatilities.get(ticker, 0.5)
        return (-abs(score), vol)

    sorted_candidates = sorted(active_candidates, key=sort_key)
    kept_candidates = sorted_candidates[:max_positions]

    for ticker in list(floored_sizes.keys()):
        if ticker not in kept_candidates:
            floored_sizes[ticker] = 0.0

    # For kept positions, check if the sum exceeds the leverage cap
    final_sizes = {ticker: 0.0 for ticker in scores}
    current_exposure = 0.0

    for ticker in kept_candidates:
        size = floored_sizes[ticker]
        abs_size = abs(size)

        if current_exposure + abs_size <= max_allowed_exposure:
            final_sizes[ticker] = size
            current_exposure += abs_size
        else:
            remaining_space = max_allowed_exposure - current_exposure
            if remaining_space >= min_order_size:
                final_sizes[ticker] = np.sign(size) * remaining_space
                current_exposure += remaining_space
            else:
                final_sizes[ticker] = 0.0

    return final_sizes

def check_rebalance_required(
    current_positions: dict,
    target_sizes: dict,
    scores: dict,
    prev_scores: dict,
    min_change: float = 10.0
) -> dict:
    """
    Determine which assets require a rebalance.
    Only execute a rebalance if:
    1. The signal flips polarity sign (positive to negative or vice versa).
       `np.sign(score) * np.sign(prev_score) < 0`.
    2. We are entering a new position (current position is 0 and score is non-zero).
    3. Deleveraging or major size adjustment is required (change >= 3.5 * min_change i.e. >= $35).
    """
    rebalance_required = {}
    for ticker, target_size in target_sizes.items():
        curr_pos = current_positions.get(ticker, 0.0)

        score = scores.get(ticker, 0.0)
        prev_score = prev_scores.get(ticker, 0.0)

        # 1. Polarity Flip (Positive to Negative or vice versa)
        sign_flip = (np.sign(score) * np.sign(prev_score) < 0)

        # 2. Entering a new position
        entry = (curr_pos == 0.0 and score != 0.0)

        # 3. Major size change (>= $35) to prevent minor daily rebalancing drift
        size_change = abs(target_size - curr_pos)
        major_size_change = size_change >= 3.5 * min_change

        if sign_flip or entry or major_size_change:
            rebalance_required[ticker] = True
        else:
            rebalance_required[ticker] = False

    return rebalance_required
