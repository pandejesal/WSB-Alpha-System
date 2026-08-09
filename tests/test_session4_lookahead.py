import pandas as pd
import numpy as np
import pytest

def test_safe_sharpe():
    from src.backtest.metrics import safe_sharpe

    # 2. safe_sharpe([1,1,1,1,1]) == 0 (zero var)
    assert safe_sharpe([1,1,1,1,1]) == 0.0

    # safe_sharpe([]) == 0
    assert safe_sharpe([]) == 0.0

def test_oos_sharpe_from_generate(monkeypatch):
    from scripts.generate_strategy_data import _compute_trade_metrics

    # Create mock trades
    trades = pd.DataFrame({
        "return": [0.01, -0.01, 0.02, 0.01, -0.01, 0.03, -0.02, 0.01, 0.01, 0.02]
    })

    metrics = _compute_trade_metrics(trades)

    # 3. oos_sharpe is not train_sharpe
    assert metrics["oos_sharpe"] is not None
    assert metrics["oos_sharpe"] != metrics["train_sharpe"]

    # Short trades dataframe -> None
    short_trades = pd.DataFrame({"return": [0.01, -0.01]})
    short_metrics = _compute_trade_metrics(short_trades)
    assert short_metrics["oos_sharpe"] is None

def test_lookahead_fix():
    from src.backtest.run_historic_backtest import run_backtest_with_params

    # 1. contrived OHLCV fixture
    dates = pd.date_range("2023-01-01", periods=10, freq="B")

    df = pd.DataFrame({
        "Date": dates,
        "Open": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        "High": [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        "Low": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "Close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5],
        "RSI_14": [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
        "GK_Vol": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
        "EMA_20": [10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
        "ATR_14": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    })

    stock_dfs = {"AAPL": df}

    # Signal post date is 2023-01-02 (index 1)
    posts = pd.DataFrame({
        "post_date": [dates[1]],
        "ticker": ["AAPL"],
        "sentiment_score": [1.0]
    })

    # Exec date will be 2023-01-03 (index 2)
    # The decision should use t-1, which is index 1
    # We will modify index 1 RSI to be valid (e.g. 50, within 30-70)
    # But index 2 RSI to be invalid (e.g. 90)
    # If there is lookahead, it uses index 2 RSI and fails to enter
    df.loc[2, "RSI_14"] = 90

    trades = run_backtest_with_params(
        posts_df=posts,
        stock_dfs=stock_dfs,
        holding_days=1,
        rsi_low=30,
        rsi_high=70,
        gk_vol_limit=1.2,
        min_confluence_score=0 # Disable confluence to focus on RSI
    )

    # It should have traded because t-1 (index 1) RSI was 50
    assert len(trades) == 1

    # Now set index 1 RSI to invalid, index 2 to valid
    df.loc[1, "RSI_14"] = 90
    df.loc[2, "RSI_14"] = 50

    trades2 = run_backtest_with_params(
        posts_df=posts,
        stock_dfs=stock_dfs,
        holding_days=1,
        rsi_low=30,
        rsi_high=70,
        gk_vol_limit=1.2,
        min_confluence_score=0
    )

    # It should NOT trade because t-1 RSI is invalid
    assert len(trades2) == 0

def test_validation_wf():
    from src.backtest.validation import run_in_sample_test
    from unittest.mock import patch
    import src.backtest.run_historic_backtest as rb

    dates = pd.date_range("2023-01-01", periods=20, freq="B")

    df = pd.DataFrame({
        "Date": dates,
        "Open": np.random.randn(20) + 10,
        "High": np.random.randn(20) + 11,
        "Low": np.random.randn(20) + 9,
        "Close": np.random.randn(20) + 10.5,
        "RSI_14": [50] * 20,
        "GK_Vol": [0.5] * 20,
        "EMA_20": [10] * 20,
        "ATR_14": [1] * 20
    })

    stock_dfs = {"AAPL": df}
    posts = pd.DataFrame({
        "post_date": dates[:5],
        "ticker": ["AAPL"] * 5,
        "sentiment_score": [1.0] * 5
    })

    spy = pd.Series(np.random.randn(20) + 10, index=dates)

    # Mocking rb.run_backtest inside validation to not take so long on permutations
    # And to ensure the contract hasn't broken.
    with patch("src.backtest.validation.NUM_PERMUTATIONS", 2):
        is_real_ret, is_real_sharpe, is_p_rets, is_p_sharpes, is_pval, is_real_ret_series, spy_ret_series = run_in_sample_test(posts, stock_dfs, spy)

        assert is_real_ret is not None
        assert len(is_p_rets) == 2
