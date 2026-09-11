"""R-C1: tradability guards for price frames (hunt-loop operability).

Rejects economically meaningless frames that pass shape checks:
all-zero, all-NaN, or zero-variance (flat) series. Hunt workers call
``assert_tradable_prices`` after fills (``ffill`` is a no-op on zeros,
so a zero-init frame would otherwise slip through silently).
"""

from __future__ import annotations

import pandas as pd

_PRICE_KEYS = ("close", "adj close", "adj_close", "price")


def _target_columns(df: pd.DataFrame) -> list:
    lowered = {str(c).lower(): c for c in df.columns}
    hits = [lowered[k] for k in _PRICE_KEYS if k in lowered]
    if hits:
        return hits
    numeric = list(df.select_dtypes(include="number").columns)
    return numeric if numeric else list(df.columns)


def assert_tradable_prices(df: pd.DataFrame, symbol: str = "unknown") -> pd.DataFrame:
    """Validate that a price frame is economically tradable (R-C1).

    Raises:
        ValueError: naming ``symbol`` and the offending column when it is
            all-NaN, all-zero, or zero-variance (flat, ``nunique<=1``).
    """
    if df is None or len(df) == 0:
        raise ValueError(f"untradable prices for {symbol}: empty frame")
    if isinstance(df, pd.Series):
        name = str(df.name) if df.name is not None else "series"
        data = df.dropna()
        if len(data) == 0:
            raise ValueError(f"untradable prices for {symbol}:{name}: all-NaN frame")
        if bool((data == 0).all()):
            raise ValueError(f"untradable prices for {symbol}:{name}: all-zero frame")
        if int(data.nunique()) <= 1:
            raise ValueError(f"untradable prices for {symbol}:{name}: zero-variance (flat) frame")
        return df
    for col in _target_columns(df):
        series = df[col]
        non_na = series.dropna()
        if len(non_na) == 0:
            raise ValueError(f"untradable prices for {symbol}:{col}: all-NaN frame")
        if bool((non_na == 0).all()):
            raise ValueError(f"untradable prices for {symbol}:{col}: all-zero frame")
        if int(non_na.nunique()) <= 1:
            raise ValueError(
                f"untradable prices for {symbol}:{col}: zero-variance (flat) frame"
            )
    return df
