import logging
from pathlib import Path

import pandas as pd
import yfinance as yf
from src.data.providers.chain import get_provider
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.persistence.catalog import ParquetDataCatalog

logger = logging.getLogger(__name__)

class NautilusCatalogBuilder:
    def __init__(self, catalog_path: str = "nautilus_data_catalog"):
        self.catalog_path = Path(catalog_path)
        self.catalog = ParquetDataCatalog(self.catalog_path.as_posix())
        self.mock_used = False

    def build_catalog(self, tickers: list[str], start_date: str = "2018-01-01", end_date: str = None):
        if end_date is None:
            end_date = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")

        provider = get_provider()

        for ticker in tickers:
            try:
                df = provider.fetch_ohlcv([ticker], start_date, end_date)
                if df.empty:
                    raise Exception(f"No data returned for {ticker}")

                if 'Ticker' in df.columns:
                    df = df[df['Ticker'] == ticker]
                if 'Date' in df.columns:
                    df = df.set_index('Date')

                logger.info(f"Successfully downloaded {len(df)} rows for {ticker}")
                self._process_and_write(ticker, df)
            except Exception as e:
                logger.warning(f"yfinance download failed for {ticker}: {e!s}. Falling back to mock data.")
                self.mock_used = True
                df_mock = self._generate_mock_data(start_date, end_date)
                self._process_and_write(ticker, df_mock)

    def _generate_mock_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.bdate_range(start=start_date, end=end_date, tz="UTC")
        df = pd.DataFrame(index=dates)
        df['Open'] = 100.0
        df['High'] = 105.0
        df['Low'] = 95.0
        df['Close'] = 100.0
        df['Volume'] = 1000000
        return df

    def _process_and_write(self, ticker: str, df: pd.DataFrame):
        venue = Venue("NASDAQ")
        symbol = Symbol(ticker)
        instrument_id = InstrumentId(symbol, venue)
        bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")

        bars = []
        for dt, row in df.iterrows():
            if dt.tz is None:
                dt = dt.tz_localize("UTC")
            else:
                dt = dt.tz_convert("UTC")

            ts = dt_to_unix_nanos(dt)

            # Using native objects
            bar = Bar(
                bar_type=bar_type,
                open=Price.from_str(str(float(row['Open'].iloc[0] if isinstance(row['Open'], pd.Series) else row['Open']))),
                high=Price.from_str(str(float(row['High'].iloc[0] if isinstance(row['High'], pd.Series) else row['High']))),
                low=Price.from_str(str(float(row['Low'].iloc[0] if isinstance(row['Low'], pd.Series) else row['Low']))),
                close=Price.from_str(str(float(row['Close'].iloc[0] if isinstance(row['Close'], pd.Series) else row['Close']))),
                volume=Quantity.from_int(int(row['Volume'].iloc[0] if isinstance(row['Volume'], pd.Series) else row['Volume'])),
                ts_event=ts,
                ts_init=ts
            )
            bars.append(bar)

        if bars:
            self.catalog.write_data(bars)
            logger.info(f"Wrote {len(bars)} bars to catalog for {ticker}")
