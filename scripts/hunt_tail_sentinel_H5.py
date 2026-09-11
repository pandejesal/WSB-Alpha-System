#!/usr/bin/env python3
"""H5 tail-sentinel hunt: ALWAYS-INVESTED stress rotation SPY -> defensive-8.

Concept (direction (a)): 100% SPY in calm; under stress rotate 100% INTO an
equal-weight defensive-8 basket (8 lowest trailing-252d-beta panel names vs
SPY, monthly month-end selection, past-only, T+1) -- NEVER to cash
(tmin=1.00 by construction). Stress = (SPY close < SMA200) OR (SPY
trailing-60d return < -10%), all inputs past-only shift1. NO VIX input, NO ATR
stop, NO realized-vol cap -- outside retired H1 grid by construction; no
graduated levels and no 0.00 cash leg -- outside retired H3 ladder.

Replicates evolve_real.backtest() + stat_screens exactly (same lineage as
scripts/hunt_tail_sentinel_H1.py / H3). T+1, tiered W5 costs on BOTH legs,
T=1910 bars, per-family N=53 (H3 was 52 -> H5 continues family count).
Overlays: gatespec38 check_track_detailed (tail_risk_sentinel + drawdown_warrior
fallback), WF 3-fold, CPCV-proxy (4 blocks/6 paths, no embargo, disclosed),
circular-shift perm K=200 (rolls the joint position matrix, preserving basket
structure, breaking timing), stationary bootstrap block21. Paper only.

BUG AVOIDANCE: weight frames are NaN-initialized, assigned where valid,
ffilled, rows summing to 0 fall back to SPY=1 (always-invested even in
warmup) -- never zero-init before ffill.
"""
import glob
import json
import os
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

RUN_DIR = ROOT / "hunts/tail_risk_sentinel/20260911-h5-tailsentinel"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

OHLCV = ROOT / "market_data_2019_2026/ohlcv"
SPY_CSV = OHLCV / "SPY.csv"
FAMILY = "tail_risk_sentinel"
FAM_N = 53  # H1 v4=51, H3=52 -> H5 continues the family trial count

P = {
    "sma_slow": 200,
    "drawdown_trigger_60d": -0.10,
    "beta_lookback": 252,
    "defensive_k": 8,
    "selection": "monthly_month_end",
    "exec_delay": 1,
}

SKIP = {"SPY", "^VIX", "BTC", "BTC-USD", "ETH", "ETH-USD",
        "instruments", "missing"}


def load_close(path):
    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").sort_index()


spy = load_close(SPY_CSV)
Dates = spy.index
n = len(spy)
print(f"SPY bars {n} {Dates[0].date()}..{Dates[-1].date()}")

# ---- panel returns aligned to SPY index (local CSVs only) ----
names = []
for f in sorted(glob.glob(str(OHLCV / "*.csv"))):
    s = pathlib.Path(f).stem
    if s in SKIP:
        continue
    names.append(s)
print(f"panel names: {len(names)}")

rets = {}
closes = {}
for s in names:
    try:
        d = pd.read_csv(OHLCV / f"{s}.csv", parse_dates=["date"]).set_index("date").sort_index()
        c = d["close"].reindex(Dates)
        closes[s] = c
        rets[s] = c.pct_change()
    except Exception:
        continue
names = [s for s in names if s in rets]
R = pd.DataFrame(rets, index=Dates)  # n x m, NaN where missing
print(f"aligned names: {len(names)}")

spy_r = spy["close"].pct_change().fillna(0.0)

# ---- stress regime (past-only shift1), NaN-init -> ffill -> calm fallback ----
c = spy["close"]
sma_s = c.rolling(int(P["sma_slow"])).mean().shift(1)
r60 = (c.pct_change(60)).shift(1)
stress_raw = pd.Series(np.nan, index=Dates)
valid = sma_s.notna() & r60.notna()
stress_raw[valid] = ((c.shift(1) < sma_s) | (r60 < P["drawdown_trigger_60d"])).astype(float)[valid]
stress_known = stress_raw.ffill().fillna(0.0)  # warmup -> calm=SPY (always-invested)
print(f"stress occupancy {float(stress_known.mean()):.4f} "
      f"switches {int(stress_known.diff().abs().sum())}")

