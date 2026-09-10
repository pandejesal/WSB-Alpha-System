# alpaca-py Adoption Study — Typed SDK Migration for Paper-to-Live Sync

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: compare `alpacahq/alpaca-py` official SDK surface (pinned `alpaca-py==0.35.0` in `requirements.txt`; probed installed 0.35.0) vs ACTUAL `src/execution/live_alpaca_executor.py` + `src/execution/alpaca_broker.py` + `src/execution/universal_broker.py` + `src/execution/paper_executor.py` + `src/data/providers/alpaca_data_provider.py`, and propose ADDITIVE diffs only that tighten paper-to-live sync. Paper only, never auto-live.
Upstream: `https://github.com/alpacahq/alpaca-py` (Apache-2.0; `pip index` latest 0.44.0, repo pins 0.35.0 — deltas noted, no upgrade proposed here).
Workdir constraint: stayed inside workdir; only NEW file is this report under `_deliverables/`.

## 1. Actual repo surveyed (read, with line refs)

Execution:

- `src/execution/live_alpaca_executor.py:1-394` — daily cron template. Raw `requests` + hand-built `HEADERS` (`APCA-API-KEY-ID/SECRET`, 102-106), no SDK import, no pydantic validation. Endpoints hand-strung: `GET /v2/account` (112), `GET /v2/positions` (125), `POST /v2/orders` with `{"symbol","notional","side","type":"market","time_in_force":"day"}` (144-150), `GET /v2/account/portfolio/history` (219). `place_fractional_market_order(symbol, notional, side)` (134-164) only. Allowlist `paper-api.alpaca.markets` vs `api.alpaca.markets` (75-92) + `_is_alpaca_url_allowed` exact match (95-99). Dual-gate `dual_gate_allows_trading` (174-180). Daily/weekly circuit breakers (211-232). Confluence filter (290-345). Paper mode returns early at line 192 — live path only when `LIVE_TRADING_ENABLED`. No order lifecycle (no GET order by id, no list/cancel/replace, no close_position), no bracket/OCO/OTO/trailing, no `client_order_id`, no fill reconciliation (log dump only, 382-387).
- `src/execution/alpaca_broker.py:1-98` — the ONLY file that uses the SDK, and only a subset. `TradingClient(api_key, secret, paper=is_paper)` (25), `get_account()` → `{equity, cash}` (29-37), `get_all_positions()` → `{symbol, qty, market_value, unrealized_pl}` (39-51). `place_order(symbol, qty, side, order_type='market', stop_loss_price)` (53-80): builds `MarketOrderRequest(symbol, qty, side, TimeInForce.DAY, stop_loss=StopLossRequest)` only; fractional-short int-cast with qty-0 raise (63-66); returns `{"status":"success","order_id","status_details": order.status}` — no `fill_price/avg_price/fee`, no `client_order_id` passthrough. `cancel_orders(symbol_or_symbols=symbol)` (87). Capabilities market/stop-limit/paper (92-98). Missing: `notional` fractional buys, `LimitOrderRequest/StopOrderRequest/StopLimitOrderRequest/TrailingStopOrderRequest`, `OrderClass.BRACKET/OCO/OTO` + `take_profit/stop_loss` legs, `GetOrdersRequest/QueryOrderStatus`, `get_order_by_id/get_order_by_client_id/cancel_order_by_id/replace_order_by_id`, `close_position/close_all_positions`, `get_portfolio_history` (typed), `get_clock/get_calendar` (tradability guard).
- `src/execution/universal_broker.py:1-162` — `AlpacaExecutor.execute_order(ticker, direction, quantity, price=None)` (66-73) calls `broker.place_order(ticker, quantity, direction)` positionally, checks `res.get('status')=='success'` → bool. Loses `order_id/status/fill`. `liquidate_strategy_positions` is a log stub (75-78). `UniversalBroker.place_order` risk interceptor (119-140) gates on 1% equity then Telegram-alerts. No lifecycle, no bracket, no recon.
- `src/execution/paper_executor.py:38-215` — idempotent plan executor (`generate_client_order_id(run_id, sleeve_id, ticker, seq)`, duplicate-skip 126-129, missing-qty fail-fast 131-135). Expects `res.get("fill_price")/avg_price/status_details/fee/order_id` (143, 161-170) but `AlpacaBroker.place_order` never returns `fill_price/avg_price/fee` — recon `fills.json/recon.json` therefore records `status_details` string instead of fills, and `recon.deltas/mismatches` stay empty (198-204). Calls `broker.place_order(ticker, qty, side, order_type="market")` (141) — typed-SDK legs never reach it.
- `src/execution/execution_bridge.py:16-41` — `execute_signal` sizes via `PositionSizer` then `broker.place_order(ticker, qty, side, "market")`. Zero-qty reject (36-37), circuit-breaker check (30-32). Same typed-leg gap.
- `src/utils/config.py:35-37,78-80` — `live_trading_enabled: bool=False`, `initial_capital: float=100.0`. Fail-closed default preserved by all proposals below.

