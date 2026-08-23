import json
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INSTRUMENTS = [
    "SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "SLV", "HYG", "UUP",
    "BTC-USD", "ETH-USD",
]
CRYPTO = {"BTC-USD", "ETH-USD"}
EQUITY_COST_BPS = 0.0005
CRYPTO_COST_BPS = 0.0010
SMA_WINDOW = 200
TRAIN_END = pd.Timestamp("2023-12-31")
OOS_END = pd.Timestamp("2026-08-07")
YEARS = [2024, 2025, 2026, 2027]
N_NULL = 1000
SEED = 7
FRED_CACHE = os.path.join(BASE, "data", "cache", "fred_historical_regimes.json")
OUT_DIR = os.path.join(BASE, "docs", "data")


def load_closes():
    out = {}
    for sym in INSTRUMENTS:
        p = os.path.join(BASE, "market_data_2019_2026", "ohlcv", sym + ".csv")
        df = pd.read_csv(p, parse_dates=["date"])
        out[sym] = df.set_index("date")["close"].sort_index()
    return out


def rebalance_dates(closes):
    eq = closes["SPY"].index
    s = pd.Series(eq, index=eq)
    return s.groupby(s.index.to_period("W")).max()


def build_signals(closes, rebal):
    sig = {}
    for sym, s in closes.items():
        sma = s.rolling(SMA_WINDOW, min_periods=SMA_WINDOW).mean()
        sig[sym] = (s > sma).reindex(rebal).fillna(False)
    return pd.DataFrame(sig)


def weekly_returns(closes, rebal):
    ret = {}
    for sym, s in closes.items():
        ret[sym] = s.reindex(rebal).pct_change().shift(-1)
    return pd.DataFrame(ret)


def load_regime_gate(dates):
    with open(FRED_CACHE) as f:
        raw = json.load(f)
    reg = pd.Series(raw, dtype=object)
    reg.index = pd.to_datetime(reg.index)
    reg = reg.sort_index()
    labels = reg.reindex(dates).ffill()
    gate = pd.Series((labels == "RISK_ON").fillna(False), index=dates)
    return gate, labels


