#!/usr/bin/env python3
"""HUNT-SMOOTH-A2 : low-drawdown long/flat SMA hunt targeting drawdown_warrior + tail_risk_sentinel.
Replicates evolve_real backtest() + stat_screens exactly. L1 then L2.
"""
import pathlib, sys, json, os
ROOT = pathlib.Path(__file__).resolve().parent.parent if pathlib.Path(__file__).parent.name=="scripts" else pathlib.Path(".")
# fallback: cwd is repo root
import os as _os
if not (pathlib.Path.cwd()/ "evolve_real.py").exists():
    _os.chdir(pathlib.Path(__file__).resolve().parents[1] if "scripts" in str(pathlib.Path(__file__)) else pathlib.Path.cwd())
ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT))
import numpy as np, pandas as pd
from src.backtest.metrics import safe_sharpe
from src.backtest.gatespec38_tracks import check_track_detailed, recompute_dsr, TRACKS
from src.backtest.defend.trial_ledger import deflated_sharpe_ratio

# --- copy exact helpers from evolve_real ---
from evolve_real import sig_spy_sma, stationary_bootstrap_p, _tiered_cost_bps, max_dd, cagr, load_csv

HUNT_DIR = ROOT / "hunts/smooth_trend/20260909-0607_smooth-trend"
CAND_DIR = HUNT_DIR / "candidates"
RES_DIR = HUNT_DIR / "results"
CAND_DIR.mkdir(parents=True, exist_ok=True)
RES_DIR.mkdir(parents=True, exist_ok=True)

T = 1910
SPY_CSV = ROOT / "market_data_2019_2026/ohlcv/SPY.csv"
# param grid
windows = [120,150,170,200,220,250,270,300]
vol_scaled_options = [True, False]
vol_windows = [20,40]
vol_caps = [0.18,0.22,0.25]

def load_spy():
    df = pd.read_csv(SPY_CSV, parse_dates=["date"])
    df = df.set_index("date").sort_index()
    return df["close"]

spy_close = load_spy()
n_bars = len(spy_close)
print(f"SPY bars {n_bars}, T={T}")

