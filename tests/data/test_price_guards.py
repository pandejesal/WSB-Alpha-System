"""R-C1: zero-frame / flat-frame guard helper (5 tests)."""

import pandas as pd
import pytest

from src.data.price_guards import assert_tradable_prices


def _frame(values, symbol="TST"):
    idx = pd.date_range("2020-01-01", periods=len(values), freq="D")
    return pd.DataFrame({"close": values}, index=idx)


def test_rc1_all_zero_rejected():
    df = _frame([0.0] * 100)
    with pytest.raises(ValueError, match="TST"):
        assert_tradable_prices(df, symbol="TST")


def test_rc1_all_nan_rejected():
    df = _frame([float("nan")] * 10)
    with pytest.raises(ValueError, match="TST"):
        assert_tradable_prices(df, symbol="TST")


def test_rc1_flat_rejected():
    df = _frame([100.0] * 50)
    with pytest.raises(ValueError, match="zero-variance"):
        assert_tradable_prices(df, symbol="TST")


def test_rc1_sane_frame_passes():
    df = _frame([100.0, 101.5, 99.0, 102.25, 101.0])
    out = assert_tradable_prices(df, symbol="TST")
    assert out is df


def test_rc1_nan_error_names_symbol():
    df = _frame([float("nan")] * 5)
    with pytest.raises(ValueError) as excinfo:
        assert_tradable_prices(df, symbol="MYSTK")
    assert "MYSTK" in str(excinfo.value)
    assert "close" in str(excinfo.value)