Data:

- `src/data/providers/alpaca_data_provider.py:1-110` — `StockHistoricalDataClient` + `CryptoHistoricalDataClient` only. `StockBarsRequest(symbol_or_symbols, TimeFrame.Day, start, end, adjustment="all")` (58-64) and `CryptoBarsRequest` (83-88), Day timeframe hardcoded, symbol `-`/`/` normalize (29-40), TZ-strip + `OHLCVSchema.validate` (66-76, 91-101). `fetch_sentiment_feed` raises `NotImplementedError` (109-110). Missing: `NewsRequest`, `NewsClient.get_news`, `CorporateActionsRequest`, `StockSnapshotRequest/StockLatestQuoteRequest/StockTradesRequest`, `TimeFrame.Min/Hour/Week`, `DataFeed` selection, `StockDataStream.subscribe_bars/subscribe_daily_bars/subscribe_updated_bars`, `NewsDataStream`, `CryptoDataStream`.
- `src/data/providers/base.py:1-13` — `fetch_ohlcv + fetch_sentiment_feed` ABC. No streaming/lifecycle/news contract.
- `src/data/providers/chain.py:1-104` — `Alpaca → Tiingo → Binance → YFinance` fallback (24-29) with `CacheEngine` write-through (72-73). Chain never sees news/streaming because provider ABC has no such method.
- `src/data/market_data.py:1-58` — `MarketDataManager.fetch_data` parquet-caches by `(ticker, start, end, timeframe)` sha256 (15-17), `ffill/bfill` (48). No intraday/streaming path.

## 2. Official SDK surface studied (probed installed `alpaca-py==0.35.0`, no network)

Trading (typed clients + pydantic validation):

- `alpaca.trading.client.TradingClient` methods (probed): `submit_order`, `get_order_by_id`, `get_order_by_client_id`, `get_orders`, `cancel_order_by_id`, `cancel_orders`, `replace_order_by_id`, `close_position`, `close_all_positions`, `get_all_positions`, `get_open_position`, `get_account`, `get_portfolio_history`, `get_clock`, `get_calendar`, `get_corporate_announcements`, `get_asset/get_all_assets`, watchlists, `get_option_contract(s)`.
- `alpaca.trading.requests` (probed `model_fields`): `MarketOrderRequest(symbol, qty|notional, side, type, time_in_force, order_class, extended_hours, client_order_id, legs, take_profit, stop_loss, position_intent)`; `LimitOrderRequest` + `limit_price`; `StopOrderRequest` + `stop_price`; `StopLimitOrderRequest` + both; `TrailingStopOrderRequest` + `trail_price|trail_percent`; `GetOrdersRequest(status, limit, after, until, direction, nested, side, symbols)`; `GetOrderByIdRequest`; `ReplaceOrderRequest`; `CancelOrderResponse`; `OrderSide/OrderType/TimeInForce/QueryOrderStatus`; `OrderClass ∈ {simple, mleg, bracket, oco, oto}` (probed enum). `TakeProfitRequest(limit_price)` / `StopLossRequest(stop_price[, limit_price])` attach to any parent request — this is how bracket/OTOCO is expressed (no separate `BracketOrderRequest` class).
- Pydantic v2 (`pydantic==2.13.4` in requirements): unknown side/timeframe/order-class rejected at construction with `ValidationError` before any HTTP — strictly stronger than the repo's hand-built dicts (`live_alpaca_executor:144-150` sends whatever string `side` it was given).

Data / streaming:

