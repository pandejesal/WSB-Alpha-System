#!/usr/bin/env python3
"""OpenProphet beat runner: one deterministic heartbeat over local CSV data.

One beat = ORIENT (phase) -> ASSESS (account state) -> MANAGE (update open
managed positions) -> SCAN (technical analysis per symbol) -> LOG (journal).

Paper-only. Never places live orders; intended orders are printed/logged.
Exit signals from the TA scan do NOT auto-open positions — opening requires
passing the pre-trade checklist AND (by repo rule) 5-gate validation for any
new strategy. This runner only manages explicitly seeded positions and logs.

Usage:
  python scripts/openprophet_beat.py --symbols SPY --beats 1
  python scripts/openprophet_beat.py --symbols SPY,QQQ --beats 3 --phases midday,market_close
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.backtest.nexttrade_backtest import load_prices  # noqa: E402
from src.execution.openprophet_positions import (  # noqa: E402
    RiskConfig,
    check_pre_trade,
    update_position,
)
from src.ops.openprophet_heartbeat import get_current_phase, run_beats  # noqa: E402
from src.research.openprophet_journal import Journal  # noqa: E402
from src.signals.openprophet_technical import analyze  # noqa: E402


def load_bars(symbol: str) -> pd.DataFrame:
    prices = load_prices(symbol, root=str(ROOT))
    close_col = [c for c in prices.columns if "close" in c][0]
    df = pd.DataFrame(index=prices.index)
    df["close"] = prices[close_col].astype(float).values
    vol = [c for c in prices.columns if "volume" in c or "vol" in c]
    if vol:
        df["volume"] = prices[vol[0]].astype(float).values
    return df


last_close: dict = {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="SPY")
    ap.add_argument("--beats", type=int, default=1)
    ap.add_argument("--phases", default="")
    ap.add_argument("--journal", default="")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    phases = [p.strip() for p in args.phases.split(",") if p.strip()] or None
    journal = Journal(args.journal) if args.journal else Journal()
    cfg = RiskConfig()
    cash, portfolio = 60000.0, 100000.0  # 60% cash floor respected
    open_positions: list = []
    trades_today = 0

    global last_close
    last_close = {s: float(load_bars(s)["close"].iloc[-1]) for s in symbols}

    def beat(phase: str, n: int) -> dict:
        nonlocal trades_today
        journal.log_activity("beat", f"beat {n} phase={phase} symbols={symbols}")
        actions: list = []
        # MANAGE
        for pos in list(open_positions):
            for o in update_position(pos, float(last_close[pos.symbol]), n):
                actions.append(o)
                trades_today += 1
                journal.log_activity("manage",
                                     f"{o['action']} {o['symbol']} qty={o['qty']}")
        # SCAN
        scans = {}
        for sym in symbols:
            bars = load_bars(sym)
            res = analyze(sym, bars)
            scans[sym] = {"signal": res.signal, "confidence": res.confidence,
                          "price": res.current_price, "rsi": round(res.rsi, 1),
                          "sma20": round(res.sma20, 2), "sma50": round(res.sma50, 2)}
            journal.log_signal(sym, res.signal, res.confidence, "openprophet_ta",
                               f"RSI {res.rsi:.1f} SMA20 {res.sma20:.1f}")
        journal.snapshot(cash, portfolio, cash)
        journal.log_decision(phase, f"beat {n}: {len(actions)} actions",
                             json.dumps(scans))
        return {"symbols": scans, "actions": actions, "trades_today": trades_today,
                "checklist_demo": check_pre_trade("SPY", 5000, portfolio, cash,
                                                  len(open_positions), trades_today,
                                                  0.0, cfg)}

    out = run_beats(beat, phases=phases, max_beats=args.beats)
    print(json.dumps({"phase_now": get_current_phase(), "beats": out,
                      "status": "paper", "live": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
