import logging

import pandas as pd

from .base import BaseDataProvider
from .yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)

class OpenBBProvider(BaseDataProvider):
    def __init__(self):
        self.use_openbb = False
        self.fallback_provider = YFinanceProvider()
        try:
            from openbb import obb
            self.use_openbb = True
            self.obb = obb
        except ImportError:
            logger.info("OpenBB not installed. OpenBBProvider will fall back to YFinanceProvider.")

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        if self.use_openbb:
            try:
                # OpenBB SDK logic for fetching historical equity data
                all_data = []
                for ticker in tickers:
                    res = self.obb.equity.price.historical(symbol=ticker, start_date=start_date, end_date=end_date, provider="yfinance")
                    if res and hasattr(res, 'to_df'):
                        df = res.to_df()
                        df['Ticker'] = ticker
                        all_data.append(df)

                if not all_data:
                    return pd.DataFrame()

                final_df = pd.concat(all_data, ignore_index=True)
                cols = final_df.columns.tolist()
                rename_map = {c: c.capitalize() for c in cols if c.lower() in ['open', 'high', 'low', 'close', 'volume', 'date', 'ticker']}
                final_df.rename(columns=rename_map, inplace=True)
                return final_df

            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                logger.warning(f"OpenBB fetch failed, falling back to yfinance: {e}")
                return self.fallback_provider.fetch_ohlcv(tickers, start_date, end_date)
        else:
            return self.fallback_provider.fetch_ohlcv(tickers, start_date, end_date)

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        # OpenBB sentiment logic requires API keys for specific providers (e.g., finbrain), we fallback.
        logger.info("OpenBB sentiment not configured with premium keys, falling back.")
        return pd.DataFrame()
