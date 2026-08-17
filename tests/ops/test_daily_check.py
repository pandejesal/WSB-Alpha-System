import json
import requests
from src.ops.signals import _fetch_single_yahoo_v8
import os
import json
import sys
import pytest
import datetime
import pandas as pd
from unittest.mock import patch, MagicMock
from src.ops.daily import run_check_mode, check_freshness

# Tests for the daily check mode script

@patch("src.ops.daily.yf.download")
def test_freshness_gate_blocked(mock_download, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Create fake strategies and data dirs
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)

    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n2023-01-31,0,0,0,0,0")

    # Mock yfinance to return stale data (10 days old)
    old_date = pd.Timestamp.now().normalize() - pd.Timedelta(days=10)
    fake_df = pd.DataFrame({'SPY': [100.0, 101.0]}, index=[old_date - pd.Timedelta(days=1), old_date])
    mock_df = pd.DataFrame(index=fake_df.index, columns=pd.MultiIndex.from_tuples([('Close', 'SPY')]))
    mock_df[('Close', 'SPY')] = fake_df['SPY']
    mock_download.return_value = mock_df

    try:
        run_check_mode()
    except SystemExit as e:
        assert e.code == 0

    assert os.path.exists("docs/data/ops/plan.json")
    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    assert "STALE_DATA" in plan["blocked"]
    assert any("stale" in w.lower() for w in plan["warnings"])

@patch("src.ops.daily.yf.download")
def test_zero_order_invariant(mock_download, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Create fake strategies and data dirs
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)

    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")
         for i in range(12): # Need at least 12 rows for weights logic
              f.write(f"2023-{i+1:02d}-28,0.01,0.02,0.01,0.05,0.03\n")

    # Mock fresh data
    recent_date = pd.Timestamp.now().normalize()
    fake_df = pd.DataFrame(
        {'SPY': [100.0]*200, 'BTC-USD': [1000.0]*200},
        index=pd.date_range(end=recent_date, periods=200)
    )
    # Add MultiIndex like yfinance
    cols = []
    for c in fake_df.columns:
        cols.append(('Close', c))
    mock_df = pd.DataFrame(index=fake_df.index, columns=pd.MultiIndex.from_tuples(cols))
    for c in fake_df.columns:
        mock_df[('Close', c)] = fake_df[c]

    mock_download.return_value = mock_df

    run_check_mode()

    # Verify no Alpaca in sys.modules
    assert "alpaca" not in sys.modules

    with open("docs/data/ops/heartbeat.json", "r") as f:
        hb = json.load(f)

    assert hb["orders_submitted"] == 0

def test_btc_floor_logic(tmp_path, monkeypatch):
    # Testing the weighting logic from daily check mode
    # We can inject a mock for yfinance and for the CSV

    monkeypatch.chdir(tmp_path)
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)

    # Create a CSV where BTC has a huge variance (so its inv vol weight is < 0.05)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")
         for i in range(12):
              # BTC variance huge, others tiny
              btc_val = (i % 2) * 20.0 - 10.0
              f.write(f"2023-{i+1:02d}-28,0.01,0.01,0.01,{btc_val},0.01\n")

    recent_date = pd.Timestamp.now().normalize()
    # Provide enough data to pass the data_unavailable gate for BTC and others
    fake_df = pd.DataFrame(
        {'SPY': [100.0]*200, 'BTC-USD': [1000.0]*200, 'AGG': [100.0]*200, 'QQQ': [100.0]*200},
        index=pd.date_range(end=recent_date, periods=200)
    )
    cols = []
    for c in fake_df.columns:
        cols.append(('Close', c))
    mock_df = pd.DataFrame(index=fake_df.index, columns=pd.MultiIndex.from_tuples(cols))
    for c in fake_df.columns:
        mock_df[('Close', c)] = fake_df[c]

    with patch("src.ops.daily.yf.download", return_value=mock_df):
        run_check_mode()

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    # verify btc_floor_applied flag
    assert plan["portfolio"]["btc_floor_applied"] is True

    weights = plan["portfolio"]["weights"]
    # Check it actually applied 0.05
    assert abs(weights["btc_vol_target_sma100"] - 0.05) < 1e-6
    # Check sum is 1.0
    assert abs(sum(weights.values()) - 1.0) < 1e-6

