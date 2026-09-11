#!/usr/bin/env python3
"""H9 tail-sentinel hunt: ALWAYS-INVESTED stress rotation SPY -> duration/metals-4.

Untried vs TABOO: LOOSER SINGLE-TRIGGER (stress = SPY close < SMA200 alone OR
SPY trailing-60d return < -8% alone -- more episodes than H7's -10%) + hard
duration/metals sleeve (fixed [TLT, GLD, SLV, HYG, UUP], max 4 lowest
trailing-252d-beta, monthly month-end, equal-weight, T+1) + DD CAP on the
INTO-leg (when the sleeve's own equal-weight trailing-60d DD exceeds 10%,
scale the INTO-leg to 0.5x with the remainder in SPY -- still always-invested,
tmin=1.00 by construction). NEVER cash. NO VIX input, NO ATR stop, NO
realized-vol cap -- outside retired H1 grid; no graduated levels and no 0.00
cash leg -- outside retired H3 ladder; no broad-panel equity defensive-8 --
outside retired H5 (52% DD); tighter -10% trigger + no cap was H7 (cycle22
HONEST_ABANDON).

Replicates evolve_real.backtest() + stat_screens exactly (same lineage as
scripts/hunt_tail_sentinel_H7.py). T+1, tiered W5 costs on BOTH legs, T=1910
bars, per-family N=55 (H7 was 54 -> H9 continues family count). Overlays:
gatespec38 check_track_detailed (tail_risk_sentinel + drawdown_warrior
fallback), WF 3-fold, CPCV-proxy (4 blocks/6 paths, no embargo, disclosed),
circular-shift perm K=200 (rolls the joint position matrix, preserving basket
structure, breaking timing), stationary bootstrap block21. Paper only.

BUG AVOIDANCE: weight frames are NaN-initialized, assigned where valid,
ffilled, rows summing to 0 fall back to SPY=1 (always-invested even in
warmup) -- never zero-init before ffill. Every row is written complete
(calm -> SPY=1; stress -> basket 1/K or capped 0.5 SPY + 0.5 basket).
"""
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

RUN_DIR = ROOT / "hunts/tail_risk_sentinel/20260911-h9-tailsentinel"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

OHLCV = ROOT / "market_data_2019_2026/ohlcv"
SPY_CSV = OHLCV / "SPY.csv"
FAMILY = "tail_risk_sentinel"
FAM_N = 55  # H1 v4=51, H3=52, H5=53, H7=54 -> H9 continues the family trial count

P = {
    "sma_slow": 200,
    "drawdown_trigger_60d": -0.08,
    "beta_lookback": 252,
    "defensive_k": 4,
    "selection": "monthly_month_end",
    "dd_cap_trigger_60d": -0.10,
    "dd_cap_scale": 0.5,
    "exec_delay": 1,
}

SLEEVE = ["TLT", "GLD", "SLV", "HYG", "UUP"]


def load_close(path):
    df = pd.read_csv(path, parse_dates=["date"])
    return df.set_index("date").sort_index()


spy = load_close(SPY_CSV)
Dates = spy.index
n = len(spy)
print(f"SPY bars {n} {Dates[0].date()}..{Dates[-1].date()}")

# ---- sleeve returns aligned to SPY index (local CSVs only) ----
rets = {}
closes = {}
for s in SLEEVE:
    d = pd.read_csv(OHLCV / f"{s}.csv", parse_dates=["date"]).set_index("date").sort_index()
    c = d["close"].reindex(Dates)
    closes[s] = c
    rets[s] = c.pct_change()
names = [s for s in SLEEVE if s in rets]
R = pd.DataFrame(rets, index=Dates)
print(f"sleeve names: {names}")

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

# ---- DD CAP gauge (past-only shift1): sleeve equal-weight index trailing-60d DD.
# Sleeve index = equal-weight cumulative of the 5 sleeve closes (rebased, past
# data only); dd60 = close/rolling60max - 1, shifted 1 so today's cap uses only
# yesterday-and-before information. Cap active when dd60 < -0.10. ----
sleeve_px = pd.DataFrame({s: closes[s] for s in names}, index=Dates)
sleeve_idx = (sleeve_px / sleeve_px.iloc[0]).mean(axis=1)
roll_max60 = sleeve_idx.rolling(60).max().shift(1)
sleeve_dd60 = (sleeve_idx.shift(1) / roll_max60 - 1.0)
cap_raw = pd.Series(np.nan, index=Dates)
cap_valid = sleeve_dd60.notna()
cap_raw[cap_valid] = (sleeve_dd60 < P["dd_cap_trigger_60d"]).astype(float)[cap_valid]
cap_known = cap_raw.ffill().fillna(0.0)  # warmup -> no cap
print(f"cap occupancy {float(cap_known.mean()):.4f} "
      f"cap switches {int(cap_known.diff().abs().sum())}")

