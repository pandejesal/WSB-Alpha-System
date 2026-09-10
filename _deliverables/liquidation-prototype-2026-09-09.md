# Liquidation-Cascade Circuit Breaker — Prototype Study (2026-09-09)

> STUDY ONLY. No code was modified. Forbidden paths untouched:
> `evolve_real.py`, `registry.json`, `strategies/` — none read for edit, none written.
> Workdir: repo root. Grounding files actually read:
> `src/risk/circuit_breakers.py` (76 lines, equity-drawdown-only),
> `src/risk/volatility_forecast.py` (graph corr + propagate + regime),
> `src/risk/crash_risk.py` (option-implied, compute-only),
> `src/execution/live_crypto_executor.py` (`gates_allow_trading`, `TARGET_RISK/HALF_KELLY/LEVERAGE_CAP`),
> `src/execution/execution_bridge.py` (`execute_signal` → breaker → sizer → broker),
> `src/execution/paper_executor.py` (idempotent plan executor), `config/risk_config.py` (canonical caps).

## 1. Research grounding (Guyon et al. stylised facts)

| Fact | Prototype use | Source mapping |
|---|---|---|
| ~88% of forced selling lands in first 30 min | 30-min post-cascade execution cooldown (new entries blocked, closes/flattens allowed) | New state in breaker; enforced in `ExecutionBridge.execute_signal` + `live_crypto_executor.gates_allow_trading` |
| OI contraction 25–70% marks cascade | OI-proxy trigger (no live OI feed today → volume-shock + neg-return + vol-regime proxy; Bybit `fetchOpenInterest` wired as Phase-2 input) | New `src/risk/liquidation_cascade.py` |
| Cross-asset coupling surge (correlations → 1) | Coupling-sigma trigger: mean \|off-diag corr\| z-scored vs rolling baseline, trip at ≥ 2σ | Reuses `volatility_forecast.build_correlation_graph` adjacency |

Why this fits this repo: current `CircuitBreaker` reacts **after** our equity drops (5%/10%/15% daily/weekly/total, regime-scaled). A liquidation cascade is **exogenous** — BTC/ETH/SOL dump together on forced selling while our equity feed lags one poll. Coupling-sigma + OI-proxy trips **before** the daily-limit halt, scaling leverage down instead of binary halt.

## 2. Architecture (new module + two gate insertions, one config extension)

New file (proposed): `src/risk/liquidation_cascade.py` — pure/numpy, fail-closed, no broker/network.
Gates: (a) `ExecutionBridge.execute_signal` — cooldown + leverage-scale check first;
(b) `live_crypto_executor.gates_allow_trading` — same for Bybit perps path.
Config: `config/risk_config.py` — 6 new constants (below). `crash_risk_gate` left untouched
(equities options signal; cascade module is the crypto-perps analogue).

```python
# src/risk/liquidation_cascade.py (prototype sketch, ~120 lines)
from __future__ import annotations
import time
import numpy as np

COUPLING_SIGMA_TRIP = 2.0
COOLDOWN_SEC = 30 * 60
LEVERAGE_SCALE_TRIPPED = 0.0   # new entries blocked during cooldown
LEVERAGE_SCALE_ELEVATED = 0.5  # 1-2σ: halve risk, cap lev 0.5x

class LiquidationCascadeBreaker:
    def __init__(self, baseline_mean=0.35, baseline_std=0.10):
        self.baseline_mean = baseline_mean
        self.baseline_std = baseline_std
        self.tripped_at: float | None = None
    def coupling_sigma(self, returns: np.ndarray) -> float:
        from src.risk.volatility_forecast import build_correlation_graph
        adj = build_correlation_graph(returns)  # fail-closed ValueError propagates
        n = adj.shape[0]
        iu = np.triu_indices(n, k=1)
        vals = np.abs(adj[iu]) if iu[0].size else np.array([0.0])
        m = float(np.mean(vals))
        return (m - self.baseline_mean) / max(self.baseline_std, 1e-9)
    def oi_proxy_shock(self, ret_30m: float, vol_ratio_30m: float) -> bool:
        # No OI feed today: cascade proxy = sharp neg return + volume/vol spike.
        return ret_30m <= -0.03 and vol_ratio_30m >= 2.0
    def check(self, returns, ret_30m, vol_ratio_30m, now=None) -> str:
        now = time.time() if now is None else now
        try:
            sigma = self.coupling_sigma(returns)
        except ValueError:
            return "NO_SIGNAL"  # fail-closed: caller treats as no-trip, equity breaker still guards
        if sigma >= COUPLING_SIGMA_TRIP and self.oi_proxy_shock(ret_30m, vol_ratio_30m):
            self.tripped_at = now
            return "TRIPPED"
        if sigma >= 1.0:
            return "ELEVATED"
        return "NORMAL"
    def is_cooldown(self, now=None) -> bool:
        if self.tripped_at is None: return False
        now = time.time() if now is None else now
        return (now - self.tripped_at) < COOLDOWN_SEC
    def leverage_scale(self, state: str) -> float:
        return {"TRIPPED": 0.0, "ELEVATED": 0.5}.get(state, 1.0)
```