from yfinance.exceptions import YFRateLimitError

@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals.fetch_daily_stooq")
@patch("src.ops.signals._orig_download")
def test_yf_fetch_retry_success(mock_orig_download, mock_fetch_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    mock_fetch_v8.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    mock_fetch_stooq.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "2")
    monkeypatch.setenv("OPS_FETCH_BACKOFF_BASE", "0")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    # Return RateLimit on first attempt, then valid mock dataframe
    recent_date = pd.Timestamp.now().normalize()
    fake_df = pd.DataFrame({'SPY': [100.0]*200}, index=pd.date_range(end=recent_date, periods=200))
    cols = [('Close', 'SPY')]
    mock_df = pd.DataFrame(index=fake_df.index, columns=pd.MultiIndex.from_tuples(cols))
    mock_df[('Close', 'SPY')] = fake_df['SPY']

    mock_orig_download.side_effect = [YFRateLimitError(), mock_df]

    # Should not exit or throw
    run_check_mode()

    assert mock_orig_download.call_count == 2

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)
    assert "STALE_DATA" not in plan.get("blocked", [])

@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals.fetch_daily_stooq")
@patch("src.ops.signals._orig_download")
def test_yf_fetch_retry_exhausted(mock_orig_download, mock_fetch_stooq, mock_fetch_v8, tmp_path, monkeypatch, capsys):
    mock_fetch_v8.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    mock_fetch_stooq.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "2")
    monkeypatch.setenv("OPS_FETCH_BACKOFF_BASE", "0")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    mock_orig_download.side_effect = YFRateLimitError()

    try:
        run_check_mode()
    except SystemExit as e:
        assert e.code == 0

    assert mock_orig_download.call_count == 2

    # Check print outputs
    captured = capsys.readouterr()
    assert "Fetch failed (attempt 1)" in captured.out

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    assert "STALE_DATA" in plan.get("blocked", [])

    with open("docs/data/ops/heartbeat.json", "r") as f:
        hb = json.load(f)
    assert any("WARN" in alert for alert in hb.get("alerts", []))


@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals._fetch_single_stooq")
@patch("src.ops.signals._orig_download")
def test_stooq_fetch_success(mock_orig_download, mock_fetch_single_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    mock_fetch_v8.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "1")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    recent_date = pd.Timestamp.now().normalize()
    fake_df = pd.DataFrame({'Close': [100.0]*200, 'Open': [100.0]*200, 'High': [100.0]*200, 'Low': [100.0]*200, 'Volume': [1000]*200}, index=pd.date_range(end=recent_date, periods=200))
    fake_df.index.name = 'Date'

    def mock_stooq(ticker):
        return fake_df.copy()

    mock_fetch_single_stooq.side_effect = mock_stooq

    run_check_mode()

    assert mock_orig_download.call_count == 0
    assert mock_fetch_single_stooq.call_count > 0

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)
    assert "STALE_DATA" not in plan.get("blocked", [])

