import logging
import pandas as pd
from typing import List

from src.data.providers.base import BaseDataProvider
from src.data.providers.alpaca_data_provider import AlpacaDataProvider
from src.data.providers.tiingo_provider import TiingoProvider
from src.data.providers.binance_public_provider import BinancePublicProvider
from src.data.providers.yfinance_provider import YFinanceProvider
from src.data.cache_engine import CacheEngine

logger = logging.getLogger(__name__)

class DataProviderChain(BaseDataProvider):
    """
    Implements a multi-provider fallback chain for OHLCV data.
    Order: Alpaca -> Tiingo -> Binance (public) -> YFinance
    Integrates with CacheEngine.
    """
    def __init__(self, cache_engine: CacheEngine = None):
        self.cache = cache_engine or CacheEngine()

        # Initialize providers (lazy load logic where applicable is inside them)
        self.providers: List[BaseDataProvider] = [
            AlpacaDataProvider(),
            TiingoProvider(),
            BinancePublicProvider(),
            YFinanceProvider(cache_engine=self.cache) # YFinance still manages its own cache interactions optionally, but we will handle top-level caching
        ]

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        missing_ranges = self.cache.determine_missing_ranges(tickers, start_date, end_date)
        tickers_to_fetch = list(missing_ranges.keys())

        all_data = []

        # Load available data from cache first
        cached_tickers = [t for t in tickers if t not in tickers_to_fetch]
        if cached_tickers:
            cached_df = self.cache.get_ohlcv(cached_tickers, start_date, end_date)
            rename_map = {c: c.capitalize() for c in cached_df.columns if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
            cached_df.rename(columns=rename_map, inplace=True)
            all_data.append(cached_df)

        if not tickers_to_fetch:
            if not all_data:
                return pd.DataFrame()
            return pd.concat(all_data, ignore_index=True)

        # Fallback chain for missing data
        remaining_tickers = set(tickers_to_fetch)
        fetched_dfs = []

        for provider in self.providers:
            if not remaining_tickers:
                break

            current_batch = list(remaining_tickers)
            provider_name = provider.__class__.__name__
            logger.info(f"Attempting fetch with {provider_name} for {len(current_batch)} tickers.")

            try:
                df = provider.fetch_ohlcv(current_batch, start_date, end_date)
                if df is not None and not df.empty:
                    # Determine which tickers were successfully fetched
                    fetched_tickers = set(df['Ticker'].unique())
                    logger.info(f"{provider_name} successfully fetched {len(fetched_tickers)} tickers.")

                    fetched_dfs.append(df)

                    # Store successfully fetched data in cache (YFinance does it internally, but we can safely write through for others)
                    if not isinstance(provider, YFinanceProvider):
                        self.cache.store_ohlcv(df)

                    remaining_tickers -= fetched_tickers
                else:
                    logger.debug(f"{provider_name} returned empty DataFrame.")
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")

        if fetched_dfs:
            combined_fetched = pd.concat(fetched_dfs, ignore_index=True)
            all_data.append(combined_fetched)

        if remaining_tickers:
            logger.warning(f"Failed to fetch data for {len(remaining_tickers)} tickers across all providers: {list(remaining_tickers)[:10]}")

        if not all_data:
            return pd.DataFrame()

        final_df = pd.concat(all_data, ignore_index=True)
        return final_df

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("Chain does not aggregate sentiment yet.")

_provider_instance = None

def get_provider() -> DataProviderChain:
    """Singleton accessor for the provider chain."""
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = DataProviderChain()
    return _provider_instance
