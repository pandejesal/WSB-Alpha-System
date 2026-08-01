from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BacktestEngine(ABC):
    @abstractmethod
    def run_backtest(self, data: pd.DataFrame, strategy: Any, **kwargs) -> Dict[str, Any]:
        """Run the backtest and return metrics."""
        pass
