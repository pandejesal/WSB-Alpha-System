# CH-14 candidate: duplicate backtest engine — candidate for consolidation into src/backtest/engines/canonical.py (no merge in this phase; canonical is engines/canonical.py)
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BacktestEngine(ABC):
    @abstractmethod
    def run_backtest(self, data: pd.DataFrame, strategy: Any, **kwargs) -> dict[str, Any]:
        """Run the backtest and return metrics."""
