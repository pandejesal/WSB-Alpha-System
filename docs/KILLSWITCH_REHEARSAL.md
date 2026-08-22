# Kill Switch Rehearsal — 2026-08-22 (Task 5.2)

## Result: PASS

Executed `python scripts/kill_switch_rehearsal.py` against the live paper config
(`config/ops_state.yaml`). Artifact: `docs/data/ops/kill_switch_rehearsal.json`.

```json
{
  "timestamp": "2026-08-22T20:11:59.175108Z",
  "dry_run": false,
  "original_state": "halt_new_orders",
  "tier2_tested": true,
  "tier3_tested": true,
  "restored": true
}
```

## What was exercised

| Tier | Mechanism | Test | Verified |
|------|-----------|------|----------|
| 2 | Repo edit of `config/ops_state.yaml` → `halt_new_orders` | `KillSwitch.set_state` round-trip | yes |
| 3 | Manual dispatch / Telegram `/flat` override → `flat` | `KillSwitch.set_state("flat")` read-back | yes |
| restore | State returned to pre-rehearsal value | `get_state() == original` | yes |

## Enforcement chain (verified by inspection)

- **Fail-closed default:** missing/unparseable/invalid state file ⇒ `halt_new_orders`
  (`src/ops/killswitch.py:22-38`). Never auto-flats.
- **Consumers:** `src/ops/gate_evaluator.py`, `src/ops/risk.py`,
  `src/execution/live_alpaca_executor.py` gate order flow on
  `KillSwitch.get_state()`; new orders only when state == `off`.
- **Watch loop:** `.github/workflows/ops_watch.yml` runs weekdays 12:00 UTC →
  `src/ops/watch.py` (Telegram `/kill` `/halt` `/flat` polling → state change +
  `send_alert`) and `src/ops/heartbeat.py --job ops_watch`.
- **Alerts:** `src/ops/alerts.py` (Telegram) wired into watch/daily/gate paths;
  killswitch.py logs alert on every state change.
- **Heartbeat:** `src/ops/heartbeat.py` writes per-job heartbeats consumed by
  ops_gate.yml freshness checks.

## Notes

- Original operational state is intentionally `halt_new_orders` until Phase 6
  paper verdicts justify `off`.
- The rehearsal mutates `config/ops_state.yaml` transiently and restores it;
  no orders were placed (paper account untouched).
