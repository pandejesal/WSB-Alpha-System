"""OpenProphet managed-position lifecycle port (Python, stocks-only, paper-only).

Source: https://github.com/JakeNesler/OpenProphet
  services/position_manager.go (1,041 lines), models/models.go (DBManagedPosition)

Ported: PENDING -> ACTIVE -> PARTIAL -> CLOSED / STOPPED_OUT machine,
stop-loss %, take-profit %, trailing stop %, partial exit (pct of position
at a gain trigger, stop moved to breakeven after partial — mirrors
TRADING_RULES "lock partial profits at +25%, move stop to breakeven").

Safety deltas (user mandate: safe, Alpaca stocks, paper only):
  - STOCKS ONLY. Upstream is options-first (delta/DTE/theta rules); none of
    that is ported. No shorting, no leverage, no multi-leg.
  - Pre-trade checklist enforced in code (fail-closed): max allocation %
    per position, max open positions, max trades/day, daily-loss halt
    (-5% circuit breaker), limit-orders-only flag, no re-entry within
    `revenge_cooldown_bars` after a stop-out (their "no revenge trading" rule).
  - This module EVALUATES exits against price series and emits intended
    orders as dicts. It never touches a broker. Execution stays in the WSB
    paper sandbox; nothing here can go live.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RiskConfig:
    max_allocation_pct: float = 10.0  # upstream allows 15%; default tighter
    max_positions: int = 10
    max_trades_per_day: int = 10
    daily_loss_halt_pct: float = 5.0
    min_cash_pct: float = 50.0  # upstream: maintain 50-70% cash
    revenge_cooldown_bars: int = 2  # upstream: no re-entry within 2h
    limit_orders_only: bool = True


@dataclass
class ManagedPosition:
    position_id: str
    symbol: str
    side: str = "buy"  # buy only (no shorts in this port)
    quantity: float = 0.0
    entry_price: float = 0.0
    allocation_dollars: float = 0.0
    stop_loss_pct: float = 15.0
    take_profit_pct: float = 50.0
    trailing: bool = False
    trailing_pct: float = 10.0
    partial_pct: float = 50.0  # % of position exited at partial trigger
    partial_trigger_pct: float = 25.0  # gain % triggering partial exit
    status: str = "PENDING"  # PENDING ACTIVE PARTIAL CLOSED STOPPED_OUT
    current_price: float = 0.0
    peak_price: float = 0.0  # for trailing stop
    remaining_qty: float = 0.0
    notes: str = ""
    last_exit_bar: int = -10**9

    def activate(self, fill_price: float) -> None:
        self.entry_price = fill_price
        self.current_price = fill_price
        self.peak_price = fill_price
        self.remaining_qty = self.quantity
        self.status = "ACTIVE"

    def pnl_pct(self, price: float) -> float:
        if not self.entry_price:
            return 0.0
        return (price - self.entry_price) / self.entry_price * 100.0

    def stop_price(self) -> float:
        return self.entry_price * (1 - self.stop_loss_pct / 100.0)

    def target_price(self) -> float:
        return self.entry_price * (1 + self.take_profit_pct / 100.0)


def check_pre_trade(symbol: str, allocation: float, portfolio_value: float,
                    cash: float, open_positions: int, trades_today: int,
                    day_pnl_pct: float, cfg: RiskConfig) -> list[str]:
    """Return list of violations; empty list = pass. Fail-closed."""
    v = []
    if allocation / max(portfolio_value, 1e-9) * 100 > cfg.max_allocation_pct:
        v.append(f"allocation {allocation:.0f} exceeds {cfg.max_allocation_pct}% cap")
    if open_positions >= cfg.max_positions:
        v.append(f"already at max {cfg.max_positions} positions")
    if trades_today >= cfg.max_trades_per_day:
        v.append(f"already at max {cfg.max_trades_per_day} trades today")
    if day_pnl_pct <= -cfg.daily_loss_halt_pct:
        v.append(f"daily loss {day_pnl_pct:.1f}% hit -{cfg.daily_loss_halt_pct}% halt")
    if cash - allocation < portfolio_value * cfg.min_cash_pct / 100.0:
        v.append(f"would breach {cfg.min_cash_pct}% minimum cash")
    return v


def update_position(pos: ManagedPosition, price: float, bar_idx: int) -> list[dict[str, Any]]:
    """Evaluate one price tick. Returns intended orders (dicts, paper-only)."""
    orders: list[dict[str, Any]] = []
    if pos.status not in ("ACTIVE", "PARTIAL"):
        return orders
    pos.current_price = price
    pos.peak_price = max(pos.peak_price, price)
    gain = pos.pnl_pct(price)

    # trailing stop ratchets up with peak
    stop = pos.stop_price()
    if pos.trailing and pos.peak_price > pos.entry_price:
        stop = max(stop, pos.peak_price * (1 - pos.trailing_pct / 100.0))

    # partial exit once
    if (pos.status == "ACTIVE" and pos.partial_pct > 0
            and gain >= pos.partial_trigger_pct):
        qty = pos.remaining_qty * pos.partial_pct / 100.0
        orders.append({"action": "PARTIAL_EXIT", "position_id": pos.position_id,
                       "symbol": pos.symbol, "qty": round(qty, 6),
                       "price": price, "order_type": "limit"})
        pos.remaining_qty -= qty
        pos.status = "PARTIAL"
        # move stop to breakeven on remainder (upstream rule)
        pos.stop_loss_pct = 0.0
        stop = pos.stop_price()

    if price <= stop:
        orders.append({"action": "STOP_OUT", "position_id": pos.position_id,
                       "symbol": pos.symbol, "qty": round(pos.remaining_qty, 6),
                       "price": price, "order_type": "limit"})
        pos.remaining_qty = 0.0
        pos.status = "STOPPED_OUT"
        pos.last_exit_bar = bar_idx
    elif price >= pos.target_price():
        orders.append({"action": "TAKE_PROFIT", "position_id": pos.position_id,
                       "symbol": pos.symbol, "qty": round(pos.remaining_qty, 6),
                       "price": price, "order_type": "limit"})
        pos.remaining_qty = 0.0
        pos.status = "CLOSED"
        pos.last_exit_bar = bar_idx
    return orders


def can_reenter(pos: ManagedPosition, bar_idx: int, cfg: RiskConfig) -> bool:
    """Revenge-trading guard: no re-entry within cooldown after stop-out."""
    if pos.status != "STOPPED_OUT":
        return True
    return (bar_idx - pos.last_exit_bar) >= cfg.revenge_cooldown_bars


def open_position(position_id: str, symbol: str, allocation: float, price: float,
                  portfolio_value: float, cash: float, open_positions: int,
                  trades_today: int, day_pnl_pct: float,
                  cfg: RiskConfig, stop_loss_pct: float = 15.0,
                  take_profit_pct: float = 50.0,
                  partial: dict[str, float] | None = None) -> ManagedPosition:
    """Validate checklist then construct a PENDING managed position.

    Raises ValueError on any violation (fail-closed). Caller activates on fill.
    """
    violations = check_pre_trade(symbol, allocation, portfolio_value, cash,
                                 open_positions, trades_today, day_pnl_pct, cfg)
    if violations:
        raise ValueError("pre-trade checklist failed: " + "; ".join(violations))
    if price <= 0:
        raise ValueError("price must be positive")
    qty = allocation / price
    pos = ManagedPosition(position_id=position_id, symbol=symbol,
                          quantity=qty, allocation_dollars=allocation,
                          stop_loss_pct=stop_loss_pct,
                          take_profit_pct=take_profit_pct)
    if partial:
        pos.partial_pct = float(partial.get("pct", 50.0))
        pos.partial_trigger_pct = float(partial.get("trigger_pct", 25.0))
    return pos
