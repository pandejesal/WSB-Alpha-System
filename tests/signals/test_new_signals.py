import pytest
import pandas as pd
import numpy as np

from src.ops.signals import (
    get_us_lowvol_top30_signal,
    get_us_pead_top5_signal,
    get_breakout_burst_signal
)

def test_lowvol_top30_fails_closed():
    res = get_us_lowvol_top30_signal(pd.DataFrame(), [])
    assert res["signal"] == "FLAT"
    assert res["warning"] == "data_unavailable"

def test_lowvol_top30_ranks_correctly():
    # Need 21+ periods and 30+ tickers for full logic, but let's test with a minimal df
    dates = pd.date_range("2023-01-01", periods=25, freq="B")

    data = {}
    for i in range(35):
        # lower i = lower vol (slope vs noise)
        np.random.seed(i)
        base = np.linspace(100, 200, 25)
        noise = np.random.randn(25) * i
        data[f"TICK{i}"] = base + noise

    df = pd.DataFrame(data, index=dates)

    res = get_us_lowvol_top30_signal(df, list(df.columns))

    assert res["signal"] == "LONG"
    assert len(res["targets"]) == 30
    # TICK0 should have lowest vol, should be in targets
    assert "TICK0" in res["targets"]

def test_pead_top5_fails_closed():
    res = get_us_pead_top5_signal(pd.DataFrame(), [])
    assert res["signal"] == "FLAT"

def test_breakout_burst_fails_closed():
    res = get_breakout_burst_signal(pd.DataFrame(), [])
    assert res["signal"] == "FLAT"
    assert res["warning"] == "data_unavailable"

def test_breakout_burst_logic():
    dates = pd.date_range("2023-01-01", periods=25, freq="B")

    # We need a breakout on the last day or recent day.
    # We want close > high_20d, ret >= 4%, vol >= 1.5 * avg_vol_20d

    closes = np.linspace(100, 110, 25)
    vols = np.linspace(1000, 1100, 25)

    closes[-1] = 120 # 120/110 = ~9% gain. high_20d = 110.
    vols[-1] = 5000 # huge volume

    df = pd.DataFrame({
        "Close": closes,
        "Volume": vols
    }, index=dates)
    df.columns = pd.MultiIndex.from_product([df.columns, ["MOCK1"]])

    res = get_breakout_burst_signal(df, ["MOCK1"])

    assert res["signal"] == "LONG"
    assert "MOCK1" in res["targets"]

def test_pead_top5_logic(monkeypatch):
    # We will mock yfinance get_earnings_dates
    class MockTicker:
        def __init__(self, ticker):
            self.ticker = ticker
        def get_earnings_dates(self, limit=100):
            # earnings 2 days ago
            dates = pd.date_range("2023-12-10", periods=5, freq="D")
            df = pd.DataFrame({
                "Reported EPS": [1.0, 1.0, 1.0, 1.0, 1.0],
                "Surprise(%)": [0.1, -0.1, 0.2, 0.0, 0.5]
            }, index=dates)
            return df

    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", MockTicker)

    dates = pd.date_range("2023-12-01", periods=15, freq="B")
    df = pd.DataFrame({
        "Close": np.linspace(100, 110, 15),
    }, index=dates)
    df.columns = pd.MultiIndex.from_product([df.columns, ["AAPL"]])

    # 2023-12-15 is last date
    res = get_us_pead_top5_signal(df, ["AAPL"])

    assert res["signal"] == "LONG"
    assert "AAPL" in res["targets"]
