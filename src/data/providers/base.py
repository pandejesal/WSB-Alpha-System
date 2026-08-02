from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Dict

class BaseDataProvider(ABC):
    @abstractmethod
    def fetch_ohlcv(self, tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical OHLCV data."""
        pass

    @abstractmethod
    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        """Fetch sentiment/posts feed."""
        pass
