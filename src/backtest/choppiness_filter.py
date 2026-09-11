"""ATR Choppiness Filter — Universal Signal Backtester concept.

Suppresses signals during low-volatility chop, mirroring LuxAlgo's
"Use ATR Choppiness Filter" setting.  The ATR_14 column is already
computed by src/alpha/indicators.py and present in stock_dfs.

Opt-in via the choppiness_filter=True parameter on run_backtest_with_params.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class ChoppinessFilter:
    """Detects low-volatility chop using the ATR ratio.

    A position is considered "choppy" when the current ATR(14) is below
    `choppiness_threshold` × the rolling median of ATR over a longer
    lookback window.
    """

    def __init__(self, atr_lookback: int = 70, choppiness_threshold: float = 0.5) -> None:
        self.atr_lookback = atr_lookback
        self.choppiness_threshold = choppiness_threshold

    def is_choppy(self, *args, **kwargs) -> bool:
        """Return True if market is choppy. Accepts both signatures:
        - is_choppy(decision_idx, df)
        - is_choppy(stock_df)
        """
        # Try to parse args
        df = None
        idx = None
        if len(args) == 1 and isinstance(args[0], pd.DataFrame):
            df = args[0]
            idx = -1
        elif len(args) == 2:
            # (decision_idx, df)
            idx, df = args[0], args[1]
        elif "stock_df" in kwargs:
            df = kwargs["stock_df"]
            idx = kwargs.get("decision_idx", -1)
        else:
            return False

        if df is None or "ATR_14" not in df.columns:
            return False
        try:
            atr_series = df["ATR_14"]
            if len(atr_series) < self.atr_lookback:
                return False
            # Resolve current ATR value
            if isinstance(idx, int) and idx >= 0 and idx < len(df):
                cur_atr = float(atr_series.iloc[idx])
                # Rolling median over lookback ending at idx
                start = max(0, idx - self.atr_lookback + 1)
                median_atr = float(atr_series.iloc[start : idx + 1].median())
            else:
                cur_atr = float(atr_series.iloc[-1])
                median_atr = float(atr_series.iloc[-self.atr_lookback :].median())
            if median_atr == 0:
                return False
            return cur_atr < self.choppiness_threshold * median_atr
        except Exception:
            return False


def is_choppy(stock_df: pd.DataFrame, atr_lookback: int = 70, choppiness_threshold: float = 0.5) -> bool:
    return ChoppinessFilter(atr_lookback=atr_lookback, choppiness_threshold=choppiness_threshold).is_choppy(stock_df)


__all__ = ["ChoppinessFilter", "is_choppy"]
