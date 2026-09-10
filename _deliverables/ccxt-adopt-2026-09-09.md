# ccxt Adoption Study — Optional Venue Adapter Behind Broker Interface

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint.
Scope: compare `ccxt/ccxt` unified exchange API (100+ venues, normalized REST+WS, L2/L3 books, OHLCV) vs ACTUAL `src/execution/` (`live_crypto_executor.py`, `universal_broker.py`, `paper_executor.py`, `ccxt_broker.py`, `base_broker.py`, `alpaca_broker.py`) + `src/data/` providers. Propose ccxt strictly as optional venue adapter behind existing interfaces.
Workdir constraint: stayed inside workdir; only new file is `_deliverables/ccxt-adopt-2026-09-09.md`.
Upstream: `https://github.com/ccxt/ccxt` (v4.5.74 pinned in `requirements.txt:168`; MIT; REST `ccxt` + WS `ccxt.pro` split).

## 1. Actual repo surveyed (read, with line refs)

Execution:

- `src/execution/base_broker.py:1-44` — `BaseBroker` ABC. Five methods only: `get_account_balance()->{equity,cash}`, `place_order(symbol,qty,side,order_type,stop_loss_price)`, `get_positions()->[{symbol,qty,market_value,unrealized_pl}]`, `cancel_order(symbol)->bool` (fail-closed hook), `get_capabilities()->{supports_market_orders,supports_stop_limit,supports_paper}` (freqtrade-style `exchange_has` mirror, checked before order types).
- `src/execution/alpaca_broker.py:1-98` — Reference implementation. `TradingClient(api_key,secret,paper=is_paper)` (`is_paper = not config.trading.live_trading_enabled`), keyless → `client=None` + safe fallbacks (`get_account_balance` returns `initial_capital`, `get_positions` returns `[]`, `place_order` raises `ConnectionError`, `cancel_order` returns `True`). Fractional-short int-cast + qty-0 raise (63-66), DAY TIF + `StopLossRequest` attach (68-80), capabilities all-True.
- `src/execution/ccxt_broker.py:1-124` — Existing CCXT adapter, functional but NOT fail-closed enough (see §3). `__init__(exchange_id="binance")`, keys from `config.api_keys.binance_*` + `get_secret_str`, raises `ConfigurationError` if either missing (24-25), `getattr(ccxt, exchange_id)` dynamic dispatch (33), `enableRateLimit=True`, `options.defaultType='spot'` (39), `set_sandbox_mode(True)` when `is_paper` (42-43). `get_account_balance` reads `balance.total/free.USDT` with `initial_capital` fallback (54-62). `get_positions` synthesizes spot positions from `fetch_balance().total` non-USDT balances (64-80). `place_order` maps to `create_order(symbol,type,side,amount,params={stopPrice,reduceOnly})`, catches `(InsufficientFunds,InvalidOrder,NetworkError,ExchangeError)` → `{"status":"failed"}` (104-106). `cancel_order` → `cancel_all_orders(symbol)` → bool (108-115). `get_capabilities` from `exchange.has` map: `market→supports_market_orders (default True)`, `stopLimit→supports_stop_limit (default False)`, `sandbox→supports_paper (default True)` (117-124).
- `src/execution/universal_broker.py:1-162` — Router + risk interceptor. `BaseExecutor` ABC (`get_account_equity`, `execute_order`, `liquidate_strategy_positions`). `AlpacaExecutor` wraps `AlpacaBroker`, `CryptoExecutor` wraps `CCXTBroker` (81-84). `UniversalBroker.get_executor(asset_class)`: `'crypto'→crypto else alpaca` (113-117). `place_order(asset_class,strategy_id,ticker,direction,quantity,risk_amount)`: 1% equity risk intercept (`MAX_RISK_PER_TRADE_PCT=0.01`), Telegram alert on success, `handle_promotion/handle_demotion` alerts + liquidate-both-executors on demotion (119-154).
- `src/execution/live_crypto_executor.py:1-444` — Bybit-specific DIRECT-ccxt script that BYPASSES `BaseBroker`/`UniversalBroker`. Module-level `BYBIT_API_KEY/SECRET` from `config.api_keys` + `os.getenv` (53-55), fail-closed raise if `LIVE_TRADING_ENABLED and missing keys` (58-59), `USE_SANDBOX = not LIVE_TRADING_ENABLED` (61). `init_bybit_exchange()`: `ccxt.bybit({apiKey,secret,enableRateLimit,options.defaultType='linear'})` + `set_sandbox_mode(True)` iff sandbox (83-102). `fetch_account_equity` from `fetch_balance().USDT.equity/total` (104-116). `fetch_historical_ohlcv` via `fetch_ohlcv(symbol,'1d',limit)` → DataFrame (118-131). `get_current_positions_and_scores` via `fetch_positions(symbols=[BTCUSDT,ETHUSDT,SOLUSDT])` + per-ticker OHLCV → momentum/vol (133-183). `execute_bybit_order` via `fetch_ticker.last` → net-qty → `create_market_order` with `InsufficientFunds→halve+retry`, `InvalidOrder→floor-$10+retry` (185-253). `gates_allow_trading` daily/weekly circuit + max-positions (256-270). `main()` dual-gate `dual_gate_allows_trading` (273-281), sandbox/live consistency abort (282-284), equity>0 abort (298-301), HWM/last-equity state file, per-entry clamp `MAX_POSITION_SIZE_PCT`, new-entry/full-close position counting, rebalance loop (388-425).
- `src/execution/paper_executor.py:1-219` — Idempotent plan executor (default `AlpacaBroker`). Loads `docs/data/ops/plan.json`, kill-switch `halt_new_orders/flat` skip (49-54), blocked-plan skip, `get_positions` fail → return (no orders), `client_order_id = generate_client_order_id(run,sleeve,ticker,seq)` dedup (123-129), missing-qty fail-fast raise (131-135), `place_order(ticker,qty,side,"market")` → `orders.json` + `fills.json` (avg_px if present else status_details) + `recon.json` + heartbeat. Broker-injected (`__init__(broker=None)`), so any `BaseBroker` works.
- `src/execution/execution_adapter.py:1-104` — Legacy `PaperTradeBroker` ABC + localhost:5000 `PaperbrokerClient` + `ExecutionAdapter.execute_signals`. Separate from `BaseBroker`; do not route ccxt through here.

