#!/usr/bin/env python3
"""Triple-check the top 5 alive paper strategies (independent re-verification).

Independent reimplementation of family signals (does NOT import
evolve_real.py): recompute metrics from params + local CSVs, then per
strategy run 3 checks:
  1. RECOMPUTE: Sharpe within 0.05 and exact trip count vs stored metrics.
  2. ROBUSTNESS: params +/-10%, first/second-half OOS, 10bps slippage —
     excess-vs-SPY sign must survive and Sharpe > 0.5 throughout.
   3. INTEGRITY: gatespec38-aligned gate on recomputed numbers (live import
      of src.backtest.gatespec38_tracks: excess + recomputed DSR + track
      union via check_track/apply_union_gate) + identical-window SPY
      baseline + T+1 execution. perm/boot overlays are read from stored
      registry metrics (NOT re-verified here) and block PASS when unknown.

Read-only vs strategies/registry.json. Paper only. No orders.
Usage: PYTHONPATH=. python scripts/top5_check.py [--top 5]
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.backtest.metrics import safe_sharpe  # noqa: E402

try:  # live gatespec38 import: C3 verifies against the real promotion gate
    from src.backtest.gatespec38_tracks import (
        CROSS_FAMILY_N_FLOOR,
        apply_union_gate,
        check_track,
        recompute_dsr,
    )
    _GATESPEC = True
except Exception:  # noqa: BLE001  # fail-closed: C3 skips verdict, see below
    _GATESPEC = False

REG = ROOT / "strategies/registry.json"
# VESTIGIAL (P1 B3c): GATE mirrors the dead evolve_real.REAL_GATE single-bar
# dict (sharpe>=0.8/oos>=0.5/trips>=10). The real promotion path is
# src/backtest/gatespec38_tracks.py (10-track union via check_track_gated) +
# perm/boot overlays + mandatory WF gate — see evolve_real.py MAIN GATE
# (~line 949). Kept (not deleted) for backward-compat; C3 below verifies
# against live gatespec38, NOT this dict. Do NOT retune here.
GATE = dict(sharpe_min=0.8, max_dd=0.35, oos_min=0.5, trips_min=10)


def load_close(ticker: str) -> pd.Series:
    df = pd.read_csv(ROOT / f"market_data_2019_2026/ohlcv/{ticker}.csv",
                     parse_dates=["date"])
    return df.set_index("date").sort_index()["close"].astype(float)


def spy_baseline() -> pd.Series:
    c = load_close("SPY")
    return c.pct_change().fillna(0.0)


def rsi2_signal(close: pd.Series, entry: int, exit_hi: int, max_hold: int) -> pd.Series:
    """Independent RSI-2 mean-reversion (written from params, not imported)."""
    d = close.diff()
    up = d.clip(lower=0.0).rolling(2).mean()
    dn = (-d).clip(lower=0.0).rolling(2).mean().replace(0, float("nan"))
    rsi = (100 - 100 / (1 + up / dn)).shift(1)
    pos = pd.Series(0.0, index=close.index)
    hold = 0
    days = 0
    for i in range(len(close)):
        r = rsi.iloc[i]
        if hold:
            days += 1
            if (pd.notna(r) and r > exit_hi) or days >= max_hold:
                hold, days = 0, 0
        elif pd.notna(r) and r < entry:
            hold, days = 1, 0
        pos.iloc[i] = hold
    return pos


def sma_signal(close: pd.Series, window: int) -> pd.Series:
    return (close > close.rolling(int(window)).mean().shift(1)).astype(float).fillna(0.0)


def run_backtest(pos: pd.Series, close: pd.Series,
                 slippage_bps: float = 5.0) -> dict:
    ex = pos.shift(1).fillna(0.0)  # T+1
    rets = close.pct_change().fillna(0.0) * ex
    to = ex.diff().abs().fillna(ex.abs())
    net = rets - to * (slippage_bps / 10000.0)
    eq = (1 + net).cumprod()
    peak = eq.cummax()
    dd = float(-((eq - peak) / peak.replace(0, float("nan"))).min())
    n = len(net)
    oos = float(safe_sharpe(net.iloc[int(n * 0.7):])) if n > 30 else 0.0
    trips = int((to > 0).sum() // 2)
    spy = spy_baseline().reindex(net.index).fillna(0.0)
    excess = float((1 + net).prod() - (1 + spy).prod()) * 100
    tmin = round(float(ex.fillna(0.0).mean()), 4)
    return {"sharpe": round(float(safe_sharpe(net)), 3), "max_dd": round(dd, 4),
            "oos": round(oos, 3), "trips": trips,
            "trades": int((to > 0).sum()), "excess_spy": round(excess, 2),
            "tmin": tmin, "n_bars": n}


def build_signal(family: str, params: dict, data: dict) -> pd.Series:
    if family == "spy_rsi2":
        return rsi2_signal(data["SPY"], params["entry"], params["exit_hi"],
                           params["max_hold"])
    if family == "spy_sma":
        return sma_signal(data["SPY"], params["window"])
    raise ValueError(f"top5 scope is SPY families, got {family}")


def dedupe_top5(strategies: list, top: int = 5) -> tuple:
    """Top UNIQUE (family, params) paper entries by stored OOS sharpe."""
    dupes = 0
    seen = set()
    out = []

    def oos(s):
        m = s.get("metrics", {}) or {}
        v = m.get("oos_sharpe", m.get("sharpe"))
        return v if isinstance(v, (int, float)) else -9.0

    for s in sorted([x for x in strategies if x.get("status") == "paper"],
                    key=oos, reverse=True):
        m = s.get("metrics", {}) or {}
        key = (s.get("family"), json.dumps(m.get("params", {}), sort_keys=True))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        out.append(s)
        if len(out) == top:
            break
    return out, dupes


def perturb(params: dict, direction: int) -> dict:
    out = {}
    for k, v in params.items():
        if isinstance(v, bool):
            out[k] = v
        elif isinstance(v, int):
            out[k] = max(1, v + direction * max(1, int(round(v * 0.1))))
        elif isinstance(v, float):
            out[k] = round(v * (1 + direction * 0.1), 4)
        else:
            out[k] = v
    return out


def check_strategy(entry: dict, data: dict, n_strats: int = 0) -> dict:
    m = entry.get("metrics", {}) or {}
    params = m.get("params", {})
    family = entry.get("family")
    res = {"id": entry.get("id"), "family": family, "params": params,
           "stored": {k: m.get(k) for k in ("sharpe", "max_dd", "oos_sharpe",
                                            "round_trips", "trips")}}
    # CHECK 1: recompute
    rec = run_backtest(build_signal(family, params, data), data["SPY"])
    res["recomputed"] = rec
    stored_trips = m.get("round_trips", m.get("trips", -1))
    res["check1_recompute"] = (abs(rec["sharpe"] - float(m.get("sharpe", 0))) <= 0.05
                               and rec["trips"] == stored_trips)
    # CHECK 2: robustness
    close = data["SPY"]
    variants = [perturb(params, +1), perturb(params, -1)]
    half = len(close) // 2
    ok = True
    notes = []
    for i, pv in enumerate(variants):
        r = run_backtest(build_signal(family, pv, data), close)
        if not (r["excess_spy"] > 0 and r["sharpe"] > 0.5):
            ok = False
            notes.append(f"perturb{'+' if i == 0 else '-'}_fail")
    for tag, sl in (("h1", slice(None, half)), ("h2", slice(half, None))):
        r = run_backtest(build_signal(family, params, data).iloc[sl],
                         close.iloc[sl])
        if not (r["excess_spy"] > 0 and r["sharpe"] > 0.5):
            ok = False
            notes.append(f"{tag}_fail")
    r = run_backtest(build_signal(family, params, data), close, slippage_bps=10.0)
    if not (r["excess_spy"] > 0 and r["sharpe"] > 0.5):
        ok = False
        notes.append("cost10bps_fail")
    res["check2_robust"] = ok
    res["robust_notes"] = notes
    # CHECK 3: gatespec38-aligned gate on recomputed numbers (NOT the dead
    # GATE dict above). DSR recomputed with cross-family N =
    # max(registry strategies, 215); tracks via check_track + union gate.
    # perm/boot overlays come from STORED metrics (not re-verified here) and
    # block PASS when missing — fail-closed.
    res["legacy_gate"] = (rec["sharpe"] >= GATE["sharpe_min"]
                          and rec["max_dd"] <= GATE["max_dd"]
                          and rec["oos"] >= GATE["oos_min"]
                          and rec["trips"] >= GATE["trips_min"])
    if not _GATESPEC:
        print("STALE-GATE WARNING: src.backtest.gatespec38_tracks unimportable; "
              "C3 verdict SKIPPED (thresholds cannot be trusted).")
        res["check3_gate"] = False
        res["tracks_cleared"] = []
        res["gate_reason"] = "stale-gate-skip"
        res["verdict"] = "SKIP-STALE-GATE"
        return res
    dsr_n = max(int(n_strats), CROSS_FAMILY_N_FLOOR)
    dsr = recompute_dsr(int(rec.get("n_bars", 0)), float(rec["sharpe"]), dsr_n)
    gm = {"sharpe": rec["sharpe"], "max_dd": rec["max_dd"], "oos": rec["oos"],
          "excess": rec["excess_spy"], "dsr": dsr, "trips": rec["trips"],
          "tmin": rec.get("tmin", 0.0)}
    raw_tracks = check_track(gm)
    gated, reason = apply_union_gate(raw_tracks)
    res["dsr"] = round(dsr, 4)
    res["dsr_n"] = dsr_n
    res["tracks_cleared"] = gated
    res["gate_reason"] = reason
    perm_p = m.get("perm_p")
    boot_p = m.get("boot_p")
    overlays_known = isinstance(perm_p, (int, float)) and isinstance(boot_p, (int, float))
    res["overlays"] = ("stored-unverified" if overlays_known else "unknown")
    overlays_pass = bool(overlays_known and perm_p <= 0.05 and boot_p <= 0.05)
    res["check3_gate"] = bool(gated) and overlays_pass
    if res["legacy_gate"] != res["check3_gate"]:
        print(f"STALE-GATE WARNING: {entry.get('id')}: legacy GATE dict says "
              f"{'PASS' if res['legacy_gate'] else 'FAIL'} but gatespec38 says "
              f"{'PASS' if res['check3_gate'] else 'FAIL'} "
              f"(tracks={gated or 'none'}/{reason} dsr={res['dsr']} "
              f"overlays={res['overlays']}); trusting gatespec38.")
    res["verdict"] = ("PASS" if all([res["check1_recompute"], res["check2_robust"],
                                     res["check3_gate"]]) else "FAIL")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    reg = json.loads(REG.read_text(encoding="utf-8"))
    strats = reg.get("strategies", [])
    top5, dupes = dedupe_top5(strats, args.top)
    print(f"deduped {dupes} repeat promotions; checking {len(top5)} unique")
    print(f"C3 gate: live gatespec38_tracks (union gate + DSR N=max(registry={len(strats)},215)); "
          f"perm/boot overlays stored-not-reverified; legacy GATE dict vestigial")
    data = {"SPY": load_close("SPY")}
    for i, entry in enumerate(top5):
        r = check_strategy(entry, data, n_strats=len(strats))
        print(f"[{i + 1}] {r['id']} {r['params']}")
        print(f"    stored sharpe={r['stored']['sharpe']} oos={r['stored']['oos_sharpe']} "
              f"trips={r['stored'].get('round_trips', r['stored'].get('trips'))}")
        print(f"    recomputed sharpe={r['recomputed']['sharpe']} oos={r['recomputed']['oos']} "
              f"trips={r['recomputed']['trips']} excessSPY={r['recomputed']['excess_spy']}%")
        print(f"    C1-recompute={r['check1_recompute']} C2-robust={r['check2_robust']} "
              f"{r['robust_notes']} C3-gate={r['check3_gate']} => {r['verdict']}")
        if r.get("gate_reason") not in (None, "stale-gate-skip"):
            print(f"    gatespec38 tracks={r.get('tracks_cleared') or 'none'}/{r.get('gate_reason')} "
                  f"dsr={r.get('dsr')} N={r.get('dsr_n')} overlays={r.get('overlays')} "
                  f"legacy_GATE={r.get('legacy_gate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
