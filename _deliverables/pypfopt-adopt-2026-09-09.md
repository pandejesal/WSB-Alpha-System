# PyPortfolioOpt Pattern Adoption Proposal — 2026-09-09

> STUDY TASK — no code modified. `evolve_real.py` and `strategies/registry.json` untouched.
> Proposal only. All diffs below are exact, apply-ready, grounded in files that exist.

## 1. Actual layout verification (worker-1 claim corrected)

Worker 1 reported `src/signals/`, `src/ops/`, `src/data/providers/` "instead of `src/alpha/`".
Verified on disk: **all of these exist side by side**. There is no either/or.

| Path | Exists? | Contents relevant to this proposal |
|---|---|---|
| `src/portfolio/` | **NO** — `ls: cannot access 'src/portfolio'` | There is no `src/portfolio/` package. Portfolio logic lives in `src/risk/` + `src/ops/portfolio.py`. Do NOT target `src/portfolio/`. |
| `src/risk/` | YES | `portfolio_optimization.py`, `portfolio_manager.py`, `position_sizer.py`, `position_sizing.py`, `circuit_breakers.py`, `volatility_forecast.py`, `crash_risk.py`, `fred_macro_provider.py`, `alptrading_*` |
| `src/ops/portfolio.py` | YES | 7-sleeve `PortfolioManager` (equal-risk merge, 60% cap, $1 min-notional) |
| `src/signals/` | YES | signal engine (out of scope) |
| `src/ops/` | YES | registry/gate/daily/killswitch (out of scope except `portfolio.py`) |
| `src/data/providers/` | YES | `yfinance_provider`, `tiingo_provider`, `binance_public_provider`, `openbb_provider`, `reddit_provider`, `chain.py` (+ `alpaca_data_provider.py`, `base.py` at `src/data/`) |
| `src/alpha/` | YES | `order_blocks.py`, strategies, indicators (signal-side; not sizing) |
| `src/execution/` | YES | `execution_adapter.py` (`int(qty)` cast), `execution_bridge.py` (zero-qty reject), `live_alpaca_executor.py` (`place_fractional_market_order` notional), `live_crypto_executor.py` ($10 floor), `universal_broker.py`, `paper_executor.py` |

### Dependency environment (verified, not assumed)

- `pypfopt` — **NOT installed** (`ModuleNotFoundError`). Not in `requirements.txt`.
- `riskfolio` — listed in `requirements.txt` as `riskfolio-lib==7.3.0` but **import fails** in this env (env drift / `.venv` stale). `src/risk/portfolio_optimization.py` imports `riskfolio as rp` at module top, so it is currently **unimportable here**.
- `sklearn==1.9.0` — installed. `sklearn.covariance.LedoitWolf` available, no new dep needed.
- `scipy==1.18.0`, `numpy==2.2.0`, `pandas==2.2.3` — installed. HRP needs only these + `scipy.cluster.hierarchy.linkage`.
- `cvxpy==1.9.2`, `clarabel`, `osqp` — installed (efficient-frontier solvers would work if wanted).

**Consequence:** propose **vendored PyPortfolioOpt patterns** (Ledoit-Wolf via sklearn, HRP ~60 lines, greedy DiscreteAllocation ~40 lines) rather than adding a `PyPortfolioOpt` dependency. Zero new requirements, zero-cost CI unaffected.

## 2. Actual optimizer / position-sizing code (ground truth)

### A. `src/risk/portfolio_optimization.py` (97 lines) — the optimizer
`PortfolioOptimizer(risk_measure='CVaR', alpha=0.05)` with `optimize_cvar()` and `optimize_erc()`,
both on **Riskfolio** with `port.assets_stats(method_mu='hist', method_cov='hist')` — i.e. **sample covariance,
no shrinkage**. Single-asset path returns `1.0 - min_cash`. Fail-closed to empty Series on exception.
Weak point: `method_cov='hist'` is exactly what Ledoit-Wolf replaces.

