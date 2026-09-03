"""Momentum Breakout Strategy — reference implementation.

Goes long when price breaks above the N-day high with rising volume, and
short on a break below the N-day low with rising volume.
"""

from __future__ import annotations

import pandas as pd

from src.alpha.adapter import BaseStrategy


class MomentumBreakoutStrategy(BaseStrategy):
    """Donchian-channel breakout with a volume-confirmation filter."""

    def __init__(
        self,
        lookback: int = 20,
        volume_factor: float = 1.2,
    ) -> None:
        self.lookback = lookback
        self.volume_factor = volume_factor

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return *df* with a ``signal`` column appended.

        Long (1) on a breakout above the N-day high when volume exceeds its
        N-day average by ``volume_factor``; short (-1) on a break below the
        N-day low under the same volume condition.
        """
        df = df.copy()
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"] if "Volume" in df.columns else pd.Series(0, index=df.index)

        rolling_high = high.rolling(self.lookback).max()
        rolling_low = low.rolling(self.lookback).min()
        avg_volume = volume.rolling(self.lookback).mean()

        volume_confirmed = volume > (avg_volume * self.volume_factor)

        df["signal"] = 0

        # Long breakout
        breakout_long = close > rolling_high.shift(1)
        df.loc[breakout_long & volume_confirmed, "signal"] = 1

        # Short breakout
        breakout_short = close < rolling_low.shift(1)
        df.loc[breakout_short & volume_confirmed, "signal"] = -1

        return df