@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals._fetch_single_stooq")
@patch("src.ops.signals._orig_download")
def test_partial_availability(mock_orig_download, mock_fetch_single_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    mock_fetch_v8.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "1")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    recent_date = pd.Timestamp.now().normalize()
    fake_df = pd.DataFrame({'Close': [100.0]*200, 'Open': [100.0]*200, 'High': [100.0]*200, 'Low': [100.0]*200, 'Volume': [1000]*200}, index=pd.date_range(end=recent_date, periods=200))
    fake_df.index.name = 'Date'

    # Stooq has only SPY
    def mock_stooq(ticker):
        if ticker == "SPY":
            return fake_df.copy()
        raise ValueError("No data")

    # YF fails for everything
    mock_fetch_single_stooq.side_effect = mock_stooq
    mock_orig_download.side_effect = YFRateLimitError()

    try:
        run_check_mode()
    except SystemExit as e:
        assert e.code == 0

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    # Should not block on STALE_DATA if at least something was fetched, but in reality if ONLY SPY is fetched,
    # dual_momentum needs QQQ, us_momentum needs 147 days of all top universe, btc needs BTC, etc.
    # The current engine fails closed if `data is None or data.empty`. If SPY is there, `data` is NOT empty.
    assert "STALE_DATA" not in plan.get("blocked", [])
    assert "spy_sma200" not in plan.get("data_unavailable", [])

@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals._fetch_single_stooq")
@patch("src.ops.signals._orig_download")
def test_all_fail(mock_orig_download, mock_fetch_single_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    mock_fetch_v8.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "1")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    mock_fetch_single_stooq.side_effect = ValueError("No data")
    mock_orig_download.side_effect = YFRateLimitError()

    try:
        run_check_mode()
    except SystemExit as e:
        assert e.code == 0

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    assert "STALE_DATA" in plan.get("blocked", [])

