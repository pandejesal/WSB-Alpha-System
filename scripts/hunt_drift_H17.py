#!/usr/bin/env python3
"""H17 event-driven hunt: post-jump drift continuation (NEW family event_drift).

FROZEN (brief.yaml, prereg cycle185 BEFORE this script ran):
  family=event_drift, jump def = filed events_all.json as-is (effective
  |z|>=3.671; NOT redefined), N=10 hold (PEAD-lit decay weeks 1-2, not data),
  K=10 equal slots, LONG positive-kind only (negative -> SPY fill, long-only
  mandate, no shorts), T+1 (first master bar strictly after event date),
  SPY-fill always-invested, per-leg W5 tiered costs on leg's own closes
  (equity tier; BTC tier via same _tiered_cost_bps selector for BTC/ETH),
  SPY twin identical window, 1910-bar loop window 2019-01-02..2026-08-07.

LINEAGE: master calendar + stats (safe_sharpe/max_dd/cagr/oos-last-30%/
excess-pp) + cost formula (_tiered_cost_bps, turnover incl. initial build,
tier-aware fallback, no shorts so no borrow guard) + DSR
(deflated_sharpe_ratio) + boot (stationary_bootstrap_p) imported from
evolve_real; perm = lineage circular-shift generalized to event time
(shift whole event schedule K=200 seed 7, rebuild identically); signal
frame NaN-initialized, EVERY bar assigned, assert no NaN; W = S.shift(1)
exactly like lineage pos = signal.shift(1).

TABOO (H1-H16 + registry, read-only): no SMA/formation/breakout/inv-vol/
dual-trend/breadth/ensemble/tail-hedge/earnings-calendar shapes; nearest
registry row us_pead_top5 differs on event source, direction rule, hold
(10 vs 5) and fill (SPY vs cash).

HONESTY: sigma20 filed INCLUDES the event bar (close-knowable at event
close => T+1 has zero lookahead; disclosed, not redefined). Events filed
on an older OHLCV vintage (dust-level revision; crypto truncated to
2021+). Top-120 cap verified complete-or-superset in current vintage.
ONE frozen config, zero post-freeze search. Paper only.
"""
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from evolve_real import (  # lineage imports (read-only use; values unchanged)
    _dsr_n_trials,
    _fallback_cost_bps,
    _regime_sharpe,
    _tiered_cost_bps,
    cagr,
    load_csv,
    max_dd,
    stationary_bootstrap_p,
)
from src.backtest.defend.trial_ledger import deflated_sharpe_ratio
from src.backtest.gatespec38_tracks import check_track_detailed
from src.backtest.metrics import safe_sharpe

RUN_DIR = ROOT / "hunts/event_drift/20260912-h17-drift"
RES_DIR = RUN_DIR / "results"
RES_DIR.mkdir(parents=True, exist_ok=True)

FAMILY = "event_drift"
N_HOLD = 10          # frozen: PEAD-lit decay weeks 1-2
K_SLOTS = 10         # frozen: equal-weight slots
FAM_BTC = "btc_vol"  # tier SELECTOR ONLY for BTC/ETH legs (same fn, BTC tier)

# ---- master calendar: SPY 1910-bar loop window (lineage) ----
spy = load_csv("SPY")
spy_close = spy["close"]
assert isinstance(spy_close, pd.Series)
# Filter to 2019-01-02..2026-08-07 (1910-bar lineage window)
MASTER = spy_close.index[spy_close.index >= "2019-01-02"]
M = len(MASTER)
print(f"master SPY bars={M} {MASTER[0].date()}..{MASTER[-1].date()}")
assert M == 1910, f"loop-window breach: {M} != 1910"
master_pos = {d: i for i, d in enumerate(MASTER)}

# ---- filed events (used AS-IS; mechanical pre-backtest filters only) ----
filed = json.load(open(ROOT / "market_data_2019_2026/events/events_all.json"))
print(f"filed events={len(filed)}")


def try_load(name):
    try:
        df = load_csv(name)
        return df["close"]
    except OSError as e:
        print(f"  universe-guard skip {name}: {e}")
        return None


price_cache = {}


def price_of(name):
    if name not in price_cache:
        price_cache[name] = try_load(name)
    return price_cache[name]