## 3. Proposed behaviour

1. **Coupling-sigma trigger → leverage scaling.** Each execution cycle computes
   `state = breaker.check(returns_60x3, ret_30m, vol_ratio)`. Effective
   `TARGET_RISK_eff = TARGET_RISK * scale`, `LEVERAGE_CAP_eff = LEVERAGE_CAP * scale`
   with `scale ∈ {1.0, 0.5, 0.0}`. Scale applies to **new entries only**; existing
   positions are managed (stops/closes bypass the gate — reduce-only).
2. **30-min post-cascade execution cooldown.** While `is_cooldown()`: `gates_allow_trading`
   and `ExecutionBridge.execute_signal` return `allowed=False / rejected(cooldown)` for
   any signal that increases gross exposure; `side` that reduces |position| is allowed.
   Cooldown timestamp persisted in `crypto_state.json` (`cascade_tripped_at`) so restarts
   don't clear it. Fail-closed: missing/invalid inputs → equity breaker path unchanged.
3. **Post-liquidation bounce entry conditions (after cooldown expiry, ALL required):**
   - `state == NORMAL` (coupling-sigma < 1σ) AND `forecast_volatility(... )["regime"] != "crisis"`;
   - 30-min return stops making new lows + 5-min reclaim of VWAP/20-EMA (avoid catching the knife during the 88% window);
   - volume normalises (`vol_ratio_30m < 1.5`) — OI-proxy for flush exhaustion;
   - `crash_risk_gate` (where options inputs exist) not HIGH / no veto;
   - half-size pilot only (`×0.5 TARGET_RISK`) for first post-cooldown entry, full size next cycle if still NORMAL.

## 4. Exact diffs (PROTOTYPE — do not apply without edge-gate review)

### D1 — `config/risk_config.py` (append constants)
```diff
--- a/config/risk_config.py
+++ b/config/risk_config.py
@@
 BORROW_COST_BPS = 10.0
 COST_FALLBACK_BPS = 5.0
 VOL_WINDOW = 20
 VOL_MEDIAN_WINDOW = 60
+# --- Liquidation-cascade prototype (crypto perps) ---
+CASCADE_COUPLING_SIGMA_TRIP = 2.0
+CASCADE_COUPLING_SIGMA_ELEVATED = 1.0
+CASCADE_COOLDOWN_SEC = 1800
+CASCADE_LEVERAGE_SCALE_ELEVATED = 0.5
+CASCADE_OI_RET_30M = -0.03
+CASCADE_OI_VOL_RATIO = 2.0
```

### D2 — `src/execution/execution_bridge.py` (cooldown gate before sizing)
```diff
--- a/src/execution/execution_bridge.py
+++ b/src/execution/execution_bridge.py
@@
     def execute_signal(self, ticker, signal, entry_price, atr, strategy_confidence=100.0, regime="normal"):
         if signal == 0:
             return {"status": "skipped", "reason": "Flat"}
+        # Prototype: liquidation-cascade cooldown (reduce-only during cooldown).
+        try:
+            cascade = getattr(self, "cascade_breaker", None)
+            if cascade is not None and cascade.is_cooldown():
+                import inspect
+                # Caller must pass is_reduce_only=True for closes; default blocks entries.
+                frame = inspect.currentframe()
+                return {"status": "rejected", "reason": "CASCADE_COOLDOWN: new entries blocked 30m post-trip"}
+        except Exception as e:
+            return {"status": "rejected", "reason": f"cascade gate fail-closed: {e}"}
         balance = self.broker.get_account_balance()
```

