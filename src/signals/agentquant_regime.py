"""
AgentQuant Regime Detection — Percentile-Based Market Regime Classification
===========================================================================

Ported from AgentQuant's src/features/regime.py.
Classifies market regime using realized volatility percentile and
multi-horizon momentum. No VIX dependency; operates on SPY-only local CSV.

Regime labels: "{VolLabel}-{TrendLabel}"
  VolLabel:  LowVol | MidVol | HighVol | Crisis  (from vol percentile)
  TrendLabel: Bull | Neutral | Bear              (from 63d momentum)
"""

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature engineering for regime detection
# ---------------------------------------------------------------------------

def compute_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute regime detection features from OHLCV data.

    Adds columns: volatility_21d, momentum_21d, momentum_63d, momentum_252d,
    sma_50, sma_200, drawdown_from_52w_high.

    Args:
        df: DataFrame with at least 'Close' column and datetime index.

    Returns:
        DataFrame with regime feature columns added.
    """
    if df.empty:
        return df.copy()

    out = df.copy()
    close = out["Close"]

    # Realized volatility (annualized)
    out["volatility_21d"] = close.pct_change().rolling(21).std() * np.sqrt(252)

    # Momentum
    out["momentum_21d"] = close.pct_change(21)
    out["momentum_63d"] = close.pct_change(63)
    out["momentum_252d"] = close.pct_change(252)

    # Simple moving averages
    out["sma_50"] = close.rolling(50).mean()
    out["sma_200"] = close.rolling(200).mean()

    # Drawdown from 52-week high
    rolling_252_high = close.rolling(252).max()
    out["drawdown_from_52w_high"] = (close / rolling_252_high) - 1.0

    return out


@dataclass
class RegimeSignals:
    """Full set of regime signals for the latest observation."""
    # Trend
    above_200sma: bool = False
    above_50sma: bool = False
    price_vs_200sma_pct: float = 0.0
    # Volatility (percentile-based, no VIX needed)
    realized_vol_21d: float = 0.0
    vol_percentile_252d: float = 50.0
    vol_regime: str = "mid"   # "low" | "mid" | "high" | "crisis"
    # Momentum
    momentum_21d: float = 0.0
    momentum_63d: float = 0.0
    momentum_252d: float = 0.0
    # Drawdown
    drawdown_from_52w_high: float = 0.0
    # Derived
    regime_label: str = "Unknown"
    regime_confidence: float = 0.5


def detect_regime(features_df: pd.DataFrame) -> str:
    """
    Detects the current market regime label from features DataFrame.

    Uses realized-vol percentile (relative, not absolute) and
    multi-horizon momentum. No VIX dependency.

    Args:
        features_df: DataFrame with columns including Close, volatility_21d,
                     momentum_63d, sma_200, sma_50. Index must be datetime.

    Returns:
        Regime label string, e.g. "LowVol-Bull", "Crisis-Bear".
    """
    signals = detect_regime_full(features_df)
    return signals.regime_label


def detect_regime_full(features_df: pd.DataFrame) -> RegimeSignals:
    """
    Full regime detection returning all signals.

    Computes realized-vol percentile from trailing 252 days of 21d vol,
    classifies vol regime, computes momentum, and returns the combined label.

    Args:
        features_df: DataFrame with columns including Close, volatility_21d,
                     momentum_63d, momentum_21d, momentum_252d, sma_200, sma_50.

    Returns:
        RegimeSignals dataclass with all computed signals.
    """
    if features_df.empty:
        return RegimeSignals(regime_label="Unknown")

    latest = features_df.iloc[-1]
    signals = RegimeSignals()

    # --- Realized vol (percentile-based, no VIX) ---
    signals.realized_vol_21d = float(latest.get("volatility_21d", 0.0) or 0.0)

    # Compute percentile of current 21d vol vs trailing 252d
    if "volatility_21d" in features_df.columns:
        vol_history = features_df["volatility_21d"].dropna().tail(252)
        if len(vol_history) > 10:
            # Percentile of current vol within historical distribution
            signals.vol_percentile_252d = float(
                np.searchsorted(np.sort(vol_history.values), signals.realized_vol_21d)
                / len(vol_history) * 100.0
            )
        else:
            signals.vol_percentile_252d = 50.0
    else:
        signals.vol_percentile_252d = 50.0

    # Vol regime buckets from percentile
    vp = signals.vol_percentile_252d
    if vp > 85:
        signals.vol_regime = "crisis"
        vol_label = "Crisis"
    elif vp > 65:
        signals.vol_regime = "high"
        vol_label = "HighVol"
    elif vp > 35:
        signals.vol_regime = "mid"
        vol_label = "MidVol"
    else:
        signals.vol_regime = "low"
        vol_label = "LowVol"

    # Confidence: distance from 50th percentile
    vol_confidence = 2.0 * abs(vp / 100.0 - 0.5)

    # --- Momentum ---
    signals.momentum_21d = float(latest.get("momentum_21d", 0.0) or 0.0)
    signals.momentum_63d = float(latest.get("momentum_63d", 0.0) or 0.0)
    signals.momentum_252d = float(latest.get("momentum_252d", 0.0) or 0.0)

    mom = signals.momentum_63d
    if mom > 0.05:
        trend_label = "Bull"
    elif mom < -0.05:
        trend_label = "Bear"
    else:
        trend_label = "Neutral"

    mom_confidence = min(abs(mom) / 0.10, 1.0)

    # --- Trend (SMA) ---
    close = latest.get("Close", None)
    sma200 = latest.get("sma_200", None)
    sma50 = latest.get("sma_50", None)

    if close is not None and sma200 is not None and not pd.isna(sma200) and float(sma200) > 0:
        pct = float(close) / float(sma200) - 1.0
        signals.price_vs_200sma_pct = pct
        signals.above_200sma = pct > 0
    if close is not None and sma50 is not None and not pd.isna(sma50) and float(sma50) > 0:
        signals.above_50sma = float(close) > float(sma50)

    # --- Drawdown from 52w high ---
    if "Close" in features_df.columns:
        close_series = features_df["Close"].dropna().tail(252)
        if len(close_series) > 1:
            peak = close_series.max()
            latest_close = close_series.iloc[-1]
            signals.drawdown_from_52w_high = (latest_close / peak) - 1.0

    # --- Final label and confidence ---
    signals.regime_label = f"{vol_label}-{trend_label}"
    signals.regime_confidence = (vol_confidence + mom_confidence) / 2.0

    logger.info(
        "Regime detected: %s (vol21d=%.2f%% at %.0fth pct, mom63d=%.1f%%, confidence=%.0f%%)",
        signals.regime_label,
        signals.realized_vol_21d * 100,
        signals.vol_percentile_252d,
        signals.momentum_63d * 100,
        signals.regime_confidence * 100,
    )

    return signals
