#!/usr/bin/env python3
"""H1 tail-sentinel v4 hunt: VIX30<=24 + ATR2.5x stop + volcap 0.20 on SPY.

Replicates evolve_real.backtest() + stat_screens exactly (same lineage as
scripts/hunt_smooth_A2.py). T+1, tiered W5 costs, T=1910 bars, per-family N=51.
Overlays: gatespec38 check_track_detailed (tail_risk_sentinel + drawdown_warrior
fallback), WF 3-fold, CPCV-proxy (4 blocks/6 paths, no embargo, disclosed),
circular-shift perm K=200, stationary bootstrap block21. Paper only.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from evolve_real import stationary_bootstrap_p, _tiered_cost_bps, max_dd, cagr
from src.backtest.gatespec38_tracks import check_track_detailed
from src.backtest.defend.trial_ledger import deflated_sharpe_ratio
from src.backtest.metrics import safe_sharpe

RUN_DIR = ROOT / "hunts/tail_risk_sentinel/20260911-h1-tail-sentinel"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

SPY_CSV = ROOT / "market_data_2019_2026/ohlcv/SPY.csv"
VIX_CSV = ROOT / "market_data_2019_2026/ohlcv/^VIX.csv"
FAMILY = "tail_risk_sentinel"
FAM_N = 51  # v1=48, v2=49, v3=50 -> v4 continues the family trial count

P = {"vix_window": 30, "vix_entry": 24, "atr_stop": 2.5, "vol_regime_cap": 0.20}


def load_close(path):
    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").sort_index()


spy = load_close(SPY_CSV)
vix = load_close(VIX_CSV)
close = spy["close"]
print(f"SPY bars {len(spy)}, VIX bars {len(vix)}")


def tail_signal(spy_df, vix_close, p):
    """1.0 long / 0.0 flat. All inputs past-only (shift1)."""
    vix_ma = vix_close.rolling(int(p["vix_window"])).mean().shift(1)
    rets = spy_df["close"].pct_change()
    vol = (rets.rolling(20).std() * np.sqrt(252)).shift(1)
    tr = ((spy_df["high"] - spy_df["low"]) / spy_df["close"]).fillna(0.0)
    atr = tr.rolling(20).mean().shift(1)
    gate = (vix_ma.reindex(spy_df.index).ffill() <= p["vix_entry"]) & (vol <= p["vol_regime_cap"])
    stop = tr > (p["atr_stop"] * atr)
    sig = pd.Series(0.0, index=spy_df.index)
    sig[gate.fillna(False) & (~stop.fillna(False))] = 1.0
    return sig


def run_bt(signal, spy_df, family=FAMILY, fam_trials_N=FAM_N):
    pos = signal.shift(1).fillna(0.0)  # T+1
    strat = spy_df["close"].pct_change().fillna(0.0) * pos
    turnover = pos.diff().abs().fillna(pos.abs())
    try:
        cost_bps = _tiered_cost_bps(spy_df["close"], family)
        cost_bps = cost_bps.reindex(turnover.index).fillna(5.0).clip(lower=5.0)
        net = strat - turnover * (cost_bps / 10000.0)
    except Exception:
        net = strat - turnover * (5.0 / 10000.0)
    eq = (1 + net).cumprod()
    n = len(net)
    split = int(n * 0.7)
    oos = float(safe_sharpe(net.iloc[split:])) if n - split > 20 else 0.0
    trips = int((turnover > 0).sum() // 2)
    trades = int((turnover > 0).sum())
    spy_r = spy_df["close"].pct_change().fillna(0.0)
    excess = float((1 + net).prod() - (1 + spy_r).prod()) * 100
    tmin = float((pos.abs() > 1e-9).mean()) if n else 0.0
    sharpe = float(safe_sharpe(net))
    try:
        dsr = float(deflated_sharpe_ratio(len(net), sharpe / np.sqrt(252.0), max(1, fam_trials_N)))
    except Exception:
        dsr = 0.0
    try:
        actual = sharpe
        pv = np.asarray(pos.fillna(0.0).values, dtype=float)
        rv = np.asarray(spy_df["close"].pct_change().fillna(0.0).values, dtype=float)
        rng = np.random.default_rng(7)
        wins = 0
        K = 200
        try:
            cost_arr = _tiered_cost_bps(spy_df["close"], family).reindex(pos.index).fillna(5.0).values / 10000.0
        except Exception:
            cost_arr = np.full(len(pv), 5.0 / 10000.0)
        for _ in range(K):
            shift = int(rng.integers(1, len(pv)))
            ps = np.roll(pv, shift)
            turn = np.abs(np.diff(ps, prepend=ps[0]))
            tn = pd.Series(rv * ps - turn * cost_arr)
            if float(safe_sharpe(tn)) >= actual:
                wins += 1
        perm_p = wins / K
    except Exception:
        perm_p = 1.0
    try:
        boot_p = stationary_bootstrap_p(np.asarray(net.fillna(0.0).values, dtype=float))
    except Exception:
        boot_p = 1.0
    return {
        "sharpe": sharpe, "cagr": cagr(eq), "max_dd": max_dd(eq), "oos": oos,
        "trips": trips, "trades": trades, "excess": round(excess, 2),
        "tmin": round(tmin, 4), "n_bars": n, "dsr": round(dsr, 4),
        "perm_p": round(perm_p, 4), "boot_p": round(boot_p, 4),
        "net": net, "pos": pos, "eq": eq,
    }


def wf_3fold(signal, spy_df):
    """3 contiguous OOS folds on frozen params (no refit): report fold OOS sharpes."""
    n = len(signal)
    edges = [0, n // 3, 2 * n // 3, n]
    folds = []
    for i in range(3):
        sl = slice(edges[i], edges[i + 1])
        seg_net = res_net.iloc[sl]
        folds.append(round(float(safe_sharpe(seg_net)) if len(seg_net) > 20 else 0.0, 4))
    return folds


def cpcv_proxy(net):
    """CPCV-proxy on strategy returns: 4 contiguous blocks, all C(4,2)=6
    two-block test paths. Reports test-path Sharpe distribution. DISCLOSED
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