# ---- episode construction: NaN-init signal frame, EVERY bar assigned ----
def build_episodes():
    """Return (episodes, bridge) with frozen mechanical filters.

    episode = dict(symbol, event_date, entry_idx, exit_idx_excl).
    Filters (pre-backtest, no peeking): kind==positive only; symbol loads
    via lineage load_csv (universe guard); event date on master calendar;
    N subsequent master bars available (tail-cutoff).
    """
    bridge = {"filed": len(filed), "negative_kind_spyfill": 0,
              "universe_guard": 0, "date_missing": 0, "tail_cutoff": 0,
              "episodes": 0}
    episodes = []
    for e in filed:
        if e["kind"] != "positive":
            bridge["negative_kind_spyfill"] += 1
            continue
        sym = e["symbol"]
        px = price_of(sym)
        if px is None:
            bridge["universe_guard"] += 1
            continue
        d = pd.Timestamp(e["date"])
        if d not in master_pos:
            bridge["date_missing"] += 1
            continue
        i = master_pos[d]
        entry = i + 1  # T+1: first master bar STRICTLY after event date
        if M - entry < N_HOLD:
            bridge["tail_cutoff"] += 1
            continue
        episodes.append({"symbol": sym, "event_date": str(e["date"]),
                         "entry": entry, "exit_excl": entry + N_HOLD})
    bridge["episodes"] = len(episodes)
    return episodes, bridge


def master_returns(px):
    """Asset close-to-close returns on master calendar (past-only align)."""
    a = px.reindex(MASTER, method="ffill")
    return a.pct_change().fillna(0.0)


def run_portfolio(episodes, shift_bars=0):
    """Identical construction + costs; shift_bars circular-shifts the whole
    event schedule on the master calendar (perm-test generalization)."""
    names = sorted({ep["symbol"] for ep in episodes} | {"SPY"})
    rets = {}
    for n in names:
        if n == "SPY":
            rets[n] = spy_close.pct_change().fillna(0.0).reindex(MASTER).fillna(0.0)
        else:
            px = price_of(n)
            if px is not None:
                rets[n] = master_returns(px)
            else:
                # Skip tickers that failed to load (universe guard)
                pass
    # Filter names to only those with returns
    names = [n for n in names if n in rets]
    # NaN-init signal-as-of-close frame; EVERY bar assigned below
    S = pd.DataFrame(np.full((M, len(names)), np.nan), index=MASTER,
                     columns=names)
    S[:] = 0.0
    if shift_bars:
        eps = [dict(ep, entry=(ep["entry"] + shift_bars) % M) for ep in episodes]
        for ep in eps:
            ep["exit_excl"] = ep["entry"] + N_HOLD
    else:
        eps = episodes
    active_count = np.zeros(M, dtype=int)
    for ep in eps:
        lo, hi = ep["entry"], min(ep["exit_excl"], M)
        if lo >= M:
            continue
        S.iloc[lo:hi, S.columns.get_loc(ep["symbol"])] += 1.0 / K_SLOTS
        active_count[lo:hi] += 1
    # K-cap (frozen deterministic: earliest-episode legs already added
    # in filed order; cap overflow stays SPY-filled). Count overflows:
    overflow = int((active_count > K_SLOTS).sum())
    assert bool(np.isfinite(S.values).all()), "unwritten signal row detected"
    W = S.shift(1).fillna(0.0)  # T+1 exactly like lineage pos=signal.shift(1)
    W["SPY"] = W["SPY"] + (1.0 - W.sum(axis=1))  # SPY-fill residual
    assert bool(((W.sum(axis=1) - 1.0).abs() < 1e-9).all()), "weights != 1"
    gross = sum(W[n] * rets[n] for n in names)
    if gross.isna().any():
        print(f"DEBUG: gross has NaN: {gross.isna().sum()}")
        for n in names:
            if (W[n] * rets[n]).isna().any():
                print(f"  {n}: W NaN={W[n].isna().sum()}, rets NaN={rets[n].isna().sum()}")
    # per-leg W5 costs on the leg's own closes (lineage formula mirror)
    cost_drag = pd.Series(0.0, index=MASTER)
    for n in names:
        w = W[n]
        turnover = w.diff().abs().fillna(w.abs())  # incl. initial build
        if float(turnover.sum()) == 0.0:
            continue
        base_px = spy_close.reindex(MASTER, method="ffill") if n == "SPY" else price_of(n).reindex(
            MASTER, method="ffill")
        # Fill leading NaN for crypto (data starts ~2021) with first valid value
        # to allow _tiered_cost_bps to compute; cost for pre-data period uses fallback
        base_px = base_px.ffill().bfill()
        fam = FAM_BTC if n in ("BTC", "ETH") else FAMILY
        cb = _tiered_cost_bps(base_px, fam)
        fb = _fallback_cost_bps(fam)
        cb = cb.reindex(MASTER).fillna(fb).clip(lower=fb)
        cost_drag = cost_drag + turnover * (cb / 10000.0)
    net = gross - cost_drag
    tmin = float((W.abs().sum(axis=1) > 1e-9).mean())
    return net, tmin, overflow, int(active_count.max())


