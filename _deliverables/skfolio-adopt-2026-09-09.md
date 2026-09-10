# skfolio Adoption Proposal — scikit-learn-Compatible Portfolio Optimization

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py` and `strategies/registry.json` untouched per task constraint.
Scope: propose exact diffs to add skfolio (`skfolio`) sklearn-compatible patterns to the **actual** optimizer code without breaking fail-closed / edge-gate mandates.

Upstream: `https://github.com/skfolio/skfolio` (`pip install skfolio`, import namespace `skfolio`).
Conventions adopted (do not invent wrappers): `BaseEstimator` `fit/predict` API, `skfolio.optimization.*`,
`skfolio.model_selection.{CombinatorialPurgedCV, WalkForward}`, `skfolio.RiskMeasure`,
`skfolio.preprocessing.prices_to_returns`. Pin floor only; verify class names against installed version before merge
(some renames across 0.x: e.g. `HierarchicalRiskParity` vs `HierarchicalEqualRiskContribution`).

## 1. Study findings (requested paths vs. actual repo — verified by read)

Requested (do not exist):

- `src/portfolio/` — NOT FOUND. `glob src/portfolio/**/*` returns no files. The `src/` top level is:
  `alpha/ backtest/ data/ evolution/ execution/ gs_compat/ monitoring/ ops/ research/ risk/ sandbox/ signals/ utils/`.
  There is a `tests/portfolio/` directory, but it tests sizing/manager logic, not a `src/portfolio/` package.

Present (actual optimizer code — all line refs verified):

- `src/risk/portfolio_optimization.py:1-97` — `PortfolioOptimizer(risk_measure='CVaR', alpha=0.05)` with
  `optimize_cvar(returns, max_weight=0.25, min_cash=0.10)` and `optimize_erc(...)`, both built on
  `riskfolio-lib==7.3.0` (`import riskfolio as rp`, `rp.Portfolio(...).optimization(...)` /
  `.rp_optimization(...)`). Fail-closed: empty/single-asset returns → degenerate `pd.Series`;
  `except Exception → logger + empty Series`. No sklearn API, no HRP/NCO, no max-diversification,
  no risk-budgeting vector, no EVaR/CDaR, no purged CV.
- `src/backtest/optimization/optimizer.py:1-53` — `GridSearchOptimizer(param_grid)` (exhaustive
  `itertools.product` + sort by `sharpe`) and `BayesianOptimizer(strategy_class, bounds)` (single
  `scipy.optimize.minimize L-BFGS-B` on `-sharpe`). No embargo/purge, no combinatorial splits,
  no sklearn splitter interface.
- `src/backtest/optimization/walk_forward.py:1-51` — `WalkForwardOptimizer(train_days=90, test_days=30,
  step_days=30)` with `generate_windows()` (calendar-day `timedelta` windows) and `optimize()` (in-sample
  argmax-sharpe → single OOS backtest per window). No embargo, no purge, no `sklearn.model_selection` compat.
- `src/risk/portfolio_manager.py:27-203` — `KellySizer` (quarter-Kelly, `min_edge=0.01`,
  `max_position_pct=0.20`, fail-closed `0.0`) + `PortfolioManager` (confidence × Kelly `min()` dual
  constraint, 2% per-trade budget). Consumer of optimizer weights, not an optimizer itself — out of scope
  for diffs except as integration point.
- `src/risk/position_sizing.py:35-113` — `PositionSizer` (fractional Kelly + `MAX_RISK_PER_TRADE_PCT=0.01`,
  `MAX_POSITION_SIZE_PCT=0.25`, confidence `< 0.5 → 0.0`). No changes proposed.
- `requirements.txt:1-169` — `scikit-learn==1.9.0`, `scipy==1.18.0`, `cvxpy==1.9.2`, `riskfolio-lib==7.3.0`,
  `pandas==2.2.3`, `numpy==2.2.0` present. **No `skfolio` entry.**
- `tests/test_quant.py:57-93` — existing `test_portfolio_cvar_allocator` / `test_portfolio_erc_allocator`
  (seeded `np.random.seed(42)`, 100×3–4 assets, assert `sum ≈ 0.90`, `max ≤ 0.2501`). Must keep passing.
- `tests/test_optimization.py:1-59` — `WalkForwardOptimizer` window-shape test + `GridSearchOptimizer`
  dummy-strategy test. Must keep passing.
