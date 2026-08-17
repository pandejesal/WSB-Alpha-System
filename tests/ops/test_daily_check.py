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

@patch("src.ops.signals._orig_download")
def test_yf_fetch_retry_success(mock_orig_download, tmp_path, monkeypatch):
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

@patch("src.ops.signals._orig_download")
def test_yf_fetch_retry_exhausted(mock_orig_download, tmp_path, monkeypatch, capsys):
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
