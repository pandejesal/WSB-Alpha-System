"""RSI Mean-Reversion Strategy — reference implementation.

Goes long when RSI dips below the oversold level and short when it exceeds
the overbought level.  Intermediate RSI values produce a flat signal.
"""

from __future__ import annotations

import pandas as pd

from src.alpha.adapter import BaseStrategy


class RSIMeanReversionStrategy(BaseStrategy):
    """Simple RSI-based mean-reversion with configurable thresholds."""

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def _compute_rsi(self, close: pd.Series) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(alpha=1 / self.rsi_period, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1 / self.rsi_period, adjust=False).mean()
        rs = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return *df* with a ``signal`` column appended.

        Long (1) when RSI < oversold, short (-1) when RSI > overbought,
        otherwise flat (0).
        """
        df = df.copy()
        rsi = self._compute_rsi(df["Close"])

        df["signal"] = 0
        df.loc[rsi < self.oversold, "signal"] = 1
        df.loc[rsi > self.overbought, "signal"] = -1

        return df
