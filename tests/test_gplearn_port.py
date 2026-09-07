"""Tests for gplearn port: terminals, parser, evaluator, fast evolution."""

import numpy as np
import pandas as pd
import pytest

from src.signals.gplearn_factors import (  # noqa: E402
    TERMINALS,
    EvolveConfig,
    build_terminals,
    evaluate_program,
    evolve,
    program_to_pandas,
)


def _bars(n=120):
    rng = np.random.RandomState(42)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    close = pd.Series(100 + np.arange(n) * 0.3 + rng.randn(n) * 2.0, index=idx)
    return pd.DataFrame({"close": close, "high": close + 1, "low": close - 1,
                         "volume": 1_000_000.0}, index=idx)


def test_terminals_no_lookahead():
    bars = _bars()
    T = build_terminals(bars)
    assert list(T.columns) == list(TERMINALS)
    # shift(1): T row 2 holds raw row-1 values (past only)
    assert T["ret_1"].iloc[2] == pytest.approx((bars["close"].iloc[1] / bars["close"].iloc[0] - 1))
    assert T.iloc[:20]["sma20_ratio"].isna().all()


def test_parser_roundtrip():
    code = program_to_pandas("add(mul(X0, X1), sqrt(X2))")
    assert "T['ret_1']" in code and "T['ret_5']" in code
    with pytest.raises(ValueError):
        program_to_pandas("frobnicate(X0)")
    with pytest.raises(ValueError):
        program_to_pandas("add(X0)")


def test_evaluator_matches_manual():
    T = build_terminals(_bars()).dropna()
    sig = evaluate_program("sub(X0, X1)", T)
    expected = T["ret_1"] - T["ret_5"]
    pd.testing.assert_series_equal(sig, expected.fillna(0.0), check_names=False)


def test_evolve_fast_smoke():
    pytest.importorskip("gplearn")
    cfg = EvolveConfig(population_size=10, generations=2, random_state=7)
    out = evolve(_bars(150), cfg)
    assert out["status"] == "paper"
    assert isinstance(out["expression"], str) and out["expression"]
    assert isinstance(out["oos_sharpe"], float)
    assert out["oos_trades"] >= 0