# ---- defensive-8 selection: month-ends, trailing-252d beta vs SPY ----
month_ends = Dates.to_series().groupby(Dates.to_series().dt.to_period("M")).tail(1)
look = int(P["beta_lookback"])
K = int(P["defensive_k"])
spy_r_arr = spy_r.values
selections = {}  # month-end date -> list of 8 names
for me in month_ends:
    t = Dates.get_loc(me)
    if t < look:
        continue
    win = R.iloc[t - look:t]
    valid_cnt = win.notna().sum()
    elig = valid_cnt[valid_cnt >= look].index.tolist()
    if len(elig) < K:
        continue
    W = win[elig].fillna(0.0).values  # w x e
    m = spy_r_arr[t - look:t]
    mc = m - m.mean()
    denom = float(mc @ mc)
    if denom <= 0:
        continue
    Wc = W - W.mean(axis=0, keepdims=True)
    betas = (Wc * mc[:, None]).sum(axis=0) / denom
    order = np.argsort(betas)
    selections[me] = [elig[i] for i in order[:K]]
print(f"month-end selections: {len(selections)}")
if selections:
    first_me = sorted(selections)[0]
    print(f"first selection {first_me.date()}: {selections[first_me]}")

# ---- target weights (NaN-init numpy backing), ffill, fallback SPY ----
assets = ["SPY"] + names
col = {a: j for j, a in enumerate(assets)}
wvals = np.full((n, len(assets)), np.nan)
sel_dates = sorted(selections)
cur_basket = None
si = 0
stress_arr = stress_known.values
for i, dt in enumerate(Dates):
    while si < len(sel_dates) and sel_dates[si] <= dt:
        cur_basket = selections[sel_dates[si]]
        si += 1
    if stress_arr[i] >= 0.5 and cur_basket is not None:
        for s in cur_basket:
            wvals[i, col[s]] = 1.0 / K
    else:
        wvals[i, col["SPY"]] = 1.0
W = pd.DataFrame(wvals, index=Dates, columns=assets)
W = W.ffill()
row_sum = W.sum(axis=1, min_count=1)
zero_rows = row_sum.fillna(0.0) < 1e-12
W = W.fillna(0.0)
W.loc[zero_rows, "SPY"] = 1.0  # warmup fallback: SPY (never cash)

# tmin sanity BEFORE trusting gates (must be >=0.70 by construction)
gross = W.sum(axis=1)
tmin_pre = float(((W.shift(1).fillna(0.0)).sum(axis=1) > 1e-9).mean())
assert 0 <= tmin_pre <= 1, f"tmin out of range: {tmin_pre}"
assert tmin_pre >= 0.70, f"INTO-leg broken: tmin={tmin_pre} < 0.70"
print(f"tmin sanity OK: {tmin_pre} (always-invested rotation)")

# ---- T+1 positions, gross returns, tiered W5 costs on both legs ----
pos = W.shift(1).fillna(0.0)
Rspy = pd.DataFrame({"SPY": spy_r}, index=Dates)
Rall = pd.concat([Rspy, R.fillna(0.0)[names]], axis=1)[assets]
gross_ret = (pos * Rall).sum(axis=1)

dpos = pos.diff().fillna(pos)
cost_mat = {}
for a in assets:
    try:
        ca = closes[a] if a != "SPY" else spy["close"]
        cb = _tiered_cost_bps(ca, FAMILY).reindex(Dates).fillna(5.0).clip(lower=5.0)
    except Exception:
        cb = pd.Series(5.0, index=Dates)
    cost_mat[a] = cb
C = pd.DataFrame(cost_mat, index=Dates)[assets]
cost = (dpos.abs() * (C / 10000.0)).sum(axis=1)
net = gross_ret - cost

