# Paper-Duel Recon 001 — First Paper-Loop Try (recon skeleton)

> **Run:** 2026-08-12 · **Agent:** OpenCode (nap session) · **Repo copy:**
> `WSB-Alpha-System-latest` · **Goal:** locate the paper path, dry-run it,
> and stand up the `paper-duel` recon log that a real paper loop will fill.
> **Constraint:** paper only — no real orders, `LIVE_TRADING_ENABLED=False`.

## 1. Paper path (located)

| Stage | Path | Notes |
|---|---|---|
| Config | `config/settings.yaml` → `environment: 'development'` | No live flag set |
| Risk rails | `src/risk/position_sizing.py` | `LIVE_TRADING_ENABLED=False`, 1% risk/trade, 4 max positions, breakers 5/10/15% |
| Execution gate | `src/execution/execution_bridge.py` → `execute_signal` | Broker + PositionSizer + CircuitBreaker |
| Paper broker | `PAPER_BROKER_SETUP.md` | paperbroker service at `http://localhost:5000`, `PAPERBROKER_API_KEY` |
| CI paper loop | `.github/workflows/paper_trade.yml` | cron `55 20 * * 1-5`, `python -m src.execution.live_alpaca_executor --mode technical`, uses GitHub secrets `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` |
| Offline tests | `tests/risk`, `tests/paper_trading`, `tests/brokers` | Risk rails test suite |

## 2. Dry-run evidence (offline, 2026-08-12)

- Real-API leg **BLOCKED**: no `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` in workspace
  root `.env` (only `JULES_API_KEY`) nor any repo `.env` (only `.env.example`);
  paper workflow depends on GitHub secrets.
- Local run of `live_alpaca_executor.py` would default to the **LIVE** endpoint
  (`https://api.alpaca.markets`) with mock-key fallback — **must not run**.
- **Offline dry pass (executed):**
  `python -m pytest tests/risk tests/paper_trading tests/brokers -q --no-header -x -p no:cacheprovider`
  (python = `C:\Users\DELL\anaconda3\python.exe`, 3.13.5)
  → **19 passed in 20.16s**.

## 3. Recon schema (columns) — one row per paper order/signal cycle

```jsonc
// run-logs/paper-duel-recon-001.md rows (append as paper loops run):
{
  "seq": 1,
  "ts_utc": "2026-08-12T00:00:00Z",     // signal emit time
  "strategy_id": "strat_XXXX",
  "symbol": "SPY",                        // or crypto CCXT pair
  "side": "BUY",                          // BUY / SELL
  "signal": {"source": "...", "conf": 0.9},
  "pre_trade_checks": {                   // must all pass before order
    "circuit_breaker": "PASS",            // daily/weekly/total + regime
    "position_cap": "PASS",               // <= MAX_CONCURRENT_POSITIONS
    "risk_per_trade": "PASS",             // <= MAX_RISK_PER_TRADE_PCT
    "broker_capability": "PASS"           // check_order_allowed() gate
  },
  "order": {
    "venue_order_id": "..." ,
    "status": "SUBMITTED",
    "fill_events": []                     // paper fill acknowledgement(s)
  },
  "reconcile": {                          // Nautilus-style startup/runtime checks
    "order_status_report": "MATCH",
    "fill_report": "MATCH",
    "position_report": "MATCH",
    "pnl_integrity": "OK"
  },
  "outcome": "PENDING",                   // PENDING / FILLED / REJECTED / HALTED
  "notes": ""
}
```

### Filled example (illustrative — mirrors offline test data, not a real order)

```jsonc
{
  "seq": 0,
  "ts_utc": "2026-08-12T00:00:00Z",
  "strategy_id": "strat_0000",
  "symbol": "SPY",
  "side": "BUY",
  "signal": {"source": "sandbox-backtest-tool", "conf": 0.9},
  "pre_trade_checks": {
    "circuit_breaker": "PASS",
    "position_cap": "PASS",
    "risk_per_trade": "PASS",
    "broker_capability": "PASS"
  },
  "order": {"venue_order_id": "paper-0001", "status": "SUBMITTED", "fill_events": []},
  "reconcile": {"order_status_report": "MATCH", "fill_report": "MATCH",
                "position_report": "MATCH", "pnl_integrity": "OK"},
  "outcome": "PENDING",
  "notes": "Illustrative seed row — real paper rows start once broker keys are wired."
}
```

## 4. Evidence links

- Offline dry pass output: 19 passed in 20.16s (risk/paper_trading/brokers).
- Blocked-keys evidence: `.env` (root) contains only `JULES_API_KEY`; repo
  `.env.example` shows expected vars; `PAPER_BROKER_SETUP.md` documents the
  paperbroker service.
- Existing trials log for schema lineage: `run-logs/trials.jsonl`.

## 5. Next steps to unblock real paper loop

1. Add Alpaca paper keys to GitHub secrets (or local `.env` with paper
   endpoint) — then the cron paper loop + reconciliation rows can run.
2. Point `live_alpaca_executor.py` at the **paper** base URL explicitly
   (`https://paper-api.alpaca.markets`) so a local run is never live.
3. Backfill this file with real `seq` rows after each paper cycle.