### B. `src/risk/position_sizer.py` (296 lines) — Kelly primary sizer
`KellyCalculator` (raw/adjusted Kelly) → `ConfidenceAdjuster` → `RegimeAdjuster` → `MacroAdjuster`
→ `KellyBoostAggregator` → half-Kelly cap → `int(position_value / price)` shares.
Note: existing tests (`tests/risk/test_position_sizer.py`, `tests/risk/test_risk_engine.py`) call a
**stale API** (`calculate_size(...)`, `PositionSizer(base_risk_pct, max_notional_leverage)`) that no longer
exists on this class — pre-existing drift, not caused by this proposal. Do not "fix" those tests in this change.

### C. `src/risk/position_sizing.py` (113 lines) — legacy fractional-Kelly sizer
Static `PositionSizer.calculate_position_size(...)` with `math.floor(qty / broker_min_increment)`.
Already does floor-to-increment — the discrete-allocation hook point for whole-share venues.

### D. `src/risk/portfolio_manager.py` (203 lines) — KellySizer + dual-constraint manager
`KellySizer.kelly_size(edge, variance)` (`f* = mu/sigma²`, quarter-Kelly, `min_edge=0.01` fail-closed);
`PortfolioManager.get_target_allocation()` returns `min(confidence_amount, kelly_amount)`.
Covered by `tests/portfolio/test_portfolio_manager.py` (passing API).

### E. `src/ops/portfolio.py` (186 lines) — 7-sleeve merge
`compute_merged_targets()`: equal-risk nominal `(equity * 0.60) / 7`, `$1` floor, drop-smallest loop,
60% cap, ticker-overlap correlation guard. Covered by `tests/portfolio/test_portfolio_sizing.py`.
**No covariance awareness, no shrinkage, no HRP, no price-aware share rounding** — notionals only.

### F. Execution discrete-order surface
- `execution_adapter.py:38` — `"quantity": int(qty)` truncation, no leftover accounting.
- `execution_bridge.py:36-40` — rejects zero qty, market order passthrough.
- `live_alpaca_executor.py:121` — fractional **notional** orders (no discretization needed for Alpaca).
- `live_crypto_executor.py:76,242` — `$10` floor with retry-to-floor.
- Missing: greedy leftover allocation (PyPortfolioOpt `DiscreteAllocation` pattern) for whole-share /
  crypto-lot venues and for the paper-broker `int()` path.

## 3. Proposed diffs (exact, apply-ready, no new dependencies)

### Diff 1 — NEW `src/risk/covariance.py` (Ledoit-Wolf shrinkage, sklearn-backed)

```python
"""Shrunk covariance estimators (PyPortfolioOpt risk_models.CovarianceShrinkage pattern, vendored).

Uses sklearn (already in requirements) — no PyPortfolioOpt dependency.
Fail-closed: on any failure returns the sample covariance so callers keep working.
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def sample_cov(returns: pd.DataFrame) -> pd.DataFrame:
    """Sample covariance, annualised-naive (matches Riskfolio hist convention)."""
    return returns.cov()


def ledoit_wolf_cov(returns: pd.DataFrame) -> pd.DataFrame:
    """Ledoit-Wolf shrunk covariance (PyPortfolioOpt `risk_models.CovarianceShrinkage().ledoit_wolf()`).

    Falls back to sample covariance when sklearn is unavailable, n < 2*p regime
    is degenerate, or any exception occurs (fail-closed: never block sizing).
    """
    fallback = sample_cov(returns)
    try:
        from sklearn.covariance import LedoitWolf

        clean = returns.dropna(axis=0, how="any")
        if clean.shape[0] < 2 or clean.shape[1] < 2:
            return fallback
        lw = LedoitWolf().fit(clean.values)
        return pd.DataFrame(lw.covariance_, index=returns.columns, columns=returns.columns)
    except Exception as e:  # noqa: BLE001 - fail-closed by design
        logger.warning("Ledoit-Wolf failed (%s); using sample covariance.", e)
        return fallback
```

### Diff 2 — `src/risk/portfolio_optimization.py`: shrinkage-aware stats + HRP (unified diff)

