"""Cycle 3 — Claim 3/4: Price-Only Low-Volatility Factor engine.

Implements docs/data/cycle3_prereg_lowvol.md EXACTLY as pre-registered. No tuning.

Pipeline:
  1. Universe: frozen 481-name S&P 500 snapshot (2026-08-14), same as Cycle 2
     and Claim 1 (tickers from cache/cycle3_13f_ticker_map.json).
  2. Weekly rebalance on the last trading bar of each ISO week (Friday close).
  3. Signal: annualized std of daily returns over the trailing 60 trading days
     (60-day realized vol), computed at each rebalance from adjusted closes.
  4. Cross-sectional ranking on the snapshot; long = bottom decile (lowest
     vol), short = top decile (highest vol); equal weight within each decile.
  5. Holding returns: close(t+1)/close(t) - 1 between consecutive rebalance
     dates. Net of costs (10 bps per side, turnover-based on weight change,
     both legs — same convention as the Claim 2 multi-asset engine).
  6. Checks: train sign gate (2019-2023 positive mean weekly factor return),
     OOS stats (2024-01-01..2026-08-07), 1000x block-shuffle null on weekly
     rebalance dates (OOS-mean statistic, RNG seed 7).

Outputs:
  docs/data/cycle3_lowvol_evaluation.json  (gate verdicts)
  docs/data/cycle3_lowvol_results.json     (full numbers)
"""
import json
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(7)

VOL_WINDOW = 60  # trading days
COST_BPS = 10  # per side
TRAIN_END = pd.Timestamp("2023-12-31")
YEARS = ["2024", "2025", "2026", "2027"]
N_NULL = 1000
MIN_N = 20  # minimum rankable tickers for a week to produce a factor (same
            # floor as the Claim 1 engine's len(both) < 20 skip)


