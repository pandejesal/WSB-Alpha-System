"""Tests for the Lean engine port (src/backtest/lean_engine.py)."""

import pathlib
import sys
from datetime import datetime

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # noqa: E402

from src.backtest.lean_engine import (  # noqa: E402
    Algorithm,
    Bar,
    FeeModel,
    SecurityHolding,
    SlippageModel,
    Slice,
)

TS = datetime(2024, 1, 1)


# ── Bar ───────────────────────────────────────────────────────────────────────

def test_bar_creation():
    bar = Bar(TS, 100.0, 105.0, 99.0, 102.5, 1_000_000)
    assert bar.time == TS
    assert bar.open == 100.0
    assert bar.high == 105.0
    assert bar.low == 99.0
    assert bar.close == 102.5
    assert bar.volume == 1_000_000


# ── Slice ─────────────────────────────────────────────────────────────────────

def test_slice_getitem_and_contains():
    bar = Bar(TS, 100, 105, 99, 102, 1000)
    s = Slice(TS, {"AAPL": bar})
    assert s["AAPL"].close == 102
    assert "AAPL" in s
    assert "GOOG" not in s


def test_slice_get():
    bar = Bar(TS, 100, 105, 99, 102, 1000)
    s = Slice(TS, {"AAPL": bar})
    assert s.get("AAPL") is bar
    assert s.get("MSFT") is None


# ── SecurityHolding ───────────────────────────────────────────────────────────

def test_holding_buy_pnl():
    h = SecurityHolding("AAPL")
    h.update_price(150.0)
    h.buy(10, 150.0, 1.0)
    assert h.quantity == 10
    # fee is rolled into average price: (150*10 + 1.0) / 10 = 150.1
    assert h.average_price == pytest.approx(150.1)
    h.update_price(160.0)
    assert h.unrealized_pnl == pytest.approx(99.0)


def test_holding_sell_pnl():
    h = SecurityHolding("AAPL")
    h.buy(10, 100.0, 0.0)
    h.sell(5, 110.0, 0.0)
    assert h.quantity == 5


# ── FeeModel ──────────────────────────────────────────────────────────────────

def test_fee_model_per_share():
    fm = FeeModel(per_share=0.01, minimum=0.0)
    assert fm.calculate(100, 50.0) == pytest.approx(1.0)


def test_fee_model_minimum():
    fm = FeeModel(per_share=0.01, minimum=1.0)
    assert fm.calculate(1, 50.0) == pytest.approx(1.0)


# ── SlippageModel ─────────────────────────────────────────────────────────────

def test_slippage_buy():
    sm = SlippageModel(bps=5)
    # 5 bps = 0.05% of price
    assert sm.apply(100.0, is_buy=True) == pytest.approx(100.05)


def test_slippage_sell():
    sm = SlippageModel(bps=5)
    assert sm.apply(100.0, is_buy=False) == pytest.approx(99.95)


# ── Algorithm API ─────────────────────────────────────────────────────────────

def test_algo_init_and_api():
    algo = Algorithm()
    algo.SetCash(50_000)
    algo.SetStartDate(2020, 1, 1)
    algo.SetEndDate(2020, 12, 31)
    algo.SetBenchmark("SPY")
    algo.AddEquity("AAPL")
    assert algo.cash == 50_000
    assert algo.start_date is not None
    assert algo.end_date is not None


def test_set_holdings_generates_order():
    algo = Algorithm()
    algo.SetCash(100_000)
    algo.AddEquity("SPY")
    # SetHoldings needs a known price to compute delta shares
    algo.portfolio["SPY"].update_price(400.0)
    algo.SetHoldings("SPY", 1.0)
    assert len(algo._pending_orders) == 1
    o = algo._pending_orders[0]
    assert o.symbol == "SPY"
    assert o.quantity > 0


def test_set_holdings_rejects_negative():
    algo = Algorithm()
    algo.AddEquity("SPY")
    with pytest.raises(ValueError):
        algo.SetHoldings("SPY", -0.5)


def test_set_holdings_rejects_leverage():
    algo = Algorithm()
    algo.AddEquity("SPY")
    with pytest.raises(ValueError):
        algo.SetHoldings("SPY", 1.5)


def test_liquidate():
    algo = Algorithm()
    algo.AddEquity("SPY")
    algo.portfolio["SPY"].buy(10, 400.0, 0.0)
    algo.Liquidate("SPY")
    assert len(algo._pending_orders) == 1
    assert algo._pending_orders[0].quantity == 10  # sells all 10 shares


# ── PortfolioTarget ───────────────────────────────────────────────────────────

def test_portfolio_target():
    algo = Algorithm()
    algo.AddEquity("SPY")
    algo.PortfolioTarget("SPY", 100)
    assert len(algo._pending_orders) == 1
    assert algo._pending_orders[0].quantity == 100


# ── Debug / Log ───────────────────────────────────────────────────────────────

def test_debug_and_log():
    algo = Algorithm()
    algo.Debug("hello")
    algo.Log("world")
    assert len(algo._log) == 2
