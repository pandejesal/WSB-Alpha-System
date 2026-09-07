"""Tests for NextTrade port: conditions + backtest + optimizer smoke."""
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]

from src.backtest.nexttrade_backtest import (  # noqa: E402
    BacktestConfig,
    load_prices,
    run_composable_backtest,
)
from src.signals.nexttrade_conditions import (  # noqa: E402
    AndCondition,
    BuyingPowerIs,
    ConditionContext,
    MovingAverageCondition,
    OrCondition,
    SimplePriceCondition,
    create,
)


def test_compare_and_compound():
    ctx = ConditionContext(symbol="SPY", price=90.0, buying_power=9000.0)
    a = SimplePriceCondition(100.0, "LT")
    b = BuyingPowerIs(8000.0, "GTE")
    assert a.is_true(ctx) is True
    assert AndCondition([a, b]).is_true(ctx) is True
    assert OrCondition([SimplePriceCondition(100.0, "GT"), b]).is_true(ctx) is True
    spec = {"type": "AndCondition", "conditions": [
        {"type": "SimplePriceCondition", "target_price": 100.0, "comparator": "LT"},
        {"type": "BuyingPowerIsCondition", "threshold": 8000.0, "comparator": "GTE"}]}
    assert create(spec).is_true(ctx) is True


def test_ma_evaluate_no_lookahead():
    idx = pd.date_range("2020-01-01", periods=20, freq="D")
    close = pd.Series(range(20), index=idx, dtype=float) + 100.0
    prices = pd.DataFrame({"spy_close": close})
    ctx = ConditionContext(symbol="SPY")
    cond = MovingAverageCondition(window=5, standard_deviation=-1.0,
                                  statistic="mean", comparator="LTE")
    sig = cond.evaluate(prices, ctx)
    assert len(sig) == 20
    assert sig.iloc[:5].sum() == 0  # warmup, no signal on incomplete window


def test_backtest_spy_real_csv():
    prices = load_prices("SPY", root=str(ROOT))
    assert len(prices) > 1000
    entry = MovingAverageCondition(window=5, standard_deviation=-1.0,
                                   statistic="mean", comparator="LTE", symbol="SPY")
    res = run_composable_backtest(entry, prices, BacktestConfig(symbol="SPY"))
    s = res["stats"]
    assert s["trades"] > 10
    assert s["max_drawdown"] >= 0.0
    assert "spy_percent" in s and "excess_percent" in s
    assert res["detail"]["equity"].iloc[-1] > 0
