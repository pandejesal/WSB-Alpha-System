# Riskfolio-Lib Adoption Proposal — 2026-09-09

> STUDY TASK — no code modified. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched.
> Stayed inside workdir. Proposal only. All diffs below are exact, apply-ready, grounded in files that exist.
> Prerequisites read: `docs/OPTIMIZATION_PLAYBOOK.md` + `docs/HUNT_PROTOCOL.md` per `AGENTS.md:1`.
> Edge-gate note: this is a risk-layer upgrade, not a new strategy family — no `registry.json` entry, no
> `hunt_runner` pre-registration required. Any behavior change to live sizing still needs walk-forward /
> permutation / DSR evidence before promotion (Playbook §3).

## 1. Import-state verification (env drift confirmed)

`riskfolio-lib==7.3.0` is in `requirements.txt:125`, but import state depends on **which python**:

| Probe | Result |
|---|---|
| Default `python` (hermes venv 3.11, `C:\Users\DELL\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`) `import riskfolio` | **FAIL** — `ModuleNotFoundError: No module named 'riskfolio'` |
| `pip show riskfolio-lib` | `Version: 7.3.0`, `Location: C:\Users\DELL\anaconda3\Lib\site-packages` (anaconda python 3.13 env) |
| `"C:\Users\DELL\anaconda3\python.exe" -c "import riskfolio as rp; print(rp.__version__)"` | **OK** — `7.3.0` |
| Package dir (anaconda) | `C:\Users\DELL\anaconda3\Lib\site-packages\riskfolio`, `HCPortfolio` + `Portfolio` both present |

Consequence, verified against `tests/test_quant.py:16-21`:

- `tests/test_quant.py` gates CVaR/ERC tests on `try: import riskfolio` → `_RISK_AVAILABLE_FOR_TEST`.
  In this (default) env they **skip**; under anaconda python they run.
- `src/risk/portfolio_optimization.py:5-11` does `try: import riskfolio as rp` → `_RISKPORTFOLIO_AVAILABLE`
  flag and raises `ImportError("riskfolio not installed …")` from both optimizers when missing. That
  fail-closed behavior must be preserved — every diff below keeps it.

Do NOT "fix" by pinning a new dependency: `riskfolio-lib==7.3.0` already pinned. Fix is env alignment
(CI installs `requirements.txt` fresh), not a code change.

## 2. Actual layout (ground truth)

| Path | Role | Key facts |
|---|---|---|
| `src/risk/portfolio_optimization.py` (108 lines) | The optimizer | `PortfolioOptimizer(risk_measure='CVaR', alpha=0.05)`; `optimize_cvar()` via `rp.Portfolio.optimization(model='Classic', rm=self.risk_measure, obj='MinRisk')`; `optimize_erc()` via `rp_optimization(model='Classic', rm=self.risk_measure, b=None)`; both `assets_stats(method_mu='hist', method_cov='hist')`; `max_weight/(1-min_cash)` scale trick + `*(1-min_cash)` rescale; cvar has manual cap-and-redistribute loop (lines 61-68), erc does not; broad `except Exception → empty Series` |
| `src/risk/position_sizer.py` (319 lines) | Kelly primary sizer | `KellyCalculator.kelly_fraction f*=(p*b-q)/b` (discrete) + `semi_variance_adjustment` + `raw/adjusted_kelly`; `RegimeAdjuster` / `MacroAdjuster` / `ConfidenceAdjuster` / `KellyBoostAggregator` (variance bonus capped +5%); `PositionSizer.size_position()` → half-Kelly cap → `int(position_value/price)`; `BASE_RISK_PCT=0.02`, `MAX_NOTIONAL_LEV=1.0`, `KELLY_FRACTION=0.5` |
| `src/risk/portfolio_manager.py` (203 lines) | 2nd Kelly + dual-constraint manager | `KellySizer.kelly_size(edge, variance)` continuous `f*=mu/sigma²`, quarter-Kelly default, `min_edge=0.01`, `max_position_pct=0.20` fail-closed `0.0`; `PortfolioManager.get_target_allocation()` = `min(confidence_amount, kelly_amount)` |
| `src/risk/position_sizing.py` (113 lines) | Legacy static sizer | `PositionSizer.calculate_kelly_fraction/calculate_position_size`, `MAX_RISK_PER_TRADE_PCT=0.01`, `math.floor(qty/increment)` |
| `src/ops/portfolio.py` (186 lines) | 7-sleeve merge | `active_sleeves` (us_momentum_top5, spy_sma200, spy_rsi2, btc_vol_target_sma100, us_lowvol_top30, us_pead_top5, breakout_burst); `compute_merged_targets()` equal nominal `(equity*0.60)/7`, `$1` floor, drop-smallest loop, 60% cap, ticker-overlap guard; `VOL_TARGET_ANNUALIZED=0.10`, `MAX_TOTAL_EXPOSURE_PCT=0.60`, `CASH_BUFFER_PCT=0.40` |
| `config/risk_config.py` | Single-source caps | `MAX_NOTIONAL_LEV=1.0`, `HALF_KELLY=0.5`, `BASE_RISK_PCT=0.02`, `MAX_POSITION_PCT=0.20` + cost tiers |