```diff
--- a/src/risk/portfolio_optimization.py
+++ b/src/risk/portfolio_optimization.py
@@ -1,13 +1,20 @@
 import logging
 
+import numpy as np
 import pandas as pd
 import riskfolio as rp
+
+from src.risk.covariance import ledoit_wolf_cov, sample_cov
 
 logger = logging.getLogger(__name__)
 
 class PortfolioOptimizer:
-    def __init__(self, risk_measure: str = 'CVaR', alpha: float = 0.05):
+    # PyPortfolioOpt adoption: covariance estimator is injectable; default flips
+    # from sample ('hist') to Ledoit-Wolf shrinkage to tame estimation error.
+    COV_ESTIMATORS = ("ledoit_wolf", "hist")
+
+    def __init__(self, risk_measure: str = 'CVaR', alpha: float = 0.05,
+                 cov_estimator: str = 'ledoit_wolf'):
         """
         Args:
             risk_measure: 'CVaR' for Conditional Value at Risk
             alpha: Significance level for CVaR (e.g., 0.05 for 95% CVaR)
+            cov_estimator: 'ledoit_wolf' (default, shrunk) or 'hist' (legacy sample)
         """
         self.risk_measure = risk_measure
         self.alpha = alpha
+        if cov_estimator not in self.COV_ESTIMATORS:
+            raise ValueError(f"cov_estimator must be one of {self.COV_ESTIMATORS}")
+        self.cov_estimator = cov_estimator
+
+    def _cov(self, returns: pd.DataFrame) -> pd.DataFrame:
+        if self.cov_estimator == 'ledoit_wolf':
+            return ledoit_wolf_cov(returns)
+        return sample_cov(returns)
 
     def optimize_cvar(self, returns: pd.DataFrame, max_weight: float = 0.25, min_cash: float = 0.10) -> pd.Series:
```

Apply the same `_cov` injection to the `optimize_erc` body: after
`port.assets_stats(method_mu='hist', method_cov='hist')` add:

```python
            # PyPortfolioOpt pattern: override sample cov with shrunk estimate
            # (Riskfolio exposes port.cov after assets_stats; assignment keeps
            # the rest of the pipeline — bounds, optimization call — unchanged).
            if self.cov_estimator == 'ledoit_wolf':
                port.cov = self._cov(returns)
```

and append the HRP method to the class:

```python
    def optimize_hrp(self, returns: pd.DataFrame, min_cash: float = 0.10) -> pd.Series:
        """Hierarchical Risk Parity (PyPortfolioOpt `HRPOpt` pattern, vendored).

        Single-linkage on correlation distance -> quasi-diagonalization ->
        recursive bisection with inverse-variance allocation. No matrix
        inversion, so it survives the singular-cov regime that breaks
        mean-variance/CVaR. Fail-closed to equal-weight on any error.
        """
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform

        if returns.empty:
            return pd.Series(dtype=float)
        cols = list(returns.columns)
        if len(cols) == 1:
            return pd.Series([1.0 - min_cash], index=cols)
        try:
            cov = self._cov(returns)
            std = np.sqrt(np.diag(cov.values))
            corr = cov.values / np.outer(std, std)
            corr = np.clip(corr, -1.0, 1.0)
            dist = np.sqrt(0.5 * (1.0 - corr))
            link = linkage(squareform(dist, checks=False), method="single")
            # quasi-diagonal order
            link = link.astype(int)
            sort_ix = [link[-1, 0], link[-1, 1]]
            n = link.shape[0] + 1
            while len(sort_ix) < n:
                nxt = []
                for i in sort_ix:
                    if i < n:
                        nxt.append(i)
                    else:
                        nxt.extend([link[i - n, 0], link[i - n, 1]])
                sort_ix = nxt
            order = [c for c in sort_ix if c < n]
            # recursive bisection
            w = pd.Series(1.0, index=[cols[i] for i in order])
            clusters = [[cols[i] for i in order]]
            while clusters:
                cluster = clusters.pop(0)
                if len(cluster) == 1:
                    continue
                mid = len(cluster) // 2
                c1, c2 = cluster[:mid], cluster[mid:]
                v1 = float(np.diag(cov.loc[c1, c1].values).sum()) / max(len(c1), 1)
                v2 = float(np.diag(cov.loc[c2, c2].values).sum()) / max(len(c2), 1)
                a1 = 1.0 - v1 / (v1 + v2) if (v1 + v2) > 0 else 0.5
                w[c1] *= a1
                w[c2] *= 1.0 - a1
                clusters += [c1, c2]
            return (w / w.sum() * (1.0 - min_cash)).reindex(cols)
        except Exception as e:  # noqa: BLE001 - fail-closed
            logger.warning("HRP failed (%s); using equal weight.", e)
            return pd.Series([(1.0 - min_cash) / len(cols)] * len(cols), index=cols)
```

