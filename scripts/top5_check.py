#!/usr/bin/env python3
"""Triple-check the top 5 alive paper strategies (independent re-verification).

Independent reimplementation of family signals (does NOT import
evolve_real.py): recompute metrics from params + local CSVs, then per
strategy run 3 checks:
  1. RECOMPUTE: Sharpe within 0.05 and exact trip count vs stored metrics.
  2. ROBUSTNESS: params +/-10%, first/second-half OOS, 10bps slippage —
     excess-vs-SPY sign must survive and Sharpe > 0.5 throughout.
  3. INTEGRITY: honest gate on recomputed numbers + identical-window SPY
     baseline + T+1 execution (positions shifted before returns).

Read-only vs strategies/registry.json. Paper only. No orders.
Usage: PYTHONPATH=. python scripts/top5_check.py [--top 5]
"""
import argparse
import json
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.backtest.metrics import safe_sharpe  # noqa: E402

REG = ROOT / "strategies/registry.json"
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
    return {"sharpe": round(float(safe_sharpe(net)), 3), "max_dd": round(dd, 4),
            "oos": round(oos, 3), "trips": trips,
            "trades": int((to > 0).sum()), "excess_spy": round(excess, 2)}


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


def check_strategy(entry: dict, data: dict) -> dict:
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
    # CHECK 3: gate on recomputed numbers
    res["check3_gate"] = (rec["sharpe"] >= GATE["sharpe_min"]
                          and rec["max_dd"] <= GATE["max_dd"]
                          and rec["oos"] >= GATE["oos_min"]
                          and rec["trips"] >= GATE["trips_min"])
    res["verdict"] = ("PASS" if all([res["check1_recompute"], res["check2_robust"],
                                     res["check3_gate"]]) else "FAIL")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    reg = json.loads(REG.read_text(encoding="utf-8"))
    top5, dupes = dedupe_top5(reg.get("strategies", []), args.top)
    print(f"deduped {dupes} repeat promotions; checking {len(top5)} unique")
    data = {"SPY": load_close("SPY")}
    for i, entry in enumerate(top5):
        r = check_strategy(entry, data)
        print(f"[{i + 1}] {r['id']} {r['params']}")
        print(f"    stored sharpe={r['stored']['sharpe']} oos={r['stored']['oos_sharpe']} "
              f"trips={r['stored'].get('round_trips', r['stored'].get('trips'))}")
        print(f"    recomputed sharpe={r['recomputed']['sharpe']} oos={r['recomputed']['oos']} "
              f"trips={r['recomputed']['trips']} excessSPY={r['recomputed']['excess_spy']}%")
        print(f"    C1-recompute={r['check1_recompute']} C2-robust={r['check2_robust']} "
              f"{r['robust_notes']} C3-gate={r['check3_gate']} => {r['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
