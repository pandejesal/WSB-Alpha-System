"""OpenProphet trade-journal port (Python, stdlib sqlite3).

Source: https://github.com/JakeNesler/OpenProphet
  models/models.go (orders/bars/positions/trades/account_snapshots/signals),
  services/activity_logger.go, vectorDB.js + backfill_embeddings.js,
  seed_data/trading_principles.json.

Ported tables: signals, trades, account_snapshots, activity_log,
decisions. `find_similar_setups` is ported as deterministic feature
matching (same symbol/strategy/signal + nearest RSI/confidence) instead
of ChromaDB embeddings — no new dependency, and semantic recall is
already covered by Mnemosyne in this repo. Documented in
docs/OPENPROPHET_PORT.md.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS signals(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, symbol TEXT, signal TEXT,
  strength REAL, strategy TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS trades(
  id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT, entry_price REAL,
  exit_price REAL, qty REAL, side TEXT, pnl REAL, pnl_pct REAL,
  entry_time TEXT, exit_time TEXT, strategy TEXT, metadata TEXT);
CREATE TABLE IF NOT EXISTS account_snapshots(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, cash REAL,
  portfolio_value REAL, buying_power REAL);
CREATE TABLE IF NOT EXISTS activity_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, message TEXT);
CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, phase TEXT, summary TEXT,
  detail TEXT);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Journal:
    def __init__(self, path: str | Path = ":memory:"):
        self.con = sqlite3.connect(str(path))
        self.con.executescript(SCHEMA)

    def log_signal(self, symbol: str, signal: str, strength: float,
                   strategy: str, reason: str = "") -> int:
        cur = self.con.execute(
            "INSERT INTO signals(ts,symbol,signal,strength,strategy,reason)"
            " VALUES(?,?,?,?,?,?)", (_now(), symbol, signal, strength, strategy, reason))
        self.con.commit()
        return int(cur.lastrowid)

    def log_trade(self, symbol: str, entry_price: float, exit_price: float,
                  qty: float, side: str, strategy: str,
                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        pnl = (exit_price - entry_price) * qty * (1 if side == "buy" else -1)
        pnl_pct = (exit_price / entry_price - 1) * 100 * (1 if side == "buy" else -1) \
            if entry_price else 0.0
        self.con.execute(
            "INSERT INTO trades(symbol,entry_price,exit_price,qty,side,pnl,pnl_pct,"
            "entry_time,exit_time,strategy,metadata) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (symbol, entry_price, exit_price, qty, side, pnl, pnl_pct,
             _now(), _now(), strategy, json.dumps(metadata or {})))
        self.con.commit()
        return {"pnl": pnl, "pnl_pct": pnl_pct}

    def snapshot(self, cash: float, portfolio_value: float, buying_power: float) -> None:
        self.con.execute(
            "INSERT INTO account_snapshots(ts,cash,portfolio_value,buying_power)"
            " VALUES(?,?,?,?)", (_now(), cash, portfolio_value, buying_power))
        self.con.commit()

    def log_activity(self, kind: str, message: str) -> None:
        self.con.execute("INSERT INTO activity_log(ts,kind,message) VALUES(?,?,?)",
                         (_now(), kind, message))
        self.con.commit()

    def log_decision(self, phase: str, summary: str, detail: str = "") -> None:
        self.con.execute("INSERT INTO decisions(ts,phase,summary,detail) VALUES(?,?,?,?)",
                         (_now(), phase, summary, detail))
        self.con.commit()

    def find_similar_setups(self, symbol: Optional[str] = None,
                            strategy: Optional[str] = None,
                            signal: Optional[str] = None,
                            strength: Optional[float] = None,
                            limit: int = 5) -> List[Dict[str, Any]]:
        """Deterministic stand-in for vector similarity search."""
        q = "SELECT symbol,signal,strength,strategy,reason FROM signals WHERE 1=1"
        args: List[Any] = []
        if symbol:
            q += " AND symbol=?"
            args.append(symbol)
        if strategy:
            q += " AND strategy=?"
            args.append(strategy)
        if signal:
            q += " AND signal=?"
            args.append(signal)
        rows = self.con.execute(q, args).fetchall()
        scored = []
        for s, sg, st, stgy, reason in rows:
            d = 0.0 if strength is None else abs(float(st) - strength)
            scored.append((d, {"symbol": s, "signal": sg, "strength": st,
                               "strategy": stgy, "reason": reason}))
        scored.sort(key=lambda x: x[0])
        return [r for _, r in scored[:limit]]

    def trade_stats(self, symbol: Optional[str] = None,
                    strategy: Optional[str] = None) -> Dict[str, float]:
        q = "SELECT pnl,pnl_pct FROM trades WHERE 1=1"
        args: List[Any] = []
        if symbol:
            q += " AND symbol=?"
            args.append(symbol)
        if strategy:
            q += " AND strategy=?"
            args.append(strategy)
        rows = self.con.execute(q, args).fetchall()
        if not rows:
            return {"trades": 0, "win_rate": 0.0, "total_pnl": 0.0, "avg_pnl_pct": 0.0}
        wins = sum(1 for _, p in rows if p > 0)
        return {"trades": len(rows), "win_rate": wins / len(rows),
                "total_pnl": float(sum(p for p, _ in rows)),
                "avg_pnl_pct": float(sum(p for _, p in rows)) / len(rows)}
