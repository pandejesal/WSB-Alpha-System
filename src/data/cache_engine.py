import logging
import os
from datetime import datetime, timedelta

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

class CacheEngine:
    def __init__(self, db_path: str = "data/cache/market_data.duckdb"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = duckdb.connect(self.db_path)
        self._initialize_tables()

    def _initialize_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                ticker VARCHAR,
                date TIMESTAMP,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                UNIQUE(ticker, date)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sentiment (
                post_id VARCHAR PRIMARY KEY,
                post_date TIMESTAMP,
                ticker VARCHAR,
                title VARCHAR,
                sentiment_score DOUBLE,
                content VARCHAR,
                score DOUBLE
            )
        """)

    def get_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch cached OHLCV data."""
        if not tickers:
            return pd.DataFrame()

        tickers_str = ",".join([f"'{t}'" for t in tickers])
        query = f"""
            SELECT * FROM ohlcv
            WHERE ticker IN ({tickers_str})
            AND date >= '{start_date}' AND date <= '{end_date}'
        """
        try:
            return self.conn.execute(query).df()
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV from cache: {e}")
            return pd.DataFrame()

    def store_ohlcv(self, df: pd.DataFrame):
        """Store OHLCV data to cache."""
        if df.empty:
            return

        # Ensure column names match schema
        # Expected: Ticker, Date, Open, High, Low, Close, Volume
        df_to_store = df.copy()
        df_to_store.columns = [c.lower() for c in df_to_store.columns]

        required_cols = ['ticker', 'date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df_to_store.columns for col in required_cols):
            logger.warning("Dataframe missing required columns for OHLCV cache.")
            return

        df_to_store = df_to_store[required_cols]

        try:
            # DuckDB insert with ON CONFLICT DO NOTHING requires a slightly different syntax in some versions or we can use INSERT OR IGNORE
            self.conn.register('temp_df', df_to_store)
            self.conn.execute("""
                INSERT INTO ohlcv
                SELECT * FROM temp_df
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume
            """)
        except Exception as e:
            logger.error(f"Failed to store OHLCV to cache: {e}")

    def clear_expired_cache(self, ttl_days: int = 30):
        """Maintenance utility to clear old cache."""
        cutoff_date = (datetime.now() - timedelta(days=ttl_days)).strftime('%Y-%m-%d')
        try:
            # For backtesting we often need old data, but per requirements we provide this utility
            # We'll clear data older than TTL to demonstrate capability
            res = self.conn.execute(f"DELETE FROM ohlcv WHERE date < '{cutoff_date}'")
            logger.info(f"Cleared OHLCV cache older than {ttl_days} days.")
        except Exception as e:
            logger.error(f"Failed to clear expired cache: {e}")


    def get_sentiment(self, limit: int) -> pd.DataFrame:
        try:
            return self.conn.execute(f"SELECT * FROM sentiment ORDER BY post_date DESC LIMIT {limit}").df()
        except Exception:
            return pd.DataFrame()

    def store_sentiment(self, df: pd.DataFrame):
        if df.empty: return
        try:
            self.conn.register('temp_sent', df)
            self.conn.execute("""
                INSERT INTO sentiment
                SELECT * FROM temp_sent
                ON CONFLICT (post_id) DO NOTHING
            """)
        except Exception as e:
            logger.error(f"Failed to store sentiment to cache: {e}")

    def determine_missing_ranges(self, tickers: list[str], start_date: str, end_date: str) -> dict:
        """
        Returns a dict mapping tickers to missing date ranges, or full range if not present.
        For simplicity, this naive implementation checks if the start_date and end_date exist.
        If either is missing, it marks the ticker to fetch the whole range.
        A more sophisticated version would find exact gaps.
        """
        missing_ranges = {}
        if not tickers:
            return missing_ranges

        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        for ticker in tickers:
            query = f"SELECT MIN(date) as min_dt, MAX(date) as max_dt FROM ohlcv WHERE ticker = '{ticker}'"
            res = self.conn.execute(query).df()

            if res.empty or pd.isna(res.iloc[0]['min_dt']):
                missing_ranges[ticker] = (start_date, end_date)
            else:

                min_dt = pd.to_datetime(res.iloc[0]['min_dt'])
                max_dt = pd.to_datetime(res.iloc[0]['max_dt'])

                from datetime import timedelta
                if max_dt < end_dt - timedelta(days=30):
                    # Potentially delisted - skip this ticker
                    continue


                # If cached range doesn't cover requested range fully, we just fetch the requested range
                # to keep it simple and ensure we don't have gaps.
                if min_dt > start_dt or max_dt < end_dt:
                    missing_ranges[ticker] = (start_date, end_date)

        return missing_ranges