# ---- duration/metals-4 selection: month-ends, trailing-252d beta vs SPY ----
month_ends = Dates.to_series().groupby(Dates.to_series().dt.to_period("M")).tail(1)
look = int(P["beta_lookback"])
K = int(P["defensive_k"])
spy_r_arr = spy_r.values
selections = {}  # month-end date -> list of 4 names
for me in month_ends:
    t = Dates.get_loc(me)
    if t < look:
        continue
    win = R.iloc[t - look:t]
    valid_cnt = win.notna().sum()
    elig = valid_cnt[valid_cnt >= look].index.tolist()
    if len(elig) < K:
        continue
    W_ = win[elig].fillna(0.0).values  # w x e
    m = spy_r_arr[t - look:t]
    mc = m - m.mean()
    denom = float(mc @ mc)
    if denom <= 0:
        continue
    Wc = W_ - W_.mean(axis=0, keepdims=True)
    betas = (Wc * mc[:, None]).sum(axis=0) / denom
    order = np.argsort(betas)
    selections[me] = [elig[i] for i in order[:K]]
print(f"month-end selections: {len(selections)}")
if selections:
    first_me = sorted(selections)[0]
    last_me = sorted(selections)[-1]
    print(f"first selection {first_me.date()}: {selections[first_me]}")
    print(f"last selection {last_me.date()}: {selections[last_me]}")

# ---- target weights: FULL-ROW assignment every day (no ffill contamination).
# Calm -> SPY=1/rest 0; stress uncapped -> basket 1/K, SPY=0; stress capped ->
# 0.5 SPY + 0.5 basket (0.5/K each); warmup stress w/o basket -> SPY=1.
# NaN-init kept so any unwritten row is detectable (assert below). ----
assets = ["SPY"] + names
col = {a: j for j, a in enumerate(assets)}
wvals = np.full((n, len(assets)), np.nan)
sel_dates = sorted(selections)
cur_basket = None
si = 0
stress_arr = stress_known.values
cap_arr = cap_known.values
cap_scale = float(P["dd_cap_scale"])
for i, dt in enumerate(Dates):
    while si < len(sel_dates) and sel_dates[si] <= dt:
        cur_basket = selections[sel_dates[si]]
        si += 1
    if stress_arr[i] >= 0.5 and cur_basket is not None:
        if cap_arr[i] >= 0.5:
            wvals[i, col["SPY"]] = 1.0 - cap_scale
            for a in names:
                wvals[i, col[a]] = (cap_scale / K) if a in cur_basket else 0.0
        else:
            wvals[i, col["SPY"]] = 0.0
            for a in names:
                wvals[i, col[a]] = (1.0 / K) if a in cur_basket else 0.0
    else:
        wvals[i, col["SPY"]] = 1.0
        for a in names:
            wvals[i, col[a]] = 0.0
W = pd.DataFrame(wvals, index=Dates, columns=assets)
assert bool((~W.isna()).all(axis=None)), "unwritten weight row detected"
gross_pre = W.sum(axis=1)
assert bool(((gross_pre - 1.0).abs() < 1e-9).all()), \
    f"gross exposure != 1.0: min={gross_pre.min()} max={gross_pre.max()}"

# tmin sanity BEFORE trusting gates (must be >=0.70 by construction)
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

print(f"h9 sharpe={sharpe:.3f} cagr={cagr(eq):.4f} dd={max_dd(eq):.4f} "
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
    "id": "tail_risk_sentinel_h9",
    "family": FAMILY,
    "params": dict(P, defensive_sleeve=SLEEVE,
                   dd_cap_choice="(c) looser -8% single-trigger + 0.5x INTO-leg cap on sleeve 60d DD>10%"),
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
tmp = RES_DIR / "eval_tail_risk_sentinel_h9.json.tmp"
final = RES_DIR / "eval_tail_risk_sentinel_h9.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
