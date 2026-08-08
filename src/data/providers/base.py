from abc import ABC, abstractmethod

import pandas as pd


class BaseDataProvider(ABC):
    @abstractmethod
    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical OHLCV data."""

    @abstractmethod
    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        """Fetch sentiment/posts feed."""