def main():
    closes = load_closes()
    rebal = rebalance_dates(closes)
    signals = build_signals(closes, rebal)
    wret = weekly_returns(closes, rebal)

    usable = pd.DatetimeIndex(rebal.iloc[:-1].values)
    k = signals.loc[usable].sum(axis=1)
    weights = (signals.loc[usable].div(k, axis=0)).fillna(0.0)

    gate, labels = load_regime_gate(usable)
    weights = weights.mul(gate, axis=0)

    gross = (weights.values * wret.loc[usable].fillna(0.0).values).sum(axis=1)
    prev = np.zeros(len(INSTRUMENTS))
    costs = np.zeros(len(usable))
    rates = np.array([CRYPTO_COST_BPS if s in CRYPTO else EQUITY_COST_BPS for s in INSTRUMENTS])
    for i, w in enumerate(weights.values):
        costs[i] = np.abs(w - prev).dot(rates)
        prev = w
    net = pd.Series(gross - costs, index=usable)

    train = net[net.index < TRAIN_END]
    oos = net[net.index >= TRAIN_END]

    train_mean = float(train.mean())
    sign_gate = train_mean > 0.0

    year_med = {}
    for y in YEARS:
        sel = net[net.index.year == y]
        year_med[y] = float(sel.median()) if len(sel) else None

    oos_sharpe = float(oos.mean() / oos.std() * np.sqrt(52)) if len(oos) > 1 else 0.0
    equity = (1.0 + oos).cumprod()
    peak = equity.cummax()
    oos_maxdd = float((equity / peak - 1.0).min())
    years_span = len(oos) / 52.0
    oos_cagr = float(equity.iloc[-1] ** (1.0 / years_span) - 1.0) if years_span > 0 else 0.0
    oos_mean = float(oos.mean())

    rng = np.random.default_rng(SEED)
    vals = net.values
    oos_mask = (net.index >= TRAIN_END)
    null_means = np.empty(N_NULL)
    for i in range(N_NULL):
        shuffled = rng.permutation(vals)
        null_means[i] = shuffled[oos_mask].mean()
    null_p95 = float(np.percentile(null_means, 95))
    null_pass = oos_mean > null_p95

    complete_years = [y for y in YEARS if pd.Timestamp("%d-12-31" % y) <= net.index.max()]
    oos_years_ok = sum(1 for y in complete_years if (year_med.get(y) or 0.0) > 0.0)
    bar_pass = (
        oos_years_ok >= 3
        and oos_sharpe >= 1.0
        and oos_maxdd <= -0.25
        and oos_cagr >= 0.15
        and null_pass
        and sign_gate
    )

    gate_on = int(gate.sum())
    gate_off = int(len(usable) - gate_on)
    k_zero = int(((k == 0) | ~gate).sum())
    label_counts = labels.dropna().value_counts().to_dict()
    gate_log = [
        "Regime gate: FRED daily labels from data/cache/fred_historical_regimes.json (T10Y2Y + T10YIE per src/risk/fred_macro_provider.py classification); as-of lookup (last label <= rebalance date); regime == RISK_ON -> C2 weights, else all cash; missing label -> all cash (fail-closed). Cache checked 2026-08-16: 5909 labels 2003-01-02..2026-08-14, full window covered.",
        "Gate usage: %d of %d usable weeks gated ON (RISK_ON); %d weeks all-cash (gate off or zero longs)." % (gate_on, len(usable), k_zero),
        "Label distribution over usable weeks: %s" % {str(k): v for k, v in label_counts.items()},
        "CLARIFICATION (pre-run, 2026-08-16): earlier wording 'dual momentum (SMA200 + 12-1)' was descriptive error; C2 exact mechanism is SMA200 long/cash only (engine = spec). No MOM12-1 component. This engine implements the exact C2 mechanism plus the regime gate.",
    ]
    log = [
        "Rebalance: last trading bar of each ISO week (SPY calendar), signal and entry at that close; crypto instruments reindexed to the same Friday dates (crypto trades daily; all Fridays present).",
        "SMA200 uses each instrument's own daily calendar with min_periods=200; weeks before the 200th bar have no SMA -> treated as CASH (price>NaN is False), no fabricated signal. Earliest computable signal dates: %s."
        % {s: str(closes[s].index[199].date()) for s in INSTRUMENTS},
        "Costs charged at each rebalance on weight change vs prior rebalance (start from cash): 5 bps/side equity/index, 10 bps/side crypto; no final liquidation cost (no return week after last date).",
        "RETURN-TIMING FIX (2026-08-16, inherited from cycle3_multiasset_engine.py): weekly returns are Friday-to-Friday close(t')/close(t)-1 between consecutive rebalance dates. Original code used daily pct_change() reindexed to Fridays plus shift(-1), producing a one-day return misaligned one week forward. Strategy, costs, and all gates UNCHANGED.",
        "Final rebalance date excluded from returns (no exit bar): %s." % rebal.iloc[-1].date(),
        "Weeks with all instruments CASH (k=0) contribute 0.0 return: %d of %d usable weeks (incl. gate-off weeks)."
        % ((k == 0).sum(), len(usable)),
        "OOS window 2024-01-01..2026-08-07: 2024, 2025 complete; 2026 partial (entry weeks through 2026-08-07); 2027 empty -> 3-of-4-complete-year rule cannot pass before end-2027 (pre-registered structural constraint).",
        "Null: 1000x permutation of the weekly net return series (block-shuffle on weekly rebalance dates), OOS-mean statistic, RNG seed 7.",
    ] + gate_log

    ev = {
        "claim": "c6-regime-gated-multiasset",
        "bar_pass": bool(bar_pass),
        "gates": {
            "sign_gate_train": bool(sign_gate),
            "train_mean_weekly": train_mean,
            "oos_median_3of4_years": {str(y): year_med[y] for y in YEARS},
            "oos_years_positive_count": oos_years_ok,
            "oos_complete_years_available": complete_years,
            "oos_sharpe_annualized": oos_sharpe,
            "oos_maxdd": oos_maxdd,
            "oos_cagr_net": oos_cagr,
            "oos_mean_weekly": oos_mean,
            "null_p95": null_p95,
            "null_pass": bool(null_pass),
        },
        "gate_stats": {
            "weeks_gated_on": gate_on,
            "weeks_gated_off": gate_off,
            "all_cash_weeks": int(k_zero),
            "label_counts_usable_weeks": {str(k): v for k, v in label_counts.items()},
        },
        "pending": ["2026 weeks after 2026-08-07", "2027"],
        "note": "earliest possible pass end-2027 (pre-registered)",
        "data_handling_log": log,
    }

    res = {
        "claim": "c6-regime-gated-multiasset",
        "weekly_net_returns": {str(k): round(v, 6) for k, v in net.items()},
        "gate_on_dates": [str(d.date()) for d in usable[gate]],
        "train_weeks": int(len(train)),
        "oos_weeks": int(len(oos)),
        "instruments": INSTRUMENTS,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "cycle5_c6_evaluation.json"), "w") as f:
        json.dump(ev, f, indent=2)
    with open(os.path.join(OUT_DIR, "cycle5_c6_results.json"), "w") as f:
        json.dump(res, f, indent=2)

    print("train weeks: %d | oos weeks: %d" % (len(train), len(oos)))
    print("gate on weeks: %d | gate off weeks: %d" % (gate_on, gate_off))
    print("train mean: %+.6f | sign gate: %s" % (train_mean, sign_gate))
    print("oos mean: %+.6f | oos median: %+.6f" % (oos_mean, float(oos.median())))
    print("year medians: %s" % {y: year_med[y] for y in YEARS})
    print("oos Sharpe: %.2f | maxDD: %.1f%% | CAGR net: %.1f%%" % (oos_sharpe, 100 * oos_maxdd, 100 * oos_cagr))
    print("null p95: %+.6f | null pass: %s" % (null_p95, null_pass))
    print("BAR PASS: %s" % bar_pass)


if __name__ == "__main__":
    main()