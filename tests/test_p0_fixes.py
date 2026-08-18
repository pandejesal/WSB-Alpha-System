import os

import numpy as np
import pandas as pd

from src.backtest.permutation_tester import PermutationValidator
from src.backtest.validators.statistical import StatisticalValidator
from src.risk.fred_macro_provider import FredMacroProvider


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






def test_validation_tearsheet_engine_is_honest():
    """E-1 regression: validation reporting must use the same honest T+1
    engine as the permutation tests (run_historic_backtest)."""
    import src.backtest.run_historic_backtest as rb
    from src.backtest import validation

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
