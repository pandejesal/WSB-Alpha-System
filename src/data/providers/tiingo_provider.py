import logging
import os

import pandas as pd
import requests

from src.data.providers.base import BaseDataProvider
from src.data.schemas import OHLCVSchema

logger = logging.getLogger(__name__)

class TiingoProvider(BaseDataProvider):
    """
    Fetches historical EOD data from Tiingo API.
    """
    def __init__(self):
        self.api_key = os.environ.get("TIINGO_API_KEY")

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        if not self.api_key:
            logger.warning("TIINGO_API_KEY not set. Skipping Tiingo provider.")
            return pd.DataFrame()

        all_data = []
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }

        for ticker in tickers:
            try:
                # EOD Endpoint
                url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
                params = {
                    'startDate': start_date,
                    'endDate': end_date,
                    'format': 'json'
                }
                response = requests.get(url, headers=headers, params=params, timeout=10)

                if response.status_code == 404:
                    logger.debug(f"Tiingo: Ticker {ticker} not found.")
                    continue

                response.raise_for_status()
                data = response.json()

                if not data:
                    continue

                df = pd.DataFrame(data)
                df['Ticker'] = ticker
                # Tiingo uses 'date' and adjusted prices
                if 'adjClose' in df.columns:
                    df.rename(columns={
                        'date': 'Date',
                        'adjOpen': 'Open',
                        'adjHigh': 'High',
                        'adjLow': 'Low',
                        'adjClose': 'Close',
                        'adjVolume': 'Volume'
                    }, inplace=True)
                else:
                    df.rename(columns={
                        'date': 'Date',
                        'open': 'Open',
                        'high': 'High',
                        'low': 'Low',
                        'close': 'Close',
                        'volume': 'Volume'
                    }, inplace=True)

                df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
                df = df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

                try:
                    df = OHLCVSchema.validate(df)
                    all_data.append(df)
                except Exception as e:
                    logger.warning(f"Schema validation failed for Tiingo ticker {ticker}: {e}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Tiingo fetch failed for {ticker}: {e}")
            except Exception as e:
                logger.warning(f"Tiingo unexpected error for {ticker}: {e}")

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("TiingoProvider does not provide sentiment feeds.")
