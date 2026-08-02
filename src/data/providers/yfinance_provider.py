import pandera as pa
from src.data.schemas import OHLCVSchema
import yfinance as yf
import pandas as pd
import time
import logging
from typing import List
from .base import BaseDataProvider
from src.data.cache_engine import CacheEngine

logger = logging.getLogger(__name__)

class YFinanceProvider(BaseDataProvider):
    def __init__(self, cache_engine: CacheEngine = None):
        self.cache = cache_engine or CacheEngine()

    def fetch_ohlcv(self, tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        missing_ranges = self.cache.determine_missing_ranges(tickers, start_date, end_date)

        tickers_to_fetch = list(missing_ranges.keys())
        all_data = []

        # Load available data from cache first
        cached_tickers = [t for t in tickers if t not in tickers_to_fetch]
        if cached_tickers:
            cached_df = self.cache.get_ohlcv(cached_tickers, start_date, end_date)
            # rename to standard capital case for the application
            rename_map = {c: c.capitalize() for c in cached_df.columns if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
            cached_df.rename(columns=rename_map, inplace=True)
            all_data.append(cached_df)

        if not tickers_to_fetch:
            if not all_data:
                return pd.DataFrame()
            return pd.concat(all_data, ignore_index=True)

        chunk_size = 50

        for i in range(0, len(tickers_to_fetch), chunk_size):
            chunk = tickers_to_fetch[i:i+chunk_size]
            for attempt in range(3):
                try:
                    df = yf.download(chunk, start=start_date, end=end_date, progress=False, auto_adjust=True)
                    if isinstance(df.columns, pd.MultiIndex):
                        df = df.stack(level=1, future_stack=True).reset_index()
                        df.rename(columns={'level_1': 'Ticker', 'Price': 'Ticker', 'Ticker': 'Ticker'}, inplace=True)
                        if 'Ticker' not in df.columns and 'level_1' in df.columns:
                             df.rename(columns={'level_1': 'Ticker'}, inplace=True)
                        if 'Date' in df.columns:
                            pass
                        elif 'Datetime' in df.columns:
                            df.rename(columns={'Datetime': 'Date'}, inplace=True)
                    else:
                        df = df.reset_index()
                        df['Ticker'] = chunk[0]


                    if not df.empty:
                        # Standardize before validation
                        cols = df.columns.tolist()
                        rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
                        df.rename(columns=rename_map, inplace=True)

                        # Validate before storing
                        from src.data.schemas import OHLCVSchema
                        df = OHLCVSchema.validate(df)

                        all_data.append(df)
                        self.cache.store_ohlcv(df)

                    break
                except Exception as e:
                    logger.error(f"YFinance batch download failed for chunk {i}: {e}")
                    time.sleep(2 ** attempt)

        if not all_data:
            return pd.DataFrame()

        final_df = pd.concat(all_data, ignore_index=True)
        # Standardize column names
        cols = final_df.columns.tolist()
        rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
        final_df.rename(columns=rename_map, inplace=True)
        return final_df

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("YFinance does not provide sentiment feeds in this abstraction.")
