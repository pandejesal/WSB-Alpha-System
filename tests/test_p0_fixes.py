import os
import pytest
import numpy as np
import pandas as pd
from src.risk.fred_macro_provider import FredMacroProvider
from src.backtest.validators.statistical import StatisticalValidator
from src.backtest.permutation_tester import PermutationValidator

def test_fred_fails_closed():
    # Make sure FRED_API_KEY is not set
    if "FRED_API_KEY" in os.environ:
        del os.environ["FRED_API_KEY"]

    provider = FredMacroProvider()
    assert provider.api_key == ""
    # fetch_series should short-circuit and return None
    res = provider._fetch_series("T10Y2Y")
    assert res is None

def test_spa_test_returns_correct_keys():
    np.random.seed(42)
    bench = np.random.randn(100)
    models = np.random.randn(100)

    result = StatisticalValidator.spa_test(models, bench)
    assert "t_stat" in result
    assert result["t_stat"] is None
    assert "p_value" in result
    assert "reject_null" in result

def test_permutation_null_circular():
    dates = pd.date_range("2023-01-01", periods=10)
    df = pd.DataFrame({
        "Open": np.linspace(10, 20, 10),
        "High": np.linspace(11, 21, 10),
        "Low": np.linspace(9, 19, 10),
        "Close": np.linspace(10.5, 20.5, 10)
    }, index=dates)

    validator = PermutationValidator(num_permutations=2, null_mode="circular", seed=42)

    def dummy_strategy(data: pd.DataFrame) -> float:
        return 1.5

    # Should not crash
    result = validator.validate(dummy_strategy, df)
    assert result["status"] in ["PASSED", "FAILED"]

def test_cpcv_embargo():
    # 10 data points, 5 splits -> block size 2.
    # We choose n_test_splits=1, so we test one block at a time.
    # Purge length 1, embargo 1
    splits = StatisticalValidator.combinatorial_purged_cv(
        data_length=10,
        n_splits=5,
        n_test_splits=1,
        purge_length=1,
        embargo=1
    )

    # Check the first split: test is block 0 (indices [0, 1]).
    # Block 1 is [2, 3]. It should have embargo applied at start (i - 1 == 0), so it loses 1 point -> [3].
    # Block 2, 3, 4 should be untouched.
    train_0, test_0 = splits[0]
    assert np.array_equal(test_0, [0, 1])
    assert 2 not in train_0 # embargoed
    assert 3 in train_0


def test_legacy_engine_t1_open_fill_and_decision_bar():
    """E-2 regression: legacy engine must decide on the last closed bar (t)
    and fill at Open[t+1] — never same-bar Close (lookahead)."""
    from src.backtest.legacy_backtest import evaluate_strategy_on_data

    dates = pd.date_range("2023-01-01", periods=6, freq="B")
    df = pd.DataFrame({
        "Open": [10, 11, 12, 13, 14, 15],
        "High": [11, 12, 13, 14, 15, 16],
        "Low": [9, 10, 11, 12, 13, 14],
        "Close": [10.5, 11.5, 12.5, 13.5, 14.5, 15.5],
        "RSI_14": [50.0] * 6,
        "GK_Vol": [0.5] * 6,
        "EMA_20": [10.0] * 6,
        "ATR_14": [1.0] * 6,
        "HA_Close": [11, 12, 13, 14, 15, 16],
        "HA_Open": [10, 11, 12, 13, 14, 15],
        "MACD_Hist": [0.1] * 6,
        "BB_Lower": [9.0] * 6,
        "BB_Upper": [16.0] * 6,
        "CVaR_95": [0.04] * 6,
    }, index=dates)
    posts = pd.DataFrame({
        "post_date": [dates[1]],
        "ticker": ["AAPL"],
        "sentiment_score": [1.0],
    })
    spy = pd.Series([100, 101, 102, 103, 104, 105], index=dates)

    # Signal bar = dates[1] (index 1). Entry bar = dates[2]: Open=12, Close=12.5.
    # Exit bar = index 3: Close=13.5.
    trades = evaluate_strategy_on_data(posts, {"AAPL": df}, spy, return_type="full_df")
    assert len(trades) == 1
    # Honest T+1 fill at Open[2]=12: raw_ret_1d = (13.5-12)/12 = 0.125.
    # Same-bar Close fill (lookahead) would be (13.5-12.5)/12.5 = 0.08.
    assert trades.iloc[0]["raw_ret_1d"] == pytest.approx(0.125, abs=1e-9)

    # Gates must read the DECISION bar (t), not the entry bar (t+1).
    # Kill every ensemble channel on the ENTRY bar (dates[2]): decision bar
    # (dates[1]) stays all-passing -> trade must still go through.
    df_clean = df.copy()
    df_mut = df.copy()
    entry_bar_kills = {"HA_Close": 11, "HA_Open": 13, "EMA_20": 100.0,
                       "RSI_14": 90.0, "BB_Lower": 100.0, "Close": 5.0}
    for col, val in entry_bar_kills.items():
        df_mut.loc[dates[2], col] = val
    trades_ok = evaluate_strategy_on_data(posts, {"AAPL": df_mut}, spy, return_type="full_df")
    assert len(trades_ok) == 1
    assert trades_ok.iloc[0]["adaptive_ret_1d"] != 0.0

    # Now kill the channels on the DECISION bar (dates[1]): the engine must NOT
    # treat it as a confluence trigger (returns zeroed).
    df_mut2 = df_clean.copy()
    for col, val in entry_bar_kills.items():
        df_mut2.loc[dates[1], col] = val
    trades_blocked = evaluate_strategy_on_data(posts, {"AAPL": df_mut2}, spy, return_type="full_df")
    assert len(trades_blocked) == 1
    assert trades_blocked.iloc[0]["adaptive_ret_1d"] == 0.0


def test_legacy_engine_marked_reference_only():
    """E-1 marker: legacy engine is reference-only and must never be bound by
    reporting/validation."""
    import src.backtest.legacy_backtest as legacy
    assert legacy.LEGACY_REFERENCE_ONLY is True


def test_validation_tearsheet_engine_is_honest():
    """E-1 regression: validation reporting must use the same honest T+1
    engine as the permutation tests (run_historic_backtest)."""
    import src.backtest.run_historic_backtest as rb
    import src.backtest.validation as validation

    assert validation.TEARSHEET_ENGINE is rb
    assert getattr(validation.TEARSHEET_ENGINE, "LEGACY_REFERENCE_ONLY", False) is False


def test_sandbox_state_toy_label():
    """E-6 regression: sandbox artifacts carry the TOY_SANDBOX exclusion
    label so they can be filtered from paper-performance reporting."""
    from scripts.paper_trading_sandbox import TOY_SANDBOX_LABEL, _new_sandbox_state

    assert TOY_SANDBOX_LABEL == "TOY_SANDBOX"
    state = _new_sandbox_state()
    assert state["mode"] == "TOY_SANDBOX"
    assert state["simulated"] is True
