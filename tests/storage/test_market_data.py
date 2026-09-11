import os

import numpy as np
import pandas as pd

from src.data.base_provider import MarketDataProvider
from src.data.market_data import MarketDataManager


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


def test_fetch_and_cache(tmp_path):
    # Isolated cache dir: never touch the real database/cache (Windows
    # PermissionError WinError 5 on rmtree of the real dir).
    cache_dir = str(tmp_path / "cache")
    manager = MarketDataManager(provider=MockProvider(), cache_dir=cache_dir)
    df = manager.fetch_data("AAPL", "2023-01-01", "2023-01-10", use_cache=True)
    assert not df.empty
    assert "Close" in df.columns
    assert os.path.exists(cache_dir)
    files = os.listdir(cache_dir)
    assert len(files) > 0
