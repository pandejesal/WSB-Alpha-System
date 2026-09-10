# CH-14 candidate: duplicate backtest engine — candidate for consolidation into src/backtest/engines/canonical.py (no merge in this phase; canonical is engines/canonical.py)
"""Port of QuantConnect Lean engine shape into Python.

Provides Algorithm base class, Slice data feed, Portfolio tracking,
fee/slippage models, benchmark comparison, and order lifecycle — all
operating on local CSV data only. No live orders, no API keys, no network.
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bar:
    """Single OHLCV bar for one symbol on one date."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Slice:
    """Point-in-time data bundle delivered to OnData.

    Mirrors Lean's Slice: only bars at or before the current time are visible.
    """

    time: datetime
    bars: dict[str, Bar]

    def __getitem__(self, symbol: str) -> Bar:
        return self.bars[symbol]

    def __contains__(self, symbol: str) -> bool:
        return symbol in self.bars

    def get(self, symbol: str, default: Any = None) -> Bar | None:
        return self.bars.get(symbol, default)

    @property
    def symbols(self) -> list[str]:
        return list(self.bars.keys())


@dataclass
class SecurityHolding:
    """Tracks quantity, average cost, and unrealized P&L for one symbol."""

    symbol: str
    quantity: int = 0
    average_price: float = 0.0
    last_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.last_price

    @property
    def unrealized_pnl(self) -> float:
        if self.quantity == 0:
            return 0.0
        return (self.last_price - self.average_price) * self.quantity

    def update_price(self, price: float) -> None:
        self.last_price = price

    def buy(self, quantity: int, price: float, fee: float = 0.0) -> float:
        cost = quantity * price + fee
        if self.quantity >= 0:
            total_cost = self.average_price * self.quantity + price * quantity + fee
            self.quantity += quantity
            self.average_price = total_cost / self.quantity if self.quantity else 0.0
        else:
            self.quantity += quantity
            if self.quantity == 0:
                self.average_price = 0.0
        self.last_price = price
        return cost

    def sell(self, quantity: int, price: float, fee: float = 0.0) -> float:
        proceeds = quantity * price - fee
        if self.quantity > 0:
            self.quantity -= quantity
            if self.quantity == 0:
                self.average_price = 0.0
        else:
            total_cost = self.average_price * abs(self.quantity) + price * quantity
            self.quantity -= quantity
            self.average_price = total_cost / abs(self.quantity) if self.quantity else 0.0
        self.last_price = price
        return proceeds


# ---------------------------------------------------------------------------
# Fee & slippage models
# ---------------------------------------------------------------------------


class FeeModel:
    """Per-share flat fee model (default $0 = Alpaca-compatible)."""

    def __init__(self, per_share: float = 0.0, minimum: float = 0.0) -> None:
        self.per_share = per_share
        self.minimum = minimum

    def calculate(self, quantity: int, _price: float) -> float:
        fee = abs(quantity) * self.per_share
        return max(fee, self.minimum)


class SlippageModel:
    """Basis-point slippage model applied to fill price."""

    def __init__(self, bps: float = 0.0) -> None:
        self.bps = bps

    def apply(self, price: float, is_buy: bool) -> float:
        slip = price * self.bps / 10_000
        return price + slip if is_buy else price - slip


# ---------------------------------------------------------------------------
# Order types
# ---------------------------------------------------------------------------

OrderSide = str  # "buy" | "sell"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: int
    order_type: str = "market"
    created: datetime | None = None
    filled: datetime | None = None
    fill_price: float = 0.0
    fee: float = 0.0
    status: str = "pending"


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


class Benchmark:
    """Tracks SPY buy-hold equity for comparison."""

    def __init__(self, symbol: str = "SPY") -> None:
        self.symbol = symbol
        self.start_price: float | None = None
        self.equity_curve: list[tuple[datetime, float]] = []

    def initialize(self, start_price: float) -> None:
        self.start_price = start_price

    def update(self, date: datetime, current_price: float) -> None:
        if self.start_price is None:
            self.start_price = current_price
        pct = current_price / self.start_price if self.start_price else 1.0
        self.equity_curve.append((date, pct))

    @property
    def total_return(self) -> float:
        if not self.equity_curve:
            return 0.0
        return self.equity_curve[-1][1] - 1.0