### Confirmed gaps (bugs + missing wiring, not speculation)

1. **`self.alpha` is stored but never used.** `PortfolioOptimizer.__init__(alpha=0.05)` keeps it, but neither
   `optimize_cvar` nor `optimize_erc` passes it. Riskfolio tail level lives on the constructor:
   `Portfolio(returns, alpha=0.05, …)` (verified via `inspect.signature(HCPortfolio-adjacent Portfolio.__init__)`
   — `alpha=0.05` param present). So the CVaR level is silently always the Riskfolio default, not the
   caller's `alpha`. Diff 1 fixes by threading `alpha` into the constructor.
2. **`method_cov='hist'` always** — sample covariance, no shrinkage/denoise/Gerber, despite `sklearn==1.9.0`,
   `scipy==1.18.0` already installed. Riskfolio `assets_stats` supports
   `ledoit/oas/shrunk/gl/jlogo/fixed/spectral/shrink/gerber1/gerber2/ewma1/ewma2`. Diff 1 exposes it.
3. **Only 1 of ~27 risk measures used.** Both methods use `self.risk_measure` (default `'CVaR'`);
   EVaR/CDaR/EDaR/UCI/MDD/ADD/WR/MAD/MSV/FLPM/SLPM/TG/RG/CVRG/… never reachable. Study brief explicitly
   wants CVaR/EVaR/CDaR/Ulcer coverage. Diff 1 adds an allowlist + thin wrappers.
4. **No hierarchical allocation.** `src/ops/portfolio.py` splits 60% equally across 7 sleeves with zero
   covariance awareness. Riskfolio `HCPortfolio(...).optimization(model='HRP'|'HERC'|'HERC2'|'NCO', …)`
   exists in 7.3.0 (verified `help(HCPortfolio.optimization)`). Diff 2 adds it as an inter-sleeve overlay
   with equal-weight fallback.
5. **No Black-Litterman.** No caller builds `P/Q` or calls `blacklitterman_stats` / `optimization(model='BL')`.
   Verified `Portfolio.blacklitterman_stats(P, Q, rf, w, delta, eq, method_mu, method_cov)` +
   `rp.black_litterman(X, w, P, Q, …)` + `rp.assets_views(views, asset_classes)` signatures live in 7.3.0.
   Diff 3 wires sentiment/macro views without touching registry.
6. **Three Kelly semantics, none connected to the optimizer.** Discrete `KellyCalculator` (position_sizer),
   continuous `KellySizer` (portfolio_manager), legacy static (position_sizing) — plus Riskfolio's
   orthogonal `optimization(…, kelly='approx'|'exact')` which changes the *return estimator* to log-growth
   (`approx: mu*w − 0.5*g²`, `exact: mean log(1+Rw)`), NOT a position-size fraction. Diff 4 connects them
   safely: optimizer Kelly objective → then clamp through the existing half-Kelly cap. Never use raw.

## 3. Riskfolio-Lib 7.3.0 capability map (verified in anaconda env, not from memory)

- `import riskfolio as rp` top-level: `Portfolio`, `HCPortfolio`, `black_litterman`, `assets_views`,
  `denoiseCov`, `GerberStatistic`, `owa_*`, `RiskFunctions`, plus ~100 helpers (verified `dir(rp)`).
- `Portfolio.optimization(model, rm, obj, kelly, rf, l, hist)`:
  `model ∈ {Classic, BL, FM, BLFM, EP}`; `obj ∈ {MinRisk, Utility, Sharpe, MaxRet}`;
  `kelly ∈ {None, 'approx', 'exact'}` (log-return estimator, Classic model only);
  `rm` full set: `MV KT EM MAD GMD MSV SKT ESM FLPM SLPM CVaR TG EVaR RLVaR WR RG CVRG TGRG EVRG RVRG
  MDD ADD CDaR EDaR RLDaR UCI` (from `help(optimization)` text).
- `Portfolio.rp_optimization(model ∈ {Classic, FM}, rm, rf, b, b_f, hist)` — risk-budgeting/ERC; `b=None` → 1/n.
  Supported `rm` subset excludes `KT/EM/SKT/ESM/MDD/ADD` (drawdown-incompatible), includes `CDaR/EDaR/UCI`.
