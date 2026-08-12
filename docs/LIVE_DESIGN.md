# LIVE_DESIGN.md — WSB-Alpha-System Live Execution Design

> **Status:** draft — consolidated from research run 2026-08-12 (vault
> `oss-live-design-reference.md`, four questions: multi-broker abstraction,
> capital floor, approval gates + paper→live reconciliation, hedges).
> Research PR #116 (recon skeleton) is the paper-loop evidence trail; this
> file folds the OSS findings into a design. No code changes in this PR.

---

## 1. Broker seam = small interface + capability flags

Copy LEAN's `IBrokerage` shape (~10 methods: `GetOpenOrders /
GetAccountHoldings / GetCashBalance / PlaceOrder / UpdateOrder / CancelOrder /
Connect / Disconnect / GetHistory` + order/account events; `IBrokerageFactory`
+ `ISymbolMapper`) — **not** a shared mega-class.

- Add a `capabilities` map (`supports_market_orders`, `supports_stop_limit`,
  `supports_paper`) checked before **every** order type, mirroring freqtrade's
  `exchange_has`/`_ft_has`.
- Keep one ABC + per-broker adapters (`AlpacaBroker`, `CCXTBroker`,
  `PaperBroker`), each mapping venue order IDs → internal canonical state.
  Hummingbot's `ConnectorBase` + `InFlightOrder` per-venue class is the model
  for crypto (140+ venues via CCXT).
- Our `BaseBroker` + `BaseExecutor` (`universal_broker.py`) already match the
  shape — add capability flags and canonical order-ID mapping.

## 2. Close the order-gate audit gap

`docs/OPENCODE_PARALLEL_AUDIT.md` flags that no `check_order_allowed()`
exists at `alpaca_broker.py:82` / `ccxt_broker.py:88`. Make the gate a
**must-run inside the broker**, not in the strategy (LEAN risk models are the
plug-in reference).

## 3. Drawdown halt in a dedicated risk object

freqtrade's `MaxDrawdown` protection is the closest OSS match: computes
equity peak-to-trough, halts new entries, releases after `stop_duration_candles`
(`unlock_at`). Our `CircuitBreaker` (`src/risk/circuit_breakers.py`) already has
the thresholds (5%/10%/15%, regime-scaled, fail-closed) — wire it into the
broker entry gate so every order path passes it.

**Highest-leverage fix:** `MAX_DRAWDOWN_CIRCUIT_BREAKER_PCT=0.15`
(`src/risk/position_sizing.py`) is defined but never enforced.

## 4. Paper→live parity via explicit reconciliation

NautilusTrader's execution reconciliation is the gold standard: on startup
fetch venue mass status via `generate_order_status_reports` /
`generate_fill_reports` / `generate_position_status_reports`, dedupe, align
order state, synthesize missing fills, compare net position per instrument.
Only the **live** engine reconciles — backtest controls both sides.

Mirror the three-report startup reconciliation plus in-flight timeout rules
(`SUBMITTED→REJECTED`, `PENDING_UPDATE→CANCELED`, `PENDING_CANCEL→CANCELED`).

The paper-loop recon schema in `run-logs/paper-duel-recon-001.md` implements
this per cycle (orders/fills/positions + PnL deltas).

## 5. Approval gate = paper→live handoff on evidence

GeneTrader precedent (manual promotion after OOS gate) + our Monte-Carlo
permutation p-value floor. **No auto-promote.**

## 6. Hedges — v1 scope: one equity overlay + one crypto lever

- **Equities:** index **puts** for tail protection (SPX/SPY protective put,
  premium ~2–5% of portfolio; roll; buy when VIX low). Inverse ETFs
  (SH/SDS/SPXU) are a **tactical short-term** substitute only — daily
  rebalancing tracking decay; not a long-term short.
- **Crypto:** per-exchange hedge via **perp/short on the same venue**
  (Hummingbot `Hedge` strategy / spot-perpetual arb) rather than cross-exchange
  transfers (slow, costly, single-leg failure risk).
- Pairs/market-neutral (cointegration) is a strategy family, not a hedge
  overlay — defer.

## 7. Execution-safety note

`live_alpaca_executor.py` forces `https://paper-api.alpaca.markets` whenever
`LIVE_TRADING_ENABLED=False` (the default) — confirmed 2026-08-12, no code
change required. Keep `LIVE_TRADING_ENABLED` gated and default-off.

## 8. Dead-ends to skip

zenbot/Gekko (archived), Backtrader/Zipline (backtest-only, maintenance
mode), Blankly (thin; venue quirks leak — re-verify fills per venue if
adopted).

---

## Provenance

- Research: vault `02-Research/Findings/OpenSource-Trading-Tools/oss-live-design-reference.md`
  (all sources accessed 2026-08-12; LEAN IBrokerage docs, freqtrade
  protections, NautilusTrader integration docs + discussions, Hummingbot
  connector architecture).
- Reference projects: QuantConnect LEAN, nautechsystems/nautilus_trader,
  freqtrade, hummingbot, blankly-finance/blankly.