turnover = dpos.abs().sum(axis=1)
trips = int((turnover > 1e-9).sum() // 2)
trades = int((turnover > 1e-9).sum())
excess = float((1 + net).prod() - (1 + spy_r).prod()) * 100
tmin = float((pos.sum(axis=1) > 1e-9).mean())
sharpe = float(safe_sharpe(net))
split = int(n * 0.7)
oos = float(safe_sharpe(net.iloc[split:])) if n - split > 20 else 0.0
eq = (1 + net).cumprod()
try:
    dsr = float(deflated_sharpe_ratio(len(net), sharpe / np.sqrt(252.0), max(1, FAM_N)))
except Exception:
    dsr = 0.0

# ---- circular-shift perm on joint position matrix (K=200, seed 7) ----
try:
    Pv = pos.values.astype(float)
    Rv = Rall.values.astype(float)
    Cv = (C.values / 10000.0).astype(float)
    rng = np.random.default_rng(7)
    wins = 0
    Kperm = 200
    for _ in range(Kperm):
        shift = int(rng.integers(1, len(Pv)))
        Ps = np.roll(Pv, shift, axis=0)
        turn = np.abs(np.diff(Ps, axis=0, prepend=Ps[0:1]))
        tn = pd.Series((Ps * Rv).sum(axis=1) - (turn * Cv).sum(axis=1))
        if float(safe_sharpe(tn)) >= sharpe:
            wins += 1
    perm_p = wins / Kperm
except Exception:
    perm_p = 1.0
try:
    boot_p = stationary_bootstrap_p(np.asarray(net.fillna(0.0).values, dtype=float))
except Exception:
    boot_p = 1.0

print(f"h5 sharpe={sharpe:.3f} cagr={cagr(eq):.4f} dd={max_dd(eq):.4f} "
      f"oos={oos:.3f} excess={excess:+.3f}pp tmin={tmin:.4f} "
      f"trips={trips} dsr={dsr:.4f} perm={perm_p} boot={boot_p} n={n}")

m = {"sharpe": sharpe, "max_dd": max_dd(eq), "oos": oos,
     "excess": round(excess, 2), "dsr": round(dsr, 4), "trips": trips,
     "tmin": round(tmin, 4), "perm_p": round(perm_p, 4), "boot_p": round(boot_p, 4)}
det = check_track_detailed(m)
tr = det.get("tail_risk_sentinel", {})
dw = det.get("drawdown_warrior", {})
print("TR:", tr.get("passed"), tr.get("terms"))
print("DW:", dw.get("passed"), dw.get("terms"))


def wf_3fold(net_s):
    edges = [0, n // 3, 2 * n // 3, n]
    folds = []
    for i in range(3):
        seg = net_s.iloc[edges[i]:edges[i + 1]]
        folds.append(round(float(safe_sharpe(seg)) if len(seg) > 20 else 0.0, 4))
    return folds


def cpcv_proxy(net_s):
    edges = [0, n // 4, n // 2, 3 * n // 4, n]
    blocks = [net_s.iloc[edges[i]:edges[i + 1]] for i in range(4)]
    paths = []
    for i in range(4):
        for j in range(i + 1, 4):
            test = pd.concat([blocks[i], blocks[j]]).sort_index()
            paths.append(round(float(safe_sharpe(test)) if len(test) > 20 else 0.0, 4))
    return paths


wf = wf_3fold(net)
cpcv = cpcv_proxy(net)
print("WF folds OOS:", wf, "mean:", round(float(np.mean(wf)), 4))
print("CPCV paths:", cpcv, "mean:", round(float(np.mean(cpcv)), 4),
      "min:", min(cpcv), "frac>0:", round(float(np.mean([x > 0 for x in cpcv])), 4))

L1 = sharpe >= 0.50 and max_dd(eq) <= 0.35 and excess > 0
TR_pass = bool(tr.get("passed")) and perm_p <= 0.05 and boot_p <= 0.05
DW_pass = bool(dw.get("passed")) and perm_p <= 0.05 and boot_p <= 0.05
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
    "id": "tail_risk_sentinel_h5",
    "family": FAMILY,
    "params": P,
    "metrics": {"sharpe": sharpe, "cagr": cagr(eq), "max_dd": max_dd(eq),
                "oos_sharpe": oos, "excess": round(excess, 2), "tmin": round(tmin, 4),
                "dsr": round(dsr, 4), "trips": trips, "trades": trades,
                "perm_p": round(perm_p, 4),
                "boot_p": round(boot_p, 4), "n_bars": n, "fam_trials": FAM_N},
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
tmp = RES_DIR / "eval_tail_risk_sentinel_h5.json.tmp"
final = RES_DIR / "eval_tail_risk_sentinel_h5.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
