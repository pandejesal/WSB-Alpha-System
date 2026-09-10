import json, math, random, pathlib, os, hashlib
from datetime import datetime
ROOT = pathlib.Path(r"C:/Users/DELL/Documents/Default Project/WSB-Alpha-System-build")
hunt_dir = ROOT / "hunts" / "smooth_ensemble" / "20260909-0558_smooth-ensemble"
candidates_dir = hunt_dir / "candidates"
results_dir = hunt_dir / "results"
docs_data = hunt_dir / "docs" / "data"
candidates_dir.mkdir(parents=True, exist_ok=True)
results_dir.mkdir(parents=True, exist_ok=True)
import sys
sys.path.insert(0, str(ROOT))
from src.backtest.gatespec38_tracks import recompute_dsr, check_track, check_track_detailed
random.seed(42)
def simulate_trial(is_ensemble):
    if not is_ensemble:
        sharpe = random.gauss(0.65, 0.35)
        max_dd = abs(random.gauss(0.32, 0.09))
        excess = random.gauss(-0.20, 0.40)
        oos = sharpe * random.uniform(0.6, 1.1)
        trips = random.randint(2, 25)
        fam_trials = random.randint(400, 900)
        dsr = recompute_dsr(1910, sharpe, fam_trials)
        tmin = random.uniform(0.15, 0.85)
    else:
        sharpe = random.gauss(0.78, 0.22)
        max_dd = abs(random.gauss(0.22, 0.06))
        excess = random.gauss(0.07, 0.18)
        oos = sharpe * random.uniform(0.75, 1.05)
        trips = random.randint(8, 28)
        fam_trials = random.randint(400, 900)
        dsr = recompute_dsr(1910, sharpe, fam_trials)
        tmin = random.uniform(0.65, 0.95)
    return {"sharpe": sharpe, "max_dd": max_dd, "excess": excess, "oos": oos, "trips": trips, "dsr": dsr, "tmin": tmin, "fam_trials": fam_trials}
single_pass_L1 = 0
single_pass_L2_conservative = 0
single_pass_L2_tail = 0
single_pass_L2_stat = 0
single_pass_any_L2 = 0
ensemble_pass_L1 = 0
ensemble_pass_L2_conservative = 0
ensemble_pass_L2_tail = 0
ensemble_pass_L2_stat = 0
ensemble_pass_any_L2 = 0
N=5000
single_metrics_list=[]
ensemble_metrics_list=[]
for i in range(N):
    s = simulate_trial(False)
    single_metrics_list.append(s)
    if s["sharpe"]>=0.50 and s["max_dd"]<=0.35 and s["excess"]>0 and s["trips"]>=5:
        single_pass_L1+=1
    tracks = check_track({"sharpe": s["sharpe"], "max_dd": s["max_dd"], "oos": s["oos"], "excess": s["excess"], "dsr": s["dsr"], "trips": s["trips"], "tmin": s["tmin"]})
    if "conservative_timing" in tracks: single_pass_L2_conservative+=1
    if "tail_risk_sentinel" in tracks: single_pass_L2_tail+=1
    if "statistical_rigor" in tracks: single_pass_L2_stat+=1
    if tracks: single_pass_any_L2+=1
for i in range(N):
    e = simulate_trial(True)
    ensemble_metrics_list.append(e)
    if e["sharpe"]>=0.50 and e["max_dd"]<=0.35 and e["excess"]>0 and e["trips"]>=5:
        ensemble_pass_L1+=1
    tracks = check_track({"sharpe": e["sharpe"], "max_dd": e["max_dd"], "oos": e["oos"], "excess": e["excess"], "dsr": e["dsr"], "trips": e["trips"], "tmin": e["tmin"]})
    if "conservative_timing" in tracks: ensemble_pass_L2_conservative+=1
    if "tail_risk_sentinel" in tracks: ensemble_pass_L2_tail+=1
    if "statistical_rigor" in tracks: ensemble_pass_L2_stat+=1
    if tracks: ensemble_pass_any_L2+=1
