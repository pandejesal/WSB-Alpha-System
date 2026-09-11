#!/usr/bin/env python3
"""H12 high-exposure-momentum hunt: slow dual-trend regime basket, all-31 held.

Untried combo (slow200, confirm63, weak0.5, quarterly, all-31) on the
31-name rotation_universe (W13-allowed max breadth; SPY twin ONLY, no
SPY-fill sleeve): TABOO priors are ALL formation-rank rotation — (126,21,5),
(189,5,10), (63,42,3), registry (95,42,7), H2 (252,21,8) dd 0.794 / dsr
0.457 / perm 0.82 HONEST_ABANDON cycle18, H4 (126,10,12)+inv-vol+voltarget15+
dd-deleverage dd 0.3887 / dsr 0.607 / perm 0.665 HONEST_ABANDON cycle19,
H6 (189,21,28)+quarterly+voltarget12 sharpe 1.15 / dd 0.2285 / dsr 0.6456 /
perm 0.645 HONEST_ABANDON cycle21 — plus H8 dual-SMA-stack (close>SMA50 AND
SMA50>SMA200, weak 0.5, monthly) perm 0.695 / excess -14.70pp HONEST_ABANDON
cycle23, plus H10 breakout252/confirm63/band0.98/SPY-fill sharpe 0.972 /
dd 0.3372 / dsr 0.4537 / perm 0.535 HONEST_ABANDON cycle26, plus H11
inv-vol63+252-21 z-tilt gain0.5 clip[0.25,2.0] monthly all-31 sharpe 1.242 /
dd 0.3104 / dsr 0.7339 / perm 0.295 HONEST_ABANDON cycle27. NONE reused here:
zero fast SMA (no SMA50 leg anywhere), zero cross-sectional ranking cutoff
(all 31 held every bar), zero breakout (no 252d-high proximity, no confirm
gate, no SPY-fill), zero vol weighting, zero momentum z-tilt. Slow
dual-trend regime per name at each quarterly signal date q (past-only
closes.loc[:q]): bull = (close[q] > SMA200[q]) AND (SMA200[q] > SMA200[q-63]);
bull names get full 1/N, others weak 0.5/N, renormalized to gross 1.0.
Warmup (<263 bars history) holds equal-weight panel. Gross = 1.0 every
post-signal bar so tmin = 1.0 by construction; never fewer than 31 names,
never cash. Attacks the 6/6 perm wall via rare persistent multi-year regime
flips whose time alignment should degrade under circular shift. Lineage:
evolve_real.load_csv / rotation_universe + _rotation_result (tiered W5
costs, T+1), check_track_detailed gate, WF 3-fold + CPCV-proxy overlays
(frozen params, returns-level, disclosed). Paper only.
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from evolve_real import (
    _rotation_result,
    first_trading_day_of_month,
    load_csv,
)
from src.backtest.defend.trial_ledger import deflated_sharpe_ratio
from src.backtest.gatespec38_tracks import check_track_detailed
from src.backtest.metrics import safe_sharpe

RUN_DIR = ROOT / "hunts/high_exposure_momentum/20260911-h12-momentum"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

FAMILY = "high_exposure_momentum"
FAM_N = 59  # v1=50..H11=58 -> H12 continues

P = {"slow_lookback": 200, "confirm_lookback": 63, "weak_weight": 0.5,
     "signal_refresh": "quarterly", "names_held": 31}


def first_trading_day_of_quarter(idx):
    months = first_trading_day_of_month(idx)
    return months[months.month.isin([1, 4, 7, 10])]


def dual_trend_regime(prices: pd.DataFrame, slow: int, confirm: int,
                      weak: float):
    """Quarterly slow dual-trend regime weights, panel-only, always 1.0.

    Past-only at each quarterly signal date q (uses closes.loc[:q] only):
      sma_s  = rolling(slow).mean of hist
      bull_s = (close[q,s] > sma_s[q,s]) AND (sma_s[q,s] > sma_s[q-confirm,s])
      w[q,s] = (1/N if bull_s else weak/N), renormalized to gross 1.0
      warmup (<slow+confirm bars history) -> equal weight 1/N
    NaN-init frames (NOT zeros) + ffill + T+1 shift(1), quarterly signal
    ffill daily under W5 tiered costs. No fast SMA, no ranking, no
    breakout, no vol tilt, no SPY-fill. Gross is 1.0 on every post-signal
    bar.
    """
    quarters = first_trading_day_of_quarter(prices.index)
    n = len(prices.columns)
    # NaN-init (NOT zeros): ffill only propagates set signals; zero-init
    # would make ffill a no-op and collapse to 1-day holding (H2 lesson).
    w = pd.DataFrame(np.nan, index=prices.index, columns=list(prices.columns))
    warm = slow + confirm
    n_set = 0
    n_bull_hist = []
    for q in quarters:
        hist = prices.loc[:q]
        if len(hist) < warm:
            for s in prices.columns:
                w.loc[q, s] = 1.0 / n
            continue
        sma = hist.rolling(slow).mean()
        last = hist.iloc[-1]
        sma_now = sma.iloc[-1]
        sma_then = sma.iloc[-(confirm + 1)]
        bull = (last > sma_now) & (sma_now > sma_then)
        bull = bull.fillna(False)
        n_bull_hist.append(int(bull.sum()))
        for s in prices.columns:
            w.loc[q, s] = (1.0 / n) if bool(bull[s]) else (weak / n)
        row_sum = float(w.loc[q].sum())
        if row_sum > 0:
            w.loc[q] = w.loc[q] / row_sum
        n_set += 1
    w = w.ffill().fillna(0.0).shift(1).fillna(0.0)  # T+1 forward-filled
    rets = prices.pct_change().reindex(w.index).fillna(0.0)
    port = (w * rets).sum(axis=1).fillna(0.0)
    gross = w.abs().sum(axis=1)
    tmin_raw = float((gross > 1e-9).mean())
    invested = gross > 1e-9
    n_held_min = float((w[invested] > 1e-9).sum(axis=1).min()) if bool(invested.any()) else 0.0
    print(f"signal sanity: tmin_raw={tmin_raw:.4f} quarters_set={n_set} "
          f"mean_gross={float(gross.mean()):.3f} min_names_held={n_held_min:.0f} "
          f"bull_frac_range=[{min(n_bull_hist) if n_bull_hist else -1}/{n}-"
          f"{max(n_bull_hist) if n_bull_hist else -1}/{n}]")
    assert tmin_raw >= 0.70, f"signal tmin sanity failed: {tmin_raw}"
    assert n_held_min >= 20, f"regime must never hold fewer than 20 names: {n_held_min}"
    return port, w, rets


def wf_3fold(net: pd.Series):
    """3 contiguous OOS folds on frozen params (no refit)."""
    n = len(net)
    edges = [0, n // 3, 2 * n // 3, n]
    folds = []
    for i in range(3):
        seg = net.iloc[edges[i]:edges[i + 1]]
        folds.append(round(float(safe_sharpe(seg)) if len(seg) > 20 else 0.0, 4))
    return folds


def cpcv_proxy(net: pd.Series):
    """CPCV-proxy: 4 blocks, all C(4,2)=6 two-block test paths. DISCLOSED
    LIMITS: returns-level (no refit), no embargo/purge between blocks."""
    n = len(net)
    edges = [0, n // 4, n // 2, 3 * n // 4, n]
    blocks = [net.iloc[edges[i]:edges[i + 1]] for i in range(4)]
    paths = []
    for i in range(4):
        for j in range(i + 1, 4):
            test = pd.concat([blocks[i], blocks[j]]).sort_index()
            paths.append(round(float(safe_sharpe(test)) if len(test) > 20 else 0.0, 4))
    return paths


# --- data (evolve_real lineage: rotation_universe panel + SPY twin) ---
uni = json.loads((ROOT / "config/universe.json").read_text(encoding="utf-8"))
PANEL = [t for t in uni["rotation_universe"] if t not in ("SPY",)]
closes = {}
for t in PANEL:
    try:
        closes[t] = load_csv(t)["close"]
    except OSError as e:
        print(f"panel skip {t}: {e}")
prices = pd.DataFrame(closes).dropna()
spy_close = load_csv("SPY")["close"].reindex(prices.index).dropna()
assert isinstance(spy_close, pd.Series)  # fail-closed Series guard (LSP)
prices = prices.reindex(spy_close.index).dropna()
spy_close = spy_close.reindex(prices.index)
print(f"panel {prices.shape} bars={len(prices)} n_names={len(prices.columns)}")

port, w, rets = dual_trend_regime(
    prices, P["slow_lookback"], P["confirm_lookback"], P["weak_weight"])
res = _rotation_result(port, spy_close, w, rets, FAMILY)
net = res["net"]
print(f"H12 sharpe={res['sharpe']:.3f} dd={res['max_dd']:.4f} oos={res['oos']:.3f} "
      f"excess={res['excess']:+.3f}pp tmin={res['tmin']:.4f} trips={res['trips']} "
      f"dsr_lineage={res['dsr']:.4f} perm={res['perm_p']} boot={res['boot_p']} n={res['n_bars']}")

# Family-continuation DSR (v1=50..H11=58 -> 59), same helper as H2/H4/H6/H8/H10/H11.
try:
    dsr_fam = float(deflated_sharpe_ratio(len(net), float(res["sharpe"]) / np.sqrt(252.0), FAM_N))
except Exception:
    dsr_fam = 0.0
dsr_gate = min(float(res["dsr"]), dsr_fam)  # fail-closed: harsher of the two
print(f"dsr_fam(N=59)={dsr_fam:.4f} dsr_gate={dsr_gate:.4f}")

m = {"sharpe": res["sharpe"], "max_dd": res["max_dd"], "oos": res["oos"],
     "excess": res["excess"], "dsr": dsr_gate, "trips": res["trips"],
     "tmin": res["tmin"], "perm_p": res["perm_p"], "boot_p": res["boot_p"]}
det = check_track_detailed(m)
t5 = det.get("high_exposure_momentum", {})
print("T5:", t5.get("passed"), t5.get("terms"))

wf = wf_3fold(net)
cpcv = cpcv_proxy(net)
wf_mean = round(float(np.mean(wf)), 4)
print("WF folds OOS:", wf, "mean:", wf_mean)
print("CPCV paths:", cpcv, "mean:", round(float(np.mean(cpcv)), 4),
      "min:", min(cpcv), "frac>0:", round(float(np.mean([x > 0 for x in cpcv])), 4))

L1 = res["sharpe"] >= 0.50 and res["max_dd"] <= 0.35 and res["excess"] > 0
T5_pass = bool(t5.get("passed")) and res["perm_p"] <= 0.05 and res["boot_p"] <= 0.05
wf_ok = wf_mean >= 0.50
if T5_pass and wf_ok:
    verdict, tracks = "PROMOTE", ["high_exposure_momentum"]
else:
    verdict, tracks = "HONEST_ABANDON", []

eval_data = {
    "id": "high_exposure_momentum_h12",
    "family": FAMILY,
    "params": P,
    "metrics": {"sharpe": res["sharpe"], "cagr": res["cagr"], "max_dd": res["max_dd"],
                "oos_sharpe": res["oos"], "excess": res["excess"], "tmin": res["tmin"],
                "dsr": dsr_gate, "dsr_fam_N59": round(dsr_fam, 4),
                "dsr_lineage": res["dsr"], "trips": res["trips"],
                "trades": res.get("trades"), "perm_p": res["perm_p"],
                "boot_p": res["boot_p"], "n_bars": res["n_bars"],
                "fam_trials": FAM_N,
                "regime_coverage": res.get("regime_coverage"),
                "regime_warn": res.get("regime_warn")},
    "tracks_cleared": tracks,
    "tracks": {"high_exposure_momentum": t5},
    "overlays": {"wf_3fold_oos": wf, "wf_mean_oos": wf_mean, "wf_ok": wf_ok,
                 "cpcv_proxy_paths": cpcv, "cpcv_mean": round(float(np.mean(cpcv)), 4),
                 "cpcv_min": min(cpcv),
                 "cpcv_frac_pos": round(float(np.mean([x > 0 for x in cpcv])), 4),
                 "cpcv_disclosure": "returns-level proxy, 4 blocks/6 paths, no embargo/purge"},
    "L1_pass": L1,
    "L2_Track5_pass": bool(t5.get("passed")),
    "verdict": verdict,
    "paper_only": True,
}
tmp = RES_DIR / "eval_high_exposure_momentum_h12.json.tmp"
final = RES_DIR / "eval_high_exposure_momentum_h12.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