@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals._fetch_single_stooq")
@patch("src.ops.signals._orig_download")
def test_mixed_stooq_and_yf_success(mock_orig_download, mock_fetch_single_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    mock_fetch_v8.return_value = {t: None for t in ["SPY", "QQQ", "AGG", "BTC-USD", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "1")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    recent_date = pd.Timestamp.now().normalize()

    # Stooq returns tz-naive
    stooq_df = pd.DataFrame({'Close': [100.0]*200, 'Open': [100.0]*200, 'High': [100.0]*200, 'Low': [100.0]*200, 'Volume': [1000]*200}, index=pd.date_range(end=recent_date, periods=200))
    stooq_df.index.name = 'Date'

    # YF returns tz-aware (e.g., America/New_York)
    yf_df = pd.DataFrame(
        {'SPY': [101.0]*200, 'BTC-USD': [1000.0]*200, 'QQQ': [100.0]*200, 'AGG': [100.0]*200},
        index=pd.date_range(end=recent_date, periods=200, tz='America/New_York')
    )
    cols = []
    for c in yf_df.columns:
        cols.append(('Close', c))
    mock_df = pd.DataFrame(index=yf_df.index, columns=pd.MultiIndex.from_tuples(cols))
    for c in yf_df.columns:
        mock_df[('Close', c)] = yf_df[c]

    # Stooq gets SPY, fails on QQQ
    def mock_stooq(ticker):
        if ticker == "SPY":
            return stooq_df.copy()
        raise ValueError("No data")

    mock_fetch_single_stooq.side_effect = mock_stooq
    mock_orig_download.return_value = mock_df

    try:
        run_check_mode()
    except SystemExit as e:
        assert e.code == 0

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    assert "STALE_DATA" not in plan.get("blocked", [])


@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals.fetch_daily_stooq")
@patch("src.ops.signals._orig_download")
def test_v8_short_circuits(mock_orig_download, mock_fetch_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "1")

    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    recent_date = pd.Timestamp.now().normalize()
    fake_df = pd.DataFrame({'Close': [100.0]*200, 'Open': [100.0]*200, 'High': [100.0]*200, 'Low': [100.0]*200, 'Volume': [1000]*200}, index=pd.date_range(end=recent_date, periods=200))
    fake_df.index.name = 'Date'

    def mock_v8(ticker_list):
        return {t: fake_df.copy() for t in ticker_list}

    mock_fetch_v8.side_effect = mock_v8

    run_check_mode()

    # V8 succeeded, so stooq and yf should not be called
    assert mock_orig_download.call_count == 0
    assert mock_fetch_stooq.call_count == 0

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)
    assert "STALE_DATA" not in plan.get("blocked", [])

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        pass

def mock_get(url, *args, **kwargs):
    # A realistic, but short payload
    payload = {
      "chart": {
        "result": [
          {
            "meta": {
              "currency": "USD",
              "symbol": "SPY",
            },
            "timestamp": [
              1660743000,
              1660829400,
              1660915800
            ],
            "indicators": {
              "quote": [
                {
                  "close": [426.65, None, 422.14],
                  "volume": [50000000, 45000000, 60000000],
                  "open": [425.0, 426.0, 424.0],
                  "high": [428.0, 427.0, 425.0],
                  "low": [424.0, 423.0, 421.0]
                }
              ]
            }
          }
        ]
      }
    }
    return MockResponse(payload)

def test_v8_json_parse(monkeypatch):
    monkeypatch.setattr("requests.Session.get", mock_get)

    df = _fetch_single_yahoo_v8("SPY")

    # 3 items, but one close is None (NaN in pandas), so it should be dropped.
    assert df is not None
    assert len(df) == 2
    assert "Date" == df.index.name
    assert "Close" in df.columns

    # First date should be 2022-08-17 13:30:00 UTC -> naive
    assert df.index[0] == pd.to_datetime(1660743000, unit='s')
    assert df.iloc[0]['Close'] == 426.65
    assert df.iloc[1]['Close'] == 422.14

from src.ops.signals import get_us_momentum_top5_signal, get_dual_momentum_signal
from src.ops.daily import MOMENTUM_UNIVERSE
import numpy as np

def _make_padded_mock_df(tickers, n_weekdays=200):
    # Simulate the hybrid download output: equity rows NaN on BTC-style weekend padding
    recent_date = pd.Timestamp.now().normalize()
    weekdays = pd.date_range(end=recent_date, periods=n_weekdays, freq="B")
    full_idx = pd.DatetimeIndex(
        sorted(set(weekdays) | set(pd.date_range(end=recent_date, periods=14, freq="D")))
    )
    cols = [("Close", t) for t in tickers]
    df = pd.DataFrame(index=full_idx, columns=pd.MultiIndex.from_tuples(cols))
    df.columns.names = ["Price", "Ticker"]
    for i, t in enumerate(tickers):
        base = 100.0 + i * 5.0
        series = pd.Series(base + np.arange(n_weekdays, dtype=float), index=weekdays)
        df[("Close", t)] = series.reindex(full_idx)
    return df

def test_momentum_robust_to_padded_index():
    tickers = ["AAPL", "MSFT", "NVDA", "JPM", "V", "WMT", "TSLA", "AMZN", "META", "GOOGL"]
    df = _make_padded_mock_df(tickers)
    mom = get_us_momentum_top5_signal(df, tickers)
    assert "top_5" in mom
    assert len(mom["top_5"]) == 5
    assert len(mom["momenta"]) >= 5
    assert all(m > 0 for m in mom["momenta"].values())

def test_dual_momentum_robust_to_padded_index():
    df = _make_padded_mock_df(["SPY", "QQQ"])
    dm = get_dual_momentum_signal(df)
    assert dm.get("momenta", {}).get("SPY", 0) > 0
    assert dm.get("momenta", {}).get("QQQ", 0) > 0
    assert dm.get("signal") in ("SPY", "QQQ")  # both positive -> risk-on leg, not AGG

def test_momentum_data_unavailable_flagged(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    recent_date = pd.Timestamp.now().normalize()
    # Only index/sleeve tickers present; NO momentum-universe names
    fake_df = pd.DataFrame(
        {'SPY': [100.0]*200, 'BTC-USD': [1000.0]*200, 'AGG': [100.0]*200, 'QQQ': [100.0]*200},
        index=pd.date_range(end=recent_date, periods=200)
    )
    cols = [('Close', c) for c in fake_df.columns]
    mock_df = pd.DataFrame(index=fake_df.index, columns=pd.MultiIndex.from_tuples(cols))
    for c in fake_df.columns:
        mock_df[('Close', c)] = fake_df[c]

    with patch("src.ops.daily.yf.download", return_value=mock_df):
        run_check_mode()

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)
    assert "us_momentum_top5" in plan["data_unavailable"]
    sleeve = next(s for s in plan["sleeves"] if s["id"] == "us_momentum_top5")
    assert sleeve["signal"]["top5"] == []
    assert sleeve["targets"] == []

def test_momentum_universe_size():
    assert len(MOMENTUM_UNIVERSE) >= 100
    assert len(set(MOMENTUM_UNIVERSE)) == len(MOMENTUM_UNIVERSE)
    assert all(t == t.upper() for t in MOMENTUM_UNIVERSE)

@patch("src.ops.signals.fetch_daily_yahoo_v8")
@patch("src.ops.signals._fetch_single_stooq")
@patch("src.ops.signals._orig_download")
def test_momentum_signals_with_hybrid_shape(mock_orig_download, mock_fetch_single_stooq, mock_fetch_v8, tmp_path, monkeypatch):
    from src.ops.daily import MOMENTUM_UNIVERSE
    tickers = ["SPY", "QQQ", "AGG", "BTC-USD"] + MOMENTUM_UNIVERSE
    mock_fetch_v8.return_value = {t: None for t in tickers}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPS_FETCH_RETRIES", "1")
    os.makedirs("strategies", exist_ok=True)
    os.makedirs("docs/data/portfolio", exist_ok=True)
    for name in ["flagship_portfolio_v1", "us_momentum_top5", "spy_sma200", "spy_rsi2", "btc_vol_target_sma100", "dual_momentum"]:
        with open(f"strategies/{name}.yaml", "w") as f:
             f.write("id: " + name)
    with open("docs/data/portfolio/monthly_returns.csv", "w") as f:
         f.write(",us_momentum_top5,spy_sma200,spy_rsi2,btc_vol_target_sma100,dual_momentum\n")

    recent_date = pd.Timestamp.now().normalize()
    dates = pd.date_range(end=recent_date, periods=200)

    frames = []
    for t in tickers:
        df = pd.DataFrame({'Close': [100.0 - i*0.1 for i in range(200)], 'Open': [100.0]*200, 'High': [100.0]*200, 'Low': [100.0]*200, 'Volume': [1000]*200}, index=dates)
        if t == "AAPL":
            df["Close"] = [100.0 + i*0.1 for i in range(200)]
        elif t == "MSFT":
            df["Close"] = [100.0 + i*0.2 for i in range(200)]

        df.index.name = 'Date'
        df.columns = pd.MultiIndex.from_product([df.columns, [t]])
        frames.append(df)

    mock_df = pd.concat(frames, axis=1)
    mock_df = mock_df.sort_index(axis=1)

    mock_fetch_single_stooq.side_effect = ValueError("No data")
    mock_orig_download.return_value = mock_df

    try:
        run_check_mode()
    except SystemExit as e:
        assert e.code == 0

    with open("docs/data/ops/plan.json", "r") as f:
        plan = json.load(f)

    assert "STALE_DATA" not in plan.get("blocked", [])

    sleeves = plan.get("sleeves", [])
    mom_sleeve = next((s for s in sleeves if s["id"] == "us_momentum_top5"), None)
    assert mom_sleeve is not None
    assert len(mom_sleeve["signal"]["top5"]) >= 5
    assert "MSFT" in mom_sleeve["signal"]["top5"]

    dual_mom_sleeve = next((s for s in sleeves if s["id"] == "dual_momentum"), None)
    assert dual_mom_sleeve is not None
    assert dual_mom_sleeve["signal"]["leg"] == "AGG"
    assert dual_mom_sleeve["signal"]["mom_spy"] < 0
    assert dual_mom_sleeve["signal"]["mom_qqq"] < 0
