"""EMA Crossover Strategy — reference implementation.

Goes long when the fast EMA crosses above the slow EMA and short on the
reverse cross.  Uses a configurable lookback to avoid whipsaws.
"""

from __future__ import annotations

import pandas as pd

from src.alpha.adapter import BaseStrategy


class EMACrossoverStrategy(BaseStrategy):
    """Dual exponential moving average crossover with optional signal smoothing."""

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        signal_threshold: float = 0.0,
    ) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_threshold = signal_threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:  # noqa: D401
        """Return *df* with a ``signal`` column appended.

        Long (1) when fast EMA > slow EMA, short (-1) when fast EMA < slow EMA.
        A small ``signal_threshold`` (fraction of price) can be used to suppress
        noise during tight consolidations.
        """
        df = df.copy()
        close = df["Close"]

        ema_fast = close.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow_period, adjust=False).mean()

        # Cross magnitude relative to price
        cross = (ema_fast - ema_slow) / close

        df["signal"] = 0
        df.loc[cross > self.signal_threshold, "signal"] = 1
        df.loc[cross < -self.signal_threshold, "signal"] = -1

        return df