Data:

- `src/data/providers/base.py:1-13` — `BaseDataProvider` ABC: `fetch_ohlcv(tickers,start,end)->DataFrame`, `fetch_sentiment_feed(limit)`.
- `src/data/base_provider.py:1-9` — `MarketDataProvider.get_historical_data(ticker,start,end,timeframe='1d')`. Older interface; chain uses `BaseDataProvider`.
- `src/data/schemas.py:1-59` — `OHLCVSchema` (pandera or stub): `Ticker,Date,Open,High,Low,Close,Volume` with `High>=Low/Open/Close`, `Low<=Open/Close`. All providers validate before returning.
- `src/data/providers/chain.py:1-104` — `DataProviderChain`: `Alpaca→Tiingo→BinancePublic→YFinance` fallback, `CacheEngine.determine_missing_ranges` top-level cache-first, write-through except YFinance (self-caching), singleton `get_provider()`. No ccxt in chain.
- `src/data/providers/alpaca_data_provider.py:1-110` — Stock+crypto bars, `BTC-USD↔BTC/USD` normalize/denormalize (29-40), inclusive end (`+1 day`), `adjustment="all"`, TZ-strip, schema-validate, keyless → warning + empty DataFrame (43-45).
- `src/data/providers/binance_public_provider.py:1-82` — Keyless REST WITHOUT ccxt: `GET https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d` (31,48), `BTC-USD→BTCUSDT` normalize (20-23), `_is_crypto` gate (`-` + `USD/USDT`) (17-18), float-cast + schema-validate, `RequestException→warning+skip` (72-75). Proves the keyless-public pattern ccxt should reuse.
- `src/data/providers/yfinance_provider.py:1-131` — Cache-first + `yf.download` batch + chunk fallback + 252-day minimum-history filter + universe fallback. Network-in-provider precedent, but backtest gates run offline on cached CSVs.
- `src/utils/config.py:1-108` — `Settings`: `BINANCE_API_KEY/SECRET`, `BYBIT_API_KEY/SECRET` (29-32) via env/`.env`, `get_secret_str()` normalizer (91-97), `ConfigWrapper` stubs (`api_keys`, `trading.live_trading_enabled/paper_trading_enabled/initial_capital`). No CCXT_EXCHANGE allowlist yet.
- `.env.example:1-16` — `LIVE_TRADING_ENABLED=False`, `PAPER_TRADING_ENABLED=True`, all keys `""` including `BINANCE_*`. Convention: empty = keyless/paper; never commit real keys.
- `requirements.txt:168` — `ccxt==4.5.74` already pinned (hard dep today; §4 proposes softening to optional).

Tests (mocking convention to reuse):

- `tests/brokers/test_broker_capability.py:1-101` — `make_ccxt_broker(has)` bypasses `__init__` via `object.__new__(CCXTBroker)` + `FakeExchange(has)`; asserts 3 capability keys bool-typed, market-defaults-True, stopLimit-defaults-False. Pattern for all new ccxt tests (no keys, no network).
- `tests/brokers/test_brokers.py:1-16` — `AlpacaBroker()` keyless mock-mode asserts (`equity` key, `place_order` success-or-ConnectionError).
- `tests/execution/test_live_crypto_executor_caps.py:1-168` + `tests/test_crypto_executor_caps.py:1-196` — `sys.modules['ccxt']=MagicMock()` BEFORE import, `monkeypatch` module keys + `risk_config` caps + `dual_gate_allows_trading→(True,"")`, `chdir(/tmp)` for state file, `MagicMock` exchange (`fetch_ticker.last=50000`, `create_market_order→{id}`), `main()` cap assertions (clamp message, skip message, single-call args `(exchange,'BTCUSDT',100.0,0.0)`).

## 2. ccxt patterns studied (v4.5.74, as pinned)

