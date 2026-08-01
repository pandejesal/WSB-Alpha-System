import unittest
import pandas as pd
import numpy as np
from storage.market_data import MarketDataManager
from storage.base_provider import MarketDataProvider
import shutil
import os

class MockProvider(MarketDataProvider):
    def get_historical_data(self, ticker: str, start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
        dates = pd.date_range(start_date, periods=10)
        df = pd.DataFrame({
            "Close": np.linspace(100, 110, 10),
            "Open": np.linspace(99, 109, 10),
            "High": np.linspace(101, 111, 10),
            "Low": np.linspace(98, 108, 10),
            "Volume": np.random.randint(100, 1000, 10)
        }, index=dates)
        return df

class TestMarketData(unittest.TestCase):
    def setUp(self):
        self.manager = MarketDataManager(provider=MockProvider())
        if os.path.exists("database/cache"):
            shutil.rmtree("database/cache")

    def test_fetch_and_cache(self):
        df = self.manager.fetch_data("AAPL", "2023-01-01", "2023-01-10", use_cache=True)
        self.assertFalse(df.empty)
        self.assertIn("Close", df.columns)
        self.assertTrue(os.path.exists("database/cache"))
        files = os.listdir("database/cache")
        self.assertGreater(len(files), 0)