- Toolchain: `Python 3.11.15`, `sklearn 1.9.0` confirmed via `bash`.

Conclusion: the correct insertion points are (a) a new sklearn-compatible estimator module beside
`src/risk/portfolio_optimization.py`, (b) additive methods on `PortfolioOptimizer` delegating to it with
riskfolio fallback, (c) a new purged/embargo splitter + walk-forward splitter beside
`src/backtest/optimization/`, and (d) a pure-numpy risk-measure module (CVaR/EVaR/CDaR) with zero new
hard dependencies at import time. No new `src/portfolio/` package needed; follow existing
`src/risk/` + `src/backtest/optimization/` layout.

Design rules for this repo (fail-closed, edge-gate compliant):

1. `skfolio` is an **optional** dependency: every new module guards `import skfolio` with `try/except
   ImportError → _SKFOLIO_AVAILABLE=False`, logs once, and falls back to riskfolio/pure-numpy paths.
   Signal/evolution code must never import `skfolio` directly — only the new modules do.
2. `evolve_real.py` and `strategies/registry.json` are NOT touched by this proposal. New estimators are
   research-only until they pass the repo edge gate (pre-registration, walk-forward, permutation,
   Deflated Sharpe — see `docs/OPTIMIZATION_PLAYBOOK.md`, `docs/HUNT_PROTOCOL.md`).
3. No lookahead: splitters purge + embargo around test windows; estimators consume past-only returns.
4. Determinism: fixed `random_state`, sorted columns, capped weights re-normalized exactly like the
   existing `optimize_cvar` cap-and-redistribute loop.

## 2. skfolio patterns adopted (canonical, to verify with `pip show skfolio`)

```python
from skfolio import RiskMeasure                    # VARIANCE, CVAR, EVAR, CDAR, MAX_DRAWDOWN, ...
from skfolio.optimization import (
    MeanRisk,                # MinRisk(maximize_return=False, risk_measure=...)
    RiskBudgeting,           # risk-budgeting / risk-parity with budget vector b
    MaximumDiversification,  # max diversification-ratio portfolio
    HierarchicalRiskParity,  # HRP (agglomerative clustering linkage)
    NestedClustersOptimization,  # NCO (cluster → intra → inter optimization)
)
from skfolio.model_selection import CombinatorialPurgedCV, WalkForward
from skfolio.preprocessing import prices_to_returns
```

Risk-measure mapping used below: `CVaR` → `RiskMeasure.CVAR`, `EVaR` → `RiskMeasure.EVAR`,
`CDaR` → `RiskMeasure.CDAR`. If the installed skfolio renames any estimator, Diff 1 raises a
fail-closed `ImportError` with the exact missing symbol (caught by the guard in Diff 2) — never a
silent wrong optimizer.

## 3. Exact diffs proposed

### Diff 0 — `requirements.txt` (append, pin floor)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 yfinance==0.2.52
 zstandard==0.25.0
 defusedxml==0.7.1
 ccxt==4.5.74
 PyYAML==6.0.3
+skfolio>=0.9.0
```

Rationale: floor `0.9.0` is the first series with stable `CombinatorialPurgedCV` + `WalkForward` +
`RiskMeasure.EVAR/CDAR`. No ceiling (upstream churn). `skfolio` pulls `scikit-learn/scipy/cvxpy`,
all already pinned compatibly. Optional at runtime (guards below), required in CI for the new tests.

### Diff 1 — NEW `src/risk/risk_measures.py` (full file, ~90 lines, zero new deps)

Pure-numpy CVaR/EVaR/CDaR estimators. Used as fallback when skfolio is absent and as cross-check
when present. All functions are pure (no I/O), deterministic, fail-closed (`np.nan` on degenerate input).

```python
"""Tail-risk estimators: CVaR / EVaR / CDaR. Pure numpy. No skfolio import here."""
from __future__ import annotations

import numpy as np
import pandas as pd

def _as_losses(returns: pd.DataFrame | pd.Series | np.ndarray) -> np.ndarray:
    r = np.asarray(returns, dtype=float)
    if r.size == 0:
        return np.empty((0, 0))
    if r.ndim == 1:
        r = r.reshape(-1, 1)
    return -r  # losses = -returns