- `alpaca.data.requests` (probed): `StockBarsRequest/CryptoBarsRequest/OptionBarsRequest(symbol_or_symbols, timeframe, start, end, adjustment, feed, sort, limit, page_token)`; `StockLatestBarRequest/StockSnapshotRequest/StockQuotesRequest/StockTradesRequest`; `NewsRequest(start, end, sort, symbols, limit, include_content, exclude_contentless, page_token)`; `CorporateActionsRequest(symbols, cusips, types, start, end, ids, limit, sort)`; `TimeFrame(Day/Hour/Min/Week/Month + amount)`; `DataFeed ∈ {SIP, IEX, OTC}`; `Sort ∈ {ASC, DESC}`.
- `StockHistoricalDataClient`: `get_stock_bars/get_stock_latest_bar/get_stock_latest_quote/get_stock_latest_trade/get_stock_quotes/get_stock_snapshot/get_stock_trades`. `NewsClient` (historical): `get_news`. Both return pydantic models with `.df` frame accessor (already used in `alpaca_data_provider:65,89`).
- Live WS (`alpaca.data.live.stock.StockDataStream`, `alpaca.data.live.news.NewsDataStream`, `crypto`, `option`): `subscribe_bars/subscribe_daily_bars/subscribe_updated_bars/subscribe_quotes/subscribe_trades/subscribe_trading_statuses` + `run/stop/close`. `alpaca.trading.stream.TradingStream`: `subscribe_trade_updates` + `run` (order fill/cancel/reject push, incl. `client_order_id` echo for recon). `sseclient-py==1.9.0` + `websockets==15.0.1` already in requirements (SSE/WS transports present, unused by repo).

## 3. Overlap (do NOT re-add)

| SDK capability | Already in repo (equal or stronger) | Verdict |
|---|---|---|
| `TradingClient(paper=)` paper/live split | `alpaca_broker:14-18` + executor allowlist + dual-gate (`live_alpaca_executor:75-99,174-180`) | OVERLAP — keep ours; SDK flag is necessary but NOT sufficient (allowlist + killswitch remain authoritative) |
| `MarketOrderRequest` DAY market | `alpaca_broker:68-79` + executor notional market (144-150) | OVERLAP — keep; gap is only legs/lifecycle/trailing/notional-client-id (§4) |
| `StopLossRequest` attach | `alpaca_broker:75-76` | OVERLAP (single-leg only); adopt take-profit + bracket/OCO/OTO legs (§4-A3) |
| Fractional-short int-cast caution | `alpaca_broker:63-66` | OVERLAP — keep; never enable fractional shorts |
| Historical daily bars + `.df` + schema validate | `alpaca_data_provider:56-107` + `OHLCVSchema` | OVERLAP — keep; adopt only feed/timeframe/snapshot/news/corp-actions (§4-A4/A5) |
| Cache-first offline gates | `chain.py` + `market_data.py` parquet + `market_data_2019_2026/` | STRONGER than live-fetch; streaming/news stay cache-warmers, never gate inputs |
| Fail-closed paper default | `config.live_trading_enabled=False`, executor early-return (192) | STRONGER — every new order path MUST re-check it; no proposal flips it |

## 4. Adopt (additive, fail-closed, paper-only — never auto-live)

Ranked by paper-to-live sync value / risk. All additions are NEW files + additive kwargs; `live_alpaca_executor.py` raw-`requests` path is NOT deleted (it stays as the audited fallback until A1-A3 prove parity in paper logs).

**A1 — Typed order builders with pydantic validation + `client_order_id` (highest value, lowest risk).**
Repo hand-builds order dicts (executor) or bare `MarketOrderRequest(qty)` (broker); invalid side/TIF sails to HTTP 422, and `paper_executor` idempotency ids never reach the venue so recon can't join on them.
Propose NEW `src/execution/alpaca_orders.py`: `build_market(symbol, side, qty|notional, tif=DAY, client_order_id, extended_hours=False)`, `build_limit(+limit_price)`, `build_stop(+stop_price)`, `build_stop_limit`, `build_trailing(+trail_price|trail_percent, exactly-one guard)`. Each validates via SDK constructors (pydantic raises before HTTP), normalizes `side` (`buy/sell` → `OrderSide`), rejects fractional-short `qty` non-int (mirrors `alpaca_broker:63-66`), rejects `notional` shorts (Alpaca restriction the executor comment at 140-142 already suspects), and REQUIRES `client_order_id` (caller passes `generate_client_order_id` output). `AlpacaBroker.place_order` gains additive kwargs `notional, limit_price, stop_price, trail_price|trail_percent, client_order_id, order_class/take_profit/stop_loss` defaulting to current behavior when absent (byte-parity path tested).