- **Unified exchange API (100+ venues):** `import ccxt; ex = getattr(ccxt, exchange_id)({apiKey,secret,enableRateLimit,options})`. Same method names across venues: `fetch_balance`, `fetch_ohlcv(symbol,timeframe,limit)`, `fetch_order_book(symbol,limit)`, `fetch_ticker`, `fetch_positions(symbols)`, `create_order(symbol,type,side,amount,price,params)`, `cancel_all_orders(symbol)`, `cancel_order(id,symbol)`, `set_sandbox_mode(bool)`, `load_markets()`. Venue differences hidden behind `exchange.has` capability map (`has['fetchOHLCV']`, `has['fetchOrderBook']`, `has['createMarketOrder']`, `has['sandbox']`, …) — the exact map `CCXTBroker.get_capabilities` already mirrors freqtrade-style.
- **OHLCV normalized shape:** `fetch_ohlcv` returns `[[ts_ms,open,high,low,close,volume],…]` regardless of venue; caller picks `timeframe ∈ {'1d','4h','1h','15m',…}` + `limit`. Repo's `live_crypto_executor.fetch_historical_ohlcv:124` already consumes this shape correctly. Public (keyless) `fetch_ohlcv` works on most spot venues without credentials — the safe read path.
- **L2/L3 books:** `fetch_order_book(symbol,limit)` → `{bids:[[price,amt],…],asks:…,timestamp,nonce}` (L2 aggregated). L3 (`fetch_l3_order_book` on few venues) and full WS books (`ccxt.pro.watch_order_book`) are venue-sparse, high-churn, high-cost. REST L2 depth 20-50 suffices for capacity/slippage estimation; nothing in repo needs L3/WS depth.
- **WS (`ccxt.pro`, separate package):** `watch_ohlcv/watch_order_book/watch_balance/watch_orders` async loops. NOT in `requirements.txt`, NOT needed: repo executes daily cron (`live_*_executor.main()`), backtests on EOD bars, paper-executor is synchronous plan replay. WS adds reconnect/backpressure/ordering risk with zero strategy demand.
- **Sandbox:** `exchange.set_sandbox_mode(True)` routes to testnet where supported (`has['sandbox']`); unsupported venues raise — hence capability-gate + try/except + fail-closed. `enableRateLimit: True` auto-throttles to venue `rateLimit`.
- **Exceptions (what to catch, in order):** `ccxt.BaseError` → `ExchangeError` (incl. `InsufficientFunds`, `InvalidOrder`, `InvalidNonce`), `NetworkError` (incl. `DDoSProtection`, `RateLimitExceeded`, `RequestTimeout`), `AuthenticationError`. Repo catches the right subset (`ccxt_broker:104`, `live_crypto_executor:231,243`) but misses `AuthenticationError→fail-closed-disable` and `DDoSProtection/RateLimitExceeded→backoff-skip` distinctions (§4).
- **Market structure:** `load_markets()` → `markets[symbol] = {limits:{amount:{min},cost:{min}},precision:{amount,price},active,…}`. Correct order sizing normalizes `amount` to venue precision/minimum BEFORE `create_order` (repo does NOT do this today — dollar→qty via `fetch_ticker.last` only; §4 adds `amount_to_precision` + `cost.min` check).

## 3. Overlap / gaps (do NOT re-add what exists)

| ccxt capability | Already in repo (equal or stronger) | Verdict |
|---|---|---|
| Spot `create_order` market | `ccxt_broker.place_order:82-106` + `live_crypto_executor.execute_bybit_order:227-230` | OVERLAP — harden, don't duplicate |
| `fetch_balance` equity/cash | Both files implement USDT-equity read | OVERLAP — unify normalization (spot `total/free.USDT` vs Bybit `equity/total`) |
| `fetch_ohlcv` daily bars | `live_crypto_executor:118-131` + `BinancePublicProvider` raw REST + chain fallback | OVERLAP on shape; gap is ONLY keyless-ccxt provider behind `BaseDataProvider` (§4) |
| `has` capability map | `ccxt_broker.get_capabilities:117-124` already mirrors it; tests pin contract | OVERLAP — extend to `fetchOHLCV/fetchOrderBook/createMarketOrder/sandbox` reads |
| Sandbox/testnet | `ccxt_broker:42-43` + `live_crypto_executor:97-101` | OVERLAP — gap is allowlist + unsupported-sandbox fail-closed |
| Risk gates (1% intercept, circuit breakers, HWM, max positions/size, dual-gate killswitch) | `universal_broker:111,119-131` + `live_crypto_executor:256-284,398-421` | STRONGER than anything ccxt offers — ccxt NEVER bypasses these |
| Idempotent plan replay (`client_order_id` dedup, fills/recon artifacts) | `paper_executor:76,123-135` | STRONGER — ccxt stays behind broker so replay is preserved |
| Keyless/paper-safe constructors | `alpaca_broker:21-27,29-41` degrades gracefully | STRONGER — `CCXTBroker.__init__` raising on missing keys (24-25) is a REGRESSION vs this pattern; fix in §4 |
| Symbol normalization | `alpaca_data_provider:29-40` (`BTC-USD↔BTC/USD`), `binance_public:20-23` (`BTC-USD→BTCUSDT`), `live_crypto_executor.BYBIT_SYMBOLS` map (65-69) | OVERLAP in spirit; gap is single `normalize_symbol()` handling `BTC-USD↔BTC/USDT↔BTCUSDT` (ccxt needs `BTC/USDT`) |

Gaps that justify a SMALL adapter (and only those):

1. `CCXTBroker` requires keys even for public reads; no keyless `fetch_ohlcv`/`fetch_order_book` path.
2. No `exchange_id` allowlist — `getattr(ccxt, anything)` will instantiate any of 100+ venues, including futures-only/illiquid ones.
3. `defaultType='spot'` hardcoded but unenforced at call time; `live_crypto_executor` uses `'linear'` perps on a different code path — two policies, neither gated.
4. No `load_markets` precision/minimum normalization; no `cost.min` floor check; `MIN_ORDER_SIZE=10.0` is a Bybit-only constant.
5. `get_positions` spot-only; futures `fetch_positions` shape unhandled; `UniversalBroker.handle_demotion` liquidates by strategy tag that neither executor resolves — needs per-symbol cancel/close, not new semantics.
6. `place_order` accepts any `order_type` string without consulting `get_capabilities()` first (Alpaca path documents the gate; CCXT path skips it).
7. `cancel_order(symbol)` → `cancel_all_orders(symbol)` over-cancels; `BaseBroker` contract says "open/working orders for a symbol" so it is technically compliant, but needs explicit doc + single-`cancel_order(id)` overload documented as rejected (§5).

## 4. Adopt (additive, fail-closed, optional venue adapter)

Principle: ccxt is a VENUE PLUGIN behind `BaseBroker` + `BaseDataProvider`. No caller imports ccxt directly except the two adapter modules. Everything else talks to `BaseBroker`/`UniversalBroker`/`PaperExecutor`/`DataProviderChain` as today.

