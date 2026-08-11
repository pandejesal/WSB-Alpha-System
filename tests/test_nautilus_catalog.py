import pytest
import pandas as pd
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.data.nautilus_catalog import NautilusCatalogBuilder
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog


class _FakeProvider:
    """Stands in for the DataProviderChain so tests never touch the network."""

    def __init__(self, df):
        self.df = df

    def fetch_ohlcv(self, tickers, start_date, end_date):
        if self.df is None:
            raise Exception("Provider unavailable")
        return self.df


def _ohlcv_frame(ticker, dates, open_px, close_px):
    return pd.DataFrame({
        'Date': pd.to_datetime(dates),
        'Open': open_px,
        'High': [p * 1.05 for p in open_px],
        'Low': [p * 0.95 for p in open_px],
        'Close': close_px,
        'Volume': 2_000_000,
        'Ticker': ticker,
    })


def test_catalog_builder_skips_failed_tickers():
    with tempfile.TemporaryDirectory() as temp_dir:
        builder = NautilusCatalogBuilder(catalog_path=temp_dir)

        # Provider chain fails: failed tickers are skipped, no fabricated mock
        # bars are persisted (honest fallback behavior).
        with patch('src.data.nautilus_catalog.get_provider', return_value=_FakeProvider(None)):
            builder.build_catalog(["SPY"], start_date="2018-01-01", end_date="2018-01-05")

        # No bar data should have been written.
        assert not list(Path(temp_dir).rglob("*.parquet"))


def test_catalog_builder_success():
    with tempfile.TemporaryDirectory() as temp_dir:
        builder = NautilusCatalogBuilder(catalog_path=temp_dir)

        frame = _ohlcv_frame(
            "AAPL",
            ['2018-01-01 00:00:00-05:00'],
            [150.0],
            [150.0],
        )
        with patch('src.data.nautilus_catalog.get_provider', return_value=_FakeProvider(frame)):
            builder.build_catalog(["AAPL"], start_date="2018-01-01", end_date="2018-01-02")

        catalog = ParquetDataCatalog(temp_dir)
        instrument_id = InstrumentId(Symbol("AAPL"), Venue("NASDAQ"))
        bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")

        bars = catalog.bars(instrument_ids=[instrument_id])
        assert len(bars) == 1

        first_bar = bars[0]
        # Verify UTC timezone conversion (America/New_York midnight -> 05:00 UTC)
        dt = pd.Timestamp(first_bar.ts_init, unit='ns', tz='UTC')
        assert dt == pd.Timestamp('2018-01-01 05:00:00+00:00', tz='UTC')

        # Verify native oracle types were preserved
        assert hasattr(first_bar.open, 'as_double')
        assert hasattr(first_bar.volume, 'as_double')
        assert first_bar.open.as_double() == 150.0
        assert first_bar.ts_event > 0