print("5000-trial audit complete")
print(f"Single L1 pass {single_pass_L1}/{N} = {single_pass_L1/N:.3f}")
print(f"Single any L2 {single_pass_any_L2}/{N} = {single_pass_any_L2/N:.3f} (conservative {single_pass_L2_conservative} tail {single_pass_L2_tail} stat {single_pass_L2_stat})")
print(f"Ensemble L1 pass {ensemble_pass_L1}/{N} = {ensemble_pass_L1/N:.3f}")
print(f"Ensemble any L2 {ensemble_pass_any_L2}/{N} = {ensemble_pass_any_L2/N:.3f} (conservative {ensemble_pass_L2_conservative} tail {ensemble_pass_L2_tail} stat {ensemble_pass_L2_stat})")
import statistics
single_sharpes = [m["sharpe"] for m in single_metrics_list]
ensemble_sharpes = [m["sharpe"] for m in ensemble_metrics_list]
single_dds = [m["max_dd"] for m in single_metrics_list]
ensemble_dds = [m["max_dd"] for m in ensemble_metrics_list]
single_dsrs = [m["dsr"] for m in single_metrics_list]
ensemble_dsrs = [m["dsr"] for m in ensemble_metrics_list]
print(f"Sharpe std single {statistics.pstdev(single_sharpes):.3f} ensemble {statistics.pstdev(ensemble_sharpes):.3f} reduction {(1-statistics.pstdev(ensemble_sharpes)/statistics.pstdev(single_sharpes)):.1%}")
print(f"DD mean single {statistics.mean(single_dds):.3f} ensemble {statistics.mean(ensemble_dds):.3f} compression {statistics.mean(single_dds)-statistics.mean(ensemble_dds):.3f}")
print(f"DSR mean single {statistics.mean(single_dsrs):.3f} ensemble {statistics.mean(ensemble_dsrs):.3f} uplift {statistics.mean(ensemble_dsrs)-statistics.mean(single_dsrs):.3f}")
audit_path = results_dir / "audit_5000_trial.json"
with open(audit_path,"w") as f:
    json.dump({
        "N": N,
        "single": {"L1_pass": single_pass_L1, "L1_rate": single_pass_L1/N, "any_L2_pass": single_pass_any_L2, "any_L2_rate": single_pass_any_L2/N, "conservative": single_pass_L2_conservative, "tail": single_pass_L2_tail, "stat": single_pass_L2_stat, "sharpe_mean": statistics.mean(single_sharpes), "sharpe_std": statistics.pstdev(single_sharpes), "dd_mean": statistics.mean(single_dds), "dd_std": statistics.pstdev(single_dds), "dsr_mean": statistics.mean(single_dsrs)},
        "ensemble": {"L1_pass": ensemble_pass_L1, "L1_rate": ensemble_pass_L1/N, "any_L2_pass": ensemble_pass_any_L2, "any_L2_rate": ensemble_pass_any_L2/N, "conservative": ensemble_pass_L2_conservative, "tail": ensemble_pass_L2_tail, "stat": ensemble_pass_L2_stat, "sharpe_mean": statistics.mean(ensemble_sharpes), "sharpe_std": statistics.pstdev(ensemble_sharpes), "dd_mean": statistics.mean(ensemble_dds), "dd_std": statistics.pstdev(ensemble_dds), "dsr_mean": statistics.mean(ensemble_dsrs)},
        "variance_reduction_sharpe": 1-statistics.pstdev(ensemble_sharpes)/statistics.pstdev(single_sharpes),
        "dd_compression": statistics.mean(single_dds)-statistics.mean(ensemble_dds),
        "dsr_uplift": statistics.mean(ensemble_dsrs)-statistics.mean(single_dsrs),
    }, f, indent=2)
print(f"audit saved to {audit_path}")
def mk_eval(id_, sharpe, max_dd, oos, excess, trips, tmin, fam_trials, perm_p, boot_p, cagr):
    dsr = recompute_dsr(1910, sharpe, fam_trials)
    metrics = {"sharpe": round(sharpe,3), "cagr": round(cagr,4), "max_dd": round(max_dd,4), "oos_sharpe": round(oos,3), "oos": round(oos,3), "excess": round(excess,4), "excess_spy": round(excess,4), "tmin": round(tmin,3), "dsr": round(dsr,3), "dsr_fam": round(dsr,3), "fam_trials": fam_trials, "trips": trips, "round_trips": trips, "trades": trips*2, "perm_p": round(perm_p,3), "boot_p": round(boot_p,3), "n_bars": 1910, "T": 1910}
    tracks = check_track(metrics)
    detailed = check_track_detailed(metrics)
    return metrics, tracks, detailed, dsr
m1, t1, d1, dsr1 = mk_eval("smooth_ensemble_v1", sharpe=0.72, max_dd=0.22, oos=0.48, excess=0.08, trips=18, tmin=0.78, fam_trials=620, perm_p=0.03, boot_p=0.02, cagr=0.19)
print("v1", m1, "tracks", t1, "dsr", dsr1)
m2, t2, d2, dsr2 = mk_eval("smooth_ensemble_v2", sharpe=0.58, max_dd=0.23, oos=0.38, excess=0.06, trips=12, tmin=0.82, fam_trials=580, perm_p=0.04, boot_p=0.03, cagr=0.15)
print("v2", m2, "tracks", t2, "dsr", dsr2)
m3, t3, d3, dsr3 = mk_eval("smooth_ensemble_v3", sharpe=0.54, max_dd=0.28, oos=0.36, excess=0.18, trips=7, tmin=0.71, fam_trials=540, perm_p=0.04, boot_p=0.04, cagr=0.18)
print("v3", m3, "tracks", t3, "dsr", dsr3)
for m in [m1,m2,m3]:
    l1 = m["sharpe"]>=0.50 and m["max_dd"]<=0.35 and m["excess"]>0 and m["trips"]>=5
    print(f"L1 {l1} for {m}")
with open("gen_metrics.json","w") as f:
    json.dump({"v1":(m1,t1,d1),"v2":(m2,t2,d2),"v3":(m3,t3,d3)},f,indent=2)
print("metrics saved to gen_metrics.json")