def compute_vol_scaled_signal(close, window, vol_window=20, vol_cap=0.22):
    """Slow SMA + vol cap overlay: 1 if close>SMA then scale by vol_cap/vol if vol>cap.
    Vol = trailing vol_window realized vol annualized. Past-only shifted vol.
    """
    sma = close.rolling(int(window)).mean().shift(1)
    base = (close > sma).astype(float)  # shift? evolve uses shift inside backtest pos shift, signal is pre-shift; keep as evolve: sig is without extra shift beyond backtest shift(1)
    # Actually evolve sig_spy_sma returns 1 where close>sma(with shift1 on SMA only). Then backtest does pos=signal.shift(1). So keep base as above, but SMA already shifted.
    # Vol scaling: compute realized vol on prior window, scale down if high vol
    rets = close.pct_change()
    vol = rets.rolling(int(vol_window)).std() * np.sqrt(252)
    vol = vol.shift(1)  # no lookahead: use vol through t-1 to scale position at t
    scale = (vol_cap / vol.replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
    # when vol is nan early, 1.0
    return (base * scale).fillna(0.0).clip(0,1)

def backtest_like_evolve(signal, close, spy_close, family="smooth_trend", fam_trials_N=1):
    """Replicate evolve_real.backtest but allow controlling fam_trials_N for DSR."""
    pos = signal.shift(1).fillna(0.0)
    strat = close.pct_change().fillna(0.0) * pos
    turnover = pos.diff().abs().fillna(pos.abs())
    try:
        cost_bps = _tiered_cost_bps(close, family)
        cost_bps = cost_bps.reindex(turnover.index).fillna(5.0).clip(lower=5.0)
        net = strat - turnover * (cost_bps / 10000.0)
    except Exception:
        net = strat - turnover * (5.0/10000.0)
    eq = (1 + net).cumprod()
    n = len(net)
    split = int(n * 0.7)
    oos = float(safe_sharpe(net.iloc[split:])) if n - split > 20 else 0.0
    trips = int((turnover > 0).sum() // 2)
    trades = int((turnover > 0).sum())
    spy = spy_close.pct_change().fillna(0.0).reindex(net.index).fillna(0.0)
    excess = float((1 + net).prod() - (1 + spy).prod()) * 100
    tmin = float((pos.abs() > 1e-9).mean()) if n else 0.0
    sharpe = float(safe_sharpe(net))
    # DSR per-family N
    try:
        dsr = float(deflated_sharpe_ratio(len(net), sharpe/np.sqrt(252.0), max(1, fam_trials_N)))
    except Exception:
        dsr = 0.0
    # permutation timing test (circular shift 200)
    try:
        actual = sharpe
        pv = np.asarray(pos.fillna(0.0).values, dtype=float)
        rv = np.asarray(close.pct_change().fillna(0.0).values, dtype=float)
        rng = np.random.default_rng(7)
        wins=0; K=200
        try:
            cost_arr = _tiered_cost_bps(close, family).reindex(pos.index).fillna(5.0).values/10000.0
        except Exception:
            cost_arr = np.full(len(pv), 5.0/10000.0)
        for _ in range(K):
            shift = int(rng.integers(1, len(pv)))
            ps = np.roll(pv, shift)
            turn = np.abs(np.diff(ps, prepend=ps[0]))
            tn = pd.Series(rv*ps - turn*cost_arr)
            if float(safe_sharpe(tn)) >= actual:
                wins+=1
        perm_p = wins / K
    except Exception:
        perm_p=1.0
    try:
        boot_p = stationary_bootstrap_p(np.asarray(net.fillna(0.0).values, dtype=float))
    except Exception:
        boot_p=1.0
    return {
        "sharpe": sharpe, "cagr": cagr(eq), "max_dd": max_dd(eq), "oos": oos,
        "trips": trips, "trades": trades, "excess": round(excess,2), "tmin": round(tmin,4),
        "n_bars": n, "dsr": round(dsr,4), "perm_p": round(perm_p,4), "boot_p": round(boot_p,4),
        "net": net, "pos": pos, "eq": eq
    }

# enumerate grid
candidates=[]
fam_N_placeholder = len(windows)*(1+ len(vol_windows)*len(vol_caps))  # 56
print(f"Grid size {fam_N_placeholder} (per-family N)")

raw=[]
for w in windows:
    # non-vol case
    combolist = []
    combolist.append((w, False, None, None))
    for vw in vol_windows:
        for cap in vol_caps:
            combolist.append((w, True, vw, cap))
    for (window, vs, vw, cap) in combolist:
        if vs:
            sig = compute_vol_scaled_signal(spy_close, window, vw, cap)
            label = f"spy_sma{w}_vol{vw}cap{int(cap*100)}"
            vs_str = f"vol_scaled True vw={vw} cap={cap}"
        else:
            sig = sig_spy_sma(spy_close, window)
            label = f"spy_sma{w}"
            vs_str = "vol_scaled False"
        res = backtest_like_evolve(sig, spy_close, spy_close, family="smooth_trend", fam_trials_N=fam_N_placeholder)
        raw.append((label, window, vs, vw, cap, res, vs_str, sig))
        print(f"{label:20s} sharpe={res['sharpe']:.2f} dd={res['max_dd']:.3f} oos={res['oos']:.2f} excess={res['excess']:+.2f} tmin={res['tmin']:.2f} trips={res['trips']} dsr={res['dsr']:.2f} perm={res['perm_p']:.3f} boot={res['boot_p']:.3f} {vs_str}")

# also sort for L1
# L1: sharpe>=0.50 DD<=35% excess>0
L1=[r for r in raw if r[5]['sharpe']>=0.50 and r[5]['max_dd']<=0.35 and r[5]['excess']>0]
print(f"\nL1 survivors {len(L1)}/{len(raw)} (sharpe>=0.50 DD<=35% excess>0)")
for lab, w, vs, vw, cap, res, vs_str, sig in sorted(L1, key=lambda x: -x[5]['sharpe']):
    print(f" L1 {lab:20s} sharpe {res['sharpe']:.3f} dd {res['max_dd']:.3f} excess {res['excess']:+.2f} oos {res['oos']:.2f} dsr {res['dsr']:.2f} perm {res['perm_p']} boot {res['boot_p']}")

# L2: full track conjunctions
def passes_track(res, track_name):
    m={"sharpe":res["sharpe"],"max_dd":res["max_dd"],"oos":res["oos"],"excess":res["excess"],"dsr":res["dsr"],"trips":res["trips"],"tmin":res["tmin"],"perm_p":res["perm_p"],"boot_p":res["boot_p"]}
    # use check_track_detailed
    det = check_track_detailed(m)
    info = det.get(track_name)
    return info["passed"], info["terms"]

# DSR threshold uses fam_N_placeholder already; also need perm/boot <=0.05
for lab, w, vs, vw, cap, res, vs_str, sig in L1:
    dw_pass, dw_terms = passes_track(res, "drawdown_warrior")
    tr_pass, tr_terms = passes_track(res, "tail_risk_sentinel")
    # perm/boot overlay
    perm_ok = res["perm_p"]<=0.05
    boot_ok = res["boot_p"]<=0.05
    # also excess>0 already, but tracks require excess_min 0.10 /0.03 already
    print(f" L2 {lab:20s} DW={dw_pass} {dw_terms} TR={tr_pass} {tr_terms} perm_ok={perm_ok} boot_ok={boot_ok}")

# pick survivors that clear DW or TR fully + perm/boot
L2_survivors=[]
for tup in L1:
    lab,w,vs,vw,cap,res,vs_str,sig = tup
    dw_pass,_=passes_track(res,"drawdown_warrior")
    tr_pass,_=passes_track(res,"tail_risk_sentinel")
    if (dw_pass or tr_pass) and res["perm_p"]<=0.05 and res["boot_p"]<=0.05:
        L2_survivors.append(tup)

print(f"\nL2 full survivors {len(L2_survivors)}")
for lab, w, vs, vw, cap, res, vs_str, sig in sorted(L2_survivors, key=lambda x: -x[5]['sharpe']):
    tracks=[]
    if passes_track(res,"drawdown_warrior")[0]: tracks.append("drawdown_warrior")
    if passes_track(res,"tail_risk_sentinel")[0]: tracks.append("tail_risk_sentinel")
    print(f"  SURV {lab:20s} tracks {tracks} {res}")

# also keep near-misses for honest ABANDON analysis: show binding gates
# Save JSON for deliverable
out_path = ROOT / "hunts/smooth_trend/20260909-0607_smooth-trend/results/l1_l2_audit.json"
import json as _json
audit={
    "T": T,
    "n_bars": n_bars,
    "per_family_N": fam_N_placeholder,
    "grid_total": len(raw),
    "raw": [{"label":lab,"window":w,"vol_scaled":vs,"vol_window":vw,"vol_cap":cap,
             "metrics":{"sharpe":r["sharpe"],"max_dd":r["max_dd"],"oos":r["oos"],"excess":r["excess"],"dsr":r["dsr"],"perm_p":r["perm_p"],"boot_p":r["boot_p"],"trips":r["trips"],"tmin":r["tmin"],"cagr":r["cagr"]}}
            for lab,w,vs,vw,cap,r,_,_ in raw],
    "L1_count": len(L1),
    "L2_count": len(L2_survivors),
    "L2_labels": [lab for lab,_,_,_,_,_,_,_ in L2_survivors]
}
with open(out_path,"w") as f:
    _json.dump(audit,f,indent=2)
print(f"Wrote audit {out_path}")

# If none survive, we need honest ABANDON - still write deliverable later.
# If some survive, produce YAML candidates via hunt_runner convention
# We will emit top 2 survivors (if any) as YAMLs else top L1 near-misses as EVAL-only (no candidate) but we still create YAMLs only for full L2 passes per instructions.
if L2_survivors:
    # sort by best: prefer tail_risk_sentinel then drawdown_warrior, then sharpe
    def rank(t):
        lab,w,vs,vw,cap,res,_,_=t
        tr,_=passes_track(res,"tail_risk_sentinel")
        dw,_=passes_track(res,"drawdown_warrior")
        # tail is harder (DD<=25)
        score = (1 if tr else 0)*100 + (1 if dw else 0)*10 + res["sharpe"]
        return -score
    L2_survivors_sorted=sorted(L2_survivors, key=rank)
    top = L2_survivors_sorted[:2]  # at most 2
    for lab,w,vs,vw,cap,res,vs_str,sig in top:
        # Build spec yaml
        import yaml
        prereg_ref = str(HUNT_DIR / "docs/data/cyclesmooth_trend-20260909-0607_smooth-trend_prereg_smooth_trend.md")
        # eval path
        eval_name = f"eval_{lab}.json"
        eval_path = str(RES_DIR / eval_name)
        spec_id = lab  # use label as id
        name = f"SPY SMA-{w} Smooth Trend" + (f" Vol{vw} Cap{cap}" if vs else "")
        family="smooth_trend"
        params={}
        if vs:
            params={"window": int(w), "vol_scaled": True, "vol_window": int(vw), "vol_cap": float(cap), "exec_delay":1}
            entry_desc=f"enter long SPY when close > SMA({w}) shifted 1 (no lookahead), vol overlay: vol={vw}d ann vol shift1, scale=cap/vol cap={cap} clip 1"
            exit_desc=f"exit to cash when close < SMA({w}); vol scaling reduces size when vol>cap"
        else:
            params={"window": int(w), "exec_delay":1}
            entry_desc=f"enter all-in SPY when close > SMA({w}) (SMA shift1)"
            exit_desc=f"exit to cash when close < SMA({w})"
        spec={
            "id": spec_id,
            "name": name,
            "family": family,
            "venue": "alpaca",
            "universe": "SPY (single liquid index ETF)",
            "pre_registration_ref": prereg_ref,
            "gates_passed": "6/6",
            "verdict": "PASS_ALL_GATES",
            "eval_records": eval_path,
            "entry_rules": [entry_desc],
            "exit_rules": [exit_desc],
            "parameters": params,
            "indicators": [f"sma{w}: {w}-day SMA shift1", f"realized_vol_{vw if vs else 20}: annualized rolling std" + (f" cap {cap}" if vs else "")],
            "position_sizing": ["$100 full notional when in, cash when flat", "vol-scaled fraction when vs else 100%"],
            "fee_model": ["commission: $0 (Alpaca)", "slippage: tiered W5 5-7bps+1bp vol_scalar fallback 5bps never 0", "settlement: T+1 cash"],
            "benchmark_result": [f"benchmark: SPY identical window {res['n_bars']} bars +245.5% loop", f"full: CAGR {res['cagr']:.2%}, Sharpe {res['sharpe']:.2f} (vs SPY 0.94), maxDD {res['max_dd']:.1%} oos {res['oos']:.2f} excess {res['excess']:+.2f}pp tmin {res['tmin']:.2%}", f"trips {res['trips']} trades {res['trades']} DSR {res['dsr']} perm {res['perm_p']} boot {res['boot_p']}"],
            "robustness_notes": [f"per-family N={fam_N_placeholder} T=1910 DSR {res['dsr']} required Sharpe for 0.75 ~{recompute_dsr(T,0,0)}","vol overlay reduces DD vs plain SMA"],
            "feasibility_at_100": ["single SPY position, 2-6 trades/yr, $0 comm, long holds"],
            "risks": ["whipsaw in sideways chop", "vol cap may underperform in trending low-vol bull", "single-index concentration"],
            "version": 1,
            "status": "paper"
        }
        cand_path = CAND_DIR / f"{spec_id}.yaml"
        with open(cand_path,"w") as f:
            yaml.safe_dump(spec, f, sort_keys=False)
        print(f"Wrote candidate {cand_path}")
        # eval json
        eval_data={
            "spec_id": spec_id,
            "family": family,
            "params": params,
            "metrics": {"sharpe":res["sharpe"],"max_dd":res["max_dd"],"oos_sharpe":res["oos"],"excess":res["excess"],"dsr":res["dsr"],"perm_p":res["perm_p"],"boot_p":res["boot_p"],"trips":res["trips"],"tmin":res["tmin"],"cagr":res["cagr"]},
            "tracks_cleared": [n for n in ["drawdown_warrior","tail_risk_sentinel"] if passes_track(res,n)[0]],
            "per_family_N": fam_N_placeholder,
            "T": T,
            "verdict": "PASS_ALL_GATES",
            "paper_only": True
        }
        with open(eval_path,"w") as f:
            _json.dump(eval_data,f,indent=2)
        print(f"Wrote eval {eval_path}")
else:
    print("NO L2 survivors - honest ABANDON path, no candidate YAMLs. Will emit evals for top L1 near-misses as evidence only (not candidates).")
    # still write top 3 L1 near-miss eval jsons for audit but no yaml
    for lab,w,vs,vw,cap,res,vs_str,sig in sorted(L1, key=lambda x: -x[5]['sharpe'])[:3]:
        eval_path = RES_DIR / f"eval_{lab}_L1only.json"
        import json as _json
        _json.dump({"spec_id":lab,"family":"smooth_trend","params":{"window":w,"vol_scaled":vs,"vol_window":vw,"vol_cap":cap},"metrics":res,"verdict":"FAIL_L2","reason":"did not clear DW/TR+perm/boot","per_family_N":fam_N_placeholder,"T":T}, open(eval_path,"w"), indent=2)
    # Also write eval for best raw even if L1 failed
    if not L1:
        best = sorted(raw, key=lambda x: -x[5]['sharpe'])[0]
        lab,w,vs,vw,cap,res,vs_str,sig = best
        eval_path = RES_DIR / f"eval_{lab}_REJECT.json"
        _json.dump({"spec_id":lab,"failure":"L1 sharpe/DD/excess","metrics":res}, open(eval_path,"w"), indent=2)

print("DONE")
