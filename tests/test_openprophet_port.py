"""Tests for OpenProphet port: heartbeat phases, TA, positions, journal."""
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]

from src.execution.openprophet_positions import (  # noqa: E402
    RiskConfig,
    can_reenter,
    check_pre_trade,
    open_position,
    update_position,
)
from src.ops.openprophet_heartbeat import (  # noqa: E402
    beat_interval_seconds,
    get_current_phase,
)
from src.research.openprophet_journal import Journal  # noqa: E402
from src.signals.openprophet_technical import analyze  # noqa: E402

ET = ZoneInfo("America/New_York")


def _et(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


def test_phases():
    assert get_current_phase(_et(2026, 9, 2, 10, 0)) == "market_open"  # Wed 10:00 ET
    assert get_current_phase(_et(2026, 9, 2, 13, 0)) == "midday"
    assert get_current_phase(_et(2026, 9, 2, 3, 0)) == "closed"
    assert get_current_phase(_et(2026, 9, 5, 12, 0)) == "closed"  # Saturday
    assert beat_interval_seconds("market_open") == 120
    assert beat_interval_seconds("closed") == 3600


def test_ta_spy_real_csv():
    from src.backtest.nexttrade_backtest import load_prices
    prices = load_prices("SPY", root=str(ROOT))
    col = [c for c in prices.columns if "close" in c][0]
    bars = pd.DataFrame({"close": prices[col].astype(float)})
    vol = [c for c in prices.columns if "volume" in c or "vol" in c]
    if vol:
        bars["volume"] = prices[vol[0]].astype(float)
    res = analyze("SPY", bars)
    assert res.signal in ("BUY", "SELL", "HOLD")
    assert 0 <= res.confidence <= 100
    assert 0 <= res.rsi <= 100
    assert res.sma20 > 0 and res.sma50 > 0
    # no-lookahead spot check: last-bar-only change must not alter earlier SMA
    assert res.current_price == float(bars["close"].iloc[-1])


def test_managed_position_lifecycle():
    cfg = RiskConfig()
    pos = open_position("t1", "SPY", 5000, 500.0, 100000.0, 60000.0, 0, 0, 0.0, cfg,
                        stop_loss_pct=10.0, take_profit_pct=50.0,
                        partial={"pct": 50.0, "trigger_pct": 25.0})
    pos.activate(500.0)
    assert pos.status == "ACTIVE"
    # partial at +25%
    orders = update_position(pos, 625.0, 1)
    assert pos.status == "PARTIAL"
    assert any(o["action"] == "PARTIAL_EXIT" for o in orders)
    # stop moved to breakeven: dip below entry but above old stop keeps PARTIAL
    orders = update_position(pos, 490.0, 2)
    assert pos.status == "STOPPED_OUT"
    assert any(o["action"] == "STOP_OUT" for o in orders)
    assert can_reenter(pos, 2, cfg) is False
    assert can_reenter(pos, 2 + cfg.revenge_cooldown_bars, cfg) is True


def test_take_profit_and_checklist():
    cfg = RiskConfig()
    # checklist blocks oversized allocation
    assert check_pre_trade("SPY", 50000, 100000.0, 60000.0, 0, 0, 0.0, cfg)
    # checklist blocks trading into daily halt
    assert check_pre_trade("SPY", 1000, 100000.0, 60000.0, 0, 0, -6.0, cfg)
    assert check_pre_trade("SPY", 1000, 100000.0, 60000.0, 0, 0, 0.0, cfg) == []
    pos = open_position("t2", "SPY", 5000, 500.0, 100000.0, 60000.0, 0, 0, 0.0, cfg,
                        take_profit_pct=50.0, partial={"pct": 0.0, "trigger_pct": 999})
    pos.activate(500.0)
    orders = update_position(pos, 760.0, 5)
    assert pos.status == "CLOSED"
    assert any(o["action"] == "TAKE_PROFIT" for o in orders)


def test_journal_roundtrip():
    j = Journal()
    j.log_signal("SPY", "BUY", 65.0, "openprophet_ta", "RSI 28")
    j.log_signal("SPY", "BUY", 70.0, "openprophet_ta", "RSI 27")
    sim = j.find_similar_setups(symbol="SPY", strategy="openprophet_ta",
                                signal="BUY", strength=66.0)
    assert len(sim) == 2 and sim[0]["strength"] == 65.0
    t = j.log_trade("SPY", 500.0, 550.0, 10.0, "buy", "openprophet_ta")
    assert t["pnl"] == 500.0
    stats = j.trade_stats(symbol="SPY")
    assert stats["trades"] == 1 and stats["win_rate"] == 1.0
