# Hummingbot Evaluation — PMM / XEMM / Avellaneda-Stoikov vs WSB-Alpha Execution + SMC Order Blocks

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint. Workdir-only.
Upstream: `https://github.com/hummingbot/hummingbot` (PMM `hummingbot/strategy/pure_market_making/`, XEMM `hummingbot/strategy/cross_exchange_market_making/`, Avellaneda `hummingbot/strategy/avellaneda_market_making/` + docs at `hummingbot.org/strategies/`).
Scope: evaluate which order-book microstructure pieces fit Alpaca-only paper trading; reject HFT/venue pieces with reasons. Propose exact diffs (NEW files only) + test plan.

## 1. Study findings (actual repo code verified by read)

### 1.1 Actual execution code (not the task's paraphrase — verified paths)

- `src/execution/execution_adapter.py:8-52` — `PaperTradeBroker` ABC (`place_order(ticker, qty, side, order_type="MARKET", target_cvar_allocation)`, `get_portfolio`, `get_open_positions`) + `PaperbrokerClient` POSTing to `http://localhost:5000/order`. `ExecutionAdapter:80-104` routes signal dicts (`ticker/side/quantity`, optional `order_type`, `target_cvar_allocation`); skips malformed signals. No limit-price, no spread, no inventory logic.
- `src/execution/live_alpaca_executor.py:134-164,166-192` — daily fractional **market** orders (`type: market`, `time_in_force: day`, notional) to Alpaca `v2/orders`; fail-closed gates: dual-gate `dual_gate_allows_trading` + exact-allowlist `_is_alpaca_url_allowed` (paper mode = `https://paper-api.alpaca.markets` only); daily/weekly circuit breakers; `MAX_CONCURRENT_POSITIONS`; technical confluence (HA + EMA20/MACD + RSI + BB + `GK_Vol < 1.20` volatility shield) at lines 30-62, 291-340. No order book, no L2, no limit irrigating.
- `src/execution/alpaca_broker.py:53-80` — `AlpacaBroker.place_order(symbol, qty, side, order_type='market', stop_loss_price)` via `alpaca-py` `MarketOrderRequest`, `TimeInForce.DAY`; sell side integer-casts qty (fractional short disallowed, raises on 0-truncation). Capabilities: market + stop-limit + paper only.
- `src/execution/paper_executor.py:38-215` — idempotent plan executor (`client_order_id = generate_client_order_id(run_id, sleeve_id, ticker, seq)`; duplicate-skip; missing-qty fail-fast `ValueError`; fills from `fill_price/avg_price` or `status_details`; recon artifacts `orders.json/fills.json/recon.json`). Per-sleeve DD breaker via `DDTracker`. All orders `type: market`.
- `src/execution/universal_broker.py:106-140` — `UniversalBroker.place_order` risk interceptor: `risk_amount > equity * 0.01` → halt (no downsize). `AlpacaExecutor`/`CryptoExecutor` route by `asset_class`. Telegram alerts only.
- `src/risk/position_sizing.py:18-27` — `MAX_RISK_PER_TRADE_PCT = 0.01`, `MAX_POSITION_SIZE_PCT = 0.25`, `MAX_CONCURRENT_POSITIONS = 4`, fractional-Kelly `PositionSizer`.
- `src/alpha/order_blocks.py:7-222` — Numba SMC detector on **daily OHLCV only**: ATR-14 (`calculate_atr`), 5-bar fractal swings (`find_swing_points`), OB = down/up-close candle at `i-2` + displacement body `> 1.0*ATR[i-1]` + FVG gap (`low[i] > high[i-2]` / `high[i] < low[i-2]`) + size filter `rng >= 0.1*ATR`; entry on touch → engulfing + wick-rejection (`wick > 0.5*body`), SL = OB edge, TP = most-recent swing (50-bar max/min fallback). No bid/ask, no depth, no trade intensity, no cost basis.

Data reality: signals come from `yfinance` daily bars or `wsb_factual_research_data.csv` (`live_alpaca_executor.py:250-275`). There is **no L2 order-book feed, no tick stream, no second venue** in the Alpaca paper path. Anything requiring a 1-second `c_tick`, live BBO, or maker/taker pair is structurally unfittable.

### 1.2 Hummingbot patterns studied (gitingest + docs)