sig = tail_signal(spy, vix["close"], P)
res = run_bt(sig, spy)
res_net = res["net"]
print(f"v4 sharpe={res['sharpe']:.3f} cagr={res['cagr']:.4f} dd={res['max_dd']:.4f} "
      f"oos={res['oos']:.3f} excess={res['excess']:+.3f}pp tmin={res['tmin']:.4f} "
      f"trips={res['trips']} dsr={res['dsr']:.4f} perm={res['perm_p']} boot={res['boot_p']} n={res['n_bars']}")

m = {"sharpe": res["sharpe"], "max_dd": res["max_dd"], "oos": res["oos"],
     "excess": res["excess"], "dsr": res["dsr"], "trips": res["trips"],
     "tmin": res["tmin"], "perm_p": res["perm_p"], "boot_p": res["boot_p"]}
det = check_track_detailed(m)
tr = det.get("tail_risk_sentinel", {})
dw = det.get("drawdown_warrior", {})
print("TR:", tr.get("passed"), tr.get("terms"))
print("DW:", dw.get("passed"), dw.get("terms"))

wf = wf_3fold(sig, spy)
cpcv = cpcv_proxy(res_net)
print("WF folds OOS:", wf, "mean:", round(float(np.mean(wf)), 4))
print("CPCV paths:", cpcv, "mean:", round(float(np.mean(cpcv)), 4),
      "min:", min(cpcv), "frac>0:", round(float(np.mean([x > 0 for x in cpcv])), 4))

L1 = res["sharpe"] >= 0.50 and res["max_dd"] <= 0.35 and res["excess"] > 0
TR_pass = bool(tr.get("passed")) and res["perm_p"] <= 0.05 and res["boot_p"] <= 0.05
DW_pass = bool(dw.get("passed")) and res["perm_p"] <= 0.05 and res["boot_p"] <= 0.05
wf_ok = float(np.mean(wf)) >= 0.35
if TR_pass:
    verdict = "PROMOTE"
    tracks = ["tail_risk_sentinel"]
elif DW_pass:
    verdict = "PROMOTE_FALLBACK"
    tracks = ["drawdown_warrior"]
else:
    verdict = "HONEST_ABANDON"
    tracks = []

eval_data = {
    "id": "tail_risk_sentinel_v4",
    "family": FAMILY,
    "params": P,
    "metrics": {"sharpe": res["sharpe"], "cagr": res["cagr"], "max_dd": res["max_dd"],
                "oos_sharpe": res["oos"], "excess": res["excess"], "tmin": res["tmin"],
                "dsr": res["dsr"], "trips": res["trips"], "perm_p": res["perm_p"],
                "boot_p": res["boot_p"], "n_bars": res["n_bars"], "fam_trials": FAM_N},
    "tracks_cleared": tracks,
    "tracks": {"tail_risk_sentinel": tr, "drawdown_warrior": dw},
    "overlays": {"wf_3fold_oos": wf, "wf_mean_oos": round(float(np.mean(wf)), 4),
                 "wf_ok": wf_ok, "cpcv_proxy_paths": cpcv,
                 "cpcv_mean": round(float(np.mean(cpcv)), 4), "cpcv_min": min(cpcv),
                 "cpcv_frac_pos": round(float(np.mean([x > 0 for x in cpcv])), 4),
                 "cpcv_disclosure": "returns-level proxy, 4 blocks/6 paths, no embargo/purge"},
    "L1_pass": L1,
    "L2_Track4_pass": bool(tr.get("passed")),
    "fallback_Track2_pass": bool(dw.get("passed")),
    "verdict": verdict,
    "paper_only": True,
}
tmp = RES_DIR / "eval_tail_risk_sentinel_v4.json.tmp"
final = RES_DIR / "eval_tail_risk_sentinel_v4.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
import os as _os
_os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