### D3 — `src/execution/live_crypto_executor.py` (leverage scaling + cooldown in `gates_allow_trading`)
```diff
--- a/src/execution/live_crypto_executor.py
+++ b/src/execution/live_crypto_executor.py
@@
-def gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count):
+def gates_allow_trading(equity, last_equity, high_water_mark, active_pos_count, cascade_state="NORMAL", cascade_cooldown=False):
+    if cascade_cooldown:
+        return False, "[!!!] CASCADE COOLDOWN: 30m post-liquidation block on new entries (reduce-only)."
     if last_equity > 0:
         daily_loss_pct = (last_equity - equity) / last_equity
@@
     return True, ""
+# Call-site (main): scale sizing inputs before calculate_target_position_sizes:
+#   scale = {"NORMAL": 1.0, "ELEVATED": 0.5, "TRIPPED": 0.0}[cascade_state]
+#   eff_target_risk, eff_lev = TARGET_RISK * scale, LEVERAGE_CAP * scale
+#   if scale == 0.0: skip entry loop (closes still executed via execute_bybit_order reduce path)
```

### D4 — new `src/risk/liquidation_cascade.py` (see §2 sketch; full file, no diff to existing code)
Phase-2 swap: `oi_proxy_shock` gains optional `oi_drop_pct` param fed by
`exchange.fetch_open_interest(symbol)` (Bybit via ccxt); trip condition becomes
`(sigma ≥ 2 AND (oi_drop ≥ 25% OR proxy_shock))`, matching the 25–70% OI-contraction fact.

## 5. Test plan (prototype acceptance)

| # | Test | File / command | Pass criterion |
|---|---|---|---|
| T1 | coupling-sigma trip on synthetic cascade (3-asset, corr 0.9, -5% 30m, vol×3) | `tests/test_liquidation_cascade.py::test_trip` — `PYTHONPATH=. pytest tests/test_liquidation_cascade.py -q` | `check() == TRIPPED`, `is_cooldown()==True` |
| T2 | no false trip on normal chop (corr 0.2, ±0.5%) | same file `::test_no_false_trip` | `NORMAL`, scale 1.0 |
| T3 | ELEVATED halves leverage | `::test_elevated_scale` | `leverage_scale==0.5` |
| T4 | cooldown expiry at 1801s | `::test_cooldown_expiry` (inject `now`) | `is_cooldown(False)` post-expiry |
| T5 | fail-closed: empty/NaN returns | `::test_fail_closed` | `NO_SIGNAL`, no exception past module boundary |
| T6 | bridge rejects entries, allows reduce-only during cooldown | `tests/test_execution_bridge_cascade.py` | entry→`rejected/CASCADE_COOLDOWN`; close→executed |
| T7 | Bybit gate: `gates_allow_trading(..., cascade_cooldown=True)` blocks | inline pytest | `allowed is False` |
| T8 | bounce entry needs all 4 conditions (matrix test) | `::test_bounce_matrix` | pilot size only when ALL true |
| T9 | backtest replay: 2022-05 LUNA / 2022-11 FTX 30m bars — cascade dates flagged, post-bounce PnL vs buy-the-dip baseline | `python scripts/run_full_backtest.py` + notebook | flag recall ≥ 80% on labelled cascades; no leverage increase mid-cascade |
| T10 | lint/security | `ruff check src/risk/liquidation_cascade.py`, `bandit -r src/risk/` | clean |

Edge-gate note: per `AGENTS.md`, promotion to `strategies/registry.json` requires
pre-registration + walk-forward + permutation + deflated-Sharpe; this prototype makes
**no registry claim** — T9 is exploratory only.

## 6. Risks / open questions

- No live OI feed today: proxy (return + volume) can confuse organic dumps with liquidations → Phase-2 `fetchOpenInterest` required before live.
- `build_correlation_graph` uses daily bars; cascade needs 1m/5m intraday returns — caller must supply 30–60 obs intraday window, else sigma lags.
- Bounce entries are counter-trend; pilot-size + reclaim filter are load-bearing. If T9 shows negative expectancy, ship breaker-only (no bounce).
- State persistence (`cascade_tripped_at` in `crypto_state.json`) must survive restarts; clock skew → use exchange server time.

## 7. Recommendation

Implement D1–D4 behind a `CASCADE_ENABLED=False` default flag, run T1–T10, then decide:
ship the **breaker + cooldown** (defensive, high prior), hold the **bounce entry** for edge-gate validation.
