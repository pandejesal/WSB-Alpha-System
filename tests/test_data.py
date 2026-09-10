import os
import shutil
import unittest

import pandas as pd
import pytest

try:
    import pandera as pa  # type: ignore

    _PANDERA_AVAILABLE = True
except ModuleNotFoundError:
    pa = None  # type: ignore
    _PANDERA_AVAILABLE = False

try:
    from src.data.cache_engine import CacheEngine
except ImportError:
    CacheEngine = None  # type: ignore

from src.data.schemas import OHLCVSchema
from src.research.ticker_extractor import extract_tickers

# Cache tests require duckdb; skip at test level if missing
try:
    import duckdb  # type: ignore

    _DUCKDB_AVAILABLE = True
except ModuleNotFoundError:
    _DUCKDB_AVAILABLE = False

class TestDataModule(unittest.TestCase):
    def setUp(self):
        if not _DUCKDB_AVAILABLE or CacheEngine is None:
            pytest.skip("duckdb not installed")
        self.db_path = "data/cache/test_market_data.duckdb"
        self.cache = CacheEngine(db_path=self.db_path)  # type: ignore

    def tearDown(self):
        self.cache.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_duckdb_cache_hit_miss(self):
        # Create dummy data
        df = pd.DataFrame({
            'Ticker': ['AAPL', 'AAPL'],
            'Date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [95.0, 96.0],
            'Close': [102.0, 103.0],
            'Volume': [1000, 1100]
        })

        # Test write
        self.cache.store_ohlcv(df)

        # Test hit
        missing = self.cache.determine_missing_ranges(['AAPL'], '2023-01-01', '2023-01-02')
        self.assertEqual(len(missing), 0, "Should be fully cached")

        cached_df = self.cache.get_ohlcv(['AAPL'], '2023-01-01', '2023-01-02')
        self.assertEqual(len(cached_df), 2)

        # Test miss
        missing = self.cache.determine_missing_ranges(['NVDA'], '2023-01-01', '2023-01-02')
        self.assertIn('NVDA', missing)

        # Test partial miss
        missing_partial = self.cache.determine_missing_ranges(['AAPL'], '2023-01-01', '2023-01-05')
        self.assertIn('AAPL', missing_partial)

    def test_pandera_schema_validation(self):
        # Valid data
        valid_df = pd.DataFrame({
            'Ticker': ['AAPL'],
            'Date': pd.to_datetime(['2023-01-01']),
            'Open': [100.0],
            'High': [105.0],
            'Low': [95.0],
            'Close': [102.0],
            'Volume': [1000]
        })
        validated = OHLCVSchema.validate(valid_df)
        self.assertFalse(validated.empty)

        # Invalid data: High < Low
        invalid_df = pd.DataFrame({
            'Ticker': ['AAPL'],
            'Date': pd.to_datetime(['2023-01-01']),
            'Open': [100.0],
            'High': [90.0],  # High is lower than low!
            'Low': [95.0],
            'Close': [102.0],
            'Volume': [1000]
        })
        # When pandera is available it raises SchemaError, otherwise stub raises ValueError
        with self.assertRaises(Exception):  # type: ignore
            OHLCVSchema.validate(invalid_df)

    def test_ticker_extraction(self):
        text = "I think NVDA and AAPL are going to the moon! CEO is doing great. FOMO is real."
        tickers = extract_tickers(text)
        self.assertIn('NVDA', tickers)
        self.assertIn('AAPL', tickers)
        self.assertNotIn('CEO', tickers)
        self.assertNotIn('FOMO', tickers)

        # Test POS filtering: 'I' or 'IT' if capitalized shouldn't pass if it's a pronoun
        # 'OR' as a conjunction shouldn't pass
        text2 = "I bought some TSLA OR maybe MSFT."
        tickers2 = extract_tickers(text2)
        self.assertIn('TSLA', tickers2)
        self.assertIn('MSFT', tickers2)
        self.assertNotIn('OR', tickers2)

if __name__ == '__main__':
    unittest.main()