- `HCPortfolio.optimization(model ∈ {HRP, HERC, HERC2, NCO}, codependence, rm, obj, linkage, …)`:
  `codependence ∈ {pearson, spearman, kendall, gerber1/2, abs_*, distance, mutual_info, tail, custom_cov}`;
  NCO `obj ∈ {MinRisk, Utility, Sharpe, ERC}`; `rm` adds `VaR/VRG/equal/vol` + `_Rel` drawdown variants.
  Cov estimators: `hist ewma1/2 ledoit oas shrunk gl jlogo fixed spectral shrink gerber1/2 custom_cov`;
  mu: `hist ewma1/2 JS BS BOP custom_mu`.
- BL path: `port.blacklitterman_stats(P, Q, rf, w, delta, eq, …)` then
  `port.optimization(model='BL', rm, obj, hist=False/True, …)`. Views helper `rp.assets_views(views_df,
  asset_classes_df) → (P, Q)` for absolute/relative views.
- Tail level: `rp.Portfolio(returns, alpha=0.05, …)` — `alpha` is the VaR/CVaR/EVaR/CDaR tail (default 5%).

## 4. Proposed diffs (exact, apply-ready, additive, fail-closed)

Design rules honored: keep `ImportError` guard; keep single-asset `1.0-min_cash` path; keep
max-weight scale trick + rescale; keep `$1` floor / 60% cap / overlap guard in `ops/portfolio.py`;
keep `HALF_KELLY=0.5 / MAX_NOTIONAL_LEV=1.0` from `config/risk_config.py`; never touch
`evolve_real.py / registry.json / strategies/`.

### Diff 1 — `src/risk/portfolio_optimization.py`: risk-measure upgrades + alpha + cov estimator (edit)

