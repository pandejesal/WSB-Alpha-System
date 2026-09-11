#!/usr/bin/env python3
"""H8 high-exposure-momentum hunt: per-name time-series own-trend long/half.

Untried combo (SMA50/200, weak 0.5, monthly) on the 31-name
rotation_universe (W13-allowed max breadth; SPY twin only):
TABOO priors are ALL formation-rank rotation — (126,21,5), (189,5,10),
(63,42,3), registry (95,42,7), H2 (252,21,8) dd 0.794 / dsr 0.457 /
perm 0.82 HONEST_ABANDON cycle18, H4 (126,10,12)+inv-vol+voltarget15+
dd-deleverage dd 0.3887 / dsr 0.607 / perm 0.665 HONEST_ABANDON cycle19,
H6 (189,21,28)+quarterly+voltarget12 sharpe 1.15 / dd 0.2285 /
dsr 0.6456 / perm 0.645 HONEST_ABANDON cycle21 — NONE reused here.
Zero cross-sectional ranking: each name independently long (1/N) when
close>SMA50 AND SMA50>SMA200 (past-only, monthly refresh), half (0.5/N)
otherwise; always invested, gross in [0.5,1.0], tmin=1.0 by construction.
Attacks rotation perm-death: time-specific defensiveness (COVID, 2022)
gives the circular-shift perm test real timing content where quasi-index
rotation had none. Lineage: evolve_real.load_csv/rotation_universe +
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

RUN_DIR = ROOT / "hunts/high_exposure_momentum/20260911-h8-momentum"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

FAMILY = "high_exposure_momentum"
FAM_N = 56  # v1=50, v2=51, v3=52, H2=53, H4=54, H6=55 -> H8 continues

P = {"sma_fast": 50, "sma_slow": 200, "weak_weight": 0.5,
     "signal_refresh": "monthly"}


def own_trend_long_half(prices: pd.DataFrame, fast: int, slow: int,
                        weak: float):
    """Monthly per-name SMA(fast/slow) own-trend, long/half aggregation.

    Past-only at each monthly signal date m (uses closes.loc[:m] only):
      on   = close > SMAfast AND SMAfast > SMAslow  -> 1/N
      off  = otherwise                               -> weak/N
      warmup (<slow bars history)                    -> 1/N (documented)
    NaN-init frame (NOT zeros) + ffill + T+1 shift(1), monthly signal
    ffill daily under W5 tiered costs. No ranking, no formation window.
    """
    months = first_trading_day_of_month(prices.index)
    n = len(prices.columns)
    # NaN-init (NOT zeros): ffill only propagates set signals; zero-init
    # would make ffill a no-op and collapse to 1-day holding (H2 lesson).
    w = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    n_set = 0
    for m in months:
        hist = prices.loc[:m]
        if len(hist) < slow:
            for s in prices.columns:
                w.loc[m, s] = 1.0 / n
            continue
        sma_f = hist.rolling(fast).mean().iloc[-1]
        sma_s = hist.rolling(slow).mean().iloc[-1]
        last = hist.iloc[-1]
        for s in prices.columns:
            on = bool(last[s] > sma_f[s] and sma_f[s] > sma_s[s])
            w.loc[m, s] = (1.0 / n) if on else (weak / n)
        n_set += 1
    w = w.ffill().fillna(0.0).shift(1).fillna(0.0)  # T+1 forward-filled
    rets = prices.pct_change()
    port = (w * rets).sum(axis=1).fillna(0.0)
    gross = w.abs().sum(axis=1)
    tmin_raw = float((gross > 1e-9).mean())
    print(f"signal sanity: tmin_raw={tmin_raw:.4f} months_set={n_set} "
          f"mean_gross={float(gross.mean()):.3f}")
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

port, w = own_trend_long_half(prices, P["sma_fast"], P["sma_slow"],
                              P["weak_weight"])
res = _rotation_result(port, spy_close, w, prices.pct_change(), FAMILY)
net = res["net"]
print(f"H8 sharpe={res['sharpe']:.3f} dd={res['max_dd']:.4f} oos={res['oos']:.3f} "
      f"excess={res['excess']:+.3f}pp tmin={res['tmin']:.4f} trips={res['trips']} "
      f"dsr_lineage={res['dsr']:.4f} perm={res['perm_p']} boot={res['boot_p']} n={res['n_bars']}")

# Family-continuation DSR (v1=50..H6=55 -> 56), same helper as H2/H4/H6.
try:
    dsr_fam = float(deflated_sharpe_ratio(len(net), float(res["sharpe"]) / np.sqrt(252.0), FAM_N))
except Exception:
    dsr_fam = 0.0
dsr_gate = min(float(res["dsr"]), dsr_fam)  # fail-closed: harsher of the two
print(f"dsr_fam(N=56)={dsr_fam:.4f} dsr_gate={dsr_gate:.4f}")

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
    "id": "high_exposure_momentum_h8",
    "family": FAMILY,
    "params": P,
    "metrics": {"sharpe": res["sharpe"], "cagr": res["cagr"], "max_dd": res["max_dd"],
                "oos_sharpe": res["oos"], "excess": res["excess"], "tmin": res["tmin"],
                "dsr": dsr_gate, "dsr_fam_N56": round(dsr_fam, 4),
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
tmp = RES_DIR / "eval_high_exposure_momentum_h8.json.tmp"
final = RES_DIR / "eval_high_exposure_momentum_h8.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
