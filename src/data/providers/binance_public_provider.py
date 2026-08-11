import logging

import pandas as pd
import requests

from src.data.providers.base import BaseDataProvider
from src.data.schemas import OHLCVSchema

logger = logging.getLogger(__name__)

class BinancePublicProvider(BaseDataProvider):
    """
    Fetches historical OHLCV data from Binance Public Data API (US-safe).
    https://data-api.binance.vision/api/v3/klines
    Only processes crypto symbols.
    """
    def _is_crypto(self, ticker: str) -> bool:
        return "-" in ticker and ("USD" in ticker or "USDT" in ticker)

    def _normalize_symbol(self, ticker: str) -> str:
        # Binance format: BTCUSDT
        parts = ticker.split("-")
        return f"{parts[0]}USDT"

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        crypto_tickers = [t for t in tickers if self._is_crypto(t)]
        if not crypto_tickers:
            return pd.DataFrame()

        all_data = []
        url = "https://data-api.binance.vision/api/v3/klines"

        start_ts = int(pd.to_datetime(start_date).tz_localize("UTC").timestamp() * 1000)
        # End date inclusive
        end_ts = int((pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1)).timestamp() * 1000)

        for ticker in crypto_tickers:
            symbol = self._normalize_symbol(ticker)
            try:
                params = {
                    "symbol": symbol,
                    "interval": "1d",
                    "startTime": start_ts,
                    "endTime": end_ts,
                    "limit": 1000
                }
                # VERIFY: Binance public API usage. Weight 1200 per minute limit.
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    continue

                # Columns: [Open time, Open, High, Low, Close, Volume, Close time, ...]
                df = pd.DataFrame(data, columns=["Open time", "Open", "High", "Low", "Close", "Volume", "Close time", "QAV", "NAT", "TBBAV", "TBQAV", "Ignore"])
                df['Ticker'] = ticker
                df['Date'] = pd.to_datetime(df['Open time'], unit='ms')

                # Convert to float
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = df[col].astype(float)

                df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

                try:
                    df = OHLCVSchema.validate(df)
                    all_data.append(df)
                except Exception as e:
                    logger.warning(f"Schema validation failed for Binance ticker {ticker}: {e}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Binance fetch failed for {ticker}: {e}")
            except Exception as e:
                logger.warning(f"Binance unexpected error for {ticker}: {e}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("BinancePublicProvider does not provide sentiment feeds.")
