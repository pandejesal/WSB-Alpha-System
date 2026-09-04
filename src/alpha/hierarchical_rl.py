"""Hierarchical observation space prototype for the RL Signal Engine.

Implements the three-tier observation layers of the HARLF framework
(arXiv 2507.18560): base agents process hybrid data, meta-agents aggregate
their decisions, and a super-agent merges decisions using market data and
sentiment. This module provides the observation-building primitives:

  * ``build_daily_layer``      — trend, momentum, volatility, drawdown
  * ``build_intraday_layer``   — session returns, volume, range geometry
  * ``build_execution_layer``  — position, liquidity, spread/slippage proxies
  * ``detect_regime``          — volatility-ratio + momentum regime label
  * ``suggest_trade_timing``   — fail-closed trade gate
  * ``build_hierarchical_observation`` — RL Signal Engine integration entry
    point: assembles the three layers into a flattened observation vector
    aligned with ``hierarchical_feature_names()``.

Pure functions only: no network calls, no file I/O, no new dependencies.
All functions are fail-closed — invalid inputs raise ``ValueError`` and
insufficient data yields a safe neutral/"no trade" state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_OHLCV = ("open", "high", "low", "close", "volume")

VOL_SHORT_WINDOW = 20
VOL_LONG_WINDOW = 60
VOL_LOW_RATIO = 0.8
VOL_HIGH_RATIO = 1.2

TREND_WINDOW = 63
TREND_BULL = 0.05
TREND_BEAR = -0.05

DAILY_FEATURE_NAMES = (
    "daily_return_1d",
    "daily_return_21d",
    "daily_vol_21d",
    "daily_vol_ratio_20_60",
    "daily_sma_50_ratio",
    "daily_sma_200_ratio",
    "daily_drawdown_52w",
)

INTRADAY_FEATURE_NAMES = (
    "intraday_return",
    "intraday_vol_20",
    "intraday_volume_ratio",
    "intraday_range_pct",
    "intraday_close_position",
)

EXECUTION_FEATURE_NAMES = (
    "execution_position",
    "execution_liquidity",
    "execution_spread_proxy",
    "execution_slippage_proxy",
)


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return the DataFrame if it has all required OHLCV columns.

    Empty/None input returns an empty DataFrame (callers decide the neutral
    state); missing columns raise ``ValueError`` (fail-closed).
    """
    if df is None or df.empty:
        return pd.DataFrame()
    missing = [col for col in REQUIRED_OHLCV if col not in df.columns]
    if missing:
        raise ValueError(f"missing required OHLCV columns: {missing}")
    return df


def _safe_float(value: Any) -> float:
    """Coerce to float, returning 0.0 for None/NaN/non-numeric values."""
    if value is None:
        return 0.0
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(result):
        return 0.0
    return result


# ---------------------------------------------------------------------------
# Daily layer
# ---------------------------------------------------------------------------

