import os
import json
import yaml
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Synthetic data generator
def create_synthetic_data(tickers=["T1", "T2", "T3"], rows=400):
    np.random.seed(42)
    dfs = []
    dates = pd.date_range(end="2023-12-31", periods=rows, freq="B")

    for t in tickers:
        df = pd.DataFrame(index=dates)
        df["Date"] = df.index
        df["Date_str"] = df.index.astype(str)
        df["post_date"] = df.index
        df["Ticker"] = t
        returns = np.random.normal(0.0005, 0.01, rows)
        prices = 100 * np.exp(returns.cumsum())
        df["Close"] = prices
        df["Open"] = prices * np.random.normal(1.0, 0.005, rows)
        df["High"] = df[["Open", "Close"]].max(axis=1) * np.random.normal(1.005, 0.002, rows)
        df["Low"] = df[["Open", "Close"]].min(axis=1) * np.random.normal(0.995, 0.002, rows)
        df["Volume"] = np.random.randint(100000, 1000000, rows)
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)

    # Validation engine base data expects specific format
    posts_data = []
    for d in dates:
        posts_data.append({"post_date": d, "ticker": "T1", "sentiment_score": 0.5, "post_id": str(d)})
    posts_df = pd.DataFrame(posts_data)

    stock_dfs = {t: combined[combined["Ticker"] == t].copy() for t in tickers}
    spy_close = combined[combined["Ticker"] == tickers[0]]["Close"].copy()

    return combined, posts_df, stock_dfs, spy_close

# Test 1: run_permutation_study
@patch("scripts.run_permutation_study.load_base_data")
@patch("scripts.run_permutation_study.run_in_sample_test")
@patch("scripts.run_permutation_study.run_walk_forward_test")
def test_run_permutation_study_synthetic(mock_wf, mock_is, mock_load):
    mock_load.return_value = (MagicMock(), MagicMock(), MagicMock())
    mock_is.return_value = (0.1, 1.5, [], [], 0.04, None, None)
    mock_wf.return_value = (0.1, 1.5, [], [], 0.03, 0.6, 10)

    from scripts.run_permutation_study import run_study

    study_file = "docs/data/permutation_study.json"
    if os.path.exists(study_file):
        os.remove(study_file)

    run_study()

    assert os.path.exists(study_file)
    with open(study_file, "r") as f:
        data = json.load(f)

    assert data["status"] == "success"
    assert "in_sample_p_value" in data
    assert data["permutations"] == 200

# Test 2: evaluate_candidate.py on ta_rules
@patch("scripts.evaluate_candidate.run_in_sample_test")
@patch("scripts.evaluate_candidate.run_walk_forward_test")
@patch("scripts.evaluate_candidate.get_provider")
def test_evaluate_candidate_ta_rules(mock_get_provider, mock_wf, mock_is, tmp_path):
    mock_is.return_value = (0.1, 1.5, [0.1], [1.5], 0.04, None, None)
    mock_wf.return_value = (0.1, 1.5, [0.1], [1.5], 0.03, 0.6, 10)
    combined, _, _, _ = create_synthetic_data()

    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = combined
    mock_get_provider.return_value = mock_provider

    spec_path = tmp_path / "ta_spec.yaml"
    eval_path = tmp_path / "eval_ta.json"
    prereg_path = tmp_path / "prereg_ta.md"

    spec = {
        "id": "test_ta",
        "name": "Test TA",
        "family": "ta_rules",
        "universe": "SPY",
        "parameters": {},
        "signal": {
            "entry": "ema_cross",
            "fast_ma": 10,
            "slow_ma": 20
        },
        "pre_registration_ref": str(prereg_path),
        "eval_records": str(eval_path)
    }

    with open(spec_path, "w") as f:
        yaml.dump(spec, f)

    import sys
    from scripts.evaluate_candidate import main

    test_args = ["evaluate_candidate.py", str(spec_path), "--tickers", "T1,T2", "--days", "100"]
    with patch.object(sys, 'argv', test_args):
        main()

    assert eval_path.exists()
    with open(eval_path, "r") as f:
        data = json.load(f)
    assert data["family"] == "ta_rules"
    assert data["status"] == "evaluated"
    assert "dsr" in data

    assert prereg_path.exists()