def cvar_historical(returns, alpha: float = 0.05) -> pd.Series:
    """Historical CVaR (Expected Shortfall) of losses at tail probability `alpha`.

    CVaR_alpha = mean(loss | loss >= VaR_alpha). Returns NaN series on degenerate input.
    """
    L = _as_losses(returns)
    cols = list(returns.columns) if isinstance(returns, pd.DataFrame) else [f"x{i}" for i in range(L.shape[1])] if L.size else []
    if L.size == 0 or L.shape[0] < 2 or not (0.0 < alpha < 1.0):
        return pd.Series([np.nan] * len(cols), index=cols)
    out = {}
    for j, c in enumerate(cols):
        col = L[:, j]
        var = np.quantile(col, 1.0 - alpha)
        tail = col[col >= var]
        out[c] = float(np.mean(tail)) if tail.size else float(var)
    return pd.Series(out)

def evar_chernoff(returns, alpha: float = 0.05, thetas: tuple = (0.5, 1.0, 2.0, 5.0, 10.0)) -> pd.Series:
    """EVaR via Chernoff bound: inf_theta>0 theta^-1 * ln(M_loss(theta) / alpha).

    Upper-bounds CVaR; coherent; more sensitive to large losses. Deterministic grid over `thetas`.
    """
    L = _as_losses(returns)
    cols = list(returns.columns) if isinstance(returns, pd.DataFrame) else [f"x{i}" for i in range(L.shape[1])] if L.size else []
    if L.size == 0 or L.shape[0] < 2 or not (0.0 < alpha < 1.0):
        return pd.Series([np.nan] * len(cols), index=cols)
    out = {}
    for j, c in enumerate(cols):
        col = L[:, j]
        best = np.inf
        for t in thetas:
            m = np.mean(np.exp(t * col - 700.0))  # shift for overflow safety
            # log-mean-exp correction: ln E[exp(tL)] = ln(mean(exp(tL-700))) + 700
            val = (np.log(max(m, 1e-300)) + 700.0 - np.log(alpha)) / t
            best = min(best, val)
        out[c] = float(best)
    return pd.Series(out)

def cdar_historical(portfolio_returns: pd.Series | np.ndarray, alpha: float = 0.05) -> float:
    """Conditional Drawdown-at-Risk of a 1-D portfolio return series.

    CDaR_alpha = mean(drawdown | drawdown >= DaR_alpha), drawdown from running peak of cum-wealth.
    """
    r = np.asarray(portfolio_returns, dtype=float).ravel()
    if r.size < 2 or not (0.0 < alpha < 1.0):
        return float("nan")
    wealth = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(np.concatenate([[1.0], wealth]))[1:]
    dd = 1.0 - wealth / np.maximum(peak, 1e-12)
    dar = float(np.quantile(dd, 1.0 - alpha))
    tail = dd[dd >= dar]
    return float(np.mean(tail)) if tail.size else dar