**A2 — Order-lifecycle sync: poll + recon join (closes the paper-to-live gap).**
Today paper logs `SUBMITTED` strings; live truth (fill/cancel/reject/partial) is never polled, so `paper_executor` fills stay `status_details` and `recon.deltas` empty.
Propose NEW `src/execution/alpaca_lifecycle.py`: `poll_order(client, venue_order_id|client_order_id)` → normalized `{venue_order_id, client_order_id, symbol, side, qty, filled_qty, avg_fill_price, status, legs}` via `get_order_by_id/get_order_by_client_id`; `list_open(status=OPEN, symbols, limit, nested=True)` via `GetOrdersRequest` (legs included so bracket children are visible); `cancel(symbol_or_id)`, `replace(order_id, qty|limit|stop|trail)`, `flatten(symbol)` (`close_position`) and `flatten_all()` — the last two gated by the SAME dual-gate + killswitch + allowlist as the executor (fail-closed; paper tests call them only against `paper-api`). `PaperExecutor.execute_plan` post-pass calls `poll_order` for each `venue_order_id` missing `avg_px` and fills `avg_px/status/filled_qty` from venue truth; `recon.py` joins `orders.json ↔ fills.json ↔ venue poll` on `client_order_id` and records mismatches instead of empty lists. `UniversalBroker` stops collapsing to bool: returns/resolves the normalized dict (bool preserved as deprecated alias for callers).

**A3 — Bracket + OCO/OTO + trailing (paper-only; live requires explicit second flag).**
Repo can only express lone market + optional stop; backtest assumes stop-loss exits (`ANALYSIS_REPORT` live-vs-backtest inconsistency note) that paper can't enforce atomically — single-leg stops drift from simulated fills.
Propose bracket builders in `alpaca_orders.py`: `build_bracket(symbol, side, qty|notional, take_profit_limit, stop_loss_stop[, stop_loss_limit])` → `order_class=BRACKET`; `build_oco(...)`, `build_oto(entry + take_profit/stop_loss)`; trailing via `build_trailing`. Guardrails: paper path always allowed (against `paper-api` only); LIVE path requires `LIVE_TRADING_ENABLED AND dual_gate_allows_trading AND explicit per-call allow_bracket_live=True` (no silent promotion — default `False`, logs CRITICAL + refuses when any conjunct fails). `BaseBroker.get_capabilities` gains `supports_bracket/supports_oco_oto/supports_trailing/supports_notional/supports_fractional` (defaults `False`; `AlpacaBroker` returns `True` except fractional-short `False`) so `ExecutionBridge`/`UniversalBroker` capability-gate before building (mirrors existing `LIVE_DESIGN §2` discipline).

**A4 — Streaming bars cache-warmer (paper only, never auto-trade).**
`StockDataStream.subscribe_bars/subscribe_daily_bars/subscribe_updated_bars` give push bars that eliminate the yfinance-vs-Alpaca daily-close skew between research CSVs and live `Open[t+1]` fills, without touching order code.
Propose NEW `src/data/alpaca_stream_cache.py`: `warm_symbols(symbols, timeframe=Day|Min, feed=IEX)` subscribes, appends to the SAME parquet cache keys `MarketDataManager` uses, stamps `source: alpaca-stream`, and STOPS (`stop/close`) on killswitch/DD-breaker or process exit. Contract: stream NEVER calls `place_order`; NEVER feeds gates directly — gates keep reading cached/history frames; stream only reduces staleness. `TimeFrame`/`DataFeed` validated by pydantic (unsupported timeframe raises, never silent-empty — same strictness sibling studies ask for). Unit-tested with mocked `StockDataStream` (no socket).

**A5 — Corporate news sentiment feed, paper-research only (never auto-live).**
`NewsClient.get_news(NewsRequest(symbols, start, end, sort, limit, include_content))` + `CorporateActionsRequest` give timestamped headlines + splits/dividends/mergers that the current `fetch_sentiment_feed → NotImplementedError` path lacks; paper research joins them to `wsb_factual_research_data.csv` debates offline.
Propose NEW `src/data/providers/alpaca_news_provider.py` (`BaseDataProvider` sibling, NOT a chain replacement): `fetch_news(symbols, start, end, limit, include_content=False)` → normalized frame `{published_at, symbol, headline, summary, url, sentiment_hint}` (raw headline/summary preserved; NO auto-score committed — scoring stays in `src/alpha`/debate engine); `fetch_corporate_actions(...)` → `{symbol, action_type, ex_date, ratio}` used ONLY to adjust/flag backtest bars (split/dividend awareness) and to BLOCK paper sleeves across ex-dates when configured. Explicit non-goals: no headline-triggered live orders, no auto-sizing on sentiment, no `include_content=True` bulk ingest without operator opt-in (payload cost). Chain (`chain.py`) unchanged; research scripts opt into the news provider directly.