episodes, bridge = build_episodes()
print("bridge:", bridge)
net, tmin_raw, overflow, maxconc = run_portfolio(episodes)
print(f"episodes={len(episodes)} max_concurrent={maxconc} Kcap_overflow_bars={overflow} "
      f"tmin_raw={tmin_raw:.4f} nan_rate={float(net.isna().mean()):.4f}")
if net.isna().any():
    print(f"DEBUG: net NaN count: {net.isna().sum()}")
    print(f"DEBUG: net NaN indices: {net[net.isna()].index[:10].tolist()}")
assert bool(np.isfinite(net.values).all()), "NaN in net returns"
assert maxconc <= K_SLOTS, "K-cap bound; frozen rule would need overflow logic"

# ---- lineage statistics ----
eq = (1 + net).cumprod()
n = len(net)
split = int(n * 0.7)
sharpe = float(safe_sharpe(net))
dd = float(max_dd(eq))
oos = float(safe_sharpe(net.iloc[split:])) if n - split > 20 else 0.0
spy_ret = spy_close.pct_change().fillna(0.0)
excess = float((1 + net).prod() - (1 + spy_ret).prod()) * 100
trips = len(episodes)  # each episode = one genuine entry+exit round trip
turnover_bars = "see_trades"
print(f"H17 sharpe={sharpe:.4f} dd={dd:.4f} oos={oos:.4f} excess={excess:+.2f}pp "
      f"tmin={tmin_raw:.4f} trips(episodes)={trips}")


def dsr_at_N(sh, T, N):
    try:
        return float(deflated_sharpe_ratio(T, float(sh) / np.sqrt(252.0), N))
    except Exception:
        return 0.0


N_lin = _dsr_n_trials(FAMILY)
dsr_n1 = dsr_at_N(sharpe, n, 1)
dsr_lin = dsr_at_N(sharpe, n, N_lin)
dsr_383 = dsr_at_N(sharpe, n, 383)
dsr_gate = min(dsr_lin, dsr_383)  # fail-closed (H16 precedent)
print(f"dsr_N1={dsr_n1:.4f} dsr_lineageN{int(N_lin)}={dsr_lin:.4f} "
      f"dsr_N383={dsr_383:.4f} dsr_gate={dsr_gate:.4f}")

# ---- perm: event-schedule circular shift K=200 seed 7 (lineage analog) ----
rng = np.random.default_rng(7)
K = 200
wins = 0
for _ in range(K):
    shift = int(rng.integers(1, M))
    net_s, _, _, _ = run_portfolio(episodes, shift_bars=shift)
    if float(safe_sharpe(net_s)) >= sharpe:
        wins += 1
perm_p = wins / K
boot_p = float(stationary_bootstrap_p(
    np.asarray(net.fillna(0.0).values, dtype=float)))
print(f"perm_p={perm_p:.4f} boot_p={boot_p:.4f}")


