"""Reference strategy implementations for the public alpha package.

These strategies follow the ``BaseStrategy`` interface defined in
``adapter.py`` and serve as working examples for new strategy development.
"""

from .ema_crossover import EMACrossoverStrategy
from .rsi_mean_reversion import RSIMeanReversionStrategy
from .momentum_breakout import MomentumBreakoutStrategy

__all__ = [
    "EMACrossoverStrategy",
    "RSIMeanReversionStrategy",
    "MomentumBreakoutStrategy",
]
