import pytest
import pandas as pd
import numpy as np
import os
import json
import tempfile
import shutil

from src.signals.engine import SignalEngine
from src.signals.api import generate_signals
from src.signals.schemas import SignalsReport

@pytest.fixture
def dummy_spy_data():
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    df = pd.DataFrame({
        "Open": np.linspace(100, 200, 250),
        "High": np.linspace(101, 201, 250),
        "Low": np.linspace(99, 199, 250),
        "Close": np.linspace(100.5, 200.5, 250),
        "Volume": np.random.randint(1000, 10000, 250)
    }, index=dates)
    return df

@pytest.fixture
def dummy_btc_data():
    dates = pd.date_range("2023-01-01", periods=250, freq="D")
    df = pd.DataFrame({
        "Open": np.linspace(20000, 30000, 250),
        "High": np.linspace(20500, 30500, 250),
        "Low": np.linspace(19500, 29500, 250),
        "Close": np.linspace(20200, 30200, 250),
        "Volume": np.random.randint(10, 100, 250)
    }, index=dates)
    return df

@pytest.fixture
def dummy_momentum_data():
    dates = pd.date_range("2023-01-01", periods=250, freq="B")
    tickers = ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA", "NVDA"]
    data = {}
    for i, t in enumerate(tickers):
        df = pd.DataFrame({
            "Close": np.linspace(100 + i*10, 200 + i*20, 250),
        }, index=dates)
        data[t] = df
    return data

@pytest.fixture(autouse=True)
def mock_ops_dir(monkeypatch):
    test_dir = tempfile.mkdtemp()

    original_makedirs = os.makedirs
    def mock_makedirs(name, mode=0o777, exist_ok=False):
        if name == "docs/data/ops":
            original_makedirs(test_dir, mode, exist_ok)
        else:
            original_makedirs(name, mode, exist_ok)

    monkeypatch.setattr(os, "makedirs", mock_makedirs)

    # We patch join specifically to redirect docs/data/ops to test_dir
    original_join = os.path.join
    def mock_join(*args):
        if args and args[0] == "docs/data/ops":
            return original_join(test_dir, *args[1:])
        return original_join(*args)

    monkeypatch.setattr(os.path, "join", mock_join)

    yield test_dir
    shutil.rmtree(test_dir)

def test_signal_engine_full_run(dummy_spy_data, dummy_btc_data, dummy_momentum_data, monkeypatch):
    import pandas as pd
    import src.ops.signals as signals_mod

    class FakeTickerEmpty:
        def __init__(self, ticker):
            self.ticker = ticker
        def get_earnings_dates(self, limit=100):
            return pd.DataFrame()

    monkeypatch.setattr(signals_mod.yf, "Ticker", FakeTickerEmpty)

    engine = SignalEngine()

    market_data = {
        "SPY": dummy_spy_data,
        "BTC-USD": dummy_btc_data,
        **dummy_momentum_data
    }

    run_date = "2023-12-15T00:00:00Z"
    run_id = "test-run-123"

    report = engine.generate_all_signals(run_id=run_id, date=run_date, mode="PAPER", market_data=market_data)

    assert report.run_id == run_id
    assert report.mode == "PAPER"
    assert len(report.sleeves) == 7

    sleeve_dict = {s.id: s for s in report.sleeves}

    # Check fail-closed sleeves (P4-ported, dummy/empty data -> FLAT with data_unavailable)
    for pending_id in ["us_lowvol_top30", "us_pead_top5", "breakout_burst"]:
        assert pending_id in sleeve_dict
        assert sleeve_dict[pending_id].signal == "FLAT"
        assert sleeve_dict[pending_id].params.get("warning") in [None, "data_unavailable"]

    # Check real sleeves
    assert sleeve_dict["spy_sma200"].signal in ["LONG", "FLAT"]
    assert "sma200" in sleeve_dict["spy_sma200"].params

    assert sleeve_dict["us_momentum_top5"].signal in ["LONG", "FLAT"]
    if sleeve_dict["us_momentum_top5"].signal == "LONG":
        assert len(sleeve_dict["us_momentum_top5"].params["top_5"]) == 5

def test_missing_data_fails_closed():
    engine = SignalEngine()
    run_date = "2023-12-15T00:00:00Z"
    report = engine.generate_all_signals(run_id="test", date=run_date, mode="PAPER", market_data={})

    for sleeve in report.sleeves:
        assert sleeve.signal == "FLAT"
        if sleeve.id not in ["us_lowvol_top30", "us_pead_top5", "breakout_burst"]:
            assert sleeve.params.get("warning") == "data_unavailable"

def test_api_writes_artifacts(dummy_spy_data, dummy_btc_data, dummy_momentum_data, mock_ops_dir):
    market_data = {
        "SPY": dummy_spy_data,
        "BTC-USD": dummy_btc_data,
        **dummy_momentum_data
    }

    run_date = "2023-12-15T00:00:00Z"
    run_id = "test-atomic-write-999"

    report = generate_signals(run_id=run_id, date=run_date, mode="PAPER", market_data=market_data)

    signals_file = os.path.join(mock_ops_dir, "signals.json")
    assert os.path.exists(signals_file)
    with open(signals_file, "r") as f:
        data = json.load(f)
        assert data["run_id"] == run_id
        assert len(data["sleeves"]) == 7

    audit_file = os.path.join(mock_ops_dir, "audit.jsonl")
    assert os.path.exists(audit_file)
    with open(audit_file, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["run_id"] == run_id
        assert event["event"] == "SIGNALS_GENERATED"
