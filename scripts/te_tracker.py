"""Phase 5.1 (Cycle 2): TE tracker — paper track vs A-config backtest benchmark.

- Benchmark: A-config (neutral conf5 hold20 stop0 long gate=F) equal-weight
  backtest monthly returns on A15, computed once from local data and cached
  to docs/data/baseline_backtest_monthly.json.
- Paper: monthly portfolio returns from baseline_state.json snapshots.
- SLA (grilling): monthly |paper - backtest| >= 2% = STOP-AND-AUDIT flag.
"""
import json
import os

import numpy as np
import pandas as pd

import scripts.improve_strategy_v2 as m
from scripts.baseline_paper_track import CFG, STATE_FILE

BENCH_FILE = "docs/data/baseline_backtest_monthly.json"
REPORT_FILE = "docs/data/te_report.json"
TE_LIMIT = 0.02


def build_benchmark(force=False):
    if os.path.exists(BENCH_FILE) and not force:
        with open(BENCH_FILE) as f:
            return json.load(f)
    stock_dfs, spy_close = m.load_local_data()
    frames, spy_trend = m.prepare_frames(stock_dfs, spy_close)
    sigs = m.gen_signals(frames, spy_trend, CFG["rsi_mode"], CFG["min_conf"],
                         CFG["direction"], CFG["spy_gate"])
    trades, port_rets = m.run_portfolio_sim(
        frames, spy_close, sigs, CFG["holding_days"], CFG["stop"])
    rets = pd.Series(dict(port_rets)).sort_index()
    monthly = (1 + rets).resample("ME").prod() - 1.0
    out = {"config": CFG,
           "monthly": {str(k.date()): round(float(v), 6)
                       for k, v in monthly.items() if not np.isnan(v)},
           "n_trades": len(trades)}
    with open(BENCH_FILE, "w") as f:
        json.dump(out, f, indent=2)
    return out


def paper_monthly_returns(state):
    mv = state.get("monthly_value", {})
    months = sorted(mv)
    out = {}
    for i in range(1, len(months)):
        p0, p1 = mv[months[i - 1]], mv[months[i]]
        out[months[i]] = p1 / p0 - 1.0
    return out


def main():
    bench = build_benchmark()
    if not os.path.exists(STATE_FILE):
        print("No baseline state yet — paper track has not run.")
        return
    with open(STATE_FILE) as f:
        state = json.load(f)
    paper = paper_monthly_returns(state)

    rows, breaches = [], []
    for month, p_ret in sorted(paper.items()):
        b_ret = bench["monthly"].get(month + "-01")
        if b_ret is None:
            rows.append({"month": month, "paper_ret": round(p_ret, 4),
                         "backtest_ret": None, "te": None, "breach": False})
            continue
        te = abs(p_ret - b_ret)
        breach = te >= TE_LIMIT
        rows.append({"month": month, "paper_ret": round(p_ret, 4),
                     "backtest_ret": round(b_ret, 4), "te": round(te, 4),
                     "breach": breach})
        if breach:
            breaches.append(month)

    report = {"te_limit": TE_LIMIT, "months": rows,
              "breaches": breaches,
              "status": "STOP-AND-AUDIT" if breaches else "OK",
              "note": "TE = |paper monthly return - A-config backtest monthly "
                      "return| (equal-weight benchmark); report updates monthly"}
    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))
    print(f"Saved {REPORT_FILE}")


if __name__ == "__main__":
    main()