import logging

import pandas as pd
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.data.providers.base import BaseDataProvider
from src.data.schemas import OHLCVSchema
from src.utils.config import config

logger = logging.getLogger(__name__)

class AlpacaDataProvider(BaseDataProvider):
    """
    Fetches historical EOD data from Alpaca API.
    Defaults to auto_adjust (ADJUSTED) for equities.
    """
    def __init__(self):
        self.api_key = config.api_keys.alpaca_api_key
        try:
            self.secret_key = config.api_keys.alpaca_secret_key.get_secret_value()
        except AttributeError:
            self.secret_key = config.api_keys.alpaca_secret_key
        self.stock_client = StockHistoricalDataClient(self.api_key, self.secret_key) if self.api_key else None
        self.crypto_client = CryptoHistoricalDataClient(self.api_key, self.secret_key) if self.api_key else None

    def _normalize_crypto_symbol(self, symbol: str) -> str:
        """Converts BTC-USD to BTC/USD for Alpaca Crypto API."""
        if "-" in symbol and ("USD" in symbol or "USDT" in symbol):
            parts = symbol.split("-")
            return f"{parts[0]}/{parts[1]}"
        return symbol

    def _denormalize_crypto_symbol(self, symbol: str) -> str:
        """Converts BTC/USD back to BTC-USD."""
        if "/" in symbol:
            return symbol.replace("/", "-")
        return symbol

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        if not self.stock_client:
            logger.warning("Alpaca data client not initialized. Check keys.")
            return pd.DataFrame()

        start_dt = pd.to_datetime(start_date).tz_localize("UTC")
        # Ensure end_date is inclusive by adding 1 day and making it UTC
        end_dt = pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1)

        crypto_tickers = [t for t in tickers if "-" in t and ("USD" in t)]
        equity_tickers = [t for t in tickers if t not in crypto_tickers]

        all_data = []

        if equity_tickers:
            try:
                req = StockBarsRequest(
                    symbol_or_symbols=equity_tickers,
                    timeframe=TimeFrame.Day,
                    start=start_dt,
                    end=end_dt,
                    adjustment="all" # equivalent to auto_adjust=True
                )
                bars = self.stock_client.get_stock_bars(req)
                if bars and bars.df is not None and not bars.df.empty:
                    df = bars.df.reset_index()
                    df.rename(columns={'symbol': 'Ticker', 'timestamp': 'Date'}, inplace=True)
                    df['Date'] = pd.to_datetime(df['Date']).dt.tz_convert(None) # Remove TZ for schema
                    df = df[['Ticker', 'Date', 'open', 'high', 'low', 'close', 'volume']]
                    df.columns = ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                    try:
                        df = OHLCVSchema.validate(df)
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Schema validation failed for Alpaca equities: {e}")
            except Exception as e:
                logger.warning(f"Alpaca equity fetch failed: {e}")

        if crypto_tickers:
            try:
                alpaca_crypto = [self._normalize_crypto_symbol(t) for t in crypto_tickers]
                req = CryptoBarsRequest(
                    symbol_or_symbols=alpaca_crypto,
                    timeframe=TimeFrame.Day,
                    start=start_dt,
                    end=end_dt
                )
                bars = self.crypto_client.get_crypto_bars(req)
                if bars and bars.df is not None and not bars.df.empty:
                    df = bars.df.reset_index()
                    df.rename(columns={'symbol': 'Ticker', 'timestamp': 'Date'}, inplace=True)
                    df['Ticker'] = df['Ticker'].apply(self._denormalize_crypto_symbol)
                    df['Date'] = pd.to_datetime(df['Date']).dt.tz_convert(None)
                    df = df[['Ticker', 'Date', 'open', 'high', 'low', 'close', 'volume']]
                    df.columns = ['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                    try:
                        df = OHLCVSchema.validate(df)
                        all_data.append(df)
                    except Exception as e:
                        logger.warning(f"Schema validation failed for Alpaca crypto: {e}")
            except Exception as e:
                logger.warning(f"Alpaca crypto fetch failed: {e}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("AlpacaDataProvider does not provide sentiment feeds.")
