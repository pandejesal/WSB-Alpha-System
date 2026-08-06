import pytest
import pandas as pd
from pathlib import Path
import tempfile
from unittest.mock import patch

from src.data.nautilus_catalog import NautilusCatalogBuilder
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.data import BarType
from nautilus_trader.persistence.catalog import ParquetDataCatalog

def test_catalog_builder_mock_fallback_and_types():
    with tempfile.TemporaryDirectory() as temp_dir:
        builder = NautilusCatalogBuilder(catalog_path=temp_dir)

        # Test fallback to mock data by passing an invalid ticker or mocking yf
        # yf.download can be bypassed using patch to ensure it fails
        with patch('yfinance.download', side_effect=Exception("Mock exception")):
            builder.build_catalog(["SPY"], start_date="2018-01-01", end_date="2018-01-05")

        assert builder.mock_used is True

        # Verify persistence
        catalog = ParquetDataCatalog(temp_dir)

        instrument_id = InstrumentId(Symbol("SPY"), Venue("NASDAQ"))
        bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")

        bars = catalog.bars(bar_types=[bar_type])
        assert len(bars) > 0, "Bars should be persisted to catalog"

        # Verify UTC enforcement and native types
        first_bar = bars[0]
        assert first_bar.bar_type == bar_type

        # check native types
        assert hasattr(first_bar.open, 'as_double')
        assert hasattr(first_bar.volume, 'as_double')

        # Ensure timestamps are valid
        assert first_bar.ts_event > 0

        # Since it's mock data, Open should be 100.0
        assert first_bar.open.as_double() == 100.0

def test_catalog_builder_success():
    with tempfile.TemporaryDirectory() as temp_dir:
        builder = NautilusCatalogBuilder(catalog_path=temp_dir)

        # Mock yf.download to return a valid DataFrame instead of making network calls
        mock_df = pd.DataFrame(index=[pd.Timestamp('2018-01-01', tz='America/New_York')])
        mock_df['Open'] = 150.0
        mock_df['High'] = 155.0
        mock_df['Low'] = 145.0
        mock_df['Close'] = 150.0
        mock_df['Volume'] = 2000000

        with patch('yfinance.download', return_value=mock_df):
            builder.build_catalog(["AAPL"], start_date="2018-01-01", end_date="2018-01-02")

        assert builder.mock_used is False

        catalog = ParquetDataCatalog(temp_dir)
        instrument_id = InstrumentId(Symbol("AAPL"), Venue("NASDAQ"))
        bar_type = BarType.from_str(f"{instrument_id}-1-DAY-LAST-EXTERNAL")

        bars = catalog.bars(bar_types=[bar_type])
        assert len(bars) == 1

        first_bar = bars[0]
        # Verify timezone conversion to UTC
        dt = pd.Timestamp(first_bar.ts_init, unit='ns', tz='UTC')
        # America/New_York at midnight is UTC 05:00
        assert dt == pd.Timestamp('2018-01-01 05:00:00+00:00', tz='UTC')
