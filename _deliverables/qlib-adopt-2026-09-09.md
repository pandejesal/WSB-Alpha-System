# qlib Alpha158/Alpha360 Adoption Proposal — Missing Operators + IC/IR Harness

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py`, `strategies/registry.json`, `strategies/` untouched per task constraint. Workdir-contained.
Scope: compare upstream `microsoft/qlib` Alpha158/Alpha360 factor pipelines + IC evaluation vs actual repo code `src/signals/qlib_alpha158.py` (47 features) and `src/backtest/validation.py`. Propose past-only `shift(1)` additions, IC/IR harness additions, explicit rejects. Exact diffs + test plan.

Upstream sources read:
- `qlib/contrib/data/loader.py` — `Alpha360DL.get_feature_config` (6×60=360 raw normalized bars) and `Alpha158DL.get_feature_config` (kbar 9 + price + volume + 29 rolling ops × windows [5,10,20,30,60] = 158).
- `qlib/contrib/data/handler.py` — `Alpha158.get_feature_config`: `{"kbar": {}, "price": {"windows": [0], "feature": ["OPEN","HIGH","LOW","VWAP"]}, "rolling": {}}`; label `Ref($close,-2)/Ref($close,-1)-1` (`LABEL0`).
- `examples/benchmarks/README.md` — signal metrics IC / ICIR / RankIC / RankICIR + portfolio metrics AnnRet / IR / MaxDD; Alpha158 tabular vs Alpha360 raw-spatial note.

Actual repo paths verified by read:
- `src/signals/qlib_alpha158.py:1-260` — pandas-only port, `WINDOWS=[5,10,20,30,60]`, `compute_alpha158(df)` + `get_feature_names()` + `get_feature_matrix()`, all feature cols `.shift(1)` at lines 228-231.
- `src/backtest/validation.py:1-382` — `run_in_sample_test` / `run_walk_forward_test` (permutation, `NUM_PERMUTATIONS=200`), SPA via `StatisticalValidator.spa_test`, tearsheet pinned to `run_historic_backtest` (E-1 guard), DSR lives in `src/backtest/defend/trial_ledger.py:388-408`, CPCV in `src/backtest/validators/statistical.py:96-135`.
- `tests/test_qlib_port.py:1-161` — gates: no-lookahead shift, `>=40` features, 12 families `>=4` variants, rotation determinism, SPY baseline, turnover, metric sanity.
- No IC/IR code anywhere: grep for `spearman|rank_ic|information ratio|IC\(` hits only `CRITICAL`/`TICKERS`/lexicon noise — zero factor-evaluation harness. Confirmed gap.

## 1. Gap analysis: actual 47 vs upstream 158

### 1a. What the 47 cover (and where they deviate)

12 windowed families × 5 windows = 60 slots but file reports 47 total, i.e. 12×5=60 would overshoot — actual count is 12 families over 5 windows minus overlap plus 10 extras? Count precisely: loop emits 12 names × 5 windows = 60, plus VWAP, HighROC_10, LowROC_10, CloseHighRatio, CloseLowRatio, LogVolumeChg_5, PriceRange_20, VolumeShock_10, RetDispersion_20, SignedVolume_10 = 70. Docstring "47 features" is STALE (predates family expansion). `get_feature_names()` after a call returns 70, which still satisfies the `>=40` gate but the header lies. Diff 1 fixes the docstring as a drive-by.

Deviation table (local → upstream truth):

| Local family | Local formula | Upstream truth | Verdict |
|---|---|---|---|
| `KMid_{w}` | `EMA(close,w)` | `KMID=($close-$open)/$open` (no window) | WRONG — Keltner-EMA invention, not qlib. Keep column (no break) but add true `Q_KMID` etc alongside; do not rename existing (test + downstream depend). |
| `KLen_{w}` | `mean(H-L,w)` | `KLEN=($high-$low)/$open` | WRONG scale/norm — same handling as above. |
| `KMid2_{w}` | `SMA(close,w)` | `KMID2=($close-$open)/($high-$low+eps)` | WRONG — same handling. |
| `KUp_{w}` | `KMid+0.5*KLen-close` | `KUP=($high-max(open,close))/$open`, plus `KUP2=.../($high-$low)` | WRONG — same handling. Missing `KLOW/KLOW2/KSFT/KSFT2` entirely. |
| `ROC_{w}` | `close.pct_change(w)` = `(C-C_d)/C_d` | `ROC_d=Ref(close,d)/close` = `C_d/C` | INVERTED normalization. Both are monotonic transforms of each other but IC-identical only under Pearson? No — `x` vs `1/(1+x)` is nonlinear; RankIC identical, Pearson IC differs. Add true `ROC` alongside; keep old. |
| `Rank_{w}` | `close.rolling(w).rank(pct=True)` (last-row pct) | `Rank($close,d)` = same percentile | CLOSEST MATCH — keep. |
| `Quantile_{w}` | `(C-Min)/(Max-Min)` over close | `QTLU=Quantile(close,d,0.8)/close`, `QTLD=Quantile(close,d,0.2)/close` | WRONG — local is actually upstream `RSV` restricted to close (upstream RSV uses high/low range). Rename-nothing; add true `QTLU/QTLD/RSV`. |
| `Std_{w}` | `std(log_ret,w)` raw | `STD_d=Std(close,d)/close` | WRONG units — add true `STD`. |
| `Sum/Mean/Max/Min_{w}` | over `ret=pct_change` | `MA=Mean(close)/close`; `MAX=Max(high)/close`; `MIN=Min(low)/close`; no SUM/MEAN-of-returns op upstream | WRONG base series — add true `MA/MAX/MIN`; keep local return-moment set (useful, just not qlib). |
| VWAP etc (10 extras) | ad-hoc | no upstream counterpart (upstream VWAP only as `price` ratio) | KEEP — genuinely useful, zero conflict. |

### 1b. Missing upstream operators (the adopt list)

29 rolling ops upstream; local covers ~4 correctly-ish (ROC-inverted, RANK-ok, QTLU/QTLD-wrong, STD/MAX/MIN-wrong-base). Missing outright:

1. `BETA_d = Slope(close,d)/close` — trend slope.
2. `RSQR_d = Rsquare(close,d)` — trend linearity.
3. `RESI_d = Resi(close,d)/close` — regression residual.
4. `MA_d` (true), `STD_d` (true), `MAX_d` (on high), `MIN_d` (on low).
5. `QTLU_d/QTLD_d` (true quantile/close).
6. `RSV_d = (close-Min(low,d))/(Max(high,d)-Min(low,d)+eps)` — stochastic position.
7. `IMAX_d = IdxMax(high,d)/d`, `IMIN_d = IdxMin(low,d)/d`, `IMXD_d = (IdxMax-IdxMin)/d` — Aroon time-since-extreme.
8. `CORR_d = Corr(close, Log(volume+1), d)` — price-volume level correlation.
9. `CORD_d = Corr(close/Ref(close,1), Log(volume/Ref(volume,1)+1), d)` — change correlation.
10. `CNTP_d = Mean(close>Ref(close,1),d)`, `CNTN_d`, `CNTD_d = CNTP-CNTN` — advance/decline breadth.
11. `SUMP/SUMN/SUMD_d` — gain/loss RSI-style ratios on `close-Ref(close,1)`.
12. `VMA_d = Mean(volume,d)/volume`, `VSTD_d = Std(volume,d)/volume` — volume mean-reversion/vol.
13. `WVMA_d` — volume-weighted price-change volatility.
14. `VSUMP/VSUMN/VSUMD_d` — volume RSI analogues.
15. Kbar remainder: true `KMID/KLEN/KMID2/KUP/KUP2/KLOW/KLOW2/KSFT/KSFT2` (9, window-free).
16. Price ratios: `OPEN0/HIGH0/LOW0/VWAP0 = $field/$close` (window 0; needs vwap — synthesize as `(H+L+C)/3` HLC3 when no vwap column, documented).
17. Alpha360 block: 360 raw normalized lookback columns `CLOSE0..59/OPEN/HIGH/LOW/VWAP/VOLUME` (past-only by construction + final shift(1); 60× scaling warning — research-only, single-ticker diagnostics, never the Alpaca order path).

Out-of-scope for Alpaca paper (reject list, §4) covers the rest of qlib: RL execution (SAOE), DataServer/distributed backtest, workflow DAG, LightGBM/GBDT training infra, CSI300/CN market bundle.

### 1c. IC evaluation gap

Upstream signal evaluation (benchmarks README): per-date cross-sectional `IC = corr(pred, ret_next)`, `RankIC` = Spearman, `ICIR = mean(IC)/std(IC)`, label 2-day-ahead `Ref(close,-2)/Ref(close,-1)-1`. Repo has NONE of this:
- `validation.py` evaluates *strategy trades* (permutation p on return+Sharpe, walk-forward pooled p + win-rate, SPA vs SPY) — no per-*factor* predictive test.
- No cross-sectional framing at all (single-ticker engine); no `LABEL0`; no purge/embargo around the label horizon; no ICIR gating before DSR/permutation spend.
- Consequence: any new operator proposed below would jump straight to the expensive 200-permutation gate with no cheap factor screen. Diff 3 adds that screen.

## 2. Design rules (all additions follow the file's own pattern)

1. Past-only `shift(1)` preserved: every new column joins the existing `feat_cols` shift block (lines 228-231) — no per-operator shifting, no exceptions. Alpha360 block likewise shifted once.
2. No renames, no removals: existing 70 column names frozen (tests + `topk_rotation` downstream). All qlib-true operators use `Q_`-prefixed names (`Q_BETA_20`, `Q_RSV_60`, …) so there is zero collision with `KMid_*/ROC_*/Std_*`.
3. Fail-closed NaN hygiene: `replace(0,nan)` / `+1e-12` eps exactly as upstream; `replace([inf,-inf],nan)`; leave warmup NaN for `get_feature_matrix(dropna=True)`. Never 0-fill a factor.
4. Single-ticker IC first: cross-sectional IC across a symbol universe is the follow-up (needs universe loader); Diff 3 implements time-series IC per symbol + panel-mean ICIR, which is valid for single-name Alpaca screening and documents the extension point.
5. Research-only: additions are columns + diagnostics. No `evolve_real.py`, no `registry.json`, no `strategies/` change. Edge gate (pre-reg → WF → permutation → DSR) still required before any registry entry.

## 3. Exact diffs proposed

### Diff 0 — fix stale header (docstring only, `src/signals/qlib_alpha158.py:1-21`)

```diff
 --- a/src/signals/qlib_alpha158.py
 +++ b/src/signals/qlib_alpha158.py
 @@ -1,7 +1,7 @@
  """qlib Alpha158-style feature library (pandas-only port).
  
 -Ported from microsoft/qlib Alpha158 factor library. Computes 47 features
 +Ported from microsoft/qlib Alpha158 factor library (qlib/contrib/data/loader.py).
 +Computes 70 features (12 windowed families x 5 windows + 10 extras);
  across OHLCV data using rolling windows. All features are lagged by 1 day
  (T+1 execution) to prevent lookahead bias.
```

Rationale: header predates family expansion; count lie confuses every follow-up study. Zero behavior change.

### Diff 1 — NEW `src/signals/qlib_alpha158_extra.py` (missing operators, `Q_`-namespaced, past-only)

New file; imports nothing new (`numpy`/`pandas` only). Caller pattern:

```python
from src.signals import qlib_alpha158 as base
from src.signals import qlib_alpha158_extra as qx
df = base.compute_alpha158(raw)          # 70 cols, shifted
df = qx.add_qlib_true_operators(df, raw) # += Q_* cols, shifted inside
df = qx.add_alpha360(df, raw)            # += CLOSE59..VOLUME0 cols (opt-in flag)
```

Full content proposed (abridged here to operator cores; each helper is ~5 lines of rolling pandas):

```python
"""True-qlib operators missing from qlib_alpha158.py (Q_-namespaced add-ons).

Source: microsoft/qlib qlib/contrib/data/loader.py :: Alpha158DL/Alpha360DL.
All outputs shifted by 1 by the caller-facing wrappers (past-only, same as
compute_alpha158 lines 228-231). Existing 70 columns untouched.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

Q_WINDOWS = [5, 10, 20, 30, 60]
Q_FEATURE_NAMES: list[str] = []

def _register(name): Q_FEATURE_NAMES.append(name); return name

def _slope(s, w):  # BETA core: OLS slope over window
    return s.rolling(w).apply(lambda y: np.polyfit(np.arange(len(y)), y, 1)[0], raw=True)
def _rsquare(s, w):
    def _r(y):
        x = np.arange(len(y)); A = np.vstack([x, np.ones_like(x)]).T
        coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
        ss_tot = ((y - y.mean()) ** 2).sum(); return 1 - res[0] / ss_tot if ss_tot > 0 else np.nan
    return s.rolling(w).apply(_r, raw=True)
def _resi(s, w):  # last residual of OLS fit
    def _e(y):
        x = np.arange(len(y)); a, b = np.polyfit(x, y, 1); return y[-1] - (a * (len(y) - 1) + b)
    return s.rolling(w).apply(_e, raw=True)

def add_qlib_true_operators(df_out, raw):
    """Append Q_* columns to compute_alpha158 output. Both indexed by date."""
    c = raw["close"].astype(float); h = raw["high"].astype(float)
    lo = raw["low"].astype(float); v = raw["volume"].astype(float)
    ref1 = c.shift(1)
    out = df_out.copy()
    # --- kbar 9 (window-free) ---
    out[_register("Q_KMID")]  = (c - raw["open"]) / raw["open"].replace(0, np.nan)
    out[_register("Q_KLEN")]  = (h - lo) / raw["open"].replace(0, np.nan)
    out[_register("Q_KMID2")] = (c - raw["open"]) / (h - lo + 1e-12)
    up = h - pd.concat([raw["open"], c], axis=1).max(axis=1)
    dn = pd.concat([raw["open"], c], axis=1).min(axis=1) - lo
    out[_register("Q_KUP")]   = up / raw["open"].replace(0, np.nan)
    out[_register("Q_KUP2")]  = up / (h - lo + 1e-12)
    out[_register("Q_KLOW")]  = dn / raw["open"].replace(0, np.nan)
    out[_register("Q_KLOW2")] = dn / (h - lo + 1e-12)
    out[_register("Q_KSFT")]  = (2 * c - h - lo) / raw["open"].replace(0, np.nan)
    out[_register("Q_KSFT2")] = (2 * c - h - lo) / (h - lo + 1e-12)
    # --- price ratios window-0 (+HLC3 VWAP fallback) ---
    vwap = raw["vwap"] if "vwap" in raw else (h + lo + c) / 3
    for nm, s in (("Q_OPEN0", raw["open"]), ("Q_HIGH0", h), ("Q_LOW0", lo), ("Q_VWAP0", vwap)):
        out[_register(nm)] = s.astype(float) / c.replace(0, np.nan)
    # --- rolling 26 ops x 5 windows ---
    for w in Q_WINDOWS:
        out[_register(f"Q_ROC_{w}")]  = c.shift(w) / c.replace(0, np.nan)
        out[_register(f"Q_MA_{w}")]   = c.rolling(w).mean() / c.replace(0, np.nan)
        out[_register(f"Q_STD_{w}")]  = c.rolling(w).std() / c.replace(0, np.nan)
        out[_register(f"Q_BETA_{w}")] = _slope(c, w) / c.replace(0, np.nan)
        out[_register(f"Q_RSQR_{w}")] = _rsquare(c, w)
        out[_register(f"Q_RESI_{w}")] = _resi(c, w) / c.replace(0, np.nan)
        out[_register(f"Q_MAX_{w}")]  = h.rolling(w).max() / c.replace(0, np.nan)
        out[_register(f"Q_MIN_{w}")]  = lo.rolling(w).min() / c.replace(0, np.nan)
        out[_register(f"Q_QTLU_{w}")] = c.rolling(w).quantile(0.8) / c.replace(0, np.nan)
        out[_register(f"Q_QTLD_{w}")] = c.rolling(w).quantile(0.2) / c.replace(0, np.nan)
        out[_register(f"Q_RSV_{w}")]  = (c - lo.rolling(w).min()) / (h.rolling(w).max() - lo.rolling(w).min() + 1e-12)
        out[_register(f"Q_IMAX_{w}")] = h.rolling(w).apply(lambda y: np.argmax(y), raw=True) / w  # days-since-high proxy; see note
        out[_register(f"Q_IMIN_{w}")] = lo.rolling(w).apply(lambda y: np.argmin(y), raw=True) / w
        out[_register(f"Q_IMXD_{w}")] = out[f"Q_IMAX_{w}"] - out[f"Q_IMIN_{w}"]
        out[_register(f"Q_CORR_{w}")] = c.rolling(w).corr(np.log(v + 1))
        out[_register(f"Q_CORD_{w}")] = (c / ref1.replace(0, np.nan)).rolling(w).corr(np.log(v / v.shift(1) + 1))
        up_d = (c > ref1).rolling(w).mean(); dn_d = (c < ref1).rolling(w).mean()
        out[_register(f"Q_CNTP_{w}")] = up_d; out[_register(f"Q_CNTN_{w}")] = dn_d
        out[_register(f"Q_CNTD_{w}")] = up_d - dn_d
        chg = c - ref1; ag = chg.clip(lower=0).rolling(w).sum(); al = (-chg).clip(lower=0).rolling(w).sum()
        tot = (chg.abs().rolling(w).sum() + 1e-12)
        out[_register(f"Q_SUMP_{w}")] = ag / tot; out[_register(f"Q_SUMN_{w}")] = al / tot
        out[_register(f"Q_SUMD_{w}")] = (ag - al) / tot
        out[_register(f"Q_VMA_{w}")]  = v.rolling(w).mean() / v.replace(0, np.nan)
        out[_register(f"Q_VSTD_{w}")] = v.rolling(w).std() / v.replace(0, np.nan)
        wv = (abs(c / ref1.replace(0, np.nan) - 1) * v)
        out[_register(f"Q_WVMA_{w}")] = wv.rolling(w).std() / (wv.rolling(w).mean() + 1e-12)
        vchg = v - v.shift(1); vag = vchg.clip(lower=0).rolling(w).sum(); val = (-vchg).clip(lower=0).rolling(w).sum()
        vtot = (vchg.abs().rolling(w).sum() + 1e-12)
        out[_register(f"Q_VSUMP_{w}")] = vag / vtot; out[_register(f"Q_VSUMN_{w}")] = val / vtot
        out[_register(f"Q_VSUMD_{w}")] = (vag - val) / vtot
    new_cols = [n for n in Q_FEATURE_NAMES if n in out.columns]
    out[new_cols] = out[new_cols].shift(1)   # past-only, matches base file
    return out
```

Count: kbar 9 + price 4 + 26 ops × 5 = 143 new `Q_*` columns. Together with base 70 → 213 columns (superset for research; the strict-158 subset = kbar 9 + price 4 + rolling 29×5 restricted to upstream's exact rolling set = 158 — document the mapping table in module docstring; the extra local 55 stay as house factors).

IMAX note: upstream `IdxMax(high,d)` = bars-since-high within window; `argmax` position proxy `pos/d` is documented as approximation (exact bars-since = `w-1-pos`; follow-up may flip — IC-identical under rank, Pearson sign flips, noted in docstring).

`add_alpha360(df_out, raw, lookback=60)` (opt-in, default OFF in tests): for `k in 59..0`: `A360_CLOSE{k}=Ref(close,k)/close`, same for OPEN/HIGH/LOW/VWAP(HLC3 fallback)/`VOLUME{k}=Ref(volume,k)/(volume+eps)`; single `.shift(1)` at end. 360 columns, documented 60× memory warning; excluded from default IC screen (too many trials → DSR penalty) unless explicitly enabled.

### Diff 2 — IC/IR harness NEW `src/backtest/factor_ic.py` (+ thin wiring, no engine change)

```python
"""Per-factor IC/IR screen (qlib-style signal metrics, single-ticker first).

IC_t = Pearson(factor_t, LABEL0_{t+h}); RankIC_t = Spearman.
ICIR = mean(IC)/std(IC); RankICIR likewise. Label default matches qlib
Alpha158 handler: LABEL0 = Ref(close,-2)/Ref(close,-1)-1 (2-day-ahead ret).
Purged: rows with label NaN dropped + `embargo` rows after each NaN gap dropped.
"""
import numpy as np, pandas as pd
from scipy.stats import spearmanr  # scipy already in requirements.txt

def qlib_label(close: pd.Series, horizon: int = 1) -> pd.Series:
    # horizon=1 reproduces Ref(c,-2)/Ref(c,-1)-1 relative to execution bar
    return close.shift(-horizon - 1) / close.shift(-horizon) - 1

def factor_ic(frame, features, close, horizon=1, embargo=5):
    lab = qlib_label(close, horizon)
    valid = lab.dropna().index
    recs = []
    for f in features:
        x = frame[f].reindex(valid); y = lab.reindex(valid)
        m = pd.concat([x, y], axis=1).dropna()
        if len(m) < 30: continue
        ic = m.iloc[:, 0].corr(m.iloc[:, 1])
        ric, _ = spearmanr(m.iloc[:, 0], m.iloc[:, 1])
        # ICIR via expanding-half split halves (time stability proxy)
        h = len(m) // 2
        ic1 = m.iloc[:h, 0].corr(m.iloc[:h, 1]); ic2 = m.iloc[h:, 0].corr(m.iloc[h:, 1])
        recs.append({"feature": f, "IC": ic, "RankIC": ric,
                     "ICIR": np.mean([ic1, ic2]) / (np.std([ic1, ic2]) + 1e-12),
                     "n": len(m)})
    out = pd.DataFrame(recs).sort_values("RankIC", key=abs, ascending=False)
    return out
```

Wiring (additive, `validation.py` untouched): new `scripts/screen_factors_ic.py` runs `compute_alpha158 → add_qlib_true_operators → factor_ic` on `data/spy_ohlcv_2019_2026.csv` (or synthetic fallback), prints top-20 by |RankIC| with gates `|RankIC|>0.02` and `|ICIR|>0.3` (qlib benchmark scale: winning models show IC≈0.03-0.05, ICIR≈0.3-0.4 — factor-level bar set just below model-level). Output CSV `output/factor_ic_screen.csv`. No permutation/DSR spend below the bar.

### Diff 3 — NEW `tests/test_qlib_adopt.py` (mirrors `test_qlib_port.py` gates)

```python
"""Gates for Q_* add-ons + IC harness: count, no-lookahead, determinism, IC sanity."""
import numpy as np, pandas as pd
from src.signals.qlib_alpha158 import compute_alpha158, get_feature_names
from src.signals.qlib_alpha158_extra import add_qlib_true_operators, Q_FEATURE_NAMES
from src.backtest.factor_ic import factor_ic, qlib_label

def _ohlcv(n=300, seed=42):
    rng = np.random.RandomState(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    close = 100 + np.cumsum(rng.randn(n) * 0.5)
    return pd.DataFrame({"date": dates, "open": close + rng.randn(n)*0.1,
        "high": close + abs(rng.randn(n)*0.5), "low": close - abs(rng.randn(n)*0.5),
        "close": close, "volume": rng.randint(1_000_000, 10_000_000, n).astype(float)})

def test_q_operator_count():
    raw = _ohlcv(); base = compute_alpha158(raw)
    ext = add_qlib_true_operators(base, raw.set_index(pd.to_datetime(raw["date"])))
    assert len([n for n in Q_FEATURE_NAMES if n in ext.columns]) >= 140

def test_q_no_lookahead_single_shift():
    raw = _ohlcv(); r = raw.set_index(pd.to_datetime(raw["date"]))
    base = compute_alpha158(raw); ext = add_qlib_true_operators(base, r)
    assert ext["Q_KMID"].iloc[0] is np.nan or pd.isna(ext["Q_KMID"].iloc[0])
    # row 1 exposes raw row-0 kbar only
    exp = (r["close"].iloc[0] - r["open"].iloc[0]) / r["open"].iloc[0]
    assert abs(ext["Q_KMID"].iloc[1] - exp) < 1e-12

def test_q_determinism():
    raw = _ohlcv(); r = raw.set_index(pd.to_datetime(raw["date"]))
    e1 = add_qlib_true_operators(compute_alpha158(raw), r)
    e2 = add_qlib_true_operators(compute_alpha158(raw), r)
    pd.testing.assert_frame_equal(e1, e2)

def test_ic_harness_runs_and_ranks_trend():
    raw = _ohlcv(500); r = raw.set_index(pd.to_datetime(raw["date"])).sort_index()
    base = compute_alpha158(raw)
    feats = get_feature_names()[:8]
    tab = factor_ic(base, feats, r["close"])
    assert len(tab) > 0 and {"feature","IC","RankIC","ICIR","n"} <= set(tab.columns)
    assert tab["RankIC"].abs().max() <= 1.0

def test_label_matches_qlib_definition():
    c = pd.Series([10.0, 11.0, 12.0, 13.0], index=pd.date_range("2020-01-01", periods=4))
    lab = qlib_label(c, horizon=1)
    assert abs(lab.iloc[0] - (11.0/12.0 - 1)) < 1e-12  # Ref(c,-2)/Ref(c,-1)-1 at row0
```

## 4. What to REJECT (out of scope for Alpaca paper)

1. **RL execution / SAOE** (qlib `qlib/rl/` — State-based Action-Order Execution, simulator-exchange loop): rejects on three grounds — Alpaca paper API accepts simple limit/market orders, not a learned execution policy; simulator needs LOB data we don't have; adds `tianshou`-class deps + nondeterminism into a fail-closed order path. Keep T+1 `Open[t+1]` fills in `run_historic_backtest`.
2. **Heavy model-training infra** (LightGBM/GBDT ensemble pipelines, `qlib/workflow` DAG, DataServer, experiment manager): rejects — zero-cost GitHub Actions mandate + no GPU; training 158-wide GBMs per symbol multiplies trial count `N` and tightens the DSR bar for everything (`trial_ledger.deflated_sharpe_threshold` grows in N). Factor screening (Diff 2) + existing TopkDropout rotation is the proportionate adopt.
3. **CSI300 / CN-market bundle + QlibDatawoners**: rejects — US Alpaca universe only; no new data vendor, no network fetch at runtime (offline-first preserved).
4. **Full 158-column rename to canonical names**: rejects — breaks `test_qlib_port` + downstream rotation. `Q_` coexistence is the migration path; a rename is a major-version task with its own edge gate, not this adopt.
5. **Alpha360 as default feature set**: rejects as default — 360 extra trials crush DSR; opt-in diagnostics only (Diff 1 flag), never the order path.

## 5. Test plan (targeted-only, per AGENTS.md)

1. `PYTHONPATH=. pytest tests/test_qlib_adopt.py -q` — new gate: ≥140 Q_* cols, single-shift no-lookahead (Q_KMID row-1 check), determinism, IC table schema + RankIC bounds, label identity.
2. `PYTHONPATH=. pytest tests/test_qlib_port.py -q` — regression: existing 70-col base, 12 families, rotation/turnover/metric gates unaffected (`Q_` namespace isolation).
3. `PYTHONPATH=. pytest tests/test_trial_ledger.py tests/test_p0_fixes.py -q` — DSR/CPCV validators untouched.
4. `python scripts/screen_factors_ic.py` (new, offline: `data/spy_ohlcv_2019_2026.csv` → `output/factor_ic_screen.csv`) — manual eyeball: top-|RankIC| factors plausible (RSV/RSQR/BETA family expected near top on trend data; pure-noise run ≈ |RankIC|<0.02).
5. `ruff check src/signals/qlib_alpha158_extra.py src/backtest/factor_ic.py tests/test_qlib_adopt.py` — lint (no config file per repo rule).
6. `bandit -r src/signals/ src/backtest/` — expected clean (pure pandas/numpy/scipy, no network, no eval).
7. Edge-gate path (follow-up hunt, NOT this diff): pre-register top IC survivors → walk-forward OOS Sharpe → 200-permutation tests in `validation.py` → DSR ledger entry → only then propose `strategies/registry.json`.

## 6. Risks

- `argmax/argmin` IMAX/IMIN proxy: documents bars-since vs position-in-window choice; RankIC-invariant, Pearson-sign documented — exact flip is a 2-line follow-up once IC screen picks a winner.
- `polyfit/lstsq` per-row cost for BETA/RSQR/RESI on 5 windows: fine on daily bars (300-row tests), flagged slow only if ported to intraday — Alpha360 intraday use explicitly rejected.
- VWAP fallback HLC3: labeled in code + docstring; symbols lacking vwap get a documented proxy, never silent synthetic volume.
- IC screen is single-ticker time-series, not cross-sectional: weaker than qlib's universe IC; framed as cheap pre-filter before the expensive permutation/DSR gates, not a replacement.