**A6 — `TradingStream` paper reconciler (push complements A2 poll).**
`TradingStream.subscribe_trade_updates(handler)` echoes `client_order_id` on fill/cancel/reject — the exact join key `paper_executor` already mints but never receives.
Propose `alpaca_lifecycle.py:TradeUpdateRecorder`: paper-only async subscriber writing `docs/data/ops/trade_updates.jsonl` (`{client_order_id, venue_order_id, event, filled_qty, avg_price, ts}`); `PaperExecutor` replays the JSONL before the A2 poll so fills resolve without extra REST calls. Never places/cancels orders itself; stops on killswitch. Mocked-`TradingStream` tests only.

## 5. Reject (with reason)

1. **Raw-`requests` executor deletion / wholesale `TradingClient` swap.** The hand-rolled allowlist + dual-gate + circuit-breaker block (`live_alpaca_executor:75-99,174-232`) is audited fail-closed history; deleting it for a pure-SDK path removes the exact-match URL guard reviewers rely on. Migrate by WRAPPING (A1 builders inside the same gated functions), not by deleting.
2. **Live streaming-triggered trading.** `subscribe_bars` → `place_order` wiring turns a daily cron system into an intraday reactor: PDT exposure, quote-churn, killswitch bypass. Stream writes cache only (A4 contract).
3. **News-headline auto-live orders / auto-sizing.** Sentiment feed is research-only; any live use needs pre-registration + walk-forward + permutation + DSR per `AGENTS.md` edge gate + human live-gate flip. Never wire `get_news` to the order path.
4. **Fractional shorts / `notional` sells.** Alpaca restricts notional shorts; `alpaca_broker:63-66` int-cast + A1 notional-short refusal stay. Keep whole-share sells.
5. **`extended_hours=True` default / OTO live default.** After-hours fills gap from backtest `Open[t+1]` assumptions; OTO chains silently add legs. Both default `False`; live needs the A3 triple conjunct.
6. **`alpaca-py` 0.35.0 → 0.44.0 upgrade inside this study.** Latest adds option/screener surfaces the repo doesn't need; upgrade risk (pydantic/requests drift) buys nothing for A1-A6. Pin stays; revisit only with a dedicated dep-bump + full gate rerun.
7. **Replacing `MarketDataManager`/chain with live-only fetch.** Offline cached gates (`DATA_IS_MOCK` discipline, sibling-study consensus) must keep passing with no network. Streaming/news are warmers/joins, never required inputs.
8. **Leverage/margin/short-intent option legs (`position_intent`, `mleg`).** Violates long/flat fail-closed mandate (`MAX_RISK_PER_TRADE_PCT`, circuit breakers). Paper-only; never enable without pre-registered gate change.

## 6. Exact diffs proposed (additive; NOT applied — study only)

### Diff 0 — `requirements.txt` (comment only; no version change)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 alpaca-py==0.35.0
+# NOTE(alpaca-adopt 2026-09-09): A1-A6 vendored against 0.35.0 typed surface
+# (TradingClient/NewsClient/StockDataStream/TradingStream + OrderClass
+# bracket/oco/oto). No upgrade to 0.44.0 in this study. sseclient-py +
+# websockets already present for streaming transports. See
+# _deliverables/alpaca-adopt-2026-09-09.md §5 for rejected live wirings.
```

### Diff 1 — NEW `src/execution/alpaca_orders.py` (~150 lines; typed builders, pydantic-validated)

```python
"""Typed Alpaca order builders (alpaca-py 0.35.0 surface, paper-safe).

Every builder constructs the real SDK request object so pydantic validates
BEFORE any HTTP. Fractional-short and notional-short refused (mirror
AlpacaBroker int-cast rule). client_order_id REQUIRED for recon join.
Live bracket/OCO/OTO/trailing additionally require allow_live_legs=True AND
the caller's dual-gate + URL allowlist (checked by callers, re-asserted here
against paper URL when allow_live_legs is False).
"""
from __future__ import annotations
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
from alpaca.trading.requests import (
    MarketOrderRequest, LimitOrderRequest, StopOrderRequest,
    StopLimitOrderRequest, TrailingStopOrderRequest,
    TakeProfitRequest, StopLossRequest,
)

PAPER_URL = "https://paper-api.alpaca.markets"

def _side(s: str) -> OrderSide:
    return OrderSide.BUY if s.lower() == "buy" else OrderSide.SELL  # pydantic rejects the rest downstream

def _guard_qty_side(side: str, qty: float | None, notional: float | None) -> None:
    if qty is not None and side.lower() == "sell" and float(qty) != int(float(qty)):
        raise ValueError("fractional shorts disallowed (whole-share sells only)")
    if notional is not None and side.lower() == "sell":
        raise ValueError("notional shorts disallowed by Alpaca; pass whole-share qty")