**A1 — Harden `CCXTBroker` (keep file, small diff; highest value).**
- `ALLOWED_EXCHANGES = {"binance","bybit","coinbase"}` module constant; `__init__(exchange_id="binance", *, sandbox: bool|None=None)` validates membership, raises `ConfigurationError` otherwise (fail-closed venue allowlist; stops `getattr(ccxt, arbitrary)`).
- `require_credentials: bool=True` split: private methods (`get_account_balance`, `get_positions`, `place_order`, `cancel_order`) keep the current `ConfigurationError`-when-keyless; NEW keyless path allowed ONLY for `fetch_ohlcv_public`/`fetch_order_book_public` (A2) which construct the exchange WITHOUT keys.
- `sandbox` resolution: explicit arg > `not config.trading.live_trading_enabled`; `set_sandbox_mode(True)` wrapped in try/except (`ExchangeError` → if live requested, raise; if paper, log + continue without sandbox rather than aborting reads).
- `defaultType` locked to `"spot"`; any caller passing `defaultType future/linear/margin` raises `ConfigurationError`. Perps/linear stay in the quarantined `live_crypto_executor` path until a pre-registered gate change explicitly promotes them (see Reject §5).
- Symbol normalization helper: `to_ccxt_symbol("BTC-USD"|"BTCUSDT"|"BTC/USDT")→"BTC/USDT"`; `from_ccxt_symbol("BTC/USDT")→"BTC-USD"` for positions. Unknown shape → `ValueError` (never guess).
- `place_order` pre-checks: (a) `get_capabilities()['supports_market_orders']` when `order_type=="market"` else raise `NotImplementedError`; (b) `load_markets()` precision via `amount_to_precision(symbol,qty)` + `cost.min`/`amount.min` floor → `ValueError("below venue minimum")` instead of venue reject; (c) `qty<=0` → `ValueError`; (d) `stop_loss_price` without `supports_stop_limit` → `NotImplementedError`. Exception mapping: `AuthenticationError→ConfigurationError (disable venue, alert)`; `DDoSProtection|RateLimitExceeded→return {"status":"failed","retryable":True}` (caller skips, does NOT halve-and-retry blindly); `InsufficientFunds|InvalidOrder→{"status":"failed","retryable":False}` (preserves current contract). Never raise network errors into `PaperExecutor` loops.
- `get_account_balance` keeps `{equity,cash}` shape; reads `total/free.USDT` then `USD` fallback then `initial_capital`; wraps ALL ccxt errors → returns `{'equity':0.0,'cash':0.0}` ONLY when called via `UniversalBroker` equity probe? No — keep raising for direct calls (fail-closed), because `UniversalBroker.AlpacaExecutor/CryptoExecutor.get_account_equity` already catches → `0.0` which trips the 1% interceptor safely. Document this layering so nobody "fixes" it by returning fake capital.

**A2 — NEW keyless `CCXTPublicProvider(BaseDataProvider)` for OHLCV (+ bounded L2).**
- `src/data/providers/ccxt_public_provider.py`: `__init__(exchange_id="binance", enable_rate_limit=True)` — NO keys, allowlisted venue, `defaultType='spot'`. `fetch_ohlcv(tickers,start,end)`: normalize each `BTC-USD→BTC/USDT`, `since = start_ms`, paginate `fetch_ohlcv(symbol,'1d',since,1000)` until `end_ms`, build `Ticker/Date/Open/High/Low/Close/Volume` frame, `OHLCVSchema.validate`, per-ticker try/except → skip-with-warning (chain tries next provider). `fetch_sentiment_feed` raises `NotImplementedError` (like siblings). Extra `fetch_order_book_snapshot(symbol,depth=20)->{bids,asks,mid,spread_bps}` for capacity/slippage diagnostics ONLY — never for signals; depth capped 50, exceptions → `None` (informational).
- Wire into `DataProviderChain.providers` as LAST resort after YFinance (public, keyless, rate-limited): `Alpaca→Tiingo→BinancePublic→YFinance→CCXTPublic`. Rationale: ccxt covers venues/dates Binance-vision gaps miss, but stays behind cache + schema + chain-fallback so a ccxt outage degrades to empty, never to an exception.
- No WS: `ccxt.pro` explicitly OUT (no dep, no event loop in providers). L2 is REST snapshot only.

**A3 — Route `UniversalBroker.CryptoExecutor` lazily + capability-gated (no behavior change when keys absent).**
- Lazy import already present; add: `CryptoExecutor.__init__` catches `ConfigurationError/ImportError` → `self.broker=None, self.disabled_reason=str(e)`; `get_account_equity→0.0`, `execute_order→False` (fail-closed, logged). `UniversalBroker.place_order` unchanged (1% intercept already handles `equity==0` by halting). `handle_demotion` calls `cancel_order` per known position symbol instead of tag-liquidate stub (positions from `get_positions()`; failures logged, never raised).
- `PaperExecutor` needs NO change (already broker-injected); document `PaperExecutor(broker=CCXTBroker(...))` as the crypto-paper path in `PAPER_BROKER_SETUP.md` appendix.

**A4 — Quarantine `live_crypto_executor.py` (no deletion, no feature work).**
- Mark module docstring `LEGACY-PERP PATH — spot policy is CCXTBroker; do not extend`. Only additive change ever allowed: route its `execute_bybit_order` THROUGH `UniversalBroker.place_order(asset_class="crypto",…)` or delete the file after the spot migration passes gates. No new symbols, no new venues, no leverage change in this study.

