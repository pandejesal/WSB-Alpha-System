# Hunt Factory Template — New Strategy Family Onboarding

> **Purpose**: Standardize the onboarding of new strategy families into the WSB Alpha registry. Every new family must pass through this template before entering `strategies/registry.json`.

---

## 1. Pre-Conditions (Gate 0)

- [ ] `LIVE_TRADING_ENABLED=false` in `config/settings.yaml`
- [ ] Registry backup exists: `python scripts/backup_registry.py`
- [ ] No active live promotions in flight
- [ ] `REGISTRY_PROMOTION_GATES.md` reviewed and understood

---

## 2. Session Brief

### 2.1 Strategy Family Identity

| Field | Value |
|-------|-------|
| **Family Name** | `[e.g. momentum_breadth, event_driven, pair_stat_arb]` |
| **Category** | `[trend / mean_reversion / event / alternative]` |
| **Universe** | `[e.g. SP500, NASDAQ100, sector_ETFs, crypto_BTCETH]` |
| **Timeframe** | `[e.g. daily, hourly, 5min]` |
| **Entry Logic** | `[one-liner describing signal]` |
| **Exit Logic** | `[one-liner describing exit]` |
| **Position Sizing** | `[equal_weight / risk_parity / vol_target]` |

### 2.2 Hypothesis

> *What edge does this family exploit? Why should it work now?*

```
[Describe the market inefficiency, behavioral bias, or structural alpha source]
```

### 2.3 Known Risks

- [Risk 1: e.g. overcrowding in momentum during late-cycle]
- [Risk 2: e.g. transaction cost erosion on low-liquidity names]
- [Risk 3: e.g. regime sensitivity — underperforms in range-bound markets]

---

## 3. Deliverables Checklist

| # | Deliverable | Status | Notes |
|---|-------------|--------|-------|
| 1 | `strategies/<family_name>.yaml` | [ ] | Must pass `validate_strategy_yaml()` |
| 2 | Entry in `strategies/registry.json` | [ ] | Schema-compliant, no dead fields |
| 3 | Backtest results (min 5yr or 200 trades) | [ ] | Stored in `results/<family_name>/` |
| 4 | Evolve-loop integration | [ ] | `evolve_real.py` can read parameters |
| 5 | Kill-switch test | [ ] | `LIVE_TRADING_ENABLED=true` blocks execution |

---

## 4. Phase Flow (from HUNT_PROTOCOL.md)

### Phase 1: Freeze

- Lock universe to one asset or instrument
- Set simulation mode: `simulation_mode: true`
- Define parameter grid (min/max/step for each param)
- Set `max_evals` (default: 100 for initial sweep)

### Phase 2: Evaluate

- Run `evolve_real.py` in simulation mode
- Record: Sharpe, CAGR, max drawdown, DSR, minerva score
- Flag any parameter sets with:
  - Sharpe > 2.0 (likely overfit)
  - Max DD > 25% (excessive risk)
  - DSR < 0.5 (poor risk-adjusted returns)
  - Trade count < 50 (insufficient sample)

### Phase 3: Verdict

- **PASS**: Sharpe ≥ 0.7, DD ≤ 20%, trades ≥ 100, no dead fields
- **REJECT**: Sharpe < 0.5 OR DD > 25% OR trades < 50
- **CONDITIONAL**: Fix issues and re-run (max 2 cycles)
- **HOLD**: Insufficient data; collect more history

### Phase 4: Write (Registry)

- Run: `python scripts/register_strategy.py --family <name> --status PASS_ALL_GATES`
- Verify: `strategies/registry.json` entry exists and passes schema validation
- Confirm: `status: "PASS_ALL_GATES"`, `verdict: "APPROVED"`

---

## 5. Acceptance Criteria (Must ALL Pass)