```

### Diff 2 — NEW `src/risk/skfolio_estimators.py` (full file, ~200 lines, sklearn-compatible)

Single choke point for all skfolio imports. Exposes `BaseEstimator`-compatible wrappers plus a
riskfolio fallback so behavior is identical with/without skfolio installed.

```python
"""sklearn-compatible portfolio estimators (skfolio patterns, riskfolio fallback).

Never imported by evolve_real.py directly. Consumed via PortfolioOptimizer methods (Diff 3).
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

logger = logging.getLogger(__name__)

try:  # optional dependency — fail-closed, never raise at import
    from skfolio import RiskMeasure
    from skfolio.optimization import (
        HierarchicalRiskParity,
        MaximumDiversification,
        MeanRisk,
        NestedClustersOptimization,
        RiskBudgeting,
    )
    _SKFOLIO_AVAILABLE = True
    _SKFOLIO_IMPORT_ERROR: Exception | None = None
except Exception as e:  # noqa: BLE001 — record and degrade
    RiskMeasure = None  # type: ignore
    HierarchicalRiskParity = MaximumDiversification = MeanRisk = None  # type: ignore
    NestedClustersOptimization = RiskBudgeting = None  # type: ignore
    _SKFOLIO_AVAILABLE = False
    _SKFOLIO_IMPORT_ERROR = e

_RISK_MEASURE_MAP = {"cvar": "CVAR", "evar": "EVAR", "cdar": "CDAR", "variance": "VARIANCE"}

def skfolio_available() -> bool:
    return _SKFOLIO_AVAILABLE

def _risk_measure(name: str):
    if not _SKFOLIO_AVAILABLE:
        raise ImportError(f"skfolio not available ({_SKFOLIO_IMPORT_ERROR}); use riskfolio fallback")
    return getattr(RiskMeasure, _RISK_MEASURE_MAP[name.strip().lower()])

def _cap_redistribute(weights: pd.Series, max_weight: float) -> pd.Series:
    w = weights.copy()
    while bool((w > max_weight + 1e-9).any()):
        w[w > max_weight] = max_weight
        excess = 1.0 - w.sum()
        under = w < max_weight
        if not bool(under.any()):
            break
        w[under] += excess / under.sum()
    return w

def _scale_cash(weights: pd.Series, min_cash: float) -> pd.Series:
    return weights * (1.0 - min_cash)

class _SkfolioBase(BaseEstimator):
    """Shared fit/predict contract: fit(X=returns DataFrame) -> self; predict -> weights_."""

    def __init__(self, risk_measure: str = "cvar", max_weight: float = 0.25,
                 min_cash: float = 0.10, random_state: int = 42):
        self.risk_measure = risk_measure
        self.max_weight = max_weight
        self.min_cash = min_cash
        self.random_state = random_state

    def _post(self, raw: pd.Series, columns) -> pd.Series:
        w = pd.Series(np.asarray(raw, dtype=float).ravel(), index=list(columns), dtype=float)
        w = _cap_redistribute(w, self.max_weight / (1.0 - self.min_cash))
        return _scale_cash(w, self.min_cash)

class RiskBudgetingEstimator(_SkfolioBase):
    """Risk budgeting (generalized risk parity). budget=None -> equal risk contribution."""

    def __init__(self, risk_measure: str = "cvar", budget=None, **kw):
        super().__init__(**kw)
        self.risk_measure = risk_measure
        self.budget = budget

    def fit(self, X: pd.DataFrame, y=None):
        X = pd.DataFrame(X).dropna()
        rm = _risk_measure(self.risk_measure)
        est = RiskBudgeting(risk_measure=rm, budget=self.budget, portfolio_params=dict(name="rb"))
        est.fit(X)
        self.weights_ = self._post(pd.Series(est.weights_, index=X.columns), X.columns)
        return self

class MaxDiversificationEstimator(_SkfolioBase):
    def fit(self, X: pd.DataFrame, y=None):
        X = pd.DataFrame(X).dropna()
        est = MaximumDiversification(portfolio_params=dict(name="md"))
        est.fit(X)
        self.weights_ = self._post(pd.Series(est.weights_, index=X.columns), X.columns)
        return self

class HierarchicalRiskParityEstimator(_SkfolioBase):
    def fit(self, X: pd.DataFrame, y=None):
        X = pd.DataFrame(X).dropna()
        est = HierarchicalRiskParity(risk_measure=_risk_measure(self.risk_measure))
        est.fit(X)
        self.weights_ = self._post(pd.Series(est.weights_, index=X.columns), X.columns)
        return self

class NestedClustersOptimizationEstimator(_SkfolioBase):
    """NCO: cluster -> intra (MeanRisk) -> inter (MeanRisk) de-noising wrapper."""

    def fit(self, X: pd.DataFrame, y=None):
        X = pd.DataFrame(X).dropna()
        rm = _risk_measure(self.risk_measure)
        inner = MeanRisk(risk_measure=rm)
        est = NestedClustersOptimization(inner_estimator=inner, outer_estimator=MeanRisk(risk_measure=rm))
        est.fit(X)
        self.weights_ = self._post(pd.Series(est.weights_, index=X.columns), X.columns)
        return self

class MeanRiskEstimator(_SkfolioBase):
    """Min-risk baseline (parity target for Combinatorial Purged CV scoring)."""

    def fit(self, X: pd.DataFrame, y=None):
        X = pd.DataFrame(X).dropna()
        est = MeanRisk(risk_measure=_risk_measure(self.risk_measure))
        est.fit(X)
        self.weights_ = self._post(pd.Series(est.weights_, index=X.columns), X.columns)
        return self
```

Verify-before-merge: `python -c "import skfolio; print(skfolio.__version__)"` then
`python -c "from skfolio.optimization import RiskBudgeting, MaximumDiversification,
HierarchicalRiskParity, NestedClustersOptimization, MeanRisk; from skfolio.model_selection
import CombinatorialPurgedCV, WalkForward; from skfolio import RiskMeasure; print('ok')"`.
If any name differs, adjust the guarded import block only — Diff 3/4 call sites stay unchanged.

### Diff 3 — `src/risk/portfolio_optimization.py` (additive methods, existing behavior untouched)

```diff
--- a/src/risk/portfolio_optimization.py
+++ b/src/risk/portfolio_optimization.py
@@ -1,8 +1,11 @@
 import logging

 import pandas as pd
 import riskfolio as rp
+from sklearn.base import clone

 logger = logging.getLogger(__name__)

+from src.risk.risk_measures import cvar_historical, cdar_historical, evar_chernoff
+from src.risk.skfolio_estimators import (
+    HierarchicalRiskParityEstimator,
+    MaxDiversificationEstimator,
+    MeanRiskEstimator,
+    NestedClustersOptimizationEstimator,
+    RiskBudgetingEstimator,
+    skfolio_available,
+)
+
 class PortfolioOptimizer:
     def __init__(self, risk_measure: str = 'CVaR', alpha: float = 0.05):
         """
         Args:
             risk_measure: 'CVaR' for Conditional Value at Risk
             alpha: Significance level for CVaR (e.g., 0.05 for 95% CVaR)
         """
         self.risk_measure = risk_measure
         self.alpha = alpha
+        self._skfolio = skfolio_available()
@@ ... optimize_erc unchanged ...
         except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
             logger.error(f"Portfolio ERC optimization failed: {e}")
             return pd.Series(dtype=float)
+
+    # ---- skfolio sklearn-compatible patterns (additive; riskfolio fallback) ----
+    def _guard(self, returns: pd.DataFrame):
+        if returns.empty or returns.shape[1] < 2:
+            if returns.shape[1] == 1:
+                return pd.Series([0.90], index=returns.columns)
+            return pd.Series(dtype=float)
+        return None
+
+    def optimize(self, estimator, returns: pd.DataFrame, **params) -> pd.Series:
+        """Generic sklearn-style entry: clone(estimator).fit(returns).weights_ (fail-closed)."""
+        try:
+            deg = self._guard(returns)
+            if deg is not None:
+                return deg
+            est = clone(estimator).set_params(**params) if params else clone(estimator)
+            est.fit(returns)
+            return est.weights_
+        except Exception as e:  # noqa: BLE001
+            logger.error(f"Portfolio optimize (sklearn API) failed: {e}")
+            return pd.Series(dtype=float)
+
+    def optimize_risk_budgeting(self, returns, budget=None, max_weight=0.25, min_cash=0.10) -> pd.Series:
+        """Risk budgeting (budget=None -> ERC). skfolio RiskBudgeting; fallback optimize_erc."""
+        if self._skfolio:
+            return self.optimize(RiskBudgetingEstimator(budget=budget, max_weight=max_weight, min_cash=min_cash), returns)
+        return self.optimize_erc(returns, max_weight=max_weight, min_cash=min_cash)
+
+    def optimize_max_diversification(self, returns, max_weight=0.25, min_cash=0.10) -> pd.Series:
+        """Max diversification-ratio portfolio. Fallback: ERC (same constraints)."""
+        if self._skfolio:
+            return self.optimize(MaxDiversificationEstimator(max_weight=max_weight, min_cash=min_cash), returns)
+        return self.optimize_erc(returns, max_weight=max_weight, min_cash=min_cash)
+
+    def optimize_hrp(self, returns, max_weight=0.25, min_cash=0.10) -> pd.Series:
+        """Hierarchical Risk Parity (clustered, no inversion). Fallback: ERC."""
+        if self._skfolio:
+            return self.optimize(HierarchicalRiskParityEstimator(max_weight=max_weight, min_cash=min_cash), returns)
+        return self.optimize_erc(returns, max_weight=max_weight, min_cash=min_cash)
+
+    def optimize_nco(self, returns, max_weight=0.25, min_cash=0.10) -> pd.Series:
+        """Nested Clusters Optimization (de-noised HRP extension). Fallback: ERC."""
+        if self._skfolio:
+            return self.optimize(NestedClustersOptimizationEstimator(max_weight=max_weight, min_cash=min_cash), returns)
+        return self.optimize_erc(returns, max_weight=max_weight, min_cash=min_cash)
+
+    def tail_risks(self, returns: pd.DataFrame) -> pd.DataFrame:
+        """Per-asset CVaR/EVaR (+ portfolio CDaR attr) cross-check, pure-numpy always available."""
+        out = pd.DataFrame({
+            "cvar": cvar_historical(returns, self.alpha),
+            "evar": evar_chernoff(returns, self.alpha),
+        })
+        out.attrs["cdar_note"] = "call cdar_historical(w.dot(returns.T)) on fitted weights for CDaR"
+        return out
```

Notes: existing `optimize_cvar`/`optimize_erc` bodies byte-identical; new code is purely additive.
`_guard` single-asset default `0.90` matches existing `1.0 - min_cash` convention at default `min_cash=0.10`.

### Diff 4 — NEW `src/backtest/optimization/purged_cv.py` (~120 lines, sklearn-compatible splitter)

Bridges existing `WalkForwardOptimizer`/`GridSearchOptimizer` to `CombinatorialPurgedCV` + `WalkForward`
without changing their public behavior.

```python
"""Purged/embargoed splitters: sklearn-compatible, skfolio-delegating, pure-python fallback."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

