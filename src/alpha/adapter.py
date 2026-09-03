"""
Strategy Adapter Module

This module provides a unified interface for loading strategies from the private
WSB-Alpha-Strategies repository (via git submodule at ./strategies/).

At runtime, strategies are loaded dynamically. At build/test time, if the
submodule is not available, this falls back to a minimal interface.
"""

import os
import sys
import importlib.util
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    This is the fallback definition used when the private strategies
    submodule is unavailable.  When the submodule is present, the
    adapter re-exports its ``BaseStrategy`` instead so that all
    strategy classes share a single canonical base.
    """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals from market data.

        Args:
            df: DataFrame with OHLCV columns

        Returns:
            DataFrame with 'signal' column (1=long, -1=short, 0=flat)
        """
        pass

    def get_name(self) -> str:
        """Return strategy identifier."""
        return self.__class__.__name__


# Cache for loaded strategies
_STRATEGY_CACHE: Dict[str, BaseStrategy] = {}
_MODULES_LOADED = False


def _find_strategies_path() -> Optional[str]:
    """Find the private strategies repository path."""
    # Check common locations
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "strategies"),
        os.environ.get("ALPHA_STRATEGIES_PATH", ""),
        os.path.join(os.path.dirname(__file__), "..", "strategies"),
    ]
    
    for path in candidates:
        if path and os.path.exists(os.path.join(path, "src", "alpha")):
            return os.path.abspath(path)
    return None


def _load_private_strategies() -> None:
    """Load strategy implementations from private repo."""
    global _MODULES_LOADED
    
    if _MODULES_LOADED:
        return
    _MODULES_LOADED = True
    
    strategies_path = _find_strategies_path()
    if not strategies_path:
        return
    
    # The private repo has structure: strategies/src/alpha/
    # We need to add strategies/src to sys.path so alpha can be imported
    private_src = os.path.join(strategies_path, "src")
    if private_src not in sys.path:
        sys.path.insert(0, private_src)
    
    try:
        # Import the private alpha package (it's at strategies/src/alpha/)
        import alpha as private_alpha

        # Cache indicators module for direct access
        _STRATEGY_CACHE["_indicators_module"] = private_alpha

        # Use the private repo's BaseStrategy for identity checks
        PrivateBaseStrategy = getattr(private_alpha, "BaseStrategy", BaseStrategy)

        # Register all exported strategy classes
        for attr_name in getattr(private_alpha, "__all__", []):
            attr = getattr(private_alpha, attr_name, None)
            if attr and isinstance(attr, type) and (hasattr(attr, 'generate_signals') or hasattr(attr, 'generate_signal')) and attr is not PrivateBaseStrategy:
                _STRATEGY_CACHE[attr_name] = attr()
                
    except ImportError:
        # Private repo not available - will use fallback
        import logging
        logging.debug("Private strategies submodule not found; using fallback indicators.")
    except Exception as exc:
        # Unexpected error loading private strategies
        import logging
        logging.debug("Failed to load private strategies: %s", exc)


def get_indicators_module():
    """Get the indicators module from private repo."""
    _load_private_strategies()
    return _STRATEGY_CACHE.get("_indicators_module")