# ---------------------------------------------------------------------------
# Scheduled events
# ---------------------------------------------------------------------------


@dataclass
class _ScheduledEvent:
    callback: Callable[["Algorithm", datetime], None]
    interval_days: int
    next_run: datetime


# ---------------------------------------------------------------------------
# Algorithm base class
# ---------------------------------------------------------------------------


class Algorithm:
    """Base class mirroring QuantConnect's QCAlgorithm.

    Subclass and override Initialize() and OnData(slice).
    """

    def __init__(self) -> None:
        self.portfolio: dict[str, SecurityHolding] = {}
        self.cash: float = 0.0
        self.start_date: datetime | None = None
        self.end_date: datetime | None = None
        self._added_symbols: list[str] = []
        self._benchmark = Benchmark()
        self._fee_model = FeeModel()
        self._slippage_model = SlippageModel()
        self._log: list[str] = []
        self._scheduled: list[_ScheduledEvent] = []
        self._orders: list[Order] = []
        self._pending_orders: list[Order] = []
        self._current_date: datetime | None = None
        self._csv_root: Path = Path("market_data_2019_2026/ohlcv")

    # -- User-facing API (mirrors QCAlgorithm) -----------------------------

    def Initialize(self) -> None:  # noqa: N802
        """Override in subclass to set up algorithm parameters."""

    def OnData(self, slice: Slice) -> None:  # noqa: N802
        """Override in subclass to handle new data."""

    def AddEquity(self, symbol: str) -> None:  # noqa: N802
        if symbol not in self.portfolio:
            self.portfolio[symbol] = SecurityHolding(symbol=symbol)
            self._added_symbols.append(symbol)

    def SetCash(self, amount: float) -> None:  # noqa: N802
        self.cash = amount

    def SetStartDate(self, year: int, month: int, day: int) -> None:  # noqa: N802
        self.start_date = datetime(year, month, day)

    def SetEndDate(self, year: int, month: int, day: int) -> None:  # noqa: N802
        self.end_date = datetime(year, month, day)

    def SetBenchmark(self, symbol: str) -> None:  # noqa: N802
        self._benchmark = Benchmark(symbol)

    def SetFeeModel(self, model: FeeModel) -> None:  # noqa: N802
        self._fee_model = model

    def SetSlippageModel(self, model: SlippageModel) -> None:  # noqa: N802
        self._slippage_model = model

    def SetCsvRoot(self, path: str | Path) -> None:  # noqa: N802
        self._csv_root = Path(path)

    def SetHoldings(self, symbol: str, percentage: float) -> None:  # noqa: N802
        """Target a portfolio percentage for a symbol. Long-only."""
        if percentage < 0:
            raise ValueError("Short selling not allowed (negative target rejected)")
        if percentage > 1.0:
            raise ValueError("Percentage target cannot exceed 1.0 (no leverage)")
        if symbol not in self.portfolio:
            raise KeyError(f"Symbol {symbol} not added via AddEquity")
        equity = self._total_equity()
        target_value = equity * percentage
        holding = self.portfolio[symbol]
        current_value = holding.quantity * holding.last_price if holding.last_price else 0.0
        delta_value = target_value - current_value
        if holding.last_price <= 0 or abs(delta_value) < 1e-9:
            return
        delta_shares = int(delta_value / holding.last_price)
        if delta_shares > 0:
            self._submit_order(symbol, "buy", delta_shares)
        elif delta_shares < 0:
            self._submit_order(symbol, "sell", abs(delta_shares))

    def Liquidate(self, symbol: str | None = None) -> None:  # noqa: N802
        targets = [symbol] if symbol else list(self.portfolio.keys())
        for sym in targets:
            h = self.portfolio.get(sym)
            if h and h.quantity > 0:
                self._submit_order(sym, "sell", h.quantity)
            elif h and h.quantity < 0:
                self._submit_order(sym, "buy", abs(h.quantity))

    def Schedule(self, callback: Callable, interval_days: int) -> None:  # noqa: N802
        if self._current_date is None:
            raise RuntimeError("Schedule called before run started")
        self._scheduled.append(
            _ScheduledEvent(callback=callback, interval_days=interval_days,
                            next_run=self._current_date + timedelta(days=interval_days))
        )

    def Debug(self, msg: str) -> None:  # noqa: N802
        self._log.append(msg)
        logger.debug(msg)

    def Log(self, msg: str) -> None:  # noqa: N802
        self._log.append(msg)
        logger.info(msg)

    def PortfolioTarget(self, symbol: str, shares: int) -> None:  # noqa: N802
        """Directly set a target share count (long-only)."""
        if shares < 0:
            raise ValueError("Negative share targets not allowed")
        if symbol not in self.portfolio:
            raise KeyError(f"Symbol {symbol} not added via AddEquity")
        current = self.portfolio[symbol].quantity
        delta = shares - current
        if delta > 0:
            self._submit_order(symbol, "buy", delta)
        elif delta < 0:
            self._submit_order(symbol, "sell", abs(delta))

    # -- Internal helpers --------------------------------------------------

    def _total_equity(self) -> float:
        equity = self.cash
        for h in self.portfolio.values():
            equity += h.quantity * h.last_price
        return equity

    def _submit_order(self, symbol: str, side: OrderSide, quantity: int) -> None:
        order = Order(symbol=symbol, side=side, quantity=quantity,
                      created=self._current_date)
        self._pending_orders.append(order)

    def _fill_pending_orders(self, current_bars: dict[str, Bar]) -> None:
        """Fill pending orders T+1 with fee and slippage."""
        filled: list[Order] = []
        for order in self._pending_orders:
            bar = current_bars.get(order.symbol)
            if bar is None:
                continue
            fill_price = self._slippage_model.apply(bar.close, order.side == "buy")
            fee = self._fee_model.calculate(order.quantity, fill_price)
            holding = self.portfolio[order.symbol]
            if order.side == "buy":
                cost = order.quantity * fill_price + fee
                if cost > self.cash:
                    self.Debug(f"REJECTED: buy {order.quantity} {order.symbol} "
                               f"costs ${cost:.2f}, only ${self.cash:.2f} cash")
                    filled.append(order)
                    continue
                self.cash -= cost
                holding.buy(order.quantity, fill_price, fee)
            else:
                proceeds = order.quantity * fill_price - fee
                self.cash += proceeds
                holding.sell(order.quantity, fill_price, fee)
            order.fill_price = fill_price
            order.fee = fee
            order.filled = self._current_date
            order.status = "filled"
            self._orders.append(order)
            filled.append(order)
        self._pending_orders = [o for o in self._pending_orders if o not in filled]

    def _run_scheduled_events(self) -> None:
        remaining: list[_ScheduledEvent] = []
        for ev in self._scheduled:
            if self._current_date and self._current_date >= ev.next_run:
                ev.callback(self, self._current_date)
                ev.next_run = self._current_date + timedelta(days=ev.interval_days)
            remaining.append(ev)
        self._scheduled = remaining

    # -- CSV loading -------------------------------------------------------

    def _load_csv(self, symbol: str) -> list[Bar]:
        path = self._csv_root / f"{symbol}.csv"
        if not path.exists():
            return []
        bars: list[Bar] = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dt = datetime.strptime(row["date"], "%Y-%m-%d")
                    bar = Bar(
                        time=dt,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(float(row["volume"])),
                    )
                    bars.append(bar)
                except (ValueError, KeyError):
                    continue
        return bars

    def _load_spy_csv(self) -> list[Bar]:
        """Load SPY from data/spy_ohlcv_2019_2026.csv (different column format)."""
        path = Path("data/spy_ohlcv_2019_2026.csv")
        if not path.exists():
            return self._load_csv("SPY")
        bars: list[Bar] = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    dt = datetime.strptime(row["Date"], "%Y-%m-%d")
                    bar = Bar(
                        time=dt,
                        open=float(row["('Open', 'SPY')"]),
                        high=float(row["('High', 'SPY')"]),
                        low=float(row["('Low', 'SPY')"]),
                        close=float(row["('Close', 'SPY')"]),
                        volume=int(float(row["('Volume', 'SPY')"])),
                    )
                    bars.append(bar)
                except (ValueError, KeyError):
                    continue
        return bars

    # -- Main run loop -----------------------------------------------------

    def run(self) -> dict[str, Any]:
        """Execute the algorithm over the configured date range."""
        self.Initialize()

        all_bars: dict[str, list[Bar]] = {}
        for sym in self._added_symbols:
            if sym == "SPY" or sym == self._benchmark.symbol:
                all_bars[sym] = self._load_spy_csv() if sym in ("SPY", self._benchmark.symbol) else self._load_csv(sym)
            else:
                all_bars[sym] = self._load_csv(sym)

        if not self.start_date or not self.end_date:
            all_dates = set()
            for bars in all_bars.values():
                for b in bars:
                    all_dates.add(b.time.date())
            if not all_dates:
                return {"error": "no data found"}
            sorted_dates = sorted(all_dates)
            if self.start_date is None:
                self.start_date = datetime.combine(sorted_dates[0], datetime.min.time())
            if self.end_date is None:
                self.end_date = datetime.combine(sorted_dates[-1], datetime.min.time())

        date_index: dict[datetime, dict[str, Bar]] = {}
        for sym, bars in all_bars.items():
            for bar in bars:
                if bar.time not in date_index:
                    date_index[bar.time] = {}
                date_index[bar.time][sym] = bar

        benchmark_sym = self._benchmark.symbol
        if benchmark_sym in all_bars and all_bars[benchmark_sym]:
            self._benchmark.initialize(all_bars[benchmark_sym][0].close)

        current = self.start_date
        while current <= self.end_date:
            self._current_date = current
            if current in date_index:
                current_bars = date_index[current]
                self._fill_pending_orders(current_bars)
                for sym, holding in self.portfolio.items():
                    if sym in current_bars:
                        holding.update_price(current_bars[sym].close)
                if benchmark_sym in current_bars:
                    self._benchmark.update(current, current_bars[benchmark_sym].close)
                self._run_scheduled_events()
                visible_bars = {}
                for sym, holding in self.portfolio.items():
                    if sym in current_bars:
                        visible_bars[sym] = current_bars[sym]
                if visible_bars:
                    slice_obj = Slice(time=current, bars=visible_bars)
                    self.OnData(slice_obj)
            current += timedelta(days=1)

        for h in self.portfolio.values():
            h.update_price(h.last_price)

        return self._build_results()

    def _build_results(self) -> dict[str, Any]:
        equity = self._total_equity()
        benchmark_return = self._benchmark.total_return
        total_fees = sum(o.fee for o in self._orders)
        return {
            "final_equity": equity,
            "cash": self.cash,
            "positions": {sym: {"quantity": h.quantity, "avg_price": h.average_price,
                                "last_price": h.last_price, "market_value": h.market_value}
                          for sym, h in self.portfolio.items() if h.quantity != 0},
            "total_orders": len(self._orders),
            "total_fees": total_fees,
            "benchmark_return": benchmark_return,
            "strategy_return": (equity / (self.cash + sum(
                h.quantity * h.average_price for h in self.portfolio.values()
            )) - 1) if self._orders else 0.0,
            "log": self._log,
            "orders": [
                {"symbol": o.symbol, "side": o.side, "quantity": o.quantity,
                 "fill_price": o.fill_price, "fee": o.fee,
                 "filled": o.filled.isoformat() if o.filled else None}
                for o in self._orders
            ],
        }