def build_daily_layer(df: pd.DataFrame) -> dict[str, float]:
    """Build the daily observation layer.

    Features: 1d/21d returns, 21d annualized volatility, 20d/60d volatility
    ratio, distance from SMA-50/SMA-200, and drawdown from the 52-week high.
    Returns an empty dict for empty input; missing OHLCV columns raise.
    """
    df = _validate_ohlcv(df)
    if df.empty:
        return {}

    close = df["close"].astype(float)
    returns = close.pct_change()
    vol_short = returns.rolling(VOL_SHORT_WINDOW).std() * np.sqrt(252)
    vol_long = returns.rolling(VOL_LONG_WINDOW).std() * np.sqrt(252)
    sma_50 = close.rolling(50).mean()
    sma_200 = close.rolling(200).mean()
    high_252 = close.rolling(252).max()

    vol_long_last = _safe_float(vol_long.iloc[-1])
    vol_short_last = _safe_float(vol_short.iloc[-1])
    vol_ratio = vol_short_last / vol_long_last if vol_long_last > 0 else 0.0

    close_last = _safe_float(close.iloc[-1])
    sma_50_last = _safe_float(sma_50.iloc[-1])
    sma_200_last = _safe_float(sma_200.iloc[-1])
    high_252_last = _safe_float(high_252.iloc[-1])

    return {
        "daily_return_1d": _safe_float(returns.iloc[-1]),
        "daily_return_21d": _safe_float(close.pct_change(21).iloc[-1]),
        "daily_vol_21d": vol_short_last,
        "daily_vol_ratio_20_60": vol_ratio,
        "daily_sma_50_ratio": close_last / sma_50_last - 1.0 if sma_50_last > 0 else 0.0,
        "daily_sma_200_ratio": close_last / sma_200_last - 1.0 if sma_200_last > 0 else 0.0,
        "daily_drawdown_52w": close_last / high_252_last - 1.0 if high_252_last > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Intraday layer
# ---------------------------------------------------------------------------

def build_intraday_layer(df: pd.DataFrame) -> dict[str, float]:
    """Build the intraday observation layer.

    Features: last-bar return, 20-bar volatility, volume ratio vs the 20-bar
    mean, bar range as a fraction of close, and close position within the
    bar's high-low range. Returns an empty dict for empty input.
    """
    df = _validate_ohlcv(df)
    if df.empty:
        return {}

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)
    returns = close.pct_change()

    vol_20 = _safe_float(returns.tail(20).std())
    vol_mean_20 = _safe_float(volume.tail(20).mean())
    volume_last = _safe_float(volume.iloc[-1])
    close_last = _safe_float(close.iloc[-1])
    low_last = _safe_float(low.iloc[-1])
    bar_range = _safe_float(high.iloc[-1]) - low_last

    close_position = (close_last - low_last) / bar_range if bar_range > 0 else 0.5

    return {
        "intraday_return": _safe_float(returns.iloc[-1]),
        "intraday_vol_20": vol_20,
        "intraday_volume_ratio": volume_last / vol_mean_20 if vol_mean_20 > 0 else 0.0,
        "intraday_range_pct": bar_range / close_last if close_last > 0 else 0.0,
        "intraday_close_position": close_position,
    }


# ---------------------------------------------------------------------------
# Execution layer
# ---------------------------------------------------------------------------

def build_execution_layer(
    df: pd.DataFrame, *, position: float = 0.0
) -> dict[str, float]:
    """Build the execution observation layer.

    Features: current position, log-volume liquidity proxy, bar-range spread
    proxy, and bar-to-bar slippage proxy. Fail-closed: empty input still
    reports the position with zeroed liquidity/spread/slippage.
    """
    df = _validate_ohlcv(df)
    if df.empty:
        return {
            "execution_position": float(position),
            "execution_liquidity": 0.0,
            "execution_spread_proxy": 0.0,
            "execution_slippage_proxy": 0.0,
        }

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)

    close_last = _safe_float(close.iloc[-1])
    prev_close = _safe_float(close.iloc[-2]) if len(close) > 1 else close_last
    spread_proxy = (
        (_safe_float(high.iloc[-1]) - _safe_float(low.iloc[-1])) / close_last
        if close_last > 0
        else 0.0
    )
    slippage_proxy = (
        abs(close_last - prev_close) / close_last if close_last > 0 else 0.0
    )

    return {
        "execution_position": float(position),
        "execution_liquidity": float(np.log1p(_safe_float(volume.iloc[-1]))),
        "execution_spread_proxy": spread_proxy,
        "execution_slippage_proxy": slippage_proxy,
    }


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

def detect_regime(df: pd.DataFrame) -> dict[str, Any]:
    """Detect the market regime from OHLCV data.

    Volatility regime from the 20d/60d realized-vol ratio (thresholds 0.8/1.2,
    matching ``h3_beta_regime_switch``); trend regime from 63d momentum
    (thresholds +/-5%, matching the ``agentquant_regime`` label vocabulary).

    Returns a dict with ``regime_label`` ("{VolLabel}-{TrendLabel}"),
    ``vol_regime``, ``trend_regime``, and ``confidence``. Fail-closed: empty
    input yields ``Unknown`` with zero confidence.
    """
    df = _validate_ohlcv(df)
    if df.empty:
        return {
            "regime_label": "Unknown",
            "vol_regime": "unknown",
            "trend_regime": "unknown",
            "confidence": 0.0,
        }

    close = df["close"].astype(float)
    returns = close.pct_change()
    vol_short = returns.rolling(VOL_SHORT_WINDOW).std()
    vol_long = returns.rolling(VOL_LONG_WINDOW).std()

    vol_long_last = _safe_float(vol_long.iloc[-1])
    vol_short_last = _safe_float(vol_short.iloc[-1])
    vol_ratio = vol_short_last / vol_long_last if vol_long_last > 0 else 0.0

    if vol_ratio < VOL_LOW_RATIO:
        vol_regime = "low"
    elif vol_ratio > VOL_HIGH_RATIO:
        vol_regime = "high"
    else:
        vol_regime = "neutral"

    mom_63d = _safe_float(close.pct_change(TREND_WINDOW).iloc[-1])
    if mom_63d > TREND_BULL:
        trend_regime = "bull"
    elif mom_63d < TREND_BEAR:
        trend_regime = "bear"
    else:
        trend_regime = "neutral"

    vol_label = {"low": "LowVol", "neutral": "MidVol", "high": "HighVol"}[vol_regime]
    trend_label = {"bull": "Bull", "neutral": "Neutral", "bear": "Bear"}[trend_regime]

    return {
        "regime_label": f"{vol_label}-{trend_label}",
        "vol_regime": vol_regime,
        "trend_regime": trend_regime,
        "confidence": min(abs(mom_63d) / 0.10, 1.0),
    }


