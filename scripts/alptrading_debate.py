#!/usr/bin/env python3
"""AlpacaTradingAgent deterministic debate runner (paper-only, local data).

Builds the 5-analyst report set from real local indicators (no LLM, no
network), runs bull/bear debate -> trader direction -> risk debate ->
Kelly/ATR sizing -> SafetyGuard, records the decision to the markdown
memory log, and prints the typed TradeIntent as JSON.

Analyst mapping (honest, documented):
  market        OpenProphet TA vote (BUY +0.6 / SELL -0.6 / HOLD 0)
  sentiment     0.0 (no social feed configured — abstains, never invents)
  news          0.0 (no news feed configured — abstains, never invents)
  fundamentals  RSI mean-reversion snap (<30 +0.5, >70 -0.5, else 0)
  macro         SPY-vs-SMA50 regime proxy (+0.3 above, -0.3 below)

Usage:
  python scripts/alptrading_debate.py --symbol SPY --equity 100000 --request 8000
"""
import argparse
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.backtest.nexttrade_backtest import load_prices  # noqa: E402
from src.research.alptrading_debate import (  # noqa: E402
    AnalystReport,
    build_intent,
)
from src.research.alptrading_memory import DecisionMemoryLog  # noqa: E402
from src.risk.alptrading_safety import SafetyGuard  # noqa: E402
from src.risk.alptrading_sizing import PositionSizer, RiskParameters  # noqa: E402
from src.signals.openprophet_technical import analyze  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="SPY")
    ap.add_argument("--equity", type=float, default=100000.0)
    ap.add_argument("--request", type=float, default=8000.0)
    ap.add_argument("--memory-log", default="docs/data/alptrading_memory.md")
    ap.add_argument("--state-dir", default="")
    args = ap.parse_args()

    prices = load_prices(args.symbol, root=str(ROOT))
    close_col = [c for c in prices.columns if "close" in c][0]
    bars = pd.DataFrame(index=prices.index)
    bars["close"] = prices[close_col].astype(float).values
    for f in ("open", "high", "low"):
        col = [c for c in prices.columns if f in c]
        if col:
            bars[f] = prices[col[0]].astype(float).values
    if "high" not in bars:
        bars["high"] = bars["close"]
        bars["low"] = bars["close"]
    vol = [c for c in prices.columns if "volume" in c or "vol" in c]
    if vol:
        bars["volume"] = prices[vol[0]].astype(float).values

    ta = analyze(args.symbol, bars)
    price = ta.current_price
    tmap = {"BUY": 0.6, "SELL": -0.6, "HOLD": 0.0}
    tconf = {"BUY": "high", "SELL": "high", "HOLD": "low"}[ta.signal]
    rsi_score = 0.5 if ta.rsi < 30 else (-0.5 if ta.rsi > 70 else 0.0)
    regime = 0.3 if price > ta.sma50 > 0 else (-0.3 if 0 < price < ta.sma50 else 0.0)
    reports = [
        AnalystReport("market", tmap[ta.signal], tconf,
                      f"TA vote {ta.signal} conf {ta.confidence:.0f}, RSI {ta.rsi:.1f}"),
        AnalystReport("sentiment", 0.0, "low", "no social feed configured — abstain"),
        AnalystReport("news", 0.0, "low", "no news feed configured — abstain"),
        AnalystReport("fundamentals", rsi_score, "medium", f"RSI snap {ta.rsi:.1f}"),
        AnalystReport("macro", regime, "medium", f"price vs SMA50 regime {regime:+.1f}"),
    ]
    flags = []
    if ta.rsi > 75:
        flags.append("overbought RSI>75")

    kw = {}
    if args.state_dir:
        kw = {"state_path": pathlib.Path(args.state_dir) / "safety-state.json",
              "kill_switch_path": pathlib.Path(args.state_dir) / "KILL_SWITCH"}
    guard = SafetyGuard(config={"max_trade_notional_usd": args.request}, **kw)
    sizer = PositionSizer(RiskParameters())
    intent = build_intent(args.symbol, reports, price, sizer, args.equity,
                          args.request, guard=guard, risk_flags=flags, bars=bars)

    mem = DecisionMemoryLog(ROOT / args.memory_log)
    entry_id = mem.record(args.symbol, intent.action, "alptrading_debate",
                          price, intent.notional, intent.reasons)
    print(json.dumps({"intent": intent.to_dict(), "memory_entry": entry_id,
                      "ta": {"signal": ta.signal, "confidence": ta.confidence,
                             "rsi": round(ta.rsi, 1)},
                      "status": "paper", "live": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
