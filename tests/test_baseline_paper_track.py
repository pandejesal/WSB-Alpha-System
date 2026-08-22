"""Hermetic tests for baseline_paper_track (Task 5.3)."""

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import baseline_paper_track as bpt  # noqa: E402


@pytest.fixture()
def mod():
    return importlib.reload(bpt)


def _fills(rows):
    return {"run_id": "t", "fills": rows}


def _fill(ts, side, qty, px, status="FILLED", sleeve="eq", ticker="SPY"):
    return {"ts": ts, "side": side, "qty": qty, "avg_px": px, "status": status, "sleeve": sleeve, "ticker": ticker}


def test_sleeve_summary_aggregates_buy_sell(mod):
    doc = _fills([
        _fill("2026-07-01T10:00:00Z", "buy", 2.0, 100.0),
        _fill("2026-08-01T10:00:00Z", "sell", 2.0, 110.0),
    ])
    agg = mod.sleeve_summary(doc)
    assert agg["eq:SPY"]["net_qty"] == pytest.approx(0.0)
    assert agg["eq:SPY"]["realized_pnl"] == pytest.approx(20.0)
    assert agg["eq:SPY"]["open_exposure_qty"] == 0.0


def test_monthly_pnl_and_green_rule(mod):
    doc = _fills([
        _fill("2026-07-01T10:00:00Z", "buy", 2.0, 100.0),
        _fill("2026-08-01T10:00:00Z", "sell", 2.0, 110.0),
    ])
    monthly = mod.monthly_pnl(doc)
    assert monthly["2026-07"] == pytest.approx(-200.0)
    assert monthly["2026-08"] == pytest.approx(220.0)
    assert not all(v > 0 for v in monthly.values())


def test_broken_executions_flags_unknown_status(mod):
    doc = {"orders": [{"client_order_id": "a", "status": "SUBMITTED"}, {"client_order_id": "b", "status": "REJECTED"}]}
    broken = mod.broken_executions(doc)
    assert len(broken) == 1 and broken[0]["client_order_id"] == "b"


def test_verdict_need_more_paper_time(mod):
    doc = _fills([_fill("2026-07-01T10:00:00Z", "buy", 1.0, 10.0)])
    # direct call with monkeypatched loaders
    orig = (mod._load)

    def fake_load(path):
        if path.name == "fills.json":
            return doc
        if path.name == "orders.json":
            return {"orders": []}
        return None

    mod._load = fake_load
    try:
        d = mod.build_dashboard(min_months=2)
        assert d["verdict"] == "NEED_MORE_PAPER_TIME"
    finally:
        mod._load = orig


def test_max_drawdown_from_monthly(mod):
    monthly = {"2026-01": 10000.0, "2026-02": -30000.0}
    mdd = mod.max_drawdown_from_monthly(monthly)
    assert 0.25 < mdd < 0.30


def test_render_verdict_md_contains_verdict(mod):
    md = mod.render_verdict_md({
        "verdict": "NEED_MORE_PAPER_TIME",
        "generated_at": "2026-08-22T00:00:00Z",
        "criteria": {"months_tracked": 0, "min_months_required": 2, "all_months_green": False,
                     "max_drawdown": None, "max_dd_limit": 0.15, "broken_executions": []},
        "monthly_realized_pnl": {},
    })
    assert "NEED_MORE_PAPER_TIME" in md and "Paper Approval Verdict" in md