- [ ] Strategy family not already in registry (dedupe check)
- [ ] All 5 gates pass (Sharpe ≥ 0.7, DD ≤ 20%, DSR computed, etc.)
- [ ] Registry entry has no dead fields (`tracks_cleared` removed or N/A)
- [ ] `evolve_real.py` can read and update parameters
- [ ] Kill-switch blocks execution when `LIVE_TRADING_ENABLED=true`
- [ ] `validate_strategy_yaml()` returns clean (no errors)
- [ ] Paper mode confirmed: no live orders possible

---

## 6. Kill Criteria (Auto-Reject)

- [ ] Overfitting detected: Sharpe > 2.5 with < 100 trades
- [ ] Survivorship bias: universe contains only currently listed stocks
- [ ] Look-ahead bias: signals use future data in backtest
- [ ] Transaction costs ignored (must model slippage + commissions)
- [ ] Family already exists in registry with same parameters (dupe)
- [ ] DSR not computed or missing
- [ ] Any live trading paths enabled

---

## 7. Registry Wiring

### 7.1 YAML Template

```yaml
family: "[family_name]"
category: "[trend|mean_reversion|event|alternative]"
status: "NOT_EVALUATED"
universe: "[universe]"
timeframe: "[timeframe]"
entry_logic: "[description]"
exit_logic: "[description]"
position_sizing: "[method]"
params:
  param_1: [value]
  param_2: [value]
backtest:
  sharpe: [computed]
  cagr: [computed]
  max_dd: [computed]
  dsr: [computed]
  trades: [count]
  period: "[start] to [end]"
evolve:
  enabled: true
  real_evolution: true
gates_passed: "0/5"
verdict: "PENDING"
created_by: "[hunt_session_id]"
created_at: "[ISO timestamp]"
```

### 7.2 Registry Entry Fields

```json
{
  "family": "[family_name]",
  "status": "NOT_EVALUATED",
  "verdict": "PENDING",
  "gates_passed": "0/5",
  "sharpe": [value],
  "cagr": [value],
  "max_dd": [value],
  "dsr": [value],
  "trades": [count],
  "category": "[trend|mean_reversion|event|alternative]",
  "universe": "[universe]",
  "timeframe": "[timeframe]",
  "params": {},
  "created_at": "[ISO timestamp]",
  "updated_at": "[ISO timestamp]"
}
```

### 7.3 Registration Commands

```bash
# Step 1: Validate YAML
python scripts/validate_strategy.py strategies/<family_name>.yaml

# Step 2: Register
python scripts/register_strategy.py --family <family_name> --status NOT_EVALUATED

# Step 3: Verify
python scripts/verify_registry.py --check-schema --check-dupes

# Step 4: Confirm paper mode
grep -E "LIVE_TRADING_ENABLED|PAPER_MODE" config/settings.yaml
```

---

## 8. Post-Onboarding

- [ ] Add to `docs/HUNT_PROTOCOL.md` under "Active Hunts"
- [ ] Update `evolution-lessons.json` with learnings
- [ ] Schedule evolve-loop review (weekly for first month)
- [ ] Set reminder: 30-day performance check

---

## 9. Example: Completing This Template

```
## Session Brief

| Field | Value |
|-------|-------|
| Family Name | momentum_breadth |
| Category | trend |
| Universe | SP500 |
| Timeframe | daily |
| Entry Logic | RSI(14) < 30 + breadth > 0.6 |
| Exit Logic | RSI(14) > 70 or trailing stop 5% |
| Position Sizing | equal_weight |

## Hypothesis

> Market breadth confirms RSI oversold signals, reducing false positives in mean-reversion entries.

## Risks
- Late-cycle breadth can stay depressed for extended periods
- Transaction costs on 500 stocks daily
- Sector concentration in technology

## Deliverables
- [x] strategies/momentum_breadth.yaml
- [x] Registry entry (family: momentum_breadth)
- [x] Backtest: Sharpe 1.1, DD 12%, 250 trades, 10yr
- [x] evolve_real.py integration confirmed
- [x] Kill-switch test passed

## Verdict
PASS — all acceptance criteria met, all kill criteria cleared.
```

---

*Template version: 1.0 | Created: 2026-09-08 | By: SUB3 FLAW-F*