def load_snapshot():
    with open(os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json"), encoding="utf-8") as f:
        return set(json.load(f)["ticker_to_names"].keys())


def load_closes():
    out = {}
    for f in os.listdir(os.path.join(BASE, "market_data_2019_2026", "ohlcv")):
        if not f.endswith(".csv"):
            continue
        t = f[:-4].upper()
        if t in {"INSTRUMENTS", "MISSING"}:
            continue
        df = pd.read_csv(os.path.join(BASE, "market_data_2019_2026", "ohlcv", f), parse_dates=["date"])
        out[t] = df.set_index("date")["close"].sort_index()
    return out


def rebalance_dates(closes, snapshot):
    all_dates = pd.DatetimeIndex(sorted(set().union(*[closes[t].index for t in snapshot])))
    s = pd.Series(all_dates, index=all_dates)
    return s.groupby(s.index.to_period("W")).max()


def main():
    snapshot = load_snapshot()
    closes = load_closes()
    rebal = rebalance_dates(closes, snapshot)
    usable = rebal[:-1]  # final bar has no exit

    daily_ret = {t: closes[t].pct_change() for t in snapshot if t in closes}
    vol = {
        t: s.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std() * np.sqrt(252)
        for t, s in daily_ret.items()
    }

    # forward-looking weekly return per ticker per rebalance entry date
    ret = {}
    for t, s in closes.items():
        if t not in snapshot:
            continue
        r = s.pct_change().reindex(rebal)
        ret[t] = r

    factors = {}
    weights_prev = None
    weeks_skipped_lt20 = 0
    weeks_with_turnover = []
    for i, d in enumerate(usable):
        d_next = rebal.iloc[i + 1]
        v = {t: vol[t].loc[d] for t in snapshot if t in vol and d in vol[t].index}
        v = pd.Series(v).dropna()
        n = len(v)
        if n < MIN_N:
            weeks_skipped_lt20 += 1
            weights_prev = None
            continue
        ranks = v.rank(method="average")
        lo = ranks <= np.ceil(n / 10)   # lowest vol -> LONG
        hi = ranks > n - np.floor(n / 10)  # highest vol -> SHORT
        w = pd.Series(0.0, index=ranks.index)
        w[lo] = 1.0 / lo.sum()
        w[hi] = -1.0 / hi.sum()
        # turnover cost: 10 bps per side on traded notional (both legs)
        if weights_prev is None:
            turn = w.abs().sum()
        else:
            w2 = w.reindex(weights_prev.index).fillna(0.0)
            turn = (w - w2).abs().sum() + w2[w2.index.difference(w.index)].abs().sum()
        cost = COST_BPS / 1e4 * turn
        weeks_with_turnover.append((str(d.date()), float(turn), float(cost)))
        r = ret
        r_vals = {t: (closes[t].loc[d_next] / closes[t].loc[d] - 1.0) if d_next in closes[t].index else np.nan for t in w.index}
        r_ser = pd.Series(r_vals)
        r_ser = r_ser[w.index]
        r_ser = r_ser.dropna()
        if len(r_ser) < MIN_N:
            weeks_skipped_lt20 += 1
            weights_prev = None
            continue
        ww = w.reindex(r_ser.index)
        factors[d] = float((ww * r_ser).sum() - cost)
        weights_prev = w

    fser = pd.Series(factors).sort_index()
    train = fser[fser.index < TRAIN_END]
    oos = fser[fser.index >= TRAIN_END]

    sign_pass = bool(train.mean() > 0)
    oos_median = float(oos.median()) if len(oos) else float("nan")
    oos_mean = float(oos.mean()) if len(oos) else float("nan")
    oos_sharpe = float(oos.mean() / oos.std() * np.sqrt(52)) if len(oos) > 1 and oos.std() > 0 else float("nan")
    eq = (1 + oos).cumprod()
    oos_maxdd = float((eq / eq.cummax() - 1).min()) if len(eq) else float("nan")
    n_years = len(oos) / 52.0
    oos_cagr = float(eq.iloc[-1] ** (1 / n_years) - 1) if len(eq) and n_years > 0 and eq.iloc[-1] > 0 else float("nan")

    fkeys = list(factors.keys())
    fvals = np.array(list(factors.values()))
    oos_mask = np.array([k >= TRAIN_END for k in fkeys])
    null_oos = []
    for _ in range(N_NULL):
        perm = RNG.permutation(len(fkeys))
        null_oos.append(float(fvals[perm][oos_mask].mean()))
    null_oos = np.array(null_oos)
    p95 = float(np.percentile(null_oos, 95))
    null_pass = bool(oos_mean > p95)

    oos_years_pos = {y: bool(fser[fser.index.year == int(y)].median() > 0) for y in YEARS}
    n_years_pos = sum(1 for y in YEARS if oos_years_pos.get(y, False))
    bar_pass = (
        n_years_pos >= 3
        and oos_sharpe >= 1.0
        and oos_maxdd >= -0.25
        and oos_cagr >= 0.15
        and null_pass
        and sign_pass
    )

    log = [
        "Rebalance: last trading bar of each ISO week (union of snapshot trading calendars; Friday close).",
        "Signal: 60-day realized vol (annualized std of daily returns, adjusted closes), min_periods=60; weeks before the 60th trading day have NaN vol -> tickers excluded that week; weeks with <20 rankable tickers produce no factor (same MIN_N floor as Claim 1).",
        "Ranking: cross-sectional on the 481-name frozen snapshot; long = bottom decile (lowest vol), short = top decile (highest vol), equal weight within each decile; rank method average.",
        "Costs: 10 bps per side on traded notional (turnover-based, both legs, weight change vs prior rebalance; first week charges full entry notional) — same convention as the Claim 2 multi-asset engine.",
        "Final rebalance date excluded from returns (no exit bar): %s." % rebal.iloc[-1].date(),
        "Weeks skipped (<%d rankable tickers): %d." % (MIN_N, weeks_skipped_lt20),
        "OOS window 2024-01-01..2026-08-07: 2024, 2025 complete; 2026 partial; 2027 empty -> 3-of-4-complete-year rule cannot pass before end-2027 (pre-registered structural constraint).",
        "Null: 1000x permutation of the weekly factor return series (block-shuffle on weekly rebalance dates), OOS-mean statistic, RNG seed 7.",
        "Mean weekly turnover (sum |w_t - w_{t-1}|): %.4f" % float(np.mean([t for _, t, _ in weeks_with_turnover])) if weeks_with_turnover else "no weeks",
    ]

    results = {
        "signal": "60-day realized vol long-short (long lowest-vol decile, short highest-vol decile, equal weight)",
        "train_weeks": [str(d.date()) for d in train.index],
        "oos_weeks": [str(d.date()) for d in oos.index],
        "weekly_factor_returns_net": {str(k.date()): float(v) for k, v in fser.items()},
        "train_mean": float(train.mean()),
        "oos_median": oos_median,
        "oos_mean": oos_mean,
        "oos_sharpe_annualized": oos_sharpe,
        "oos_maxdd": oos_maxdd,
        "oos_cagr_net": oos_cagr,
        "oos_years_positive_median": oos_years_pos,
        "null_p95_oos_mean": p95,
        "costs_bps_per_side": COST_BPS,
    }
    evaluation = {
        "claim": "price-only low-volatility factor (low-vol long / high-vol short)",
        "gates": {
            "sign_gate_train": {"pass": sign_pass, "value": float(train.mean())},
            "oos_median_3of4_years": {"pass": n_years_pos >= 3, "value": oos_years_pos,
                                       "note": "2026 partial, 2027 not computable; earliest possible pass end-2027 (pre-registered)"},
            "oos_sharpe_ge_1": {"pass": bool(oos_sharpe >= 1.0), "value": oos_sharpe},
            "oos_maxdd_le_25": {"pass": bool(oos_maxdd >= -0.25), "value": oos_maxdd},
            "oos_cagr_ge_15_net": {"pass": bool(oos_cagr >= 0.15), "value": oos_cagr},
            "null_p95": {"pass": null_pass, "value": p95},
        },
        "bar_pass": bar_pass,
        "pending": {"note": "2026 weeks after 2026-08-07 and 2027 not yet computable"},
        "data_handling_log": log,
    }
    with open(os.path.join(BASE, "docs", "data", "cycle3_lowvol_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2)
    with open(os.path.join(BASE, "docs", "data", "cycle3_lowvol_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"factor weeks: {len(fser)} | train weeks: {len(train)} | OOS weeks: {len(oos)}")
    print(f"train mean: {train.mean():+.5f} | OOS median: {oos_median:+.5f} | OOS mean: {oos_mean:+.5f}")
    print(f"OOS Sharpe: {oos_sharpe:.2f} | maxDD: {oos_maxdd:.1%} | CAGR net: {oos_cagr:.1%}")
    print(f"null p95: {p95:+.5f} | null pass: {null_pass} | sign gate: {sign_pass}")
    print(f"years positive: {oos_years_pos}")
    print(f"BAR PASS: {bar_pass}")


if __name__ == "__main__":
    main()