**A5 — Keys/ops hygiene (docs + asserts, no live behavior change).**
- `.env.example` gains `CCXT_EXCHANGE_ID="binance"` (allowlist default) + comment `# never commit real keys; sandbox when LIVE_TRADING_ENABLED=False`. No key names added (reuse `BINANCE_*`/`BYBIT_*`).
- `PAPER_BROKER_SETUP.md` appendix: (1) venue allowlist, (2) spot-only policy, (3) sandbox matrix (`live=False→sandbox attempt, fail-soft for reads / fail-closed for orders`), (4) `PaperExecutor(broker=CCXTBroker)` recipe, (5) key-rotation note (env-only, `get_secret_str`, never in `crypto_state.json`/artifacts/logs).
- `requirements.txt`: keep `ccxt==4.5.74` pin; add comment `# OPTIONAL venue adapter — code must `try: import ccxt` + skip-with-reason (tests mock sys.modules)`. Do NOT add `ccxt.pro`/websockets deps.

## 5. Reject (with reason)

1. **Direct exchange trading bypassing `BaseBroker`/`UniversalBroker`/`PaperExecutor`.** New `ccxt.bybit(...)`/`create_market_order` call sites outside `ccxt_broker.py` orphan risk intercept, idempotency, recon, Telegram audit, killswitch. `live_crypto_executor` is the existing violation — quarantine, don't replicate.
2. **Leverage / margin / futures / linear perps as general policy.** `defaultType future/linear`, `set_leverage()`, `reduceOnly` games, funding-rate carry. Violates fail-closed risk mandate (`MAX_RISK_PER_TRADE_PCT`, `MAX_POSITION_SIZE_PCT`, `LEVERAGE_CAP=1.0` asserted in `live_crypto_executor:80`). `reduce_only` param stays accepted-but-ignored-or-Verdade? — decision: REMOVE `reduce_only` from `CCXTBroker.place_order` signature (it implies margined shorts); spot sells are plain `side="sell"`. Paper-only until pre-registered gate change.
3. **WS / `ccxt.pro` live loops (`watch_order_book/watch_ohlcv/watch_orders`).** No strategy consumes streaming depth; reconnect/backpressure/ordering bugs + extra dep for zero edge-gate value. REST snapshots only.
4. **L3 books / full-depth HFT slippage models.** Venue-sparse, high-churn; repo's ATR+bps+volume-cap cost stack (see pybroker study) already covers capacity. `fetch_order_book_snapshot(depth≤50)` informational only.
5. **Auto venue discovery / triangulation / multi-exchange arbitrage.** Allowlist is the control; scanning 100+ venues invites illiquid/unsupported markets + rate-limit bans.
6. **ccxt as hard import.** Every adapter module keeps `try: import ccxt / except ImportError → raise-with-reason`, and `CryptoExecutor` degrades to disabled. Tests MUST pass with `sys.modules['ccxt']=MagicMock()` AND with ccxt uninstalled.
7. **Live keys in repo, logs, state files, or artifacts.** No `apiKey/secret` in `crypto_state.json`, `docs/data/ops/*.json`, logs, or tests (fake keys only). `get_secret_str` at read time; never `print(keys)`.
8. **Single-`cancel_order(order_id)` overload on `BaseBroker`.** Contract is per-symbol fail-closed cancel; adding id-based cancel invites partial-fill confusion. Keep `cancel_all_orders(symbol)` semantics + document.
9. **`fetch_ohlcv` inside promotion gates as authoritative source.** Chain cache + existing backtest CSVs stay authoritative; ccxt-public is last-resort filler so gates stay deterministic/offline-capable.

## 6. Exact diffs proposed (additive; NOT applied — study only)

### Diff 0 — `requirements.txt` (comment only)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 ccxt==4.5.74
+# NOTE(ccxt-adopt 2026-09-09): ccxt is an OPTIONAL venue adapter behind
+# BaseBroker/BaseDataProvider only. All ccxt call sites must `try: import ccxt`
+# and degrade fail-closed when missing (see _deliverables/ccxt-adopt-2026-09-09.md §4-5).
+# Do NOT add ccxt.pro / websocket deps. Pin stays for repro.
```

### Diff 1 — `src/execution/ccxt_broker.py` (harden; ~60 added lines)

```diff
--- a/src/execution/ccxt_broker.py
+++ b/src/execution/ccxt_broker.py
@@
+ALLOWED_EXCHANGES = frozenset({"binance", "bybit", "coinbase"})
+SPOT_ONLY = "spot"
+
+def to_ccxt_symbol(symbol: str) -> str:
+    """BTC-USD / BTCUSDT / BTC/USDT -> BTC/USDT (ccxt spot). Raise ValueError otherwise."""
+    s = (symbol or "").upper().strip().replace("-", "/").replace(":", "/")
+    if "/" in s:
+        base, quote = s.split("/", 1)
+        quote = "USDT" if quote in ("USD", "USDT") else quote
+        return f"{base}/{quote}"
+    if s.endswith("USDT"):
+        return f"{s[:-4]}/USDT"
+    raise ValueError(f"Unrecognized symbol shape: {symbol!r}")
+
 class CCXTBroker(BaseBroker):
-    def __init__(self, exchange_id: str = "binance"):
+    def __init__(self, exchange_id: str = "binance", *, sandbox: bool | None = None):
+        if exchange_id not in ALLOWED_EXCHANGES:
+            raise ConfigurationError(f"exchange_id {exchange_id!r} not in allowlist {sorted(ALLOWED_EXCHANGES)}")
         self.logger = logging.getLogger(__name__)
         self.is_paper = not config.trading.live_trading_enabled
+        if sandbox is not None:
+            self.is_paper = bool(sandbox)
         self.exchange_id = exchange_id
