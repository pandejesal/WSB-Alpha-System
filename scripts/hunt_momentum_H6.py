#!/usr/bin/env python3
"""H6 high-exposure-momentum hunt: broad-panel quarterly low-turnover momentum.

Untried combo (189,21,28)+quarterly+voltarget12 on the 31-name
rotation_universe (W13-allowed max breadth; 100-stock panel unavailable
offline — universe.json caps at 31, so 28-of-31 is broadest feasible):
TABOO priors are (126,21,5), (189,5,10), (63,42,3), registry (95,42,7),
H2 (252,21,8) dd 0.794 / dsr 0.457 / perm 0.82 HONEST_ABANDON cycle18,
H4 (126,10,12)+inv-vol+voltarget15+dd-deleverage dd 0.3887 / dsr 0.607 /
perm 0.665 HONEST_ABANDON cycle19. Attacks H2/H4 failure modes: 28-of-31
breadth (~90% vs H4 39% vs H2 80%), QUARTERLY reselection (vs monthly
churn), equal-weight + deleverage-only 12%-ann vol target (scale
[0.7,1.0], quarterly past-only, never cash-flat so tmin>=0.70 by
construction). Lineage: evolve_real.load_csv/rotation_universe +
_rotation_result (tiered W5 costs, T+1), check_track_detailed gate,
WF 3-fold + CPCV-proxy overlays (frozen params, returns-level,
disclosed). Paper only.
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

RUN_DIR = ROOT / "hunts/high_exposure_momentum/20260911-h6-momentum"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

FAMILY = "high_exposure_momentum"
FAM_N = 55  # v1=50, v2=51, v3=52, H2=53, H4=54 -> H6 continues family trial count

P = {"lookback": 189, "skip": 21, "top_n": 28, "vol_target_ann": 0.12,
     "scale_min": 0.7, "scale_max": 1.0}


def first_trading_day_of_quarter(idx):
    months = first_trading_day_of_month(idx)
    return months[months.month.isin([1, 4, 7, 10])]


def broad_quarterly_rotation(prices: pd.DataFrame, lookback: int, skip: int,
                             top_n: int, vol_target_ann: float,
                             scale_min: float, scale_max: float):
    """Quarterly top_n equal-weight rotation with deleverage-only vol targeting.

    Past-only at each quarterly rebalance date q (uses rets.loc[:q] only):
      picks  = top_n by formation mean over [-(lookback+skip):-skip]
      w_uns  = equal 1/top_n
      scale  = clip(vol_target_ann / trailing-60d unscaled-sleeve ann vol,
               scale_min, scale_max); warmup (<60d sleeve history) -> 1.0
    NaN-init frame (NOT zeros) + ffill + T+1 shift(1), quarterly scale ffill
    daily (slower turnover than H2/H4 monthly) under W5 tiered costs.
    """
    rets = prices.pct_change()
    quarters = first_trading_day_of_quarter(prices.index)
    # NaN-init (NOT zeros): ffill only propagates NaN; zero-init would make
    # ffill a no-op and collapse to 1-day holding (H2 lesson 2026-09-11).
    w = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    unsc = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    scale_by_q = {}
    for q in quarters:
        hist = rets.loc[:q].iloc[-(lookback + skip):-skip] if skip else rets.loc[:q].iloc[-lookback:]
        if len(hist) < 20:
            continue
        score = hist.mean().sort_values(ascending=False)
        picks = list(score.head(int(top_n)).index)
        wgt = {s: 1.0 / len(picks) for s in picks}
        for s, v in wgt.items():
            unsc.loc[q, s] = v
        # past-only sleeve history -> trailing vol -> quarterly scale
        up = unsc.ffill()
        sleeve = (up * rets).sum(axis=1).loc[:q].fillna(0.0)
        if len(sleeve) >= 60:
            trail = sleeve.iloc[-60:]
            rvol = float(trail.std() * np.sqrt(252)) if float(trail.std()) > 0 else np.nan
            scale = float(np.clip(vol_target_ann / rvol, scale_min, scale_max)) if rvol and rvol > 0 else 1.0
        else:
            scale = 1.0  # warmup: full weight (documented)
        scale_by_q[str(q.date())] = round(scale, 4)
        for s, v in wgt.items():
            w.loc[q, s] = v * scale
    w = w.ffill().fillna(0.0).shift(1).fillna(0.0)  # T+1 forward-filled holding
    port = (w * rets).sum(axis=1).fillna(0.0)
    gross = w.abs().sum(axis=1)
    tmin_raw = float((gross > 1e-9).mean())
    print(f"signal sanity: tmin_raw={tmin_raw:.4f} quarters_set={len(scale_by_q)} "
          f"mean_scale={float(np.mean(list(scale_by_q.values()))) if scale_by_q else 0:.3f}")
    assert tmin_raw >= 0.70, f"signal tmin sanity failed: {tmin_raw}"
    return port, w


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
print(f"panel {prices.shape} bars={len(prices)} n_names={len(prices.columns)}")

port, w = broad_quarterly_rotation(prices, P["lookback"], P["skip"], P["top_n"],
                                   P["vol_target_ann"], P["scale_min"],
                                   P["scale_max"])
res = _rotation_result(port, spy_close, w, prices.pct_change(), FAMILY)
net = res["net"]
print(f"H6 sharpe={res['sharpe']:.3f} dd={res['max_dd']:.4f} oos={res['oos']:.3f} "
      f"excess={res['excess']:+.3f}pp tmin={res['tmin']:.4f} trips={res['trips']} "
      f"dsr_lineage={res['dsr']:.4f} perm={res['perm_p']} boot={res['boot_p']} n={res['n_bars']}")

# Family-continuation DSR (v1=50,v2=51,v3=52,H2=53,H4=54 -> 55), same helper as H2/H4.
try:
    dsr_fam = float(deflated_sharpe_ratio(len(net), float(res["sharpe"]) / np.sqrt(252.0), FAM_N))
except Exception:
    dsr_fam = 0.0
dsr_gate = min(float(res["dsr"]), dsr_fam)  # fail-closed: harsher of the two
print(f"dsr_fam(N=55)={dsr_fam:.4f} dsr_gate={dsr_gate:.4f}")

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
    "id": "high_exposure_momentum_h6",
    "family": FAMILY,
    "params": P,
    "metrics": {"sharpe": res["sharpe"], "cagr": res["cagr"], "max_dd": res["max_dd"],
                "oos_sharpe": res["oos"], "excess": res["excess"], "tmin": res["tmin"],
                "dsr": dsr_gate, "dsr_fam_N55": round(dsr_fam, 4),
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
tmp = RES_DIR / "eval_high_exposure_momentum_h6.json.tmp"
final = RES_DIR / "eval_high_exposure_momentum_h6.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