try:
    from skfolio.model_selection import CombinatorialPurgedCV as _SkCPCV, WalkForward as _SkWF
    _SKFOLIO_MS = True
except Exception:  # noqa: BLE001
    _SkCPCV = _SkWF = None
    _SKFOLIO_MS = False

class PurgedWalkForward:
    """sklearn splitter: trainWindow -> embargo -> testWindow, rolling. `split(X)` yields (train, test)."""

    def __init__(self, train_size: int = 252, test_size: int = 63, step: int = 63, embargo_pct: float = 0.01):
        self.train_size, self.test_size, self.step = train_size, test_size, step
        self.embargo_pct = embargo_pct

    def split(self, X, y=None, groups=None):
        n = len(X)
        embargo = int(self.test_size * self.embargo_pct)
        start = 0
        while start + self.train_size + embargo + self.test_size <= n:
            tr = np.arange(start, start + self.train_size)
            te = np.arange(start + self.train_size + embargo, start + self.train_size + embargo + self.test_size)
            yield tr, te
            start += self.step

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return sum(1 for _ in self.split(X if X is not None else []))

class CombinatorialPurgedCVSplitter:
    """Thin sklearn-compatible facade over skfolio's CombinatorialPurgedCV.

    Falls back to K non-overlapping purged folds when skfolio is absent (fail-closed, never silent).
    """

    def __init__(self, n_folds: int = 6, n_test_folds: int = 2, embargo_pct: float = 0.01, random_state: int = 42):
        self.n_folds, self.n_test_folds = n_folds, n_test_folds
        self.embargo_pct, self.random_state = embargo_pct, random_state

    def split(self, X, y=None, groups=None):
        import itertools

        n = len(X)
        if _SKFOLIO_MS:
            cv = _SkCPCV(n_folds=self.n_folds, n_test_folds=self.n_test_folds)
            yield from cv.split(X, y)
            return
        logger.warning("skfolio absent — CombinatorialPurgedCVSplitter using sequential purged fallback")
        fold = n // self.n_folds
        emb = int(fold * self.embargo_pct)
        idx = [np.arange(i * fold, (i + 1) * fold if i + 1 < self.n_folds else n) for i in range(self.n_folds)]
        for test_folds in itertools.combinations(range(self.n_folds), self.n_test_folds):
            te = np.concatenate([idx[i] for i in test_folds])
            tr = np.concatenate([idx[i] for i in range(self.n_folds) if i not in test_folds])
            # purge: drop train rows within embargo of any test row
            keep = np.ones(len(tr), dtype=bool)
            lo, hi = te.min() - emb, te.max() + emb
            keep &= (tr < lo) | (tr > hi)
            yield tr[keep], te
