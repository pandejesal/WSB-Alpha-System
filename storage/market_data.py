import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging
import hashlib
import os

class MarketDataManager:
    def __init__(self, provider=None):
        self.logger = logging.getLogger(__name__)
        # Fallback to yfinance if no provider is passed.
        self.provider = provider

    def _generate_cache_key(self, ticker: str, start_date: str, end_date: str, timeframe: str) -> str:
        key_str = f"{ticker}_{start_date}_{end_date}_{timeframe}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def fetch_data(self, ticker: str, start_date: str, end_date: str, timeframe: str = '1d', use_cache: bool = True) -> pd.DataFrame:
        """
        Fetches data, handles basic caching, and ensures minimum data quality
        (e.g., handles missing values, ensures datetime index).
        """
        # A simple local file cache for this iteration. In a real system, DuckDB/Polars would be used.
        cache_dir = "database/cache"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{self._generate_cache_key(ticker, start_date, end_date, timeframe)}.parquet")

        if use_cache and os.path.exists(cache_file):
            self.logger.info(f"Loading {ticker} from cache.")
            try:
                df = pd.read_parquet(cache_file)
                if not df.empty:
                    return df
            except Exception as e:
                self.logger.warning(f"Cache corrupted for {ticker}: {e}")

        self.logger.info(f"Downloading {ticker} from {start_date} to {end_date}")
        if self.provider:
            df = self.provider.get_historical_data(ticker, start_date, end_date, timeframe)
        else:
            df = yf.download(ticker, start=start_date, end=end_date, interval=timeframe, progress=False)

        if df is None or df.empty:
            self.logger.error(f"Failed to fetch data for {ticker}")
            return pd.DataFrame()

        # Data Quality Checks
        df = df.ffill().bfill() # Basic forward/back fill for missing prices

        # Flatten MultiIndex columns if yfinance returned them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        if use_cache:
            try:
                df.to_parquet(cache_file)
            except Exception as e:
                self.logger.warning(f"Failed to write cache for {ticker}: {e}")

        return df
