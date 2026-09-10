# LIVE-GATE REVIEW CHECKLIST (human go/no-go only)

Doc-only gate. No code change. A human reviewer must check every box before
any live promotion. Any unchecked box = NO-GO. References: D3-infra-safety.md
gaps G-2 (CI collect-only gate) and G-6 (circuit breakers), P2-infra-safety-plan.md.

- [ ] KillSwitch is ON (`off` = halt_new_orders; `can_trade()` false; missing/invalid/extra-keys state fails closed per `src/ops/killswitch.py:23-78`; dual conjunctive gate `can_trade() AND LIVE_TRADING_ENABLED` per `src/ops/killswitch.py:81-97`)
- [ ] Circuit breakers OFF only by explicit user order (2026-08-21 `CIRCUIT_BREAKER_ENABLED=False` in `src/risk/position_sizing.py`; deliberate, not a bug — re-affirmation recorded here, never auto-enabled by code)
- [ ] 30-day paper history reviewed (paper executor runs, ops heartbeats, reconciliation artifacts in `docs/data/ops/`)
- [ ] Cost fix applied and sane (B4a: 2-3bp retail commission floor in `_tiered_cost_bps`, BTC tier 15-25bps everywhere incl. rotation, GATESPEC header reflects tiered 5-26bps + commission)
- [ ] WF + DSR + union gate passed (walk-forward optimization, Deflated Sharpe Ratio, union gate per `docs/HUNT_PROTOCOL.md` edge-gate path)
- [ ] Prereg enforcement active (frozen spec -> evaluation JSON -> verdict; no unregistered strategy promoted to `strategies/registry.json`)
- [ ] Registry lock verified (cross-OS `filelock` + tmp + `os.replace` + validation on all writers per `evolve_real.py:772-803`; no manual unclocked edits pending)

Verdict: GO (all checked + reviewer name/date) / NO-GO (any unchecked, state which).