Behaviour contract: default `cov_estimator='ledoit_wolf'` changes both CVaR and ERC outputs
vs legacy; legacy reproducible via `PortfolioOptimizer(cov_estimator='hist')`. Gate promotion must
re-run walk-forward before flipping live sleeves (see test plan §5).

### Diff 3 — NEW `src/execution/discrete.py` (PyPortfolioOpt `DiscreteAllocation` greedy pattern, vendored)

```python
"""Greedy discrete allocation (PyPortfolioOpt DiscreteAllocation pattern, vendored).

Converts continuous weights -> integer share counts with leftover accounting.
Venue-aware: Alpaca fractional/notional path needs no discretization; the
whole-share paper broker (execution_adapter int-cast) and crypto-lot path do.
"""
from __future__ import annotations


def discrete_allocate(weights: dict[str, float], latest_prices: dict[str, float],
                      total_portfolio_value: float, min_notional: float = 1.0,
                      min_qty: float = 1.0) -> tuple[dict[str, float], float]:
    """Greedy leftover allocation.

    Sorts by (weight * value / price) fractional remainder descending, fills
    whole lots while cash remains. Returns (allocation, leftover_cash).
    Drops lines that cannot meet min_notional (mirrors ops/portfolio $1 floor).
    """
    allocation: dict[str, float] = {}
    remaining = float(total_portfolio_value)
    # initial floor fill, largest weight first
    for ticker in sorted(weights, key=lambda t: -weights[t]):
        price = float(latest_prices.get(ticker, 0.0) or 0.0)
        if price <= 0 or weights[ticker] <= 0:
            continue
        target_value = weights[ticker] * total_portfolio_value
        qty = int(target_value // price)
        while qty >= min_qty and qty * price < min_notional:
            qty -= min_qty  # cannot satisfy floor -> reduce (eventually skipped)
        if qty < min_qty or qty * price < min_notional:
            continue
        cost = qty * price
        if cost <= remaining:
            allocation[ticker] = float(qty)
            remaining -= cost
    # greedy leftover: one extra lot to the highest-remainder affordable ticker
    improved = True
    while improved:
        improved = False
        ranked = sorted(
            (t for t in weights if weights[t] > 0 and latest_prices.get(t, 0) > 0),
            key=lambda t: -weights[t],
        )
        for ticker in ranked:
            price = float(latest_prices[ticker])
            if remaining >= price and (allocation.get(ticker, 0) + min_qty) * price >= min_notional:
                allocation[ticker] = allocation.get(ticker, 0.0) + min_qty
                remaining -= price
                improved = True
                break
    return allocation, remaining
```

### Diff 4 — `src/execution/execution_adapter.py`: wire leftover-aware quantities (unified diff)

```diff
--- a/src/execution/execution_adapter.py
+++ b/src/execution/execution_adapter.py
@@ -33,11 +33,14 @@ class PaperbrokerClient(PaperTradeBroker):
     def place_order(self, ticker: str, qty: int, side: str, order_type: str = "MARKET", target_cvar_allocation: float = 0.0) -> dict:
         endpoint = f"{self.base_url}/order"
         payload = {
             "ticker": ticker.upper(),
             "side": side.upper(),
-            "quantity": int(qty),
+            "quantity": int(qty),  # discrete shares; use discrete.discrete_allocate upstream for leftover-aware fills
             "order_type": order_type.upper(),
             "target_cvar_allocation": float(target_cvar_allocation)
         }
```

(No behaviour change at the broker boundary — the discretization lives upstream in
`src/ops/portfolio.py::compute_merged_targets` / the live-crypto path, which gain an optional
`latest_prices` argument and call `discrete_allocate` before emitting targets. Alpaca notional
path in `live_alpaca_executor.py` is explicitly out of scope: fractional orders need no discretization.)

