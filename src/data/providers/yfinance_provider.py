import logging
import os

import pandas as pd
import yfinance as yf

from src.data.cache_engine import CacheEngine

from .base import BaseDataProvider

logger = logging.getLogger(__name__)

class YFinanceProvider(BaseDataProvider):
    def __init__(self, cache_engine: CacheEngine = None):
        self.cache = cache_engine or CacheEngine()

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
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

        if tickers_to_fetch:
            try:
                df = yf.download(tickers_to_fetch, start=start_date, end=end_date, progress=False, auto_adjust=True, threads=True)
                if isinstance(df.columns, pd.MultiIndex):
                    df = df.stack(level=1, future_stack=True).reset_index()
                    df.rename(columns={'level_1': 'Ticker', 'Price': 'Ticker', 'Ticker': 'Ticker'}, inplace=True)
                    if 'Ticker' not in df.columns and 'level_1' in df.columns:
                        df.rename(columns={'level_1': 'Ticker'}, inplace=True)
                    if 'Date' not in df.columns and 'Datetime' in df.columns:
                        df.rename(columns={'Datetime': 'Date'}, inplace=True)
                else:
                    df = df.reset_index()
                    df['Ticker'] = tickers_to_fetch[0]

                if not df.empty:
                    cols = df.columns.tolist()
                    rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
                    df.rename(columns=rename_map, inplace=True)
                    from src.data.schemas import OHLCVSchema
                    df = OHLCVSchema.validate(df)
                    all_data.append(df)
                    self.cache.store_ohlcv(df)
            except Exception as e:
                logger.error(f"Batch download failed: {e}")
                # Fallback to smaller chunks
                chunk_size = 100
                for i in range(0, len(tickers_to_fetch), chunk_size):
                    chunk = tickers_to_fetch[i:i+chunk_size]
                    try:
                        df = yf.download(chunk, start=start_date, end=end_date, progress=False, auto_adjust=True)
                        if isinstance(df.columns, pd.MultiIndex):
                            df = df.stack(level=1, future_stack=True).reset_index()
                            df.rename(columns={'level_1': 'Ticker', 'Price': 'Ticker', 'Ticker': 'Ticker'}, inplace=True)
                            if 'Ticker' not in df.columns and 'level_1' in df.columns:
                                df.rename(columns={'level_1': 'Ticker'}, inplace=True)
                            if 'Date' not in df.columns and 'Datetime' in df.columns:
                                df.rename(columns={'Datetime': 'Date'}, inplace=True)
                        else:
                            df = df.reset_index()
                            df['Ticker'] = chunk[0]
                        if not df.empty:
                            cols = df.columns.tolist()
                            rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
                            df.rename(columns=rename_map, inplace=True)
                            df = OHLCVSchema.validate(df)
                            all_data.append(df)
                            self.cache.store_ohlcv(df)
                    except Exception as e:
                        logger.debug(f"Failed to cache OHLCV: {e}")
        if not all_data:
            return pd.DataFrame()

        final_df = pd.concat(all_data, ignore_index=True)

        # After fetching df, before storing to cache
        min_history_days = 252
        if 'Ticker' in final_df.columns:
            ticker_counts = final_df.groupby('Ticker').size()
            valid_tickers = ticker_counts[ticker_counts >= min_history_days].index.tolist()
            final_df = final_df[final_df['Ticker'].isin(valid_tickers)]

# Standardize column names
        cols = final_df.columns.tolist()
        rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
        final_df.rename(columns=rename_map, inplace=True)

        if 'Ticker' in final_df.columns and len(final_df['Ticker'].unique()) < 20:
            import json
            universe_path = "config/universe.json"
            if os.path.exists(universe_path):
                try:
                    with open(universe_path, "r") as f:
                        universe = json.load(f).get("tickers", [])
                    fallback_tickers = [t for t in universe if t not in tickers][:20]
                    if fallback_tickers:
                        df_fb = yf.download(fallback_tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)
                        if isinstance(df_fb.columns, pd.MultiIndex):
                            df_fb = df_fb.stack(level=1, future_stack=True).reset_index()
                            df_fb.rename(columns={'level_1': 'Ticker', 'Price': 'Ticker', 'Ticker': 'Ticker'}, inplace=True)
                            if 'Date' not in df_fb.columns and 'Datetime' in df_fb.columns:
                                df_fb.rename(columns={'Datetime': 'Date'}, inplace=True)
                        else:
                            df_fb = df_fb.reset_index()
                            df_fb['Ticker'] = fallback_tickers[0]
                        cols_fb = df_fb.columns.tolist()
                        rename_map_fb = {c: c.capitalize() for c in cols_fb if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
                        df_fb.rename(columns=rename_map_fb, inplace=True)
                        final_df = pd.concat([final_df, df_fb], ignore_index=True)
                except Exception as e:
                    logger.error(f"Fallback universe failed: {e}")

        return final_df

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("YFinance does not provide sentiment feeds in this abstraction.")