```

Wiring (no signature changes to existing classes — separate one-line usages):

- `WalkForwardOptimizer.optimize(...)`: alternative path `for tr, te in PurgedWalkForward(...).split(data)`
  replacing calendar `generate_windows` when `use_purged=True` (new kwarg, default `False`).
- `GridSearchOptimizer.optimize(...)`: wrap loop with splitter for CPCV scoring when caller passes
  `cv=CombinatorialPurgedCVSplitter(...)` (new optional kwarg, default `None` → current behavior).

### Diff 5 — `src/backtest/optimization/__init__.py` (exports; create if absent)

```diff
+# new or appended
+from src.backtest.optimization.purged_cv import CombinatorialPurgedCVSplitter, PurgedWalkForward
+from src.risk.skfolio_estimators import (
+    HierarchicalRiskParityEstimator,
+    MaxDiversificationEstimator,
+    MeanRiskEstimator,
+    NestedClustersOptimizationEstimator,
+    RiskBudgetingEstimator,
+)
+__all__ = ["CombinatorialPurgedCVSplitter", "PurgedWalkForward", "RiskBudgetingEstimator",
+           "MaxDiversificationEstimator", "HierarchicalRiskParityEstimator",
+           "NestedClustersOptimizationEstimator", "MeanRiskEstimator"]
```

## 4. What is deliberately NOT changed

- `evolve_real.py`, `strategies/registry.json` — untouched (edge-gate: no strategy graduates without
  pre-registration + walk-forward + permutation + DSR).
- `optimize_cvar` / `optimize_erc` bodies, `GridSearchOptimizer` / `WalkForwardOptimizer` default paths,
  `PositionSizer`, `KellySizer`/`PortfolioManager` — behavior-preserving; new code is additive with
  `use_purged=False` / `cv=None` defaults.
- No live-trading, broker, or circuit-breaker flags touched.

## 5. Test plan (offline-first, deterministic, serial per repo policy)

New file `tests/test_skfolio_adopt.py` (unittest, seeded, zero network; skip-if-absent for skfolio paths,
hard asserts for numpy fallbacks):

1. `test_risk_measures_cvar_evar_ordering` — synthetic 500×3 returns (`seed 42`); assert
   `evar >= cvar - 1e-9` per asset (Chernoff upper bound), no NaN, `cdar_historical` in `[0, 1]`.
2. `test_estimators_weights_sum_cash` — each estimator (or fallback when `skfolio` absent):
   `weights.sum() ≈ 0.90`, `max ≤ 0.2501`, no NaN, deterministic across two `fit` calls.
3. `test_sklearn_clone_compat` — `sklearn.base.clone(estimator).fit(X).weights_` works for all five
   estimators (skipped if `skfolio` absent; fallback path asserts ERC parity instead).
4. `test_purged_walk_forward_no_overlap` — `PurgedWalkForward(252, 63, 63).split(1000-row frame)`:
   every `(train, test)` has `max(train) + embargo <= min(test)`, `len(test) == 63`.
5. `test_cpcv_covers_all_samples` — `CombinatorialPurgedCVSplitter(6, 2).split(600-row frame)` yields
   `C(6,2)=15` splits; union of test indices covers all rows; train/test disjoint per split.
6. `test_existing_quant_still_passes` — re-run `tests/test_quant.py::TestQuantPhase3` CVaR/ERC asserts unchanged.

Commands (run ONE file at a time, strictly serial):

```
PYTHONPATH=. pytest tests/test_skfolio_adopt.py -v
PYTHONPATH=. pytest tests/test_quant.py -v
PYTHONPATH=. pytest tests/test_optimization.py -v
ruff check src/risk/risk_measures.py src/risk/skfolio_estimators.py src/backtest/optimization/purged_cv.py src/risk/portfolio_optimization.py
bandit -r src/risk/ src/backtest/optimization/
python -c "from skfolio.optimization import RiskBudgeting, MaximumDiversification, HierarchicalRiskParity, NestedClustersOptimization, MeanRisk; from skfolio.model_selection import CombinatorialPurgedCV, WalkForward; print('skfolio API ok')"
```

Acceptance: all six tests green; `ruff`/`bandit` clean; existing `test_quant` + `test_optimization`
unbroken; `skfolio`-absent run still green via fallbacks (prove by `pip uninstall -y skfolio` in a venv).

Edge-gate note: merging these diffs does NOT register any strategy. Promotion to
`strategies/registry.json` requires the standard hunt gate (walk-forward OOS Sharpe, permutation
p-value, DSR) documented in the playbook — tracked separately.

## 6. Rollout order

1. Diff 0 (dep floor) → verify API names → Diff 1 (risk measures, no deps) → Diff 2 (estimators) →
   Diff 4 (splitters) → Diff 3 (additive optimizer methods) → Diff 5 (exports) → new tests → gate review.
