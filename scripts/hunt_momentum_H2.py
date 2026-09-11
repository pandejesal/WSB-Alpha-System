#!/usr/bin/env python3
"""H2 high-exposure-momentum hunt: 12-1 slow-formation (252/21) diversified top-8.

Untried combo (252,21,8): v1=(126,21,5) v2=(189,5,10) v3=(63,42,3) all failed
Track 5 on maxDD (0.456/0.488/0.514) + DSR (0.845/0.834/0.862); registry
us_momentum=(95,42,7) retired. Slowest formation + widest diversification aims
at the DD blocker. Lineage: evolve_real.load_csv/UNIVERSE/_rotation_result
(tiered W5 costs, T+1), check_track_detailed gate, WF 3-fold + CPCV-proxy
overlays (frozen params, returns-level, disclosed). Paper only.
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
    UNIVERSE,
    _rotation_result,
    first_trading_day_of_month,
    load_csv,
)
from src.backtest.defend.trial_ledger import deflated_sharpe_ratio
from src.backtest.gatespec38_tracks import check_track_detailed
from src.backtest.metrics import safe_sharpe

RUN_DIR = ROOT / "hunts/high_exposure_momentum/20260911-h2-momentum"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

FAMILY = "high_exposure_momentum"
FAM_N = 53  # v1=50, v2=51, v3=52 -> H2 continues the family trial count

P = {"lookback": 252, "skip": 21, "top_n": 8, "vol_confirm": 1.2}


def diversified_rotation(prices: pd.DataFrame, lookback: int, skip: int,
                         top_n: int, vol_confirm: float):
    """Monthly top_n rotation with past-only vol-confirm filter + ffill holding.

    Mirrors evolve_real.monthly_rotation scoring (mean formation return) but
    (a) filters to names with 20d vol > vol_confirm x 60d-median (past-only at
    each rebalance date; warmup <80 bars -> filter open, documented), and
    (b) forward-fills monthly weights daily (buy-hold-companion style holding
    for tmin>=0.70) with T+1 via shift(1). Zero weight (cash) if none pass.
    """
    rets = prices.pct_change()
    months = first_trading_day_of_month(prices.index)
    # NaN-init (NOT zeros): ffill only propagates NaN; zero-init would make
    # ffill a no-op and collapse to 1-day holding (found 2026-09-11: tmin 0.03).
    w = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for m in months:
        hist = rets.loc[:m].iloc[-(lookback + skip):-skip] if skip else rets.loc[:m].iloc[-lookback:]
        if len(hist) < 20:
            continue
        score = hist.mean().sort_values(ascending=False)
        past = rets.loc[:m]
        if len(past) >= 80:
            vol20 = past.rolling(20).std().iloc[-1]
            volmed = past.rolling(20).std().rolling(60).median().iloc[-1]
            scalar = (vol20 / volmed.replace(0, np.nan)).fillna(1.0)
            passing = [s for s in score.index if float(scalar.get(s, 1.0)) > vol_confirm]
        else:
            passing = list(score.index)  # warmup: filter open (documented)
        picks = passing[: int(top_n)]
        if not picks:
            # FAIL-SAFE (H2v2, frozen cycle18): empty vol-filter falls back to
            # unfiltered top_n by formation rank — matches v1-v3 lineage
            # (tmin 0.90+) and never sits in cash on filter binding. Params
            # unchanged; the v1 literal run is preserved as cycle17 HONEST_ABANDON.
            picks = list(score.head(int(top_n)).index)
        if picks:
            w.loc[m, picks] = 1.0 / len(picks)
    w = w.ffill().fillna(0.0).shift(1).fillna(0.0)  # T+1 forward-filled holding
    port = (w * rets).sum(axis=1).fillna(0.0)
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


# --- data (evolve_real lineage: UNIVERSE panel + SPY twin, dropna-aligned) ---
uni = {}
for t in UNIVERSE:
    try:
        uni[t] = load_csv(t)["close"]
    except OSError as e:
        print(f"universe skip {t}: {e}")
prices = pd.DataFrame(uni).dropna()
spy_close = load_csv("SPY")["close"].reindex(prices.index).dropna()
assert isinstance(spy_close, pd.Series)  # fail-closed Series guard (LSP)
prices = prices.reindex(spy_close.index).dropna()
print(f"panel {prices.shape} bars={len(prices)} cols={list(prices.columns)}")

port, w = diversified_rotation(prices, P["lookback"], P["skip"], P["top_n"], P["vol_confirm"])
res = _rotation_result(port, spy_close, w, prices.pct_change(), FAMILY)
net = res["net"]
print(f"H2 sharpe={res['sharpe']:.3f} dd={res['max_dd']:.4f} oos={res['oos']:.3f} "
      f"excess={res['excess']:+.3f}pp tmin={res['tmin']:.4f} trips={res['trips']} "
      f"dsr_lineage={res['dsr']:.4f} perm={res['perm_p']} boot={res['boot_p']} n={res['n_bars']}")

# Family-continuation DSR (v1=50,v2=51,v3=52 -> 53), same helper as H1.
try:
    dsr_fam = float(deflated_sharpe_ratio(len(net), float(res["sharpe"]) / np.sqrt(252.0), FAM_N))
except Exception:
    dsr_fam = 0.0
dsr_gate = min(float(res["dsr"]), dsr_fam)  # fail-closed: harsher of the two
print(f"dsr_fam(N=53)={dsr_fam:.4f} dsr_gate={dsr_gate:.4f}")

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
    "id": "high_exposure_momentum_h2",
    "family": FAMILY,
    "params": P,
    "metrics": {"sharpe": res["sharpe"], "cagr": res["cagr"], "max_dd": res["max_dd"],
                "oos_sharpe": res["oos"], "excess": res["excess"], "tmin": res["tmin"],
                "dsr": dsr_gate, "dsr_fam_N53": round(dsr_fam, 4),
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
tmp = RES_DIR / "eval_high_exposure_momentum_h2.json.tmp"
final = RES_DIR / "eval_high_exposure_momentum_h2.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