- **PMM** (`pure_market_making.pyx`, `data_types.py`, `inventory_skew_calculator.pyx`, `moving_price_band.py`): 1-sec `c_tick` loop → `c_create_base_proposal` (bid/ask = `mid * (1 ∓ spread)`) → modifiers (levels, price band, ping-pong, price/size, inventory skew, budget) → `c_filter_out_takers` → `c_execute_orders_proposal`; refresh via `order_refresh_time` (default 30 s) + `max_order_age` + `order_refresh_tolerance_pct`. Helpers: `calculate_bid_ask_ratios_from_base_asset_ratio` (linear interp 2.0→1.0→0.0 sizing skew around `target_base_asset_ratio ± range`), `MovingPriceBand` (floor/ceiling = `±pct` of ref, refreshed every `price_band_refresh_time`), `InventoryCostPriceDelegate` (SQL-backed average cost; sells floored at cost), order-optimization (jump to inside BBO), hanging-orders, ping-pong.
- **XEMM** (`cross_exchange_market_making/` + v2 `XEMMExecutor`): maker limit orders on illiquid venue + immediate hedge market order on liquid venue when filled; profitability gate `min_profitability` vs taker price + fees; `active_order_canceling` toggle for CEX-vs-DEX. Explicitly two-venue.
- **Avellaneda-Stoikov** (`avellaneda_market_making.pyx:713-777,846-946,980-1033`): per-tick `reservation_price r = mid − q·γ·σ²·T_left` and `optimal_spread = γ·σ²·T + (2/γ)·ln(1+γ/κ)` (note: upstream PR #8147 fixed `σ→σ²` per paper; this repo must use `σ²` if it ever ports the formula); inputs `σ` from `InstantVolatilityIndicator`, `α/κ` from `TradingIntensityIndicator` (needs ~200 **order-book-snapshot** ticks before `c_is_algorithm_ready`); `η` (`order_amount_shape_factor`) sizes levels asymmetrically toward `inventory_target_base_pct`; `minimum_spread` floor; `order_optimization` + tx-cost widening. Timeframes `infinite / from_date_to_date / daily_between_times`.

## 2. Verdict: adopt vs reject

| # | Hummingbot piece | Verdict | Reason (Alpaca-only paper fit) |
|---|---|---|---|
| A1 | PMM **inventory-skew sizing ratios** (`calculate_bid_ask_ratios_from_base_asset_ratio`) | **ADOPT (adapted, sizing-only)** | Pure arithmetic, no venue/L2. Fits `UniversalBroker` 1%-risk interceptor + `PositionSizer`: scale buy qty by `bid_ratio/2`, sell qty by `ask_ratio/2` around a per-sleeve target allocation. Daily equities version: compute from Alpaca positions + cash, not per-second. Zero network, zero order-type change (still market DAY). |
| A2 | PMM **`MovingPriceBand`** (floor/ceiling guard) | **ADOPT (adapted, daily)** | Pure guard, no quoting. Repo has volatility shield + DD breakers but no per-symbol stale/erratic-price guard. Daily refresh (`price_band_refresh_time = 86400`) matches this repo's cadence; skip signal when `price <= floor` / `>= ceiling`. Prevents chasing gaps on yfinance-lagged bars. |
| A3 | PMM **`minimum_spread` / take-if-crossed filter** (`c_filter_out_takers`, `c_cancel_orders_below_min_spread`) | **ADOPT (as pre-trade spread filter)** | No L2 needed if implemented as: skip market entry when `(ask-bid)/mid` from Alpaca quote (or `BB_Upper-BB_Lower` proxy when quotes absent) `< min_spread_pct`. Stops buying illiquid wide-spread names at market. Fail-closed skip, never reroute. |
| A4 | PMM **inventory-cost floor** (`InventoryCostPriceDelegate`) | **ADOPT (narrow: cost-basis guard for sells)** | Alpaca `get_positions` already returns `unrealized_pl`; track per-symbol average cost in-memory (no SQL) and require bearish OB SHORT/sell signal to pass `price >= cost * (1 + fee_buffer)` OR explicit short-intent flag, else skip. Prevents selling winners into noise at market. No order-type change. |
| A5 | Avellaneda **reservation-price skew as offline feature** (`r = mid − q·γ·σ²·T`) | **ADOPT (research-only signal, NOT execution)** | Math ports cleanly to daily bars: `q` = sleeve inventory displacement, `σ²` = Garman-Klass variance already in `compute_indicators`, `T` = fraction of day/session left. Use as an OB-entry score tilt (prefer longs when `r > mid`), never as a quote price. Keeps edge-gate path (pre-reg + walk-forward + permutation + DSR) intact. |
| R1 | PMM 1-sec `c_tick` quote/refresh loop, `order_refresh_time`, `max_order_age`, hanging orders, ping-pong, order optimization (BBO-jump) | **REJECT** | Requires live L2 + limit-order churn on a CLOB. This repo trades daily market DAY orders via cron (`live_alpaca_executor.py:9`). Porting would create overtrading, PDT exposure, quote-stuffing on paper, and break the fail-closed daily gates. No Alpaca L2 stream exists here. |
| R2 | XEMM maker+taker hedging (`min_profitability`, hedge-on-fill) | **REJECT** | Two-venue by definition. Mandate is Alpaca-only; there is no second hedge venue in the paper path, and the crypto executor is out of scope for equities paper. Hedge-leg failure mode (filled maker, failed taker) adds unhedged exposure the risk interceptor was built to prevent. |
| R3 | Avellaneda live quoting (`optimal_ask/bid`, `level_distances`, `η` level sizing, `κ/α` trading-intensity) | **REJECT as execution** | `κ/α` needs ~200 order-book-snapshot ticks; repo has daily OHLCV only. `optimal_spread` in basis points of a crypto book does not transfer to equity daily market orders. (The `r` formula alone is salvaged as A5; the quoting machinery is not.) |
| R4 | Avellaneda `daily_between_times` / `from_date_to_date` session engine, Cython `.pyx` indicators | **REJECT (do not port)** | Session engine duplicates cron + killswitch + DD breakers already enforced. Cython adds build toolchain for zero paper benefit; use Numba/pandas already in repo (`order_blocks.py` precedent). |

Net rule: **adopt stateless arithmetic + guards that sit BEFORE the existing market order; reject anything that changes venue count, order type, or tick cadence.**

## 3. Exact diffs proposed (NEW files only — nothing applied by this study)

### Diff 1 — NEW `src/execution/microstructure_guards.py` (the whole adoption; pure, venue-free, testable)

Rationale: single home for A1–A4 + A5-math so `paper_executor`/`live_alpaca_executor` can call guards without touching broker code. No imports from `alpaca*`, `ccxt`, `requests`, or hummingbot. Lowercase-neutral (works on plain floats), fail-closed (`None`/NaN → skip signal, never force trade).

```python
"""Hummingbot-inspired microstructure guards, adapted to Alpaca-only daily paper trading.

Adopts (sizing/guards only, no quoting, no second venue):
  A1 PMM inventory-skew ratios  (hummingbot/strategy/pure_market_making/inventory_skew_calculator.pyx)
  A2 PMM moving price band      (hummingbot/strategy/pure_market_making/moving_price_band.py)
  A3 PMM minimum-spread filter  (c_filter_out_takers / c_cancel_orders_below_min_spread)
  A4 PMM inventory-cost floor   (inventory_cost_price_delegate.py, in-memory not SQL)
  A5 Avellaneda reservation-price tilt (r = mid - q*gamma*sigma2*T_left), signal-only
Rejects (documented, NOT implemented): 1-sec c_tick refresh, hanging/ping-pong/BBO-jump,
  XEMM hedge leg, live optimal-spread quoting, kappa/alpha intensity (needs L2 snapshots).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def inventory_skew_ratios(
    base_value: float,
    quote_value: float,
    target_base_ratio: float = 0.5,
    range_value: float = 0.0,
) -> tuple[float, float]:
    """Port of PMM c_calculate_bid_ask_ratios_from_base_asset_ratio, venue-free.

    Returns (bid_ratio, ask_ratio) in [0, 2] summing to 2. Caller sizes:
      buy_qty  *= bid_ratio / 2 ; sell_qty *= ask_ratio / 2.
    Degenerate (total <= 0 or range <= 0) -> (0.0, 0.0) = skip, matching upstream.
    """
    total = base_value + quote_value
    if total <= 0.0 or range_value <= 0.0 or not math.isfinite(total):
        return (0.0, 0.0)
    half = total * 0.5
    band = min(range_value, half)
    target = total * target_base_ratio
    lo = max(target - band, 0.0)
    hi = target + band

    def _interp(x: float, xp0: float, xp1: float, fp0: float, fp1: float) -> float:
        if xp1 == xp0:
            return fp0
        t = min(max((x - xp0) / (xp1 - xp0), 0.0), 1.0)
        return fp0 + t * (fp1 - fp0)

    if base_value < target:
        left_ratio = _interp(base_value, lo, target, 0.0, 0.5)
        bid_adj = _interp(left_ratio, 0.0, 0.5, 2.0, 1.0)
    else:
        right_ratio = _interp(base_value, target, hi, 0.5, 1.0)
        bid_adj = _interp(right_ratio, 0.5, 1.0, 1.0, 0.0)
    ask_adj = 2.0 - bid_adj
    return (bid_adj, ask_adj)


@dataclass
class DailyPriceBand:
    """Daily-cadence port of PMM MovingPriceBand (A2).

    floor = ref * (1 + floor_pct/100); ceiling = ref * (1 + ceiling_pct/100).
    Upstream refreshes every price_band_refresh_time seconds; here default 86400
    to match the daily cron in live_alpaca_executor.py:9. check() is pure.
    """
    floor_pct: float = -8.0
    ceiling_pct: float = 8.0
    ref_price: float = 0.0
    enabled: bool = True

    def update(self, ref_price: float) -> None:
        self.ref_price = float(ref_price)

    @property
    def floor(self) -> float:
        return (100.0 + self.floor_pct) / 100.0 * self.ref_price

    @property
    def ceiling(self) -> float:
        return (100.0 + self.ceiling_pct) / 100.0 * self.ref_price

    def breached(self, price: float) -> bool:
        if not self.enabled or not math.isfinite(price) or self.ref_price <= 0:
            return False
        return price <= self.floor or price >= self.ceiling


def passes_min_spread(mid: float, spread_abs: float, min_spread_pct: float = 0.10) -> bool:
    """A3: PMM minimum_spread as a pre-trade skip (pct of mid). NaN/degenerate -> False."""
    if not math.isfinite(mid) or not math.isfinite(spread_abs) or mid <= 0:
        return False
    return (spread_abs / mid * 100.0) >= min_spread_pct


def passes_cost_floor(side: str, price: float, avg_cost: float | None, fee_buffer_pct: float = 0.05) -> bool:
    """A4: inventory-cost floor for sells. Buys always pass; sells need price >= cost*(1+buffer).

    avg_cost None (unknown basis, e.g. fresh short intent) -> pass only if side == 'sell'
    carries explicit short_intent=True (see should_enter); this function alone returns True
    for None so the intent check lives in one place. Keep simple: None -> True.
    """
    if side.lower() == "buy":
        return True
    if avg_cost is None or not math.isfinite(avg_cost) or avg_cost <= 0:
        return True
    if not math.isfinite(price) or price <= 0:
        return False
    return price >= avg_cost * (1.0 + fee_buffer_pct / 100.0)


def reservation_price(mid: float, inventory_displacement_q: float, gamma: float, sigma2: float, t_left: float) -> float:
    """A5: Avellaneda-Stoikov reservation price, signal-only (uses sigma^2 per paper + PR #8147).

    r = mid - q * gamma * sigma2 * t_left. No quoting; compare r vs mid for tilt.
    """
    return mid - inventory_displacement_q * gamma * sigma2 * t_left


def should_enter(
    *,
    side: str,
    price: float,
    mid: float,
    spread_abs: float,
    base_value: float,
    quote_value: float,
    avg_cost: float | None = None,
    short_intent: bool = False,
    band: DailyPriceBand | None = None,
    target_base_ratio: float = 0.5,
    range_value: float = 0.0,
    min_spread_pct: float = 0.10,
    fee_buffer_pct: float = 0.05,
) -> dict:
    """Combined fail-closed gate: band -> spread -> cost -> skew-size. Never raises on bad data.

    Returns {"enter": bool, "bid_ratio": float, "ask_ratio": float, "size_mult": float, "reason": str}.
    size_mult already includes skew (bid side uses bid_ratio/2, ask side ask_ratio/2); 0.0 = skip.
    Bearish OB SHORT without known basis requires short_intent=True, else skip (avoids
    accidental sell of unknown-basis long into noise).
    """
    if not math.isfinite(price) or price <= 0 or not math.isfinite(mid) or mid <= 0:
        return {"enter": False, "bid_ratio": 0.0, "ask_ratio": 0.0, "size_mult": 0.0, "reason": "bad_price"}
    if band is not None and band.breached(price):
        return {"enter": False, "bid_ratio": 0.0, "ask_ratio": 0.0, "size_mult": 0.0, "reason": "price_band_breach"}
    if not passes_min_spread(mid, spread_abs, min_spread_pct):
        return {"enter": False, "bid_ratio": 0.0, "ask_ratio": 0.0, "size_mult": 0.0, "reason": "spread_below_min"}
    if side.lower() != "buy" and avg_cost is None and not short_intent:
        return {"enter": False, "bid_ratio": 0.0, "ask_ratio": 0.0, "size_mult": 0.0, "reason": "unknown_basis_no_short_intent"}
    if not passes_cost_floor(side, price, avg_cost, fee_buffer_pct):
        return {"enter": False, "bid_ratio": 0.0, "ask_ratio": 0.0, "size_mult": 0.0, "reason": "below_cost_floor"}
    bid_ratio, ask_ratio = inventory_skew_ratios(base_value, quote_value, target_base_ratio, range_value)
    if bid_ratio == 0.0 and ask_ratio == 0.0:
        return {"enter": False, "bid_ratio": bid_ratio, "ask_ratio": ask_ratio, "size_mult": 0.0, "reason": "degenerate_inventory"}
    mult = (bid_ratio if side.lower() == "buy" else ask_ratio) / 2.0
    if mult <= 0.0:
        return {"enter": False, "bid_ratio": bid_ratio, "ask_ratio": ask_ratio, "size_mult": 0.0, "reason": "skewed_to_zero"}
    return {"enter": True, "bid_ratio": bid_ratio, "ask_ratio": ask_ratio, "size_mult": mult, "reason": "ok"}
```

Wiring (PROPOSAL ONLY — not applied; shows where guards slot in without changing brokers):

```diff
--- a/src/execution/paper_executor.py (PROPOSED, not applied)
+++ b/src/execution/paper_executor.py (PROPOSED, not applied)
@@ execute_plan: before broker.place_order(ticker, qty, side)
+                from src.execution.microstructure_guards import should_enter
+                gate = should_enter(side=side, price=float(target.get("ref_price", 0) or 0),
+                                    mid=float(target.get("ref_price", 0) or 0),
+                                    spread_abs=float(target.get("spread_abs", 0) or 0),
+                                    base_value=..., quote_value=...,
+                                    avg_cost=position_map.get(ticker, {}).get("avg_cost"),
+                                    short_intent=bool(target.get("short_intent", False)))
+                if not gate["enter"]:
+                    self.audit.log_event(self.run_id, "EXECUTION_SKIPPED_ORDER", "order",
+                                         client_order_id, {"reason": gate["reason"]})
+                    continue
+                qty = max(1, int(qty * gate["size_mult"]))  # equities integer shares; crypto path keeps float
                 res = self.broker.place_order(ticker, qty=qty, side=side, order_type="market")
```

```diff
--- a/src/alpha/order_blocks.py (PROPOSED SCORING HOOK, not applied)
+++ b/src/alpha/order_blocks.py (PROPOSED SCORING HOOK, not applied)
@@ OrderBlockDetector.detect: after building entries DataFrame
+                # Optional A5 tilt (research-only): entries["as_tilt"] = reservation_price(mid=Entry_Price, ...)
+                # using GK variance (sigma2) from compute_indicators + sleeve q. Sort/filter only;
+                # never changes Entry_Price/Stop_Loss/Take_Profit semantics.
```

No changes to `evolve_real.py`, `strategies/registry.json`, `strategies/`, broker clients, or order types. Promotion still requires pre-registration + walk-forward + permutation + DSR per `AGENTS.md`.

### Diff 2 — NEW `tests/test_microstructure_guards.py` (gates the adoption)

```python
"""Tests for src/execution/microstructure_guards.py (hummingbot-adapted, venue-free)."""
import math

from src.execution.microstructure_guards import (
    DailyPriceBand,
    inventory_skew_ratios,
    passes_cost_floor,
    passes_min_spread,
    reservation_price,
    should_enter,
)


def test_skew_neutral_gives_unit_mult():
    bid, ask = inventory_skew_ratios(5000.0, 5000.0, 0.5, 1000.0)
    assert bid == ask == 1.0


def test_skew_overweight_base_cuts_bids():
    bid_hi, ask_hi = inventory_skew_ratios(9000.0, 1000.0, 0.5, 1000.0)
    bid_lo, ask_lo = inventory_skew_ratios(1000.0, 9000.0, 0.5, 1000.0)
    assert bid_hi < 1.0 < ask_hi and bid_lo > 1.0 > ask_lo
    assert abs((bid_hi + ask_hi) - 2.0) < 1e-9


def test_skew_degenerate_returns_zeros():
    assert inventory_skew_ratios(0.0, 0.0, 0.5, 100.0) == (0.0, 0.0)
    assert inventory_skew_ratios(5000.0, 5000.0, 0.5, 0.0) == (0.0, 0.0)


def test_band_breach_blocks():
    band = DailyPriceBand(floor_pct=-8.0, ceiling_pct=8.0)
    band.update(100.0)
    assert band.breached(91.0) and band.breached(109.0) and not band.breached(100.0)


def test_min_spread_filter():
    assert passes_min_spread(100.0, 0.20, 0.10)
    assert not passes_min_spread(100.0, 0.05, 0.10)
    assert not passes_min_spread(float("nan"), 0.2, 0.10)


def test_cost_floor():
    assert passes_cost_floor("buy", 90.0, 100.0)
    assert not passes_cost_floor("sell", 100.01, 100.0, fee_buffer_pct=0.05)
    assert passes_cost_floor("sell", 100.10, 100.0, fee_buffer_pct=0.05)


def test_reservation_price_uses_variance():
    # r = 100 - 1*0.5*0.04*0.5 = 99.99 ; linear in sigma2 catches the PR-#8147 sigma-vs-variance bug
    assert reservation_price(100.0, 1.0, 0.5, 0.04, 0.5) == 100.0 - 1.0 * 0.5 * 0.04 * 0.5


def test_should_enter_fail_closed():
    band = DailyPriceBand()
    band.update(100.0)
    ok = should_enter(side="buy", price=100.0, mid=100.0, spread_abs=0.2,
                      base_value=5000.0, quote_value=5000.0, band=band,
                      target_base_ratio=0.5, range_value=1000.0)
    assert ok["enter"] and ok["size_mult"] == 0.5
    bad = should_enter(side="buy", price=float("nan"), mid=100.0, spread_abs=0.2,
                       base_value=5000.0, quote_value=5000.0)
    assert not bad["enter"] and bad["size_mult"] == 0.0
    no_basis = should_enter(side="sell", price=100.0, mid=100.0, spread_abs=0.2,
                            base_value=5000.0, quote_value=5000.0, avg_cost=None)
    assert not no_basis["enter"] and no_basis["reason"] == "unknown_basis_no_short_intent"
```

## 4. Test plan (serial, one file; no full-suite runs per session rule)

1. `PYTHONPATH=. pytest tests/test_microstructure_guards.py -q` — all 8 tests pass; degenerate/NaN cases return skip-reasons, never raise.
2. Offline OB hook check (no network): run `OrderBlockDetector().detect` on vendored daily CSV, join `should_enter` per entry with synthetic `spread_abs = 0.002*mid`, `band` ref = prior close; assert breach/skip rows carry reasons and no entry prices mutate.
3. Paper-path dry run: instantiate `should_enter` with Alpaca `get_positions()` snapshot values (read-only) in a REPL; confirm overweight sleeve yields `size_mult < 1` on buys and `> 1` on sells, symmetric sum = 2.0.
4. Lint/security: `ruff check src/execution/microstructure_guards.py tests/test_microstructure_guards.py` (if ruff present), `bandit -r src/execution/microstructure_guards.py`; no secrets, no network calls, no venue SDK imports.
5. Edge-gate compliance: no `strategies/registry.json` entry, no `evolve_real.py` change; any future live use needs pre-registration, walk-forward, permutation tests, DSR before promotion.

## 5. SMC interplay note (`src/alpha/order_blocks.py`)

OB detection stays the alpha; microstructure guards stay the risk overlay. Recommended (not applied): add optional `as_tilt` column from `reservation_price` using existing `GK_Vol²` as `sigma2` and sleeve `q` — sort OB entries by tilt alignment, drop counter-tilt entries only when backtest proves OOS value. FVG/displacement/engulfing logic itself needs no Hummingbot input (different microstructure: lit-book FVG vs equity daily gaps).

## 6. Final verdict (one line per family)

- **PMM: ADOPT A1–A4 adapted (sizing + guards + cost floor); REJECT quoting loop.**
- **XEMM: REJECT whole — single-venue Alpaca mandate, no hedge leg, asymmetric failure risk.**
- **Avellaneda-Stoikov: ADOPT A5 math as offline tilt; REJECT live spread/level/kappa machinery (needs L2 ticks).**
