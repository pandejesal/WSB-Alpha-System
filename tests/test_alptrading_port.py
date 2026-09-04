"""Tests for AlpacaTradingAgent port: safety, sizing, debate, memory."""
import pathlib
import tempfile

import pandas as pd

from src.research.alptrading_debate import (  # noqa: E402
    AnalystReport,
    build_intent,
    extract_protective_price,
    extract_signal,
    run_investment_debate,
    run_risk_debate,
)
from src.research.alptrading_memory import DecisionMemoryLog  # noqa: E402
from src.risk.alptrading_safety import SafetyGuard  # noqa: E402
from src.risk.alptrading_sizing import (  # noqa: E402
    PositionSizer,
    RiskParameters,
    compute_atr,
    kelly_position_fraction,
)

ACCT = {"equity": 100_000.0, "last_equity": 100_000.0}


def _guard(**over):
    tmp = tempfile.mkdtemp()
    return SafetyGuard(config=over, state_path=pathlib.Path(tmp) / "s.json",
                       kill_switch_path=pathlib.Path(tmp) / "KS")


def test_kill_switch():
    g = _guard()
    assert g.check_order("AAPL", 100.0, account=ACCT).allowed
    g.engage_kill_switch("test halt")
    v = g.check_order("AAPL", 100.0, account=ACCT)
    assert not v.allowed and "kill switch" in v.reasons[0].lower()
    g.release_kill_switch()
    assert g.check_order("AAPL", 100.0, account=ACCT).allowed


def test_notional_and_concentration():
    g = _guard(max_trade_notional_usd=5_000.0, max_symbol_concentration_pct=25.0)
    assert g.check_order("AAPL", 5_000.0, account=ACCT).allowed
    v = g.check_order("AAPL", 5_000.01, account=ACCT)
    assert not v.allowed and any("notional" in r.lower() for r in v.reasons)
    v = g.check_order("AAPL", 10_000.0, account=ACCT, position_value=20_000.0)
    assert not v.allowed  # 30% > 25%
    assert g.check_order("AAPL", 4_000.0, account=ACCT, position_value=20_000.0).allowed
    v = g.check_order("AAPL", 1_000.0, position_value=90_000.0)  # no account
    assert v.allowed and v.checks["concentration"]["status"] == "skipped"


def test_breakers_and_nan_safety():
    g = _guard()
    v = g.check_order("AAPL", 100.0, account={"equity": 94_000.0, "last_equity": 100_000.0})
    assert not v.allowed and any("daily loss" in r.lower() for r in v.reasons)
    # risk-reducing exits bypass breakers
    assert g.check_order("AAPL", 100.0, account={"equity": 94_000.0, "last_equity": 100_000.0},
                         risk_reducing=True).allowed
    # NaN equity never silently passes: checks skip, no crash
    v = g.check_order("AAPL", 100.0, account={"equity": float("nan"), "last_equity": 100_000.0})
    assert v.allowed and v.checks["daily_loss"]["status"] == "skipped"


def test_atr_and_kelly_reference():
    bars = pd.DataFrame({"high": [101, 103, 102, 104, 103.5, 105],
                         "low": [99, 101, 100, 102, 101.5, 103],
                         "close": [100, 102, 101, 103, 102.5, 104]})
    assert abs(compute_atr(bars, period=3) - 66.5 / 27) < 1e-6
    assert compute_atr(pd.DataFrame(), period=14) is None
    assert abs(kelly_position_fraction(0.55, 1.5, 0.5) - 0.125) < 1e-9
    assert kelly_position_fraction(0.40, 1.0, 0.5) == 0.0


def test_sizer_caps():
    s = PositionSizer(RiskParameters())
    d = s.size_position(equity=100_000.0, price=100.0, atr=2.0,
                        confidence="high", requested_notional=50_000.0)
    assert d.approved and abs(d.notional - 12_500.0) < 0.01 and "kelly" in d.caps_applied
    assert abs(d.stop_loss_price - 96.0) < 1e-6 and abs(d.risk_amount - 500.0) < 0.01


def test_debate_and_signal_utils():
    reps = [AnalystReport("market", 0.6, "high", "uptrend"),
            AnalystReport("macro", 0.3, "medium", "regime"),
            AnalystReport("news", -0.2, "low", "noise")]
    r = run_investment_debate(reps, max_rounds=1)
    assert r.rounds == 2 and r.judge == "bull" and r.margin > 0
    tie = run_investment_debate([AnalystReport("market", 0.0, "low", "flat")])
    assert tie.judge == "tie"
    risk = run_risk_debate("BUY", ["overbought RSI>75"])
    assert risk["final"] == "HOLD" and risk["downgraded"]
    assert run_risk_debate("BUY", [])["final"] == "BUY"
    assert extract_signal("blah FINAL TRANSACTION PROPOSAL: **SELL** blah") == "SELL"
    assert extract_signal("no decision here") == "HOLD"
    assert extract_protective_price("stop at $4,250.50 area") == 4250.50
    assert extract_protective_price("8% below entry") is None
    assert extract_protective_price("below support") is None


def test_build_intent_spy_real_csv():
    from src.backtest.nexttrade_backtest import load_prices
    from src.signals.openprophet_technical import analyze
    root = pathlib.Path(__file__).resolve().parents[1]
    prices = load_prices("SPY", root=str(root))
    cc = [c for c in prices.columns if "close" in c][0]
    bars = pd.DataFrame({"close": prices[cc].astype(float).values,
                         "high": prices[cc].astype(float).values,
                         "low": prices[cc].astype(float).values})
    ta = analyze("SPY", bars)
    reps = [AnalystReport("market", 0.6 if ta.signal == "BUY" else -0.6, "high", ta.signal),
            AnalystReport("macro", 0.3, "medium", "regime")]
    g = _guard(max_trade_notional_usd=50_000.0)
    intent = build_intent("SPY", reps, ta.current_price, PositionSizer(RiskParameters()),
                          100_000.0, 8_000.0, guard=g, bars=bars)
    assert intent.action in ("BUY", "HOLD", "SELL") and intent.paper
    if intent.action == "BUY":
        assert 0 < intent.notional <= 8_000.0 and intent.stop_loss_price


def test_memory_log_roundtrip():
    tmp = tempfile.mkdtemp()
    mem = DecisionMemoryLog(pathlib.Path(tmp) / "mem.md")
    eid = mem.record("SPY", "BUY", "alptrading_debate", 500.0, 8000.0, ["debate=bull"])
    out = mem.resolve(eid, 550.0, "trend continued")
    assert out["realized_pct"] == 10.0
    stats = mem.stats(strategy="alptrading_debate")
    assert stats["decisions"] == 1 and stats["win_rate"] == 1.0