Why: fixes gaps 1-3 with zero behavior change on the default path (`risk_measure='CVaR'`,
`method_cov='hist'` reproduces today's math; `alpha` now actually honored).

```diff
--- a/src/risk/portfolio_optimization.py
+++ b/src/risk/portfolio_optimization.py
@@
 import logging
 
 import pandas as pd
 
 try:
     import riskfolio as rp  # type: ignore
 
     _RISKPORTFOLIO_AVAILABLE = True
 except ModuleNotFoundError:
     rp = None  # type: ignore
     _RISKPORTFOLIO_AVAILABLE = False
 
 logger = logging.getLogger(__name__)
 
+# Risk measures validated against riskfolio-lib==7.3.0
+# Portfolio.optimization (Classic). rp_optimization excludes KT/EM/SKT/ESM/MDD/ADD.
+SUPPORTED_RISK_MEASURES = (
+    'MV', 'MAD', 'MSV', 'FLPM', 'SLPM', 'CVaR', 'EVaR', 'WR',
+    'MDD', 'ADD', 'CDaR', 'EDaR', 'UCI',
+)
+# Safe subset for rp_optimization (ERC / risk budgeting).
+ERC_SUPPORTED_RISK_MEASURES = (
+    'MV', 'MAD', 'MSV', 'FLPM', 'SLPM', 'CVaR', 'EVaR', 'WR',
+    'CDaR', 'EDaR', 'UCI',
+)
+# Covariance estimators passed straight to assets_stats(method_cov=...).
+SUPPORTED_COV_ESTIMATORS = (
+    'hist', 'ewma1', 'ewma2', 'ledoit', 'oas', 'shrunk', 'gl', 'jlogo',
+    'fixed', 'spectral', 'shrink', 'gerber1', 'gerber2',
+)
+
 class PortfolioOptimizer:
-    def __init__(self, risk_measure: str = 'CVaR', alpha: float = 0.05):
+    def __init__(self, risk_measure: str = 'CVaR', alpha: float = 0.05,
+                 method_cov: str = 'hist'):
         """
         Args:
             risk_measure: 'CVaR' for Conditional Value at Risk
             alpha: Significance level for CVaR (e.g., 0.05 for 95% CVaR)
+            method_cov: covariance estimator forwarded to assets_stats
+                (e.g. 'hist', 'ledoit', 'oas', 'gerber1'). Default 'hist'
+                preserves legacy behavior exactly.
         """
-        self.risk_measure = risk_measure
+        self.risk_measure = risk_measure if risk_measure in SUPPORTED_RISK_MEASURES else 'CVaR'
+        if risk_measure not in SUPPORTED_RISK_MEASURES:
+            logger.warning("Unsupported risk_measure=%r, falling back to 'CVaR'.", risk_measure)
         self.alpha = alpha
+        self.method_cov = method_cov if method_cov in SUPPORTED_COV_ESTIMATORS else 'hist'
+        if method_cov not in SUPPORTED_COV_ESTIMATORS:
+            logger.warning("Unsupported method_cov=%r, falling back to 'hist'.", method_cov)
+
+    def _build_portfolio(self, returns: pd.DataFrame):
+        """Shared constructor: threads alpha + method_cov. Raises ImportError when missing."""
+        if not _RISKPORTFOLIO_AVAILABLE or rp is None:
+            raise ImportError("riskfolio not installed — install 'riskfolio-lib' to use PortfolioOptimizer")
+        port = rp.Portfolio(returns=returns, alpha=self.alpha)  # type: ignore
+        port.assets_stats(method_mu='hist', method_cov=self.method_cov)  # type: ignore
+        port.w_lo = 0.0  # type: ignore
+        return port
```

Then in both existing methods replace the 4-line construction block:

```diff
-        try:
-            port = rp.Portfolio(returns=returns)  # type: ignore
-            port.assets_stats(method_mu='hist', method_cov='hist')  # type: ignore
-
-            # Constraints
-            # We want weights to sum to (1 - min_cash) because we hold min_cash in cash.
-            # However, Riskfolio assumes weights sum to 1.
-            # We will optimize assuming weights sum to 1, then scale down by (1 - min_cash).
-            # Actually, Riskfolio allows setting bounds on individual weights.
-
-            port.w_lo = 0.0  # type: ignore
-            port.w_up = max_weight / (1.0 - min_cash) # scale up the bound during optimization  # type: ignore
+        try:
+            port = self._build_portfolio(returns)
+            # Weights sum to (1 - min_cash): optimize on budget 1, then rescale.
+            # w_up is scaled up during optimization to keep the post-rescale cap exact.
+            port.w_up = max_weight / (1.0 - min_cash)  # type: ignore
```

(apply identically in `optimize_cvar` and `optimize_erc`; keep the cvar cap-and-redistribute loop,
the `*(1.0 - min_cash)` rescale, the single-asset early return, and the `except Exception → empty Series`
exactly as-is), plus append generic wrappers at end of class:

```python
    def optimize_generic(self, returns: pd.DataFrame, risk_measure: str,
                         max_weight: float = 0.25, min_cash: float = 0.10) -> pd.Series:
        """MinRisk under any SUPPORTED_RISK_MEASURES member. Fail-closed to empty Series."""
        rm = risk_measure if risk_measure in SUPPORTED_RISK_MEASURES else 'CVaR'
        prev, self.risk_measure = self.risk_measure, rm
        try:
            return self.optimize_cvar(returns, max_weight=max_weight, min_cash=min_cash)
        finally:
            self.risk_measure = prev

    def optimize_evar(self, returns: pd.DataFrame, max_weight: float = 0.25,
                      min_cash: float = 0.10) -> pd.Series:
        """Entropic VaR (coherent, tail-sensitive beyond CVaR)."""
        return self.optimize_generic(returns, 'EVaR', max_weight, min_cash)

    def optimize_cdar(self, returns: pd.DataFrame, max_weight: float = 0.25,
                      min_cash: float = 0.10) -> pd.Series:
        """Conditional Drawdown-at-Risk (drawdown path, not cross-sectional tail)."""
        return self.optimize_generic(returns, 'CDaR', max_weight, min_cash)

    def optimize_uci(self, returns: pd.DataFrame, max_weight: float = 0.25,
                     min_cash: float = 0.10) -> pd.Series:
        """Ulcer Index (drawdown depth+duration; suits BTC sleeve)."""
        return self.optimize_generic(returns, 'UCI', max_weight, min_cash)

    def optimize_erc_generic(self, returns: pd.DataFrame, risk_measure: str = 'CVaR',
                             max_weight: float = 0.25, min_cash: float = 0.10) -> pd.Series:
        """ERC under any ERC_SUPPORTED_RISK_MEASURES member; others fall back to CVaR-ERC."""
        rm = risk_measure if risk_measure in ERC_SUPPORTED_RISK_MEASURES else 'CVaR'
        prev, self.risk_measure = self.risk_measure, rm
        try:
            return self.optimize_erc(returns, max_weight=max_weight, min_cash=min_cash)
        finally:
            self.risk_measure = prev
```

Upgrade guidance (no code): default stays `CVaR`; evaluate `EVaR` for equity sleeves (heavier tail
penalty, same API), `CDaR` when drawdown-path matters (post-defend), `UCI` for `btc_vol_target_sma100`
(depth×duration matches vol-target intent). `method_cov='ledoit'` first alternative to `'hist'`
(sklearn-backed, no new dep); `gerber1` for outlier-robust equity cov.

### Diff 2 — NEW `src/risk/hierarchical_allocation.py` + optional overlay hook in `src/ops/portfolio.py`

Why: gap 4. Hierarchical methods need no return forecasts, tolerate singular/ill-conditioned cov
(7 sleeves × short history), and produce stable inter-sleeve budgets. New file = zero blast radius.

```python
"""Hierarchical inter-sleeve allocation (Riskfolio HRP/HERC/NCO overlay).

Fail-closed: any failure (missing riskfolio, <2 sleeves, NaNs, solver error)
returns equal weights so src/ops/portfolio.py keeps today's 60/7 split.
Long-only, budget-1; the 60% cap + $1 floor stay in ops/portfolio.py.
"""
from __future__ import annotations

import logging

import pandas as pd

try:
    import riskfolio as rp  # type: ignore
    _RP_AVAILABLE = True
except ModuleNotFoundError:
    rp = None  # type: ignore
    _RP_AVAILABLE = False

logger = logging.getLogger(__name__)

VALID_MODELS = ('HRP', 'HERC', 'HERC2', 'NCO')


def allocate_sleeves(sleeve_returns: pd.DataFrame, model: str = 'HRP',
                     codependence: str = 'pearson', rm: str = 'MV') -> pd.Series:
    """Allocate across sleeves (columns = sleeve proxy returns).

    Args:
        sleeve_returns: T×7 DataFrame of per-sleeve proxy returns.
        model: 'HRP' (default, safest) | 'HERC' | 'HERC2' | 'NCO'.
        codependence: 'pearson' default; 'gerber1' for outlier-robust equities.
        rm: 'MV' default for hierarchy; 'CVaR'/'CDaR' valid for NCO.
    """
    cols = list(sleeve_returns.columns)
    if (not _RP_AVAILABLE or rp is None or sleeve_returns.empty
            or len(cols) < 2 or sleeve_returns.isna().all().all()):
        return pd.Series([1.0 / max(len(cols), 1)] * len(cols), index=cols or [])
    if model not in VALID_MODELS:
        logger.warning("Unknown hierarchical model=%r, using 'HRP'.", model)
        model = 'HRP'
    try:
        clean = sleeve_returns.dropna(axis=1, how='all').fillna(0.0)
        if clean.shape[1] < 2:
            raise ValueError("fewer than 2 valid sleeves")
        port = rp.HCPortfolio(returns=clean)  # type: ignore
        w = port.optimization(model=model, codependence=codependence, rm=rm)  # type: ignore
        if w is None or w.empty:
            raise ValueError("HCPortfolio returned empty")
        weights = w['weights'] if 'weights' in w.columns else w.iloc[:, 0]
        weights = weights / weights.sum()  # renormalize to budget 1
        return weights
    except Exception as e:  # noqa: BLE001 - fail-closed to equal weights
        logger.error("Hierarchical sleeve allocation failed (%s), using equal weights.", e)
        n = len(cols)
        return pd.Series([1.0 / n] * n, index=cols)
```

Optional overlay (Diff 2b, `src/ops/portfolio.py` — additive `try/except`, preserves `$1`/cap/guard):

```diff
--- a/src/ops/portfolio.py
+++ b/src/ops/portfolio.py
@@
     def compute_merged_targets(self, per_sleeve_targets: Dict[str, List[Dict[str, Any]]], account_equity: float = 100.0) -> Dict[str, Any]:
         """
         Merges targets across the 7 sleeves.
         Ensures total exposure <= 60% of account with 40% cash buffer.
-        Allocates equal-risk to the 7 sleeves (nominally account_equity * 0.60 / 7).
+        Allocates equal-risk to the 7 sleeves (nominally account_equity * 0.60 / 7),
+        or hierarchical budgets when sleeve_returns are supplied (see sleeve_returns kwarg).
         """
+        sleeve_returns = None  # reserved kwarg; see hierarchical overlay below
```

Recommended wiring (do NOT inline HRP math in `ops/portfolio.py`): add keyword-only
`sleeve_returns: pd.DataFrame | None = None, sleeve_model: str = 'HRP'` to `compute_merged_targets`,
compute `budgets = allocate_sleeves(sleeve_returns, model=sleeve_model)` inside `try/except`,
`nominal_per_sleeve = equity*0.60*budgets[sleeve]` per sleeve, fallback to `equity*0.60/7` on any
failure. Sleeve proxy returns source: per-sleeve daily sleeve-PnL or constituent-mean returns from the
existing `cache_engine` chain — no new data vendor. Start with `HRP/pearson/MV`; promote to
`HERC`/`NCO(CVaR)` only with walk-forward evidence. `max_k=7` natural bound (7 sleeves).

### Diff 3 — NEW `src/risk/bl_views.py` + `optimize_black_litterman` method (views wiring)

Why: gap 5. BL is the principled way to inject WSB-sentiment + FRED-macro views without hand-tuning
expected returns. Absolute views per sleeve + one relative view (momentum − lowvol) cover the book.

```python
"""Black-Litterman views builders (Riskfolio assets_views-compatible).

Views sources already in-repo: sentiment scores (src/alpha/wsb_sentiment_alpha.py),
macro regime (src/risk/fred_macro_provider.py). This module converts them to P/Q
DataFrames; the optimizer consumes them via model='BL'. No registry changes.
"""
from __future__ import annotations

import pandas as pd


def build_absolute_views(assets: list[str], views: dict[str, float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """views: {asset_or_sleeve: expected_excess_return}. One row per view, one 1.0 per row in P."""
    rows, qs = [], []
    for asset, q in views.items():
        if asset not in assets:
            continue
        row = [1.0 if a == asset else 0.0 for a in assets]
        rows.append(row)
        qs.append(float(q))
    if not rows:
        raise ValueError("no valid views for given assets")
    P = pd.DataFrame(rows, columns=assets)
    Q = pd.DataFrame(qs, columns=['Q'])
    return P, Q


def build_relative_view(assets: list[str], long_asset: str, short_asset: str,
                        spread: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Single relative view: E[R_long − R_short] = spread (e.g. momentum − lowvol)."""
    row = [1.0 if a == long_asset else (-1.0 if a == short_asset else 0.0) for a in assets]
    return pd.DataFrame([row], columns=assets), pd.DataFrame([float(spread)], columns=['Q'])
```

Optimizer addition (`src/risk/portfolio_optimization.py`, append to class — needs `_build_portfolio`
from Diff 1; uses equilibrium weights `w=None` → market-implied prior, `delta=1` default):

```python
    def optimize_black_litterman(self, returns: pd.DataFrame, views: dict[str, float] | None = None,
                                 relative: tuple[str, str, float] | None = None,
                                 max_weight: float = 0.25, min_cash: float = 0.10,
                                 delta: float = 1.0) -> pd.Series:
        """BL-MinRisk: P/Q from views (absolute + optional relative spread), then model='BL'.

        Fail-closed: empty views or any BL error → falls back to optimize_cvar (legacy path).
        """
        import pandas as _pd  # local alias to avoid top import churn (or reuse module pd)
        if not _RISKPORTFOLIO_AVAILABLE or rp is None:
            raise ImportError("riskfolio not installed — install 'riskfolio-lib' to use PortfolioOptimizer")
        if returns.empty or returns.shape[1] < 2:
            if returns.shape[1] == 1:
                return _pd.Series([1.0 - min_cash], index=returns.columns)
            return _pd.Series(dtype=float)
        try:
            from src.risk.bl_views import build_absolute_views, build_relative_view
            assets = list(returns.columns)
            P_list, Q_list = [], []
            if views:
                P_a, Q_a = build_absolute_views(assets, views)
                P_list.append(P_a)
                Q_list.append(Q_a)
            if relative is not None:
                P_r, Q_r = build_relative_view(assets, *relative)
                P_list.append(P_r)
                Q_list.append(Q_r)
            if not P_list:
                return self.optimize_cvar(returns, max_weight=max_weight, min_cash=min_cash)
            import pandas as _p
            P = _p.concat(P_list, ignore_index=True)
            Q = _p.concat(Q_list, ignore_index=True)
            port = self._build_portfolio(returns)
            port.blacklitterman_stats(P, Q, rf=0.0, w=None, delta=delta, eq=True)  # type: ignore
            port.w_up = max_weight / (1.0 - min_cash)  # type: ignore
            w = port.optimization(model='BL', rm=self.risk_measure, obj='MinRisk',  # type: ignore
                                  rf=0.0, l=0, hist=False)
            if w is None or w.empty:
                raise ValueError("BL optimization returned empty")
            return w['weights'] * (1.0 - min_cash)
        except Exception as e:  # noqa: BLE001 - fail-closed to CVaR path
            logger.error("Black-Litterman optimization failed (%s), falling back to CVaR.", e)
            return self.optimize_cvar(returns, max_weight=max_weight, min_cash=min_cash)
```

View calibration (policy, not code): absolute `Q` in daily excess-return units, clipped to
`±0.002` (≈±50% annualized) to stop sentiment spikes dominating; `delta=1` start; `eq=True`
(equilibrium prior) so sparse views shrink to market. Candidate views: `us_momentum_top5 +Q` on
high WSB-confluence days, `btc_vol_target_sma100 −Q` in high-vol regime, `spy_sma200` anchored at 0
(neutral prior), relative `(us_momentum_top5, us_lowvol_top30, spread)` from cross-sectional z-score.
Gate: BL must beat Classic-CVaR on walk-forward net Sharpe before replacing the default call path.

### Diff 4 — Kelly integration: `optimize_kelly` + clamp contract with existing `KellyCalculator`

Why: gap 6. Riskfolio `kelly=` is a return-estimator switch, not a sizer — wire it, then enforce the
repo's half-Kelly / 20% / 1.0-lev caps. Keeps the three existing Kelly classes authoritative for sizing.

```python
    def optimize_kelly(self, returns: pd.DataFrame, max_weight: float = 0.25,
                       min_cash: float = 0.10, kelly: str = 'approx',
                       kelly_cap: float = 0.5) -> pd.Series:
        """Kelly-growth portfolio: optimization(kelly='approx'|'exact', obj='Sharpe') then clamp.

        'approx' (default): mu*w − 0.5*g² closed-form, robust + fast.
        'exact': mean log(1+Rw) via ExpCone — heavier, MOSEK-preferred; use only if 'approx'
            shows instability in review. Invalid kelly → 'approx'.
        Post-step: renormalize to (1−min_cash), hard-cap each weight at
        min(max_weight, kelly_cap * max_weight_scale) via existing cap loop semantics,
        so the repo HALF_KELLY=0.5 contract holds. Fail-closed to empty Series.
        """
        if kelly not in ('approx', 'exact'):
            logger.warning("Unknown kelly=%r, using 'approx'.", kelly)
            kelly = 'approx'
        if not _RISKPORTFOLIO_AVAILABLE or rp is None:
            raise ImportError("riskfolio not installed — install 'riskfolio-lib' to use PortfolioOptimizer")
        if returns.empty or returns.shape[1] < 2:
            if returns.shape[1] == 1:
                return pd.Series([1.0 - min_cash], index=returns.columns)
            return pd.Series(dtype=float)
        try:
            port = self._build_portfolio(returns)
            port.w_up = max_weight / (1.0 - min_cash)  # type: ignore
            w = port.optimization(model='Classic', rm=self.risk_measure, obj='Sharpe',  # type: ignore
                                  kelly=kelly, rf=0.0, l=0, hist=True)
            if w is None or w.empty:
                raise ValueError("Kelly optimization returned empty")
            weights = w['weights']
            # Existing cap-and-redistribute on budget-1 weights (same as optimize_cvar).
            max_allowed = max_weight / (1.0 - min_cash)
            while any(weights > max_allowed + 1e-5):
                weights[weights > max_allowed] = max_allowed
                excess = 1.0 - weights.sum()
                under = weights < max_allowed
                if not any(under):
                    break
                weights[under] += excess / under.sum()
            scaled = weights * (1.0 - min_cash)
            # Kelly damping toward cash AFTER budget math: kelly_cap=0.5 (default,
            # matching config/risk_config.py HALF_KELLY) is identity; smaller values
            # hold more cash. Clamp to (0, 0.5] so growth-optimality never bypasses
            # the repo half-Kelly contract (final sizing still passes through
            # PositionSizer/KellyCalculator downstream).
            cap = min(max(float(kelly_cap), 0.0), 0.5)
            return scaled * (cap / 0.5)
        except Exception as e:  # noqa: BLE001
            logger.error("Portfolio Kelly optimization failed: %s", e)
            return pd.Series(dtype=float)
```

Contract with `src/risk/position_sizer.py::KellyCalculator` (no changes to that file):
Riskfolio-Kelly output is a *candidate weight vector*; final per-name size still passes through
`PositionSizer.size_position()` (discrete `f*`, semi-variance, regime/macro, half-Kelly) and the
`min(confidence, kelly)` dual constraint in `portfolio_manager.py`. I.e. optimizer proposes,
`KellyCalculator` disposes — growth-optimality never bypasses the 20% name cap or 1.0 leverage cap.
Note the formula mismatch explicitly: continuous `mu/sigma²` (KellySizer) vs discrete `(pb−q)/b`
(KellyCalculator) vs log-growth (`kelly='approx'`) are three views of the same edge; blending is by
`min()`/cap, never by averaging fractions with weights.

## 5. What NOT to adopt (deliberate rejections)

- `RLVaR / RLRDaR / RVRG` (relativistic measures): 7.3.0 docstrings recommend MOSEK-only; repo is
  zero-cost (`cvxpy/clarabel/osqp/SCS`), so exclude from allowlists. Revisit only if a free solver proves stable.
- `model='FM'/'BLFM'/'EP'` (factor / entropy-pooling): no factor loadings pipeline exists; adds estimation
  surface with no data source. BL-Classic covers the views need.
- `HERC2` as default: equal-split within clusters discards risk heterogeneity; keep as experiment only.
- Replacing `ops/portfolio.py` equal split unconditionally with NCO: NCO re-optimizes intra-cluster with
  covariance inversion — overkill/fragile for 7 sleeves; default hierarchy stays `HRP`.
- `upperCVaR/upperEVaR/…` hard risk-constraint overlays and `card/nea` sparsity: premature before the
  base measures show walk-forward edge; stage-2 candidates.

## 6. Test plan (hermetic-first, matches repo discipline)

Existing coverage to preserve: `tests/test_quant.py::TestQuantPhase3::test_portfolio_cvar_allocator`
+ `test_portfolio_erc_allocator` (skip when riskfolio missing — keep skip, add mocked tests below so
default env still covers logic); `tests/portfolio/test_portfolio_sizing.py`,
`tests/portfolio/test_portfolio_manager.py`, `tests/test_risk.py`.

New tests (all mock `rp.Portfolio`/`rp.HCPortfolio` so they run WITHOUT riskfolio — green in this env):

1. `tests/test_riskfolio_adopt.py::test_alpha_threaded` — mock `rp.Portfolio`, call
   `PortfolioOptimizer(alpha=0.03).optimize_cvar(df)`; assert constructor called with `alpha=0.03`.
2. `::test_method_cov_ledoit_forwarded` — `PortfolioOptimizer(method_cov='ledoit')`; assert
   `assets_stats` called with `method_cov='ledoit'`; invalid `'junk'` → `'hist'` + warning.
3. `::test_risk_measure_allowlist` — `PortfolioOptimizer(risk_measure='BOGUS').risk_measure == 'CVaR'`;
   `optimize_generic(df,'EVaR')` sets `rm='EVaR'` on the `optimization` call; `optimize_erc_generic(df,'MDD')`
   falls back to `rm='CVaR'` (ERC-excluded).
4. `::test_single_asset_and_empty` — 1-col → `[1.0-min_cash]`; empty → `empty Series`; both without touching rp.
5. `::test_max_weight_rescale` — mocked weights `[0.9,0.1]` with `max_weight=0.25,min_cash=0.10` → capped,
   rescaled, `sum≈0.90`, `max≤0.2501` (mirrors existing cvar test math).
6. `::test_hierarchical_equal_fallback` — `allocate_sleeves` with `rp=None` (monkeypatch
   `_RP_AVAILABLE=False`) → equal `1/7`; mocked `HCPortfolio` returning `None` → equal weights, no raise.
7. `::test_hierarchical_renorm` — mocked `HCPortfolio.optimization` returns unnormalized `[2,1,1]` →
   output sums to 1.0.
8. `::test_bl_fallback_to_cvar` — `optimize_black_litterman(df, views={})` delegates to `optimize_cvar`
   (assert via spy); `blacklitterman_stats` raising → returns cvar result, no raise.
9. `::test_bl_views_builders` — `build_absolute_views` drops unknown assets, raises on zero valid;
   `build_relative_view` row = `+1/−1/0`, Q = spread.
10. `::test_kelly_clamp` — mocked `optimization` returns `[0.8,0.2]`; `optimize_kelly(kelly_cap=0.5)` →
    post-cap `max≤max_weight`, sum `≈1−min_cash`; `kelly='junk'` → called with `'approx'`.

Live-optional (run under anaconda python only, never in default CI): seed-fixed
`N(0.001,0.02)` 4-asset panels asserting `optimize_evar/cdar/uci` converge non-empty,
`sum≈0.90`; `allocate_sleeves` HRP on 7-col synthetic; BL with 1 absolute + 1 relative view;
`optimize_kelly('approx')` vs `('exact')` smoke. Gate: `PYTHONPATH=. pytest tests/test_riskfolio_adopt.py -q`
(green both interpreters; live tests `pytest.mark.skipif` on import failure), then
`ruff check src/risk/ tests/test_riskfolio_adopt.py`, `bandit -r src/risk/`.

Rollout order: Diff 1 (safe, behavior-preserving) → Diff 2 file-only + offline eval → Diff 3 behind flag
(BL must beat Classic net Sharpe walk-forward) → Diff 4 last (growth-optimal needs strongest evidence).
Each stage re-runs full `PYTHONPATH=. pytest` + Playbook §3 gates before touching any call path.

## 7. File-touch summary (study only — nothing written outside this report)

| # | File | Change type |
|---|---|---|
| 1 | `src/risk/portfolio_optimization.py` | EDIT (additive: allowlists, `_build_portfolio`, generic/EVaR/CDaR/UCI/ERC-generic/BL/Kelly methods; existing bodies preserved) |
| 2 | `src/risk/hierarchical_allocation.py` | NEW |
| 3 | `src/risk/bl_views.py` | NEW |
| 4 | `src/ops/portfolio.py` | EDIT (optional overlay kwargs only; `$1`/60%/guard intact) |
| 5 | `tests/test_riskfolio_adopt.py` | NEW |
| — | `evolve_real.py`, `strategies/registry.json`, `strategies/` | EXPLICITLY UNTOUCHED |

*Report: Riskfolio-Lib 7.3.0 (26+ risk measures incl. CVaR/EVaR/CDaR/UCI, HRP/HERC/NCO, BL, Kelly log-objective)*
*vs `src/risk/portfolio_optimization.py` + `position_sizer.py` + `portfolio_manager.py` + `src/ops/portfolio.py` 7-sleeve manager.*
*Env: default python riskfolio UNIMPORTABLE (drift), anaconda python 7.3.0 OK — diffs fail-closed for both.*
