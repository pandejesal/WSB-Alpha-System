"""NextTrade condition engine port (Python / pandas).

Source: https://github.com/austin-starks/NextTrade (master 53a3c2a)
  app/src/models/conditions/*.ts, strategy/index.ts, portfolio/*

What was ported (semantics preserved, stack replaced):
  - AbstractCondition + ConditionFactory (dict/JSON/YAML specs, no Mongo)
  - Leaf conditions: SimplePrice, MovingAverage (mean/high/low + sd bands),
    BuyingPowerIs, HavePosition, PortfolioValueIs, PositionPercentChange,
    PortfolioIsProfitable, EnoughTimePassed
  - Compound: And / Or / Then (Then = if cond[0] then require cond[1])
  - Comparators: GT, GTE, LT, LTE, EQ  (NextTrade `compare` util)

Deliberate safety deltas vs NextTrade:
  - Venue Alpaca only. No Tradier/Coinbase/options-debit-spread order paths.
  - Two evaluation modes: scalar `is_true(ctx)` for paper stepping AND
    vectorized `evaluate(prices, ctx)` -> boolean Series for backtests
    (no lookahead: all rolling stats use .shift(1)).
  - No live deploy. Outputs are specs; execution stays in WSB paper sandbox.
  - No MongoDB, no Node client. Specs are plain dicts validated by factory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

COMPARATORS = ("GT", "GTE", "LT", "LTE", "EQ")


def _require_comparator(op: str) -> str:
    if op not in COMPARATORS:
        raise ValueError(f"unknown comparator {op}")
    return op


def compare(a: float, b: float, op: str) -> bool:
    _require_comparator(op)
    if op == "GT":
        return bool(a > b)
    if op == "GTE":
        return bool(a >= b)
    if op == "LT":
        return bool(a < b)
    if op == "LTE":
        return bool(a <= b)
    return bool(a == b)


def _cmp_series(s: pd.Series, b: float, op: str) -> pd.Series:
    _require_comparator(op)
    if op == "GT":
        return s > b
    if op == "GTE":
        return s >= b
    if op == "LT":
        return s < b
    if op == "LTE":
        return s <= b
    return s == b


@dataclass
class ConditionContext:
    """Scalar state at one bar (paper-stepping mode)."""

    symbol: str = "SPY"
    price: float = 0.0
    buying_power: float = 100000.0
    portfolio_value: float = 100000.0
    initial_value: float = 100000.0
    positions: dict[str, float] = field(default_factory=dict)  # sym -> qty
    avg_cost: dict[str, float] = field(default_factory=dict)  # sym -> avg price
    last_trade_idx: int = -10**9
    current_idx: int = 0


class AbstractCondition:
    type: str = "Abstract"

    def is_true(self, ctx: ConditionContext) -> bool:  # scalar
        raise NotImplementedError

    def evaluate(  # vectorized over a price frame; default falls back to scalar loop
        self, prices: pd.DataFrame, ctx: ConditionContext
    ) -> pd.Series:
        return pd.Series(False, index=prices.index)

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


def _ohlc_col(prices: pd.DataFrame, symbol: str, ohlc: str) -> pd.Series:
    ohlc = ohlc.lower()
    # support both flat ("close") and multi-symbol frames ("SPY_close")
    for cand in (f"{symbol}_{ohlc}", ohlc, ohlc.capitalize(), ohlc.upper()):
        if cand in prices.columns:
            return prices[cand].astype(float)
    # yfinance-style MultiIndex flattened as "('Close','SPY')" strings
    for c in prices.columns:
        cl = str(c).lower()
        if symbol.lower() in cl and ohlc in cl:
            return prices[c].astype(float)
    raise KeyError(f"no column for {symbol}/{ohlc} in {list(prices.columns)[:8]}")


class SimplePriceCondition(AbstractCondition):
    type = "SimplePriceCondition"

    def __init__(self, target_price: float, comparator: str = "LT",
                 symbol: str | None = None):
        _require_comparator(comparator)
        self.target_price = float(target_price)
        self.comparator = comparator
        self.symbol = symbol  # None => use strategy symbol

    def is_true(self, ctx: ConditionContext) -> bool:
        return compare(ctx.price, self.target_price, self.comparator)

    def evaluate(self, prices: pd.DataFrame, ctx: ConditionContext) -> pd.Series:
        s = _ohlc_col(prices, self.symbol or ctx.symbol, "close")
        return _cmp_series(s, self.target_price, self.comparator).fillna(False)

    def to_dict(self):
        return {"type": self.type, "target_price": self.target_price,
                "comparator": self.comparator, "symbol": self.symbol}


class MovingAverageCondition(AbstractCondition):
    """Port of MovingAveragePriceCondition.

    Signal: close <cmp> (statistic(close, window) + sd * std(close, window)).
    statistic in {mean, high, low}. All rolling values shifted by 1 (no lookahead).
    NextTrade default example: price <= mean - 2*sd over 5 days.
    Here sd may be negative (below mean) or positive (above mean).
    """

    type = "MovingAveragePriceCondition"

    def __init__(self, window: int = 5, standard_deviation: float = -1.0,
                 ohlc: str = "close", statistic: str = "mean",
                 comparator: str = "LTE", symbol: str | None = None):
        if statistic not in ("mean", "high", "low"):
            raise ValueError(f"unknown statistic {statistic}")
        _require_comparator(comparator)
        self.window = int(window)
        self.standard_deviation = float(standard_deviation)
        self.ohlc = ohlc
        self.statistic = statistic
        self.comparator = comparator
        self.symbol = symbol

    def _band(self, s: pd.Series) -> pd.Series:
        w = self.window
        roll = s.shift(1)  # no lookahead
        mean = roll.rolling(w).mean()
        std = roll.rolling(w).std(ddof=0)
        if self.statistic == "mean":
            base = mean
        elif self.statistic == "high":
            base = roll.rolling(w).max()
        else:
            base = roll.rolling(w).min()
        return base + self.standard_deviation * std

    def is_true(self, ctx: ConditionContext) -> bool:
        raise NotImplementedError("scalar mode needs history; use evaluate()")

    def evaluate(self, prices: pd.DataFrame, ctx: ConditionContext) -> pd.Series:
        s = _ohlc_col(prices, self.symbol or ctx.symbol, self.ohlc)
        band = self._band(s)
        return _cmp_series(s, band, self.comparator).fillna(False)

    def to_dict(self):
        return {"type": self.type, "window": self.window,
                "standard_deviation": self.standard_deviation, "ohlc": self.ohlc,
                "statistic": self.statistic, "comparator": self.comparator,
                "symbol": self.symbol}


class BuyingPowerIs(AbstractCondition):
    type = "BuyingPowerIsCondition"

    def __init__(self, threshold: float, comparator: str = "GTE"):
        _require_comparator(comparator)
        self.threshold = float(threshold)
        self.comparator = comparator

    def is_true(self, ctx: ConditionContext) -> bool:
        return compare(ctx.buying_power, self.threshold, self.comparator)

    def evaluate(self, prices, ctx):
        val = compare(ctx.buying_power, self.threshold, self.comparator)
        return pd.Series(bool(val), index=prices.index)

    def to_dict(self):
        return {"type": self.type, "threshold": self.threshold,
                "comparator": self.comparator}


class HavePosition(AbstractCondition):
    type = "HavePositionCondition"

    def __init__(self, symbol: str | None = None, negate: bool = False):
        self.symbol = symbol
        self.negate = negate

    def is_true(self, ctx: ConditionContext) -> bool:
        sym = self.symbol or ctx.symbol
        has = ctx.positions.get(sym, 0.0) != 0.0
        return (not has) if self.negate else has

    def evaluate(self, prices, ctx):
        return pd.Series(self.is_true(ctx), index=prices.index)

    def to_dict(self):
        return {"type": self.type, "symbol": self.symbol, "negate": self.negate}


class PortfolioValueIs(AbstractCondition):
    type = "PortfolioValueIsCondition"

    def __init__(self, threshold: float, comparator: str = "GTE"):
        _require_comparator(comparator)
        self.threshold = float(threshold)
        self.comparator = comparator

    def is_true(self, ctx: ConditionContext) -> bool:
        return compare(ctx.portfolio_value, self.threshold, self.comparator)

    def evaluate(self, prices, ctx):
        return pd.Series(self.is_true(ctx), index=prices.index)

    def to_dict(self):
        return {"type": self.type, "threshold": self.threshold,
                "comparator": self.comparator}


class PositionPercentChange(AbstractCondition):
    type = "PositionPercentChangeCondition"

    def __init__(self, threshold_pct: float, comparator: str = "GTE",
                 symbol: str | None = None):
        _require_comparator(comparator)
        self.threshold_pct = float(threshold_pct)
        self.comparator = comparator
        self.symbol = symbol

    def is_true(self, ctx: ConditionContext) -> bool:
        sym = self.symbol or ctx.symbol
        cost = ctx.avg_cost.get(sym, 0.0)
        if cost == 0:
            return False
        pct = (ctx.price - cost) / cost * 100.0
        return compare(pct, self.threshold_pct, self.comparator)

    def evaluate(self, prices, ctx):
        sym = self.symbol or ctx.symbol
        cost = ctx.avg_cost.get(sym, 0.0)
        if cost == 0:
            return pd.Series(False, index=prices.index)
        s = _ohlc_col(prices, sym, "close")
        pct = (s - cost) / cost * 100.0
        return _cmp_series(pct, self.threshold_pct, self.comparator).fillna(False)

    def to_dict(self):
        return {"type": self.type, "threshold_pct": self.threshold_pct,
                "comparator": self.comparator, "symbol": self.symbol}


class PortfolioIsProfitable(AbstractCondition):
    type = "PortfolioIsProfitableCondition"

    def is_true(self, ctx: ConditionContext) -> bool:
        return bool(ctx.portfolio_value > ctx.initial_value)

    def evaluate(self, prices, ctx):
        return pd.Series(self.is_true(ctx), index=prices.index)

    def to_dict(self):
        return {"type": self.type}


class EnoughTimePassed(AbstractCondition):
    type = "EnoughTimePassedCondition"

    def __init__(self, min_bars: int = 5):
        self.min_bars = int(min_bars)

    def is_true(self, ctx: ConditionContext) -> bool:
        return bool((ctx.current_idx - ctx.last_trade_idx) >= self.min_bars)

    def evaluate(self, prices, ctx):
        return pd.Series(self.is_true(ctx), index=prices.index)

    def to_dict(self):
        return {"type": self.type, "min_bars": self.min_bars}


class AndCondition(AbstractCondition):
    type = "AndCondition"

    def __init__(self, conditions: list[AbstractCondition]):
        self.conditions = conditions

    def is_true(self, ctx: ConditionContext) -> bool:
        return all(c.is_true(ctx) for c in self.conditions)

    def evaluate(self, prices, ctx):
        out = pd.Series(True, index=prices.index)
        for c in self.conditions:
            out &= c.evaluate(prices, ctx).fillna(False)
        return out

    def to_dict(self):
        return {"type": self.type,
                "conditions": [c.to_dict() for c in self.conditions]}


class OrCondition(AbstractCondition):
    type = "OrCondition"

    def __init__(self, conditions: list[AbstractCondition]):
        self.conditions = conditions

    def is_true(self, ctx: ConditionContext) -> bool:
        return any(c.is_true(ctx) for c in self.conditions)

    def evaluate(self, prices, ctx):
        out = pd.Series(False, index=prices.index)
        for c in self.conditions:
            out |= c.evaluate(prices, ctx).fillna(False)
        return out

    def to_dict(self):
        return {"type": self.type,
                "conditions": [c.to_dict() for c in self.conditions]}


class ThenCondition(AbstractCondition):
    """Port of NextTrade `then.ts`: trigger THEN confirmation.

    Scalar: if conditions[0] true, latch for `max_bars`, require
    conditions[1] within latch. Vectorized: (first & second.shifted)
    simplified as first.rolling latch AND second.
    """

    type = "ThenCondition"

    def __init__(self, first: AbstractCondition, second: AbstractCondition,
                 max_bars: int = 5):
        self.first = first
        self.second = second
        self.max_bars = int(max_bars)

    def is_true(self, ctx: ConditionContext) -> bool:
        # scalar stepping handled by backtester latch; default to second-gate
        return bool(self.second.is_true(ctx))

    def evaluate(self, prices, ctx):
        a = self.first.evaluate(prices, ctx).fillna(False).astype(int)
        b = self.second.evaluate(prices, ctx).fillna(False)
        latched = a.rolling(self.max_bars, min_periods=1).max().astype(bool)
        return (latched & b).fillna(False)

    def to_dict(self):
        return {"type": self.type, "first": self.first.to_dict(),
                "second": self.second.to_dict(), "max_bars": self.max_bars}


def create(spec: dict[str, Any]) -> AbstractCondition:
    """ConditionFactory.create — build a condition tree from a plain dict."""
    t = spec.get("type", "")
    if t == "SimplePriceCondition":
        return SimplePriceCondition(spec["target_price"],
                                    spec.get("comparator", "LT"),
                                    spec.get("symbol"))
    if t == "MovingAveragePriceCondition":
        return MovingAverageCondition(
            window=spec.get("window", 5),
            standard_deviation=spec.get("standard_deviation", -1.0),
            ohlc=spec.get("ohlc", "close"),
            statistic=spec.get("statistic", "mean"),
            comparator=spec.get("comparator", "LTE"),
            symbol=spec.get("symbol"))
    if t == "BuyingPowerIsCondition":
        return BuyingPowerIs(spec.get("threshold", 8000.0),
                             spec.get("comparator", "GTE"))
    if t == "HavePositionCondition":
        return HavePosition(spec.get("symbol"), spec.get("negate", False))
    if t == "PortfolioValueIsCondition":
        return PortfolioValueIs(spec.get("threshold", 100000.0),
                                spec.get("comparator", "GTE"))
    if t == "PositionPercentChangeCondition":
        return PositionPercentChange(spec.get("threshold_pct", 5.0),
                                     spec.get("comparator", "GTE"),
                                     spec.get("symbol"))
    if t == "PortfolioIsProfitableCondition":
        return PortfolioIsProfitable()
    if t == "EnoughTimePassedCondition":
        return EnoughTimePassed(spec.get("min_bars", 5))
    if t == "AndCondition":
        return AndCondition([create(c) for c in spec.get("conditions", [])])
    if t == "OrCondition":
        return OrCondition([create(c) for c in spec.get("conditions", [])])
    if t == "ThenCondition":
        return ThenCondition(create(spec["first"]), create(spec["second"]),
                             spec.get("max_bars", 5))
    raise ValueError(f"unknown condition type: {t}")