@@
-        self.exchange = exchange_class({
-            'apiKey': self.api_key,
-            'secret': self.secret_key,
-            'enableRateLimit': True,
-            'options': {'defaultType': 'spot'}
-        })
-        if self.is_paper:
-            self.exchange.set_sandbox_mode(True)
+        self.exchange = exchange_class({
+            'apiKey': self.api_key, 'secret': self.secret_key,
+            'enableRateLimit': True, 'options': {'defaultType': SPOT_ONLY}})
+        if self.is_paper:
+            try:
+                self.exchange.set_sandbox_mode(True)
+            except Exception as e:  # sandbox unsupported -> reads may continue, orders stay gated
+                self.logger.warning(f"sandbox mode unavailable on {exchange_id}: {e}")
@@
     def place_order(self, symbol: str, qty: float | None, side: str, order_type: str = 'market', stop_loss_price: float | None = None, reduce_only: bool = False) -> dict:
+        # NOTE: reduce_only deprecated (margin implication) — spot sells are side='sell'. Kept as ignored kwarg one release, then removed.
+        ccxt_symbol = to_ccxt_symbol(symbol)
+        caps = self.get_capabilities()
+        if order_type == 'market' and not caps['supports_market_orders']:
+            raise NotImplementedError(f"{self.exchange_id} does not support market orders")
+        if stop_loss_price is not None and not caps['supports_stop_limit']:
+            raise NotImplementedError(f"{self.exchange_id} does not support stop-limit orders")
+        if qty is None or float(qty) <= 0:
+            raise ValueError("qty must be > 0")
+        try:
+            markets = self.exchange.load_markets()
+            mkt = markets.get(ccxt_symbol, {})
+            floored = float(self.exchange.amount_to_precision(ccxt_symbol, float(qty)))
+            min_amt = (((mkt.get('limits') or {}).get('amount') or {}).get('min')) or 0.0
+            if floored < float(min_amt or 0.0):
+                raise ValueError(f"qty {floored} below venue minimum {min_amt} for {ccxt_symbol}")
+        except (ValueError, NotImplementedError):
+            raise
+        except Exception as e:
+            self.logger.warning(f"market-metadata unavailable, proceeding with raw qty: {e}")
+            floored = float(qty)
-        import ccxt
-        ccxt_side = side.lower()
+        import ccxt  # noqa: E402
+        ccxt_side = side.lower()
@@
-            order = self.exchange.create_order(symbol=symbol, type=order_type, side=ccxt_side, amount=qty, params=params)
+            order = self.exchange.create_order(symbol=ccxt_symbol, type=order_type, side=ccxt_side, amount=floored, params=params)
             return {"status": "success", "order_id": str(order['id']), "status_details": order['status']}
-        except (ccxt.InsufficientFunds, ccxt.InvalidOrder, ccxt.NetworkError, ccxt.ExchangeError) as e:
+        except ccxt.AuthenticationError as e:
+            logger.error(f"CCXT auth failed for {ccxt_symbol}: {e}")
+            raise ConfigurationError(f"venue auth failed for {self.exchange_id}; venue disabled") from e
+        except (ccxt.DDoSProtection, ccxt.RateLimitExceeded, ccxt.RequestTimeout) as e:
+            logger.warning(f"CCXT retryable for {ccxt_symbol}: {e}")
+            return {"status": "failed", "error_message": str(e), "retryable": True}
+        except (ccxt.InsufficientFunds, ccxt.InvalidOrder, ccxt.NetworkError, ccxt.ExchangeError) as e:
             logger.error(f"CCXT Order Placement failed for {symbol}: {e}")
-            return {"status": "failed", "error_message": str(e)}
+            return {"status": "failed", "error_message": str(e), "retryable": False}
```

Plus `cancel_order` docstring (`cancel_all_orders(symbol)` semantics) and `get_capabilities` extension reading `has.get('fetchOHLCV')/has.get('fetchOrderBook')/has.get('createMarketOrder')` into an informational `venue` sub-dict WITHOUT changing the 3 required bool keys (contract test stays green).

### Diff 2 — NEW `src/data/providers/ccxt_public_provider.py` (~90 lines; keyless)

```python
"""Keyless ccxt public-data provider (OHLCV + bounded L2 snapshot). No keys, no WS, fail-soft."""
import logging, time
import pandas as pd
from src.data.providers.base import BaseDataProvider
from src.data.schemas import OHLCVSchema
from src.execution.ccxt_broker import ALLOWED_EXCHANGES, to_ccxt_symbol

logger = logging.getLogger(__name__)

