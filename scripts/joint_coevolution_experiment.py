#!/usr/bin/env python3
"""Joint signal+execution co-evolution experiment (E-darwin follow-up, MadEvolve).

Question: does jointly varying SIGNAL params x EXECUTION cost change which
candidates survive, vs signal-only search?

Method (offline, read-only except report file):
- Top paper spy_sma / spy_rsi2 rows from strategies/registry.json (by OOS Sharpe).
- Grid: signal params {base, -20%, +20%} x slippage_bps {2.5, 5.0, 10.0}.
- Metric: OOS Sharpe from backtest() (same engine as the loop).
- DSR counters (TRIAL_COUNT, FAM_TRIALS) are snapshot/restored so the
  experiment never pollutes the live loop's multiple-testing accounting.
- Report: docs/data/joint_coevolution_report.json + printed table.

Exit 0 with report even if some cells error (fail-closed cells marked).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

import evolve_real as EV

REPORT = ROOT / "docs" / "data" / "joint_coevolution_report.json"
COMMISSIONS = (1.0, 2.5, 5.0)  # execution axis: retail commission bps
SCALES = (0.8, 1.0, 1.2)  # signal axis: param scale
TOP_N_PER_FAMILY = 3


def _scale_params(params: dict, scale: float) -> dict:
    out = {}
    for k, v in params.items():
        if isinstance(v, bool):
            out[k] = v
        elif isinstance(v, int):
            out[k] = max(1, round(v * scale))
        elif isinstance(v, float):
            out[k] = v * scale
        else:
            out[k] = v
    return out


def _signal(family: str, p: dict, data: dict) -> pd.Series:
    if family in ("spy_sma", "spy_ltrend"):
        return EV.sig_spy_sma(data["SPY"], p["window"])
    if family == "spy_rsi2":
        return EV.sig_spy_rsi2(data["SPY"], p["entry"], p["exit_hi"], p["max_hold"])
    raise ValueError(f"family {family} not in joint-experiment scope (spy_* only)")


def main() -> int:
    reg_path = ROOT / "strategies" / "registry.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    rows = reg["strategies"] if isinstance(reg, dict) else reg
    paper = [r for r in rows if r.get("status") == "paper"
             and r.get("family") in ("spy_sma", "spy_rsi2")]
    paper.sort(key=lambda r: (r.get("metrics") or {}).get("oos_sharpe", -9), reverse=True)
    picks: dict[str, list[dict]] = {}
    for r in paper:
        picks.setdefault(r["family"], []).append(r)
    picks = {f: rs[:TOP_N_PER_FAMILY] for f, rs in picks.items()}

    data = {"SPY": EV.load_csv("SPY")["close"]}
    snap_trials, snap_fam = EV.TRIAL_COUNT[0], copy.deepcopy(EV.FAM_TRIALS)
    snap_commission = EV.COST_COMMISSION_BPS
    cells = []
    try:
        for family, rs in picks.items():
            for r in rs:
                base = (r.get("metrics") or {}).get("params", {})
                if not base:
                    continue
                for sc in SCALES:
                    sig = _signal(family, _scale_params(base, sc), data)
                    for comm in COMMISSIONS:
                        EV.COST_COMMISSION_BPS = comm
                        try:
                            m = EV.backtest(sig, data["SPY"], data["SPY"], family)
                            cells.append({
                                "id": r.get("id"), "family": family,
                                "scale": sc, "commission_bps": comm,
                                "sharpe": round(m.get("sharpe", 0.0), 3),
                                "oos_sharpe": round(m.get("oos_sharpe", m.get("oos", 0.0)), 3),
                                "max_dd": round(m.get("max_dd", 0.0), 4),
                            })
                        except Exception as e:  # noqa: BLE001 - fail-closed cell
                            cells.append({"id": r.get("id"), "family": family,
                                          "scale": sc, "commission_bps": comm,
                                          "error": str(e)[:120]})
    finally:
        EV.TRIAL_COUNT[0] = snap_trials
        EV.FAM_TRIALS.clear()
        EV.FAM_TRIALS.update(snap_fam)
        EV.COST_COMMISSION_BPS = snap_commission
    report = {"cells": cells, "note": "counters snapshot/restored; registry untouched"}
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    ok = [c for c in cells if "error" not in c]
    print(f"cells={len(cells)} ok={len(ok)} report={REPORT}")
    for c in ok:
        print(f"  {c['family']} scale={c['scale']} comm={c['commission_bps']} "
              f"sharpe={c['sharpe']} oos={c['oos_sharpe']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