def build_market(symbol, side, qty=None, notional=None, tif=TimeInForce.DAY,
                 client_order_id: str = "", extended_hours: bool = False, **legs):
    if not client_order_id: raise ValueError("client_order_id required (recon join)")
    _guard_qty_side(side, qty, notional)
    return MarketOrderRequest(symbol=symbol, qty=qty, notional=notional, side=_side(side),
                              time_in_force=tif, client_order_id=client_order_id,
                              extended_hours=extended_hours, **legs)

def build_limit(symbol, side, qty=None, notional=None, limit_price: float = 0.0, **kw):
    _guard_qty_side(side, qty, notional)
    return LimitOrderRequest(limit_price=limit_price, symbol=symbol, qty=qty,
                             notional=notional, side=_side(side), **kw)

def build_trailing(symbol, side, qty=None, trail_price=None, trail_percent=None, **kw):
    if (trail_price is None) == (trail_percent is None):
        raise ValueError("exactly one of trail_price|trail_percent")
    _guard_qty_side(side, qty, None)
    return TrailingStopOrderRequest(symbol=symbol, qty=qty, side=_side(side),
                                    trail_price=trail_price, trail_percent=trail_percent, **kw)

def build_bracket(symbol, side, qty=None, notional=None, take_profit_limit: float = 0.0,
                  stop_loss_stop: float = 0.0, stop_loss_limit: float | None = None,
                  client_order_id: str = "", **kw):
    if not client_order_id: raise ValueError("client_order_id required")
    _guard_qty_side(side, qty, notional)
    sl = {"stop_price": stop_loss_stop} | ({"limit_price": stop_loss_limit} if stop_loss_limit else {})
    return MarketOrderRequest(symbol=symbol, qty=qty, notional=notional, side=_side(side),
                              order_class=OrderClass.BRACKET,
                              take_profit=TakeProfitRequest(limit_price=take_profit_limit),
                              stop_loss=StopLossRequest(**sl),
                              client_order_id=client_order_id, **kw)
# build_oco / build_oto mirror with OrderClass.OCO / .OTO (same leg shape).
```

Wiring (additive): `AlpacaBroker.place_order(..., notional=None, limit_price=None, stop_price=None, trail_price=None, trail_percent=None, client_order_id=None, order_class=None, take_profit=None, stop_loss=None)` — when all new args are `None`/empty, delegates to the CURRENT `MarketOrderRequest(qty)` path byte-identical; else dispatches to the builder above. `get_capabilities()` gains `supports_bracket/supports_oco_oto/supports_trailing/supports_notional/supports_fractional` (True except fractional-short False).

### Diff 2 — NEW `src/execution/alpaca_lifecycle.py` (~130 lines; poll/recon/push-recorder)

```python
"""Order-lifecycle sync (poll + push recorder). No order placement here."""
from __future__ import annotations
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import QueryOrderStatus

def normalize(order) -> dict:
    return {"venue_order_id": str(order.id),
            "client_order_id": getattr(order, "client_order_id", ""),
            "symbol": order.symbol, "side": str(order.side),
            "qty": float(order.qty or 0), "filled_qty": float(order.filled_qty or 0),
            "avg_fill_price": float(order.filled_avg_price or 0) or None,
            "status": str(order.status), "legs": [normalize(l) for l in (order.legs or [])]}

def poll_order(client, venue_order_id=None, client_order_id=None) -> dict:
    o = client.get_order_by_id(venue_order_id) if venue_order_id else client.get_order_by_client_id(client_order_id)
    return normalize(o)

def list_open(client, symbols=None, limit=50) -> list[dict]:
    req = GetOrdersRequest(status=QueryOrderStatus.OPEN, symbols=symbols, limit=limit, nested=True)
    return [normalize(o) for o in client.get_orders(req)]

def cancel(client, venue_order_id): return client.cancel_order_by_id(venue_order_id)
def replace(client, venue_order_id, **kw): return normalize(client.replace_order_by_id(venue_order_id, kw))
# flatten()/flatten_all() thin wrappers over close_position/close_all_positions,
# each asserting dual-gate + paper-URL allowlist before delegating (fail-closed).

class TradeUpdateRecorder:
    """Paper-only TradingStream sink -> docs/data/ops/trade_updates.jsonl."""
    def __init__(self, stream, sink_path="docs/data/ops/trade_updates.jsonl"): ...
    async def handler(self, update): ...  # writes {client_order_id, event, filled_qty, avg_price, ts}