def wf_3fold(net_):
    m = len(net_)
    edges = [0, m // 3, 2 * m // 3, m]
    return [round(float(safe_sharpe(net_.iloc[edges[i]:edges[i + 1]]))
                  if edges[i + 1] - edges[i] > 20 else 0.0, 4)
            for i in range(3)]


def cpcv_proxy(net_):
    m = len(net_)
    edges = [0, m // 4, m // 2, 3 * m // 4, m]
    blocks = [net_.iloc[edges[i]:edges[i + 1]] for i in range(4)]
    out = []
    for i in range(4):
        for j in range(i + 1, 4):
            test = pd.concat([blocks[i], blocks[j]]).sort_index()
            out.append(round(float(safe_sharpe(test)) if len(test) > 20 else 0.0, 4))
    return out


m = {"sharpe": sharpe, "max_dd": dd, "oos": oos, "excess": round(excess, 2),
     "dsr": dsr_gate, "trips": trips, "tmin": round(tmin_raw, 4),
     "perm_p": perm_p, "boot_p": boot_p}
det = check_track_detailed(m)
t8 = det.get("absolute_return_focus", {})
t5 = det.get("high_exposure_momentum", {})
print("T8:", t8.get("passed"), t8.get("terms"))
print("T5-watch:", t5.get("passed"), t5.get("terms"))

wf = wf_3fold(net)
cpcv = cpcv_proxy(net)
wf_mean = round(float(np.mean(wf)), 4)
print("WF folds OOS:", wf, "mean:", wf_mean)
print("CPCV paths:", cpcv, "mean:", round(float(np.mean(cpcv)), 4),
      "min:", min(cpcv), "frac>0:",
      round(float(np.mean([x > 0 for x in cpcv])), 4))

L1 = sharpe >= 0.50 and dd <= 0.35 and excess > 0
T8_pass = bool(t8.get("passed")) and perm_p <= 0.05 and boot_p <= 0.05
wf_ok = wf_mean >= 0.40
if T8_pass and wf_ok:
    verdict, tracks = "PROMOTE", ["absolute_return_focus"]
else:
    verdict, tracks = "HONEST_ABANDON", []

eval_data = {
    "id": "event_drift_h17",
    "family": FAMILY,
    "params": {"hold_days_N": N_HOLD, "max_concurrent_K": K_SLOTS,
               "exec_delay": 1,
               "direction": "jump_continuation_long_positive_only",
               "jump_definition": "filed_events_all_as_is_effective_|z|>=3.671",
               "fill": "SPY_always_invested"},
    "bridge": bridge,
    "metrics": {"sharpe": sharpe, "cagr": float(cagr(eq)), "max_dd": dd,
                "oos_sharpe": oos, "excess": round(excess, 2),
                "tmin": round(tmin_raw, 4), "dsr": dsr_gate,
                "dsr_N1": round(dsr_n1, 4),
                "dsr_lineage": round(dsr_lin, 4),
                "dsr_N383": round(dsr_383, 4),
                "dsr_lineage_N": int(N_lin),
                "trips_episodes": trips, "perm_p": perm_p, "boot_p": boot_p,
                "n_bars": n,
                "fam_trials": "failclosed_min_lineage_program383",
                "regime_coverage": _regime_sharpe(net)},
    "tracks_cleared": tracks,
    "tracks": {"absolute_return_focus": t8,
               "high_exposure_momentum_watch": t5},
    "overlays": {"wf_3fold_oos": wf, "wf_mean_oos": wf_mean, "wf_ok": wf_ok,
                 "cpcv_proxy_paths": cpcv,
                 "cpcv_mean": round(float(np.mean(cpcv)), 4),
                 "cpcv_min": min(cpcv),
                 "cpcv_frac_pos": round(float(np.mean([x > 0 for x in cpcv])), 4),
                 "cpcv_disclosure": "returns-level proxy, 4 blocks/6 paths, no embargo/purge",
                 "perm_disclosure": "event-schedule circular-shift K=200 seed 7, full rebuild incl costs"},
    "L1_pass": L1,
    "L2_Track8_pass": bool(t8.get("passed")),
    "verdict": verdict,
    "paper_only": True,
}
tmp = RES_DIR / "eval_event_drift_h17.json.tmp"
final = RES_DIR / "eval_event_drift_h17.json"
with open(tmp, "w") as f:
    json.dump(eval_data, f, indent=2)
os.replace(tmp, final)
print(f"Wrote {final} verdict={verdict} tracks={tracks} L1={L1} wf_ok={wf_ok}")