# ---------------------------------------------------------------------------
# Trade timing gate
# ---------------------------------------------------------------------------

def suggest_trade_timing(
    df: pd.DataFrame,
    *,
    position: float = 0.0,
    max_position: float = 1.0,
) -> dict[str, Any]:
    """Suggest whether to trade now, fail-closed.

    Blocks trading when data is insufficient, the volatility regime is high,
    or the position limit is reached. Returns a dict with ``should_trade``,
    ``reason``, ``regime``, and ``confidence``.
    """
    regime = detect_regime(df)
    if regime["regime_label"] == "Unknown":
        return {
            "should_trade": False,
            "reason": "insufficient data",
            "regime": regime["regime_label"],
            "confidence": 0.0,
        }
    if regime["vol_regime"] == "high":
        return {
            "should_trade": False,
            "reason": "high volatility regime",
            "regime": regime["regime_label"],
            "confidence": regime["confidence"],
        }
    if abs(float(position)) >= float(max_position):
        return {
            "should_trade": False,
            "reason": "position limit reached",
            "regime": regime["regime_label"],
            "confidence": regime["confidence"],
        }
    return {
        "should_trade": True,
        "reason": "regime supports trading",
        "regime": regime["regime_label"],
        "confidence": regime["confidence"],
    }


# ---------------------------------------------------------------------------
# Hierarchical observation assembly (RL Signal Engine entry point)
# ---------------------------------------------------------------------------

@dataclass
class HierarchicalObservation:
    """Assembled three-tier observation for the RL Signal Engine."""

    daily: dict[str, float]
    intraday: dict[str, float]
    execution: dict[str, float]
    regime: dict[str, Any]
    timing: dict[str, Any]
    feature_names: list[str]
    features: list[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "daily": dict(self.daily),
            "intraday": dict(self.intraday),
            "execution": dict(self.execution),
            "regime": dict(self.regime),
            "timing": dict(self.timing),
            "feature_names": list(self.feature_names),
            "features": list(self.features),
        }


def build_hierarchical_observation(
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    execution_df: pd.DataFrame,
    *,
    position: float = 0.0,
) -> HierarchicalObservation:
    """Assemble the three-tier observation (RL Signal Engine entry point).

    Builds each layer, detects the regime, gates trade timing, and flattens
    all features into a fixed-order vector aligned with
    :func:`hierarchical_feature_names`. The RL Signal Engine consumes this
    vector as its observation space and the ``timing`` gate before acting.
    """
    daily = build_daily_layer(daily_df)
    intraday = build_intraday_layer(intraday_df)
    execution = build_execution_layer(execution_df, position=position)
    regime = detect_regime(daily_df)
    timing = suggest_trade_timing(daily_df, position=position)

    names = hierarchical_feature_names()
    merged = {**daily, **intraday, **execution}
    features = [float(merged.get(name, 0.0)) for name in names]

    return HierarchicalObservation(
        daily=daily,
        intraday=intraday,
        execution=execution,
        regime=regime,
        timing=timing,
        feature_names=list(names),
        features=features,
    )


def hierarchical_feature_names() -> list[str]:
    """Ordered feature names of the flattened RL observation vector."""
    return list(DAILY_FEATURE_NAMES + INTRADAY_FEATURE_NAMES + EXECUTION_FEATURE_NAMES)


def observation_space_size() -> int:
    """Dimensionality of the flattened RL observation vector."""
    return len(hierarchical_feature_names())