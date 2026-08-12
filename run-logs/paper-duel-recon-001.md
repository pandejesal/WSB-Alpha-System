# Paper-Duel Recon 001 — First Paper-Loop Try (recon skeleton)

> **Run:** 2026-08-12 · **Agent:** OpenCode (nap session) · **Repo copy:**
> `WSB-Alpha-System-latest` · **Goal:** locate the paper path, verify it
> end-to-end, and stand up the `paper-duel` recon log that real paper cycles
> fill. **Constraint:** paper only — no real orders,
> `LIVE_TRADING_ENABLED=False`.

## 1. Paper path (located)

| Stage | Path | Notes |
|---|---|---|
| Config | `config/settings.yaml` → `environment: 'development'` | No live flag set |
| Risk rails | `src/risk/position_sizing.py` | `LIVE_TRADING_ENABLED=False`, 1% risk/trade, 4 max positions, breakers 5/10/15% |
| Execution gate | `src/execution/execution_bridge.py` → `execute_signal` | Broker + PositionSizer + CircuitBreaker |
| Paper broker | `PAPER_BROKER_SETUP.md` | paperbroker service at `http://localhost:5000`, `PAPERBROKER_API_KEY` |
| CI paper loop | `.github/workflows/paper_trade.yml` | cron `55 20 * * 1-5` UTC, `python -m src.execution.live_alpaca_executor --mode technical`, uses GitHub secrets `ALPACA_API_KEY`/`ALPACA_SECRET_KEY`; also `sandbox.yml` (same cron) |
| Offline tests | `tests/risk`, `tests/paper_trading`, `tests/brokers` | Risk rails test suite |

## 2. Evidence — the CI paper loop is LIVE and healthy (2026-08-11 run)

**Keys confirmed present as GitHub secrets** (`gh secret list`): `ALPACA_API_KEY`
(set 2026-08-03), `ALPACA_SECRET_KEY` (set 2026-08-03). The paper workflow runs
**on schedule from `main` and succeeds** — 21 total runs, last several green
(e.g. run `31538251005`, 2026-08-11, 1m29s; scheduled + `workflow_dispatch`).

Executor output (run `31538251005`, 2026-08-11, paper endpoint):

```
ALPACA AUTOMATED LIVE/PAPER ORDER EXECUTOR
[*] Account Equity: $100,000.00
[*] Open Positions: 0
[*] No active signals found for today. Cash preserved.
```

- The executor **forces the paper endpoint**: `live_alpaca_executor.py` sets
  `ALPACA_BASE_URL = "https://paper-api.alpaca.markets"` whenever
  `LIVE_TRADING_ENABLED=False` (the default) — confirmed at line 79-83. A
  local run without keys is therefore safe-by-default, but still not run here
  (no local keys; CI owns the loop).
- Same-run upstream warning: `YFRateLimitError('Too Many Requests')` when
  fetching the S&P-500 constituent list (yfinance), yet the executor continued
  and completed with "Cash preserved" — the equity data path degrades
  gracefully but loses universe freshness that day.
- The run's dashboard step (`Save portfolio data for dashboard`) writes
  `docs/data/*.json` and commits `chore: update dashboard data from paper
  trading` to `main` (verified commit `c486383`).

**Local note:** no `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` in the workspace root
`.env` (only `JULES_API_KEY`) or any repo `.env` (only `.env.example`). The
paper loop is owned by CI, not by this machine.

### Offline dry pass (executed 2026-08-12)

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
  "notes": "Illustrative seed row — the live CI paper cycle on main (cron) starts appending real rows."
}
```

## 4. Evidence links

- CI paper run evidence: `gh run view 31538251005 --log`
  (`workflow: paper_trade.yml`, `main`, 2026-08-11, success 1m29s).
- Secrets: `gh secret list` — `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` present.
- Endpoint safety: `src/execution/live_alpaca_executor.py:79-83` forces the
  paper base URL when `LIVE_TRADING_ENABLED=False`.
- Offline dry pass output: 19 passed in 20.16s (risk/paper_trading/brokers).
- Existing trials log for schema lineage: `run-logs/trials.jsonl`.

## 5. Next steps for the paper-duel loop

1. Backfill this file with real `seq` rows **after each CI paper cycle**
   (cron currently fires weekdays 20:55 UTC; reconcile against the run log +
   committed `docs/data/*.json`).
2. Optional: mitigate the yfinance `YFRateLimitError` seen 2026-08-11 (universe
   cache/retry/backoff) so the paper loop uses a fresh S&P-500 universe every
   day.
3. Decide whether to also consume the `Daily Paper Trading` dashboard snapshot
   (`docs/data/trade_history.json`, `portfolio.json`) as part of the
   reconciliation schema.
