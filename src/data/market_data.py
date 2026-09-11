import hashlib
import logging
import os

import pandas as pd

from src.data.price_guards import assert_tradable_prices
from src.data.providers.chain import get_provider


class MarketDataManager:
    def __init__(self, provider=None, cache_dir: str = "database/cache"):
        self.logger = logging.getLogger(__name__)
        self.provider = provider or get_provider()
        self.cache_dir = cache_dir

    def _generate_cache_key(self, ticker: str, start_date: str, end_date: str, timeframe: str) -> str:
        key_str = f"{ticker}_{start_date}_{end_date}_{timeframe}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _apply_fill_policy(self, df: pd.DataFrame, ticker: str, fill_policy: str) -> pd.DataFrame:
        """Apply the fill policy after cache load/download (R-B3).

        ``ffill_only`` (default) never backfills: leading NaNs stay NaN so no
        pre-history prices are fabricated. ``ffill_bfill`` additionally
        backfills leading NaNs and always logs an opt-in warning.
        Filled-cell counts are emitted via ``logger.warning``.
        """
        na_before = int(df.isna().sum().sum())
        if fill_policy == "ffill_bfill":
            self.logger.warning(
                f"fill_policy='ffill_bfill' opted in for {ticker}: "
                f"backfilling leading NaNs may fabricate pre-history prices"
            )
            df = df.ffill().bfill()
        else:
            df = df.ffill()
        na_after = int(df.isna().sum().sum())
        filled = na_before - na_after
        if filled > 0:
            self.logger.warning(
                f"fill_policy='{fill_policy}' for {ticker}: "
                f"filled {filled} cells ({na_before} NaN before, {na_after} NaN after)"
            )
        # R-C1: post-fill tradability guard (single call site; covers both
        # cache-load and fresh-download paths since both flow through here).
        assert_tradable_prices(df, symbol=ticker)
        return df

    def fetch_data(self, ticker: str, start_date: str, end_date: str, timeframe: str = '1d', use_cache: bool = True, fill_policy: str = 'ffill_only') -> pd.DataFrame:
        if fill_policy not in ('ffill_only', 'ffill_bfill'):
            raise ValueError(
                f"unknown fill_policy {fill_policy!r} for {ticker}: "
                f"expected 'ffill_only' (default) or 'ffill_bfill'"
            )
        cache_dir = self.cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{self._generate_cache_key(ticker, start_date, end_date, timeframe)}.parquet")

        if use_cache and os.path.exists(cache_file):
            self.logger.info(f"Loading {ticker} from cache.")
            try:
                df = pd.read_parquet(cache_file)
                if not df.empty:
                    # R-B3: cache holds the RAW frame; fills apply after load.
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [col[0] for col in df.columns]
                    return self._apply_fill_policy(df, ticker, fill_policy)
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                self.logger.warning(f"Cache corrupted for {ticker}: {e}")

        self.logger.info(f"Downloading {ticker} from {start_date} to {end_date}")
        if hasattr(self.provider, 'get_historical_data'):
            df = self.provider.get_historical_data(ticker, start_date, end_date, timeframe)
        else:
            df = self.provider.fetch_ohlcv([ticker], start_date, end_date)
            if not df.empty and 'Ticker' in df.columns:
                df = df[df['Ticker'] == ticker]
                if 'Date' in df.columns:
                    df = df.set_index('Date')

        if df is None or df.empty:
            self.logger.error(f"Failed to fetch data for {ticker}")
            return pd.DataFrame()

        # R-B3: cache the RAW frame before any fill, so fills are never baked
        # into the cache.
        if use_cache:
            try:
                df.to_parquet(cache_file)
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                self.logger.warning(f"Failed to write cache for {ticker}: {e}")

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        return self._apply_fill_policy(df, ticker, fill_policy)
