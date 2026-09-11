"""AlpacaTradingAgent position-sizing port (pure math, no broker, no LLM).

Source: https://github.com/huygiatrng/AlpacaTradingAgent
  tradingagents/risk/position_sizing.py (245 lines)

Faithful port: Wilder-smoothed ATR (seed = mean of first `period` true
ranges, then RMA), fractional Kelly with shrunk confidence edges
(high 0.55/1.5, medium 0.52/1.3, low 0.50/1.1 — slight edge assumed even
at high confidence), 5% fallback stop without volatility data, caps =
min(requested, risk-per-trade, Kelly, max-position-%, exposure-room),
min-notional rejection, risk_amount = sized qty x stop distance.

The design maxim is kept: the decider picks direction, this layer picks
size. Complements (not replaces) WSB src/risk/position_sizing.py.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

DEFAULT_CONFIDENCE_EDGE = {
    "high": (0.55, 1.5),
    "medium": (0.52, 1.3),
    "low": (0.50, 1.1),
}

FALLBACK_STOP_PCT = 0.05


def compute_atr(bars, period: int = 14) -> float | None:
    try:
        if bars is None or len(bars) < period + 1:
            return None
        columns = {str(c).lower(): c for c in bars.columns}
        high = bars[columns["high"]].astype(float).reset_index(drop=True)
        low = bars[columns["low"]].astype(float).reset_index(drop=True)
        close = bars[columns["close"]].astype(float).reset_index(drop=True)
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1).iloc[1:]
    if len(true_range) < period or true_range.isna().any():
        return None
    atr = float(true_range.iloc[:period].mean())
    for value in true_range.iloc[period:]:
        atr = (atr * (period - 1) + float(value)) / period
    if not math.isfinite(atr) or atr <= 0:
        return None
    return atr


def kelly_position_fraction(win_rate: float, win_loss_ratio: float,
                            kelly_fraction: float = 0.5) -> float:
    try:
        win_rate = float(win_rate)
        win_loss_ratio = float(win_loss_ratio)
        kelly_fraction = float(kelly_fraction)
    except (TypeError, ValueError):
        return 0.0
    if not 0.0 < win_rate < 1.0 or win_loss_ratio <= 0.0 or kelly_fraction <= 0.0:
        return 0.0
    return max(0.0, (win_rate - (1.0 - win_rate) / win_loss_ratio) * kelly_fraction)


@dataclass(frozen=True)
class RiskParameters:
    risk_per_trade_pct: float = 0.01
    kelly_fraction: float = 0.5
    atr_period: int = 14
    atr_stop_multiplier: float = 2.0
    max_position_pct: float = 0.20
    max_total_exposure_pct: float = 0.80
    min_notional: float = 10.0
    confidence_edge: dict = field(default_factory=lambda: dict(DEFAULT_CONFIDENCE_EDGE))

    @classmethod
    def from_dict(cls, overrides: dict | None) -> "RiskParameters":
        if not overrides:
            return cls()
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in overrides.items() if k in known})


@dataclass(frozen=True)
class SizingDecision:
    approved: bool
    notional: float
    stop_loss_price: float | None
    risk_amount: float
    caps_applied: list
    reason: str

    def to_dict(self) -> dict:
        return {"approved": self.approved, "notional": self.notional,
                "stop_loss_price": self.stop_loss_price, "risk_amount": self.risk_amount,
                "caps_applied": list(self.caps_applied), "reason": self.reason}


def _rejection(reason: str, notes=None) -> SizingDecision:
    return SizingDecision(False, 0.0, None, 0.0, list(notes or []), reason)


class PositionSizer:
    def __init__(self, params: RiskParameters | None = None):
        self.params = params or RiskParameters()

    def size_position(self, *, equity: float, price: float, atr: float | None,
                      confidence: str, requested_notional: float,
                      current_gross_exposure: float = 0.0,
                      side: str = "buy") -> SizingDecision:
        params = self.params
        try:
            equity = float(equity)
            price = float(price)
            requested_notional = float(requested_notional)
            current_gross_exposure = max(0.0, float(current_gross_exposure or 0.0))
        except (TypeError, ValueError):
            return _rejection("Invalid numeric inputs for position sizing.")
        if not math.isfinite(equity) or equity <= 0.0:
            return _rejection(f"Invalid account equity: {equity}.")
        if not math.isfinite(price) or price <= 0.0:
            return _rejection(f"Invalid price: {price}.")
        if not math.isfinite(requested_notional) or requested_notional <= 0.0:
            return _rejection(f"Invalid requested notional: {requested_notional}.")

        notes = []
        if atr is not None and math.isfinite(atr) and atr > 0.0:
            stop_distance = float(atr) * params.atr_stop_multiplier
        else:
            stop_distance = price * FALLBACK_STOP_PCT
            notes.append("atr_unavailable_default_stop")

        exposure_room = equity * params.max_total_exposure_pct - current_gross_exposure
        if exposure_room < params.min_notional:
            return _rejection(
                f"Portfolio exposure limit reached: gross exposure "
                f"{current_gross_exposure:.2f} leaves only {max(exposure_room, 0.0):.2f} "
                f"of the {params.max_total_exposure_pct:.0%} cap.", notes)

        risk_budget = equity * params.risk_per_trade_pct
        risk_notional = (risk_budget / stop_distance) * price
        edge = params.confidence_edge.get(str(confidence).strip().lower(),
                                          params.confidence_edge.get("low", (0.50, 1.1)))
        win_rate, win_loss_ratio = edge
        kelly_f = kelly_position_fraction(win_rate, win_loss_ratio, params.kelly_fraction)
        if kelly_f <= 0.0:
            return _rejection(f"No positive edge for confidence '{confidence}'; Kelly allocation is zero.", notes)
        caps = {"requested_notional": requested_notional, "risk_per_trade": risk_notional,
                "kelly": equity * kelly_f, "max_position_pct": equity * params.max_position_pct,
                "max_total_exposure": exposure_room}
        notional = min(caps.values())
        binding = [n for n, v in caps.items() if math.isclose(v, notional, rel_tol=1e-9, abs_tol=1e-9)]
        if notional < params.min_notional:
            return _rejection(f"Sized notional {notional:.2f} below minimum {params.min_notional:.2f} "
                              f"(binding cap: {binding[0]}).", notes)
        notional = round(notional, 2)
        quantity = notional / price
        risk_amount = round(quantity * stop_distance, 2)
        if str(side).strip().lower() in ("sell", "short"):
            stop_loss_price = round(price + stop_distance, 6)
        else:
            stop_loss_price = round(price - stop_distance, 6)
        return SizingDecision(True, notional, stop_loss_price, risk_amount,
                              binding + notes, f"Sized {notional:.2f} bound by {', '.join(binding)}.")