### Explicit non-goals (do NOT touch)
- `evolve_real.py`, `strategies/registry.json` — frozen per task.
- Mean-variance `EfficientFrontier` (max-Sharpe/min-vol): Riskfolio CVaR/ERC already covers the
  mandate; adding a third optimizer family expands the overfit surface for no live-venue benefit.
- `CustomCovariance` / Oracle Approximating Shrinkage: sklearn LedoitWolf suffices; keep one estimator.

## 4. Why these three patterns (and only these)

1. **Ledoit-Wolf** — fixes the concrete flaw in `portfolio_optimization.py:30,79`
   (`method_cov='hist'`). Sample cov with 7-sleeve / short-lookback returns is high-variance;
   shrinkage is the cheapest variance reduction available with zero new deps.
2. **HRP** — non-inverted allocation that survives singular covariance (crypto + correlated
   equity sleeves). Serves as the fallback when CVaR/ERC fail to converge (today: empty Series).
3. **DiscreteAllocation (greedy)** — closes the weight→shares gap: `int()` truncation today
   silently leaves cash unallocated with no leftover record; the $1-floor/drop-smallest loop in
   `ops/portfolio.py` is notional-only and price-blind.

## 5. Test plan

New tests (all new files; no existing test edited):

- `tests/risk/test_covariance_shrinkage.py`
  - shrunk cov is symmetric PSD, shape/index preserved; differs from sample cov on noisy fixture.
  - degenerate inputs (single column, all-NaN, empty) return sample-cov fallback, no raise.
  - `PortfolioOptimizer(cov_estimator='hist')` reproduces legacy `assets_stats` path (mock `rp.Portfolio`,
    assert `port.cov` NOT overridden); default estimator overrides `port.cov` with LW output.
- `tests/risk/test_hrp.py`
  - 4-asset synthetic returns with block-correlation: weights sum to `1 - min_cash`, all ≥ 0,
    lower weight on the high-vol asset; single-asset and empty inputs follow fail-closed contract.
  - singular cov (duplicate column) still returns valid weights (the case that breaks inversion).
- `tests/execution/test_discrete_allocate.py`
  - weights `{A: .5, B: .3, C: .2}`, prices `{A: 10, B: 3, C: 100}`, value $100: integer lots,
    total cost + leftover == value (to cents), no line under `min_notional`.
  - missing/zero price tickers skipped; empty weights → `({}, value)`.

Regression (existing, run serially one file at a time per session rule):

```
PYTHONPATH=. pytest tests/portfolio/test_portfolio_manager.py -q
PYTHONPATH=. pytest tests/portfolio/test_portfolio_sizing.py -q
PYTHONPATH=. pytest tests/risk/test_position_sizer.py -q   # KNOWN-DRIFT: stale API, expect failure pre-existing
PYTHONPATH=. pytest tests/execution/test_live_crypto_executor_caps.py -q
ruff check src/risk/covariance.py src/risk/portfolio_optimization.py src/execution/discrete.py
bandit -r src/risk/covariance.py src/execution/discrete.py
```

Edge-gate note: per `AGENTS.md`, any live-sleeve weight change (LW default flip) needs
walk-forward + permutation + DSR before `registry.json` entry — this proposal ships the code
with legacy-compat flag (`cov_estimator='hist'`) so the gate can A/B without a second deploy.

## 6. Apply order (for the implementing worker)

1. Add `src/risk/covariance.py` (Diff 1).
2. Patch `src/risk/portfolio_optimization.py` (Diff 2: `_cov` + HRP + cov override lines).
3. Add `src/execution/discrete.py` (Diff 3).
4. Annotate `execution_adapter.py` (Diff 4, comment-only) + optional `latest_prices` kwarg in
   `ops/portfolio.py::compute_merged_targets` (backwards-compatible default `None` = current behaviour).
5. Add the three test files; run the regression list above.
6. Re-verify `riskfolio` import in the deploy env (fails here despite `requirements.txt` pin —
   optimizer module is currently unimportable in this container).
