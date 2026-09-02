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
    """Abstract base class for all trading strategies."""
    
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
        os.path.join(os.path.dirname(__file__), "..", "..", "strategies", "src"),
        os.environ.get("ALPHA_STRATEGIES_PATH", ""),
        os.path.join(os.path.dirname(__file__), "..", "strategies", "src"),
    ]
    
    for path in candidates:
        if path and os.path.exists(os.path.join(path, "alpha")):
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
    
    if strategies_path not in sys.path:
        sys.path.insert(0, strategies_path)
    
    try:
        # Import the private alpha package
        import alpha.strategies as private_strategies
        import alpha.indicators as private_indicators
        
        # Cache indicators module for direct access
        _STRATEGY_CACHE["_indicators_module"] = private_indicators
        
        # Auto-register all BaseStrategy subclasses
        for attr_name in dir(private_strategies):
            attr = getattr(private_strategies, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseStrategy) and attr != BaseStrategy:
                _STRATEGY_CACHE[attr_name] = attr()
                
    except ImportError as e:
        # Private repo not available - will use fallback
        pass
    except Exception:
        # Any other error - fail silently
        pass


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
    
    # Bollinger Bands
    df["BB_Middle"] = df["Close"].rolling(window=20).mean()
    df["BB_Std"] = df["Close"].rolling(window=20).std().fillna(1e-4)
    df["BB_Upper"] = df["BB_Middle"] + 2.0 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2.0 * df["BB_Std"]
    
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