def compute_indicators(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Compute technical indicators using private implementation."""
    mod = get_indicators_module()
    if mod and hasattr(mod, "compute_indicators"):
        return mod.compute_indicators(df)
    return None


def compute_regime_returns(*args, **kwargs):
    """Compute regime returns using private implementation."""
    mod = get_indicators_module()
    if mod and hasattr(mod, "compute_regime_returns"):
        return mod.compute_regime_returns(*args, **kwargs)
    return None


def get_strategy(name: str) -> Optional[BaseStrategy]:
    """Get a strategy by name from private repo."""
    _load_private_strategies()
    return _STRATEGY_CACHE.get(name)


def list_strategies() -> List[str]:
    """List all available strategy names."""
    _load_private_strategies()
    return [k for k in _STRATEGY_CACHE.keys() if not k.startswith("_")]


def load_strategy_from_spec(spec_dict: Dict[str, Any]) -> Optional[BaseStrategy]:
    """Load a strategy from a candidate spec dictionary."""
    _load_private_strategies()
    
    # Map family/rule to strategy class names
    family = spec_dict.get("family", "")
    rule = spec_dict.get("signal", {}).get("entry", "").lower()
    
    strategy_map = {
        ("ta_rules", "ema_cross"): "H3AlphaEnsemble",
        ("ta_rules", "macd_histogram"): "H3AlphaEnsemble", 
        ("ta_rules", "rsi2"): "H3BetaRegimeSwitch",
        ("sentiment_overlay", "sma_entry"): "H3BetaRegimeSwitch",
        ("sentiment_overlay", "momentum"): "H3AlphaEnsemble",
        ("xgboost_exits", "rsi2"): "H3BetaRegimeSwitch",
        ("xgboost_exits", "momentum"): "H3AlphaEnsemble",
        ("multi_factor", ""): "ManAHLStrategy",
    }
    
    key = (family, "ema_cross" if "ema" in rule else 
                  "macd_histogram" if "macd" in rule else
                  "rsi2" if "rsi" in rule else
                  "sma_entry" if "sma" in rule else
                  "momentum" if "momentum" in rule else "")
    
    strategy_name = strategy_map.get(key)
    if strategy_name:
        return get_strategy(strategy_name)
    
    return None


# Fallback indicator computation (minimal, for when private repo unavailable)
def _fallback_compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Minimal fallback indicator computation."""
    import numpy as np
    
    df = df.copy()
    if len(df) < 20:
        return None
    
    # EMA 20
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    
    # ATR 14
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = true_range.rolling(14).mean()
    
    # RSI 14
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df["RSI_14"] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema_12 - ema_26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]
    
    # Heikin-Ashi
    df["HA_Close"] = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4.0
    ha_open = np.zeros(len(df))
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + df["HA_Close"].iloc[i-1]) / 2.0
    df["HA_Open"] = ha_open
    df["HA_High"] = df[["High", "HA_Open", "HA_Close"]].max(axis=1)
    df["HA_Low"] = df[["Low", "HA_Open", "HA_Close"]].min(axis=1)
    
    # Bollinger Bands
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    df["BB_Std"] = df["Close"].rolling(window=20).std().fillna(1e-4)
    df["BB_Upper"] = df["BB_Middle"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2.0 * df["BB_Std"]
    df["BB_Middle"] = df["BB_Middle"].fillna(df["Close"])
    df["BB_Upper"] = df["BB_Upper"].fillna(df["Close"] * 1.05)
    df["BB_Lower"] = df["BB_Lower"].fillna(df["Close"] * 0.95)
    
    # Garman-Klass Volatility
    safe_high = df["High"].replace(0, 0.01)
    safe_low = df["Low"].replace(0, 0.01)
    safe_close = df["Close"].replace(0, 0.01)
    safe_open = df["Open"].replace(0, 0.01)
    
    log_hl = np.log(safe_high / safe_low)
    log_co = np.log(safe_close / safe_open)
    gk_element = 0.5 * (log_hl ** 2) - (2 * np.log(2) - 1) * (log_co ** 2)
    gk_variance = gk_element.rolling(window=20).mean()
    gk_variance = gk_variance.clip(lower=1e-10)
    df["GK_Vol"] = np.sqrt(252 * gk_variance)
    first_valid = df["GK_Vol"].dropna().iloc[0] if len(df["GK_Vol"].dropna()) > 0 else 0.50
    df["GK_Vol"] = df["GK_Vol"].fillna(first_valid)
    
    # VaR and CVaR (Rolling 20-day 95%)
    daily_pct_returns = df["Close"].pct_change().fillna(0)
    rolling_var = []
    rolling_cvar = []
    for i in range(len(df)):
        if i < 20:
            rolling_var.append(0.02)
            rolling_cvar.append(0.04)
        else:
            window_rets = daily_pct_returns.iloc[i-19:i+1].dropna()
            sorted_rets = np.sort(window_rets.values.astype(float)) if len(window_rets) > 0 else np.array([], dtype=float)
            if len(sorted_rets) > 0:
                var_idx = max(0, int(0.05 * len(sorted_rets)) - 1)
                var_val = -sorted_rets[var_idx]
                cvar_val = -sorted_rets[:var_idx + 1].mean()
            else:
                var_val = 0.02
                cvar_val = 0.04
            rolling_var.append(max(var_val, 0.0))
            rolling_cvar.append(max(cvar_val, 0.0))
    
    df["VaR_95"] = rolling_var
    df["CVaR_95"] = rolling_cvar
    
    return df


# Patch compute_indicators if private module unavailable
if not get_indicators_module():
    compute_indicators = _fallback_compute_indicators


__all__ = [
    "BaseStrategy",
    "compute_indicators",
    "compute_regime_returns",
    "get_strategy",
    "list_strategies",
    "load_strategy_from_spec",
    "get_indicators_module",
]