from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BacktestEngine(ABC):
    @abstractmethod
    def run_backtest(self, data: pd.DataFrame, strategy: Any, **kwargs) -> dict[str, Any]:
        """Run the backtest and return metrics."""
