"""Public API exports for the alpha package - re-exporting from adapter"""
from src.alpha.adapter import (
    BaseStrategy,
    compute_indicators,
    compute_regime_returns,
    get_strategy,
    list_strategies,
    load_strategy_from_spec,
    get_indicators_module,
)

# Re-export schemas from private repo via adapter
def _get_private_schemas():
    """Lazily load schemas from private repo."""
    try:
        from src.alpha.adapter import get_indicators_module
        mod = get_indicators_module()
        if mod:
            import alpha.schemas as private_schemas
            return private_schemas
    except ImportError:
        import logging
        logging.debug("Private schemas module not available.")
    return None

# These are lazy-loaded
class _LazyModule:
    def __getattr__(self, name):
        mod = _get_private_schemas()
        if mod:
            return getattr(mod, name)
        raise AttributeError(f"module 'src.alpha.schemas' not available - private repo not loaded")

import sys
sys.modules['src.alpha.schemas'] = _LazyModule()
sys.modules['src.alpha.generator'] = _LazyModule()
sys.modules['src.alpha.reporting'] = _LazyModule()
sys.modules['src.alpha.strategy_man_ahl'] = _LazyModule()
sys.modules['src.alpha.strategy_wsb_alpha'] = _LazyModule()
sys.modules['src.alpha.fade_strategy'] = _LazyModule()
sys.modules['src.alpha.macro_regime'] = _LazyModule()
sys.modules['src.alpha.wsb_sentiment_alpha'] = _LazyModule()

__all__ = [
    "BaseStrategy",
    "compute_indicators",
    "compute_regime_returns",
    "get_strategy",
    "list_strategies",
    "load_strategy_from_spec",
    "get_indicators_module",
]