class CCXTPublicProvider(BaseDataProvider):
    def __init__(self, exchange_id: str = "binance"):
        if exchange_id not in ALLOWED_EXCHANGES:
            raise ValueError(f"exchange_id {exchange_id!r} not allowlisted")
        self.exchange_id = exchange_id
        self.exchange = None  # lazy; built without keys

    def _client(self):
        if self.exchange is None:
            try:
                import ccxt
            except ImportError as e:
                raise ImportError("ccxt not installed; CCXTPublicProvider unavailable") from e
            cls = getattr(ccxt, self.exchange_id)
            self.exchange = cls({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
        return self.exchange

    def fetch_ohlcv(self, tickers, start_date, end_date) -> pd.DataFrame:
        out = []
        start_ms = int(pd.to_datetime(start_date).tz_localize("UTC").timestamp() * 1000)
        end_ms = int((pd.to_datetime(end_date).tz_localize("UTC") + pd.Timedelta(days=1)).timestamp() * 1000)
        for ticker in tickers:
            try:
                ex = self._client()
                symbol = to_ccxt_symbol(ticker)
                rows, since = [], start_ms
                while True:  # paginate 1d candles, 1000/page
                    batch = ex.fetch_ohlcv(symbol, timeframe='1d', since=since, limit=1000)
                    if not batch:
                        break
                    rows.extend([r for r in batch if r[0] < end_ms])
                    since = batch[-1][0] + 86400_000
                    if batch[-1][0] >= end_ms or len(batch) < 1000:
                        break
                    time.sleep(ex.rateLimit / 1000.0)
                if not rows:
                    continue
                df = pd.DataFrame(rows, columns=['Ts','Open','High','Low','Close','Volume'])
                df['Ticker'] = ticker
                df['Date'] = pd.to_datetime(df['Ts'], unit='ms')
                df = df[['Ticker','Date','Open','High','Low','Close','Volume']]
                out.append(OHLCVSchema.validate(df))
            except Exception as e:
                logger.warning(f"CCXTPublic {self.exchange_id} skip {ticker}: {e}")
        return pd.concat(out, ignore_index=True) if out else pd.DataFrame()

    def fetch_order_book_snapshot(self, ticker: str, depth: int = 20) -> dict | None:
        """Informational L2 snapshot {mid, spread_bps, bids, asks}. Never for signals. None on any error."""
        try:
            ob = self._client().fetch_order_book(to_ccxt_symbol(ticker), min(max(depth, 5), 50))
            bid, ask = ob['bids'][0][0], ob['asks'][0][0]
            mid = (bid + ask) / 2.0
            return {'mid': mid, 'spread_bps': (ask - bid) / mid * 1e4,
                    'bids': ob['bids'][:depth], 'asks': ob['asks'][:depth]}
        except Exception as e:
            logger.warning(f"L2 snapshot failed for {ticker}: {e}")
            return None

    def fetch_sentiment_feed(self, limit: int) -> pd.DataFrame:
        raise NotImplementedError("CCXTPublicProvider does not provide sentiment feeds.")
```

Wiring (`chain.py`, one line): append `CCXTPublicProvider()` AFTER `YFinanceProvider` in `self.providers`.

### Diff 3 — `src/execution/universal_broker.py` (lazy-disable CryptoExecutor; ~15 lines)

```diff
--- a/src/execution/universal_broker.py
+++ b/src/execution/universal_broker.py
@@
 class CryptoExecutor(BaseExecutor):
     def __init__(self):
-        from src.execution.ccxt_broker import CCXTBroker
-        self.broker = CCXTBroker()
+        try:
+            from src.execution.ccxt_broker import CCXTBroker
+            self.broker = CCXTBroker()
+            self.disabled_reason = ""
+        except Exception as e:  # ImportError/ConfigurationError -> fail-closed disabled venue
+            import logging as _logging
+            _logging.getLogger(__name__).warning(f"[Crypto] venue disabled: {e}")
+            self.broker = None
+            self.disabled_reason = str(e)
     def get_account_equity(self) -> float:
+        if self.broker is None:
+            return 0.0  # trips 1% risk intercept -> order halted
@@
     def execute_order(self, ticker: str, direction: str, quantity: float, price: float | None = None) -> bool:
+        if self.broker is None:
+            import logging as _logging
+            _logging.getLogger(__name__).warning(f"[Crypto] order blocked, venue disabled: {self.disabled_reason}")
+            return False
@@
     def liquidate_strategy_positions(self, strategy_id: str):
-        logger.info(f"[Crypto] Liquidating positions for strategy {strategy_id}")
+        if self.broker is None:
+            return
+        try:
+            for p in self.broker.get_positions():
+                self.broker.cancel_order(p.get('symbol', ''))
+        except Exception as e:
+            logger.warning(f"[Crypto] liquidation best-effort failed: {e}")
```

### Diff 4 — `src/execution/live_crypto_executor.py` (quarantine banner only)

```diff
--- a/src/execution/live_crypto_executor.py
+++ b/src/execution/live_crypto_executor.py
@@
 """
+LEGACY PERP PATH (linear/bybit) — QUARANTINED 2026-09-09 (ccxt-adopt study).
+Spot policy is CCXTBroker behind UniversalBroker. Do NOT add symbols/venues/leverage here.
+Next allowed change only: route execute_bybit_order through UniversalBroker.place_order
+or delete this file after the spot migration passes gates.
 🤖 Live Bybit Perpetual Broker Execution Template ...
```

### Diff 5 — `.env.example` + `PAPER_BROKER_SETUP.md` (docs only)

```diff
--- a/.env.example
+++ b/.env.example
@@
 BINANCE_API_KEY=""
 BINANCE_SECRET_KEY=""
+# CCXT venue adapter (optional; allowlist: binance | bybit | coinbase; spot-only)
+# Leave keys empty for paper/sandbox + public-data-only mode. Never commit real keys.
+CCXT_EXCHANGE_ID="binance"
 TELEGRAM_BOT_TOKEN=""
```

`PAPER_BROKER_SETUP.md` appendix (new section): allowlist table, spot-only rule, sandbox matrix, `PaperExecutor(broker=CCXTBroker())` recipe, key-hygiene checklist (env-only, `get_secret_str`, never in state/artifacts/logs, fake keys in tests).

## 7. Test plan (mocked ccxt, zero network, serial per SWARM config)

New `tests/execution/test_ccxt_adopt.py` — every test constructs its own `FakeExchange`/patched `sys.modules['ccxt']`; NO sockets, NO keys, NO sleeps (patch `time.sleep`):

1. `test_allowlist_rejects_unknown_venue` — `CCXTBroker(exchange_id="fakeswap")` raises `ConfigurationError`; `CCXTPublicProvider("fakeswap")` raises `ValueError`.
2. `test_symbol_normalization` — `to_ccxt_symbol("BTC-USD")=="BTC/USDT"`, `"BTCUSDT"→"BTC/USDT"`, `"ETH/USD"→"ETH/USDT"`; garbage (`"BTC"`, `""`) raises `ValueError`.
3. `test_keyless_public_ohlcv_uses_pagination_no_keys` — `FakeExchange.fetch_ohlcv` returns 2 pages `[[ts,o,h,l,c,v],…]`; assert combined frame validates `OHLCVSchema`, exchange built WITHOUT `apiKey` in ctor kwargs, `fetch_ohlcv` called with `timeframe='1d'`; per-ticker exception → skipped, other ticker still returned.
4. `test_place_order_capability_gate` — `has={'createMarketOrder':False}` + `order_type='market'` raises `NotImplementedError` and `create_order` NOT called; `stop_loss_price` without `stopLimit` raises `NotImplementedError`.
5. `test_place_order_minimum_and_precision` — `load_markets→{limits:{amount:{min:0.001}}}`, `amount_to_precision→rounded`; qty below min raises `ValueError`; happy path asserts `create_order(symbol='BTC/USDT', amount=floored)`; `qty<=0/None` raises `ValueError`.
6. `test_exception_mapping` — `create_order` raising `InsufficientFunds` → `{"status":"failed","retryable":False}`; `RateLimitExceeded/DDoSProtection/RequestTimeout` → `retryable:True`; `AuthenticationError` → raises `ConfigurationError`; `NetworkError` → `failed/retryable False`, never propagates.
7. `test_crypto_executor_disabled_without_keys` — patch `CCXTBroker.__init__` to raise `ConfigurationError("no keys")`; `CryptoExecutor().execute_order→False`, `get_account_equity→0.0`; `UniversalBroker.place_order("crypto",…,risk_amount>0)` returns `False` (1% intercept on zero equity) with no network.
8. `test_order_book_snapshot_bounded_and_fail_soft` — `fetch_order_book` returns 100-deep book; snapshot truncates to `depth`, `spread_bps` hand-computed; raising book → `None`, never raises.
9. `test_no_live_keys_in_repo` — scan adapter + new provider + tests for `apiKey` literal leakage: assert no test contains a non-`fake_*` key string and `crypto_state.json`/`docs/data/ops/*.json` untouched (path-existence guard); `get_secret_str` used at every key-read site (`grep`-equivalent assertion on file text).
10. `test_chain_wiring_last_resort` — `DataProviderChain` with stubbed providers `[empty, empty, empty, FakeCCXTPublic(df)]` returns ccxt frame; all-empty → empty DataFrame (never raises); cache-first path preserved.

Existing suites to re-run (one file at a time, serial):

```
PYTHONPATH=. pytest tests/execution/test_ccxt_adopt.py -q
PYTHONPATH=. pytest tests/brokers/test_broker_capability.py -q
PYTHONPATH=. pytest tests/execution/test_live_crypto_executor_caps.py -q
PYTHONPATH=. pytest tests/test_crypto_executor_caps.py -q
PYTHONPATH=. pytest tests/brokers/test_brokers.py -q
```

Acceptance: 10/10 new pass with ccxt installed AND with `ccxt` import-blocked (`sys.modules['ccxt']=None` → keyless-public tests skip-with-reason, broker tests assert disabled-venue path); legacy capability/crypto suites green; `ruff check` + `bandit -r src/execution/ccxt_broker.py src/data/providers/ccxt_public_provider.py` clean; `git status --porcelain` shows ONLY the adapter/provider/universal-broker diffs + new test + this report — `evolve_real.py`, `strategies/registry.json`, `strategies/` clean.

## 8. Rollout (for implementer, not done here)

1. Land Diff 1+tests 1,2,4,5,6 → spot broker hardened, keys still required for private ops.
2. Land Diff 2+tests 3,8,10 → keyless OHLCV filler live behind cache+chain; monitor `rateLimit` logs one cycle.
3. Land Diff 3+test 7 → keyless installs degrade to disabled-crypto instead of import crash.
4. Land Diff 4+5 → quarantine banner + docs; schedule perp-path deletion review after one clean spot-paper cycle.
5. Never promote: futures/leverage, `ccxt.pro`, L3, auto-discovery, hard ccxt import — each needs its own pre-registered gate change + this report's Reject §5 sign-off.

## 9. References

- Actuals: `src/execution/{base_broker.py:1-44,alpaca_broker.py:1-98,ccxt_broker.py:1-124,universal_broker.py:1-162,live_crypto_executor.py:1-444,paper_executor.py:1-219,execution_adapter.py:1-104}` + `src/data/{base_provider.py:1-9,schemas.py:1-59,providers/base.py:1-13,providers/chain.py:1-104,providers/alpaca_data_provider.py:1-110,providers/binance_public_provider.py:1-82,providers/yfinance_provider.py:1-131}` + `src/utils/config.py:1-108` + `.env.example:1-16` + `requirements.txt:168`.
- Tests: `tests/brokers/test_broker_capability.py:1-101`, `tests/brokers/test_brokers.py:1-16`, `tests/execution/test_live_crypto_executor_caps.py:1-168`, `tests/test_crypto_executor_caps.py:1-196`.
- Sibling study format: `_deliverables/pybroker-adopt-2026-09-09.md` (overlap table + additive diffs + serial test plan convention followed here).
- Upstream: `ccxt/ccxt` unified API (`fetch_balance/fetch_ohlcv/fetch_order_book/fetch_ticker/fetch_positions/create_order/cancel_all_orders/set_sandbox_mode/load_markets/amount_to_precision`), `exchange.has` map, exception hierarchy (`AuthenticationError/ExchangeError/InsufficientFunds/InvalidOrder/NetworkError/DDoSProtection/RateLimitExceeded/RequestTimeout`), `enableRateLimit`, `options.defaultType`.