```

Wiring (additive): `PaperExecutor.execute_plan` post-pass — for each order missing `avg_px`, call `poll_order` (or replay `trade_updates.jsonl` first) and backfill `avg_px/status/filled_qty`; `recon["mismatches"]` records venue-vs-log joins instead of `[]`. `UniversalBroker.execute_order` returns the normalized dict (truthy bool-compatible `{"status","order_id",...}`; legacy `==True` callers keep working via `__bool__`-safe `"status"=="success"` shape).

### Diff 3 — `src/execution/alpaca_broker.py` (additive kwargs, parity default)

```diff
--- a/src/execution/alpaca_broker.py
+++ b/src/execution/alpaca_broker.py
@@
-    def place_order(self, symbol: str, qty: float | None, side: str, order_type: str = 'market', stop_loss_price: float | None = None) -> dict:
+    def place_order(self, symbol: str, qty: float | None = None, side: str = 'buy', order_type: str = 'market',
+                    stop_loss_price: float | None = None, notional: float | None = None,
+                    limit_price: float | None = None, trail_price: float | None = None,
+                    trail_percent: float | None = None, client_order_id: str | None = None,
+                    order_class=None, take_profit=None, stop_loss=None) -> dict:
+        """Additive typed path (alpaca-adopt A1/A3). All-new args None/empty ->
+        legacy MarketOrderRequest(qty) path byte-identical. Bracket/OCO/OTO live
+        legs additionally require the caller's dual-gate + allowlist (fail-closed)."""
```

Return shape gains `fill_price/avg_price` (from `filled_avg_price` when immediately available, else `None` so the A2 poll backfills) + `client_order_id` echo + `fee: 0.0` (Alpaca equities commission-free; explicit zero beats missing key).

### Diff 4 — NEW `src/data/providers/alpaca_news_provider.py` (~90 lines; paper-research only)

```python
"""Corporate news + actions feed (paper research only, never auto-live)."""
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest, CorporateActionsRequest

class AlpacaNewsProvider:
    def __init__(self, api_key, secret_key): ...
    def fetch_news(self, symbols, start, end, limit=50, include_content=False) -> pd.DataFrame:
        """Columns: published_at, symbol, headline, summary, url. No scoring here."""
    def fetch_corporate_actions(self, symbols, start, end) -> pd.DataFrame:
        """Columns: symbol, action_type, ex_date, ratio. Consumed to flag/adjust bars only."""
```

### Diff 5 — NEW `src/data/alpaca_stream_cache.py` (~80 lines; WS cache-warmer, never trades)

```python
"""Streaming bars -> parquet cache warmer (paper only). NEVER calls place_order."""
from alpaca.data.live.stock import StockDataStream
from alpaca.data.timeframe import TimeFrame
from alpaca.data.requests import StockBarsRequest  # history bootstrap counterpart

async def warm_symbols(stream: StockDataStream, symbols, handler, timeframe=TimeFrame.Day, ...):
    """subscribe_bars(symbols, handler) + run(); handler appends MarketDataManager
    cache keys with source='alpaca-stream'. stop()/close() on killswitch/DD-breaker."""
