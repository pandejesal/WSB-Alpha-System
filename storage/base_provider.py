from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional

class MarketDataProvider(ABC):
    @abstractmethod
    def get_historical_data(self, ticker: str, start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
        """Fetch historical market data."""
        pass