# Test 3: evaluate_candidate.py on multi_factor
def test_evaluate_candidate_multi_factor(tmp_path):
    spec_path = tmp_path / "mf_spec.yaml"
    eval_path = tmp_path / "eval_mf.json"
    prereg_path = tmp_path / "prereg_mf.md"

    spec = {
        "id": "test_mf",
        "name": "Test MF",
        "universe": "SPY",
        "family": "multi_factor",
        "parameters": {},
        "signal": {"entry": "mock", "exit": "mock"},
        "pre_registration_ref": str(prereg_path),
        "eval_records": str(eval_path)
    }

    with open(spec_path, "w") as f:
        import yaml
        yaml.dump(spec, f)

    import sys
    from scripts.evaluate_candidate import main

    test_args = ["evaluate_candidate.py", str(spec_path), "--tickers", "T1,T2", "--days", "100"]
    with patch.object(sys, 'argv', test_args):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert eval_path.exists()
    with open(eval_path, "r") as f:
        import json
        data = json.load(f)

    assert data["family"] == "multi_factor"
    assert data["verdict"] == "HONEST_ABANDON"
    assert data["status"] == "not_evaluable_missing_plumbing"

# Test 4: build_signal_posts for ta_rules ema_cross
def test_build_signal_posts_ta_rules_ema_cross():
    from scripts.evaluate_candidate import build_signal_posts
    combined, _, _, _ = create_synthetic_data(tickers=["T1"], rows=250)

    # Manipulate data to force a specific crossover
    # EMA10 and EMA50, SMA200. We will set close high enough to pass SMA200,
    # and force a crossover at index 230.
    combined['Close'] = 150.0 # High flat line
    # Drop EMA 10 low before 230, spike after 230
    combined.loc[:229, 'Close'] = 100.0
    combined.loc[230:, 'Close'] = 120.0

    # We won't simulate exact EMA math precisely to force it manually via price,
    # but we can just use simple price steps. The compute_indicators will run and EMA will lag.
    # A sharp jump in price will cause fast EMA to cross slow EMA.

    spec = {
        "family": "ta_rules",
        "parameters": {"ema_fast": 2, "ema_slow": 5, "sma_window": 10},
        "signal": {"entry": "ema_cross"}
    }

    posts_df = build_signal_posts(spec, combined, ["T1"])
    assert not posts_df.empty
    assert "ticker" in posts_df.columns
    assert "post_date" in posts_df.columns
    assert posts_df["sentiment_score"].iloc[0] == 1.0

# Test 5: build_signal_posts for sentiment_overlay
def test_build_signal_posts_sentiment_overlay():
    from scripts.evaluate_candidate import build_signal_posts
    combined, _, _, _ = create_synthetic_data(tickers=["T1"], rows=100)

    # Force SMA condition. First 50 days Close = 100, SMA climbs to 100.
    # Day 51 Close jumps to 110. Close > SMA for days 51+.
    combined['Close'] = 100.0
    combined.loc[50:, 'Close'] = 110.0

    spec = {
        "family": "sentiment_overlay",
        "parameters": {"window": 20}
    }

    posts_df = build_signal_posts(spec, combined, ["T1"])
    assert not posts_df.empty
    assert posts_df["sentiment_score"].iloc[0] == 0.5

    # Only days where close > SMA should have posts.
    # We should have roughly 50 posts.
    assert len(posts_df) > 0

# Test 6: build_signal_posts for xgboost_exits
def test_build_signal_posts_xgboost_exits():
    from scripts.evaluate_candidate import build_signal_posts
    combined, _, _, _ = create_synthetic_data(tickers=["T1", "T2"], rows=200)

    # T1 has positive momentum, T2 negative
    # Prices
    combined.loc[combined['Ticker'] == 'T1', 'Close'] = np.linspace(100, 200, len(combined[combined['Ticker'] == 'T1']))
    combined.loc[combined['Ticker'] == 'T2', 'Close'] = np.linspace(200, 100, len(combined[combined['Ticker'] == 'T2']))

    spec = {
        "family": "xgboost_exits",
        "parameters": {"lookback_days": 20, "skip_days": 5, "top_n": 1}
    }

    posts_df = build_signal_posts(spec, combined, ["T1", "T2"])

    # Should only select T1 since T1 has positive momentum
    assert not posts_df.empty
    assert (posts_df['ticker'] == 'T1').all()
    assert (posts_df['sentiment_score'] == 1.0).all()
