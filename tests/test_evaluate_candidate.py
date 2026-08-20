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