```

### Diff 6 — docs/checklist only (no live change)

- `PAPER_BROKER_SETUP.md` appendix: typed-order parity checklist (pydantic-before-HTTP, `client_order_id` required, bracket/OCO/OTO paper-only matrix, trailing exactly-one rule, notional-buy vs whole-share-sell matrix, `GetOrdersRequest(nested=True)` recon query, `DataFeed` choice logged, unsupported-timeframe raise).
- `live_alpaca_executor.py` header comment: documents that A1 builders are the ONLY sanctioned constructor for new order types; raw dict path stays for the audited market/notional leg until parity is proven in paper logs.

## 7. Test plan (offline, deterministic, mocked SDK — serial per SWARM config)

New `tests/execution/test_alpaca_adopt.py` (+ `tests/data/test_alpaca_news_stream.py`). NO network, NO keys, NO socket: `unittest.mock.MagicMock` for `TradingClient/NewsClient/StockHistoricalDataClient/StockDataStream/TradingStream`; SDK request classes used REAL (pydantic validation is the subject).

1. `test_market_builder_validates` — bad `side="yolo"` raises `ValidationError` before any `submit_order`; `submit_order` mock not called.
2. `test_client_order_id_required` — `build_market` without id raises `ValueError`; with `generate_client_order_id(...)` passes and echoes on the mock's returned order.
3. `test_notional_buy_vs_short_refusal` — `notional` buy builds; `notional` sell raises; fractional sell `qty=1.5` raises; whole-share sell passes.
4. `test_bracket_legs` — `build_bracket` yields `order_class==BRACKET` with `take_profit.limit_price` + `stop_loss.stop_price`; mocked `submit_order` receives legs; nested `list_open(nested=True)` normalizer exposes children.
5. `test_oco_oto_classes` — `OrderClass.OCO/OTO` builders set class + legs; live call without `allow_live_legs=True` refuses fail-closed (paper URL assert).
6. `test_trailing_exactly_one` — both/neither `trail_price/trail_percent` raises; each alone builds `TrailingStopOrderRequest`.
7. `test_lifecycle_poll_backfill` — mock `get_order_by_id` returns filled order; `poll_order` normalizes `{avg_fill_price, filled_qty, status}`; `PaperExecutor` backfill writes `avg_px/FAILED-vs-FILLED` without network.
8. `test_idempotent_recon_join` — duplicate `client_order_id` skipped (existing executor rule); `recon mismatches` records venue-vs-log divergence fixture.
9. `test_news_normalize` — mocked `get_news` page → frame cols `{published_at, symbol, headline, summary, url}`; `include_content` default False; corporate-actions frame `{symbol, action_type, ex_date, ratio}`.
10. `test_stream_warmer_never_trades` — mocked `StockDataStream.subscribe_bars/run` appends cache rows with `source=alpaca-stream`; assert `place_order`/`submit_order` mocks NEVER called; `stop/close` called on breaker.
11. `test_capabilities_gate` — `supports_bracket/trailing/notional` True on `AlpacaBroker`, `supports_fractional` False for shorts; `ExecutionBridge` refuses bracket when capability False.
12. `test_no_forbidden_edits` — `git status --porcelain` shows only NEW `alpaca_orders.py/alpaca_lifecycle.py/alpaca_news_provider.py/alpaca_stream_cache.py` + additive broker/executor hunks + new tests; `evolve_real.py`, `strategies/registry.json`, `strategies/` clean.

Commands (one file at a time, serial):

```
PYTHONPATH=. pytest tests/execution/test_alpaca_adopt.py -q
PYTHONPATH=. pytest tests/data/test_alpaca_news_stream.py -q
PYTHONPATH=. pytest tests/execution/test_paper_executor.py -q
```

Acceptance: 12/12 new pass, legacy executor/broker suites green, no socket/key/network in tests (mock-asserted), forbidden-files clean, paper-URL allowlist + dual-gate tests still green.

## 8. Rollout (for implementer, not done here)

1. Land Diff 1 + tests 1-3,6 → paper logs show pydantic-before-HTTP + `client_order_id` echo one cycle; raw-dict path untouched.
2. Land Diff 2 + tests 7-8 → `fills.json/recon.json` backfilled from venue truth in paper; `deltas/mismatches` non-empty-where-diverged.
3. Land Diff 3 (A3) + tests 4-5,11 → bracket/OTO paper sleeves behind `allow_bracket_live=False`; live legs stay refused.
4. Land Diffs 4-5 + tests 9-10 → stream-warmed cache + news/corp-actions research joins offline; gates unchanged.
5. Diff 6 docs → parity checklist in `PAPER_BROKER_SETUP.md`; `live_alpaca_executor` gates untouched throughout.
6. Revisit dep bump / options / `DataFeed.SIP` / `extended_hours` ONLY with dedicated proposal + full edge gate (pre-register → walk-forward → permutation → DSR) — never bundled with this sync work.

## 9. References

- Pinned SDK: `requirements.txt:1` (`alpaca-py==0.35.0`); probed 0.35.0 surfaces §2 (`TradingClient`, `*.requests.model_fields`, `OrderClass`, `NewsRequest`, `CorporateActionsRequest`, `StockDataStream.*subscribe*`, `TradingStream.subscribe_trade_updates`).
- Actuals: `src/execution/{live_alpaca_executor.py:1-394, alpaca_broker.py:1-98, universal_broker.py:1-162, paper_executor.py:38-215, execution_bridge.py:16-41, base_broker.py:1-44}` + `src/data/{market_data.py:1-58, providers/alpaca_data_provider.py:1-110, providers/base.py:1-13, providers/chain.py:1-104}` + `src/utils/config.py:35-80` + `PAPER_BROKER_SETUP.md` + `ANALYSIS_REPORT.md` backtest-vs-live stop-loss note.
- Sibling study format: `_deliverables/pybroker-adopt-2026-09-09.md` (additive diffs + test plan convention followed here).
