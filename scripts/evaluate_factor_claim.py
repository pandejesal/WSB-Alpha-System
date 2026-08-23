"""Phase 4 (Cycle 2): pre-registered evaluation of the factor claim.

Per docs/data/factor_claim_preregistration.md:
- Train 2020-01-06..2023-12-31 (factors need 12 months of month-end closes,
  so the first factor week is 2020-01-06 despite data starting 2019-01-01).
- Publication sign gate (kill criterion): MOM-only long-short mean > 0 AND
  REV1-only long-short mean < 0 on train. Wrong sign = dead on arrival.
- OOS 2024-01-01..2026-08-07 vs adapted bar: median weekly factor return > 0
  in 3 of 4 complete OOS years (2024/2025 complete, 2026 partial; earliest
  pass end-2027), full-OOS Sharpe >= 1.0, PF >= 1.5, maxDD <= 35%.
- Nulls: 1000x factor-rank permutation (primary, cross-sectional
  no-information null) and 1000x literal time-shuffle (order-dependent only;
  median invariant under permutation). Beat 95th pct of null.
Fail-closed: any unmet pre-BAR criterion -> claim falsified now.
"""
import json

import pandas as pd

from scripts.factor_engine import (
    load_frames, run_engine, summary_stats, null_distribution,
    time_shuffle_null,
)

TRAIN_START = pd.Timestamp("2020-01-06")
TRAIN_END = pd.Timestamp("2023-12-31")
OOS_START = pd.Timestamp("2024-01-01")
OUT = "docs/data/factor_evaluation.json"


def _stats(series):
    st = summary_stats(series)
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in st.items()}


def main():
    frames = load_frames()
    res = run_engine(frames)
    r = res["returns"]
    for col in ("factor_return", "mom_ls", "rev_ls"):
        r[col] = pd.to_numeric(r[col], errors="coerce")
    r["exec_date"] = pd.to_datetime(r["exec_date"])

    train = r[(r["exec_date"] >= TRAIN_START) & (r["exec_date"] <= TRAIN_END)]
    oos = r[r["exec_date"] >= OOS_START]

    # ---- sign gate (train) ----
    mom_mean = train["mom_ls"].mean()
    rev_mean = train["rev_ls"].mean()
    sign_gate = bool(mom_mean > 0 and rev_mean < 0)

    # ---- OOS bar ----
    oos_med = oos["factor_return"].median()
    oos_sharpe = summary_stats(oos["factor_return"])["sharpe_ann"]
    oos_pf = summary_stats(oos["factor_return"])["pf"]
    oos_maxdd = summary_stats(oos["factor_return"])["maxdd"]
    oos["year"] = oos["exec_date"].dt.year
    complete_years = sorted({y for y in oos["year"] if y in (2024, 2025)})
    pos_years = {y: (oos[oos["year"] == y]["factor_return"].median() > 0)
                 for y in complete_years}
    n_pos = sum(pos_years.values())

    bar_checks = {
        "sign_gate": sign_gate,
        "oos_median_gt_0": bool(oos_med > 0),
        "oos_sharpe_ge_1": bool(oos_sharpe >= 1.0),
        "oos_pf_ge_1_5": bool(oos_pf >= 1.5),
    }
    bar_checks["oos_maxdd_le_35pct"] = bool(oos_maxdd >= -0.35)
    bar_checks["years_positive"] = pos_years
    bar_checks["n_complete_years_positive"] = n_pos
    bar_checks["need_3_of_4_complete_oos_years"] = bool(n_pos >= 3)

    # ---- nulls (OOS) ----
    oos_ser = oos["factor_return"].dropna()
    perm = null_distribution(frames, n=1000, seed=0, oos_start=OOS_START)
    tshuf = time_shuffle_null(oos_ser, n=1000, seed=0)
    perm_p95 = perm["median"].quantile(0.95)
    tshuf_p95 = tshuf["median"].quantile(0.95)
    bar_checks["beat_95pct_permutation_null"] = bool(oos_med > perm_p95)
    bar_checks["beat_95pct_timeshuffle_null"] = bool(oos_med > tshuf_p95)

    # ---- verdict (fail-closed) ----
    needs = ["sign_gate", "oos_median_gt_0", "oos_sharpe_ge_1", "oos_pf_ge_1_5",
             "oos_maxdd_le_35pct", "need_3_of_4_complete_oos_years",
             "beat_95pct_permutation_null"]
    unmet = [k for k in needs if not bar_checks[k]]
    verdict = "CLAIM_FALSIFIED" if unmet else "SURVIVES_PREBAR_EVALUATION"

    ev = {
        "verdict": verdict,
        "unmet_criteria": unmet,
        "windows": {
            "train": [str(TRAIN_START.date()), str(TRAIN_END.date()),
                      int(train["exec_date"].nunique())],
            "oos": [str(OOS_START.date()), str(oos["exec_date"].max().date()),
                    int(oos["exec_date"].nunique())],
        },
        "train_stats": {
            "mom_ls_mean": round(float(mom_mean), 6),
            "rev_ls_mean": round(float(rev_mean), 6),
            "composite": _stats(train["factor_return"]),
        },
        "oos_stats": _stats(oos["factor_return"]),
        "bar_checks": bar_checks,
        "nulls": {
            "permutation_1000": {
                "p95_median": round(float(perm_p95), 6),
                "p95_sharpe": round(float(perm["sharpe_ann"].quantile(0.95)), 6),
                "p50_median": round(float(perm["median"].median()), 6),
            },
            "timeshuffle_1000": {
                "p95_median": round(float(tshuf_p95), 6),
                "p95_sharpe": round(float(tshuf["sharpe_ann"].quantile(0.95)), 6),
                "p50_median": round(float(tshuf["median"].median()), 6),
                "note": "median invariant under time permutation; "
                        "statistic order-dependent only",
            },
        },
    }
    with open(OUT, "w") as f:
        json.dump(ev, f, indent=2, default=str)

    print(json.dumps(ev, indent=2, default=str))
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()