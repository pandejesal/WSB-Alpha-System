"""R-B3: fill-policy + cache discipline for MarketDataManager (4 tests)."""

import glob
import logging
import os

import pandas as pd
import pytest

from src.data.market_data import MarketDataManager


class GapProvider:
    """Fake provider returning a frame with leading + interior NaNs."""

    def get_historical_data(self, ticker, start_date, end_date, timeframe="1d"):
        idx = pd.date_range("2020-01-01", periods=5, freq="D")
        return pd.DataFrame(
            {"close": [float("nan"), float("nan"), 100.0, float("nan"), 102.0]},
            index=idx,
        )


@pytest.fixture
def isolated_manager(tmp_path, monkeypatch):
    """Run inside tmp so the repo-local database/cache stays untouched."""
    monkeypatch.chdir(tmp_path)
    return MarketDataManager(provider=GapProvider())


def test_rb3_default_never_backfills_leading_nan(isolated_manager):
    df = isolated_manager.fetch_data("TST", "2020-01-01", "2020-01-05")
    assert df["close"].iloc[0] != df["close"].iloc[0]  # stays NaN
    assert df["close"].iloc[1] != df["close"].iloc[1]  # stays NaN
    assert df["close"].iloc[2] == 100.0
    assert df["close"].iloc[3] == 100.0  # interior ffill still works
    assert df["close"].iloc[4] == 102.0


def test_rb3_opt_in_bfill_warns(isolated_manager, caplog):
    with caplog.at_level(logging.WARNING, logger="src.data.market_data"):
        df = isolated_manager.fetch_data(
            "TST", "2020-01-01", "2020-01-05", fill_policy="ffill_bfill"
        )
    assert df["close"].iloc[0] == 100.0  # leading backfilled under opt-in
    assert any("ffill_bfill" in r.message for r in caplog.records)


def test_rb3_cache_stores_raw_frame(isolated_manager):
    isolated_manager.fetch_data("TST", "2020-01-01", "2020-01-05")
    cached = glob.glob(os.path.join("database", "cache", "*.parquet"))
    assert len(cached) == 1
    raw = pd.read_parquet(cached[0])
    # Raw cached frame keeps its NaNs — fills are never baked into cache.
    assert int(raw.isna().sum().sum()) == 3


def test_rb3_filled_cell_counts_logged(isolated_manager, caplog):
    with caplog.at_level(logging.WARNING, logger="src.data.market_data"):
        isolated_manager.fetch_data("TST", "2020-01-01", "2020-01-05")
    fill_records = [r for r in caplog.records if "filled" in r.message]
    assert fill_records
    assert any("1 cells" in r.message or "1 cell" in r.message for r in fill_records)
