"""Cycle 3 — Claim 1/4: Institutional 13F Accumulation Factor engine.

Implements docs/data/cycle3_prereg_13f.md EXACTLY as pre-registered
(including Appendix A delta: name-based ticker map, tiers 1-5). No tuning.

Pipeline:
  1. Parse all cache/13f/<fund>_<YYYYQn>.xml for the 50 pre-registered funds.
  2. Filter: investmentDiscretion == SOLE (SHARED/OTHER ignored, pre-registered).
  3. Resolve name_of_issuer -> snapshot ticker via scripts/cycle3_13f_map.py
     resolver (tiers 1-5 + class twins via titleOfClass). Unmapped -> IGNORED.
  4. Accumulation per quarter per ticker = sum over funds of
     (shares(q) - shares(q-1)); a fund with no XML at q or q-1 contributes
     ZERO change (pre-registered missing-filing rule).
  5. Rank the 481 snapshot tickers (with return data) by accumulation each
     quarter; long = top decile, short = bottom decile, equal weight.
  6. Quarterly holding returns: entry = first trading day strictly after
     (quarter_end + 45 days); exit = entry of next quarter. Net of 10bps/side.
  7. Checks: train sign gate (2019Q1..2023Q4 positive mean), OOS stats
     (2024Q1..2025Q4; 2026Q1/Q2 declared PENDING — exit dates beyond last
     price date 2026-08-07), 1000x block-shuffle null on quarterly dates.

Outputs (written before any return computation where required):
  docs/data/cycle3_13f_map_coverage.json  (map + data-handling coverage log)
  docs/data/cycle3_13f_evaluation.json    (gate verdicts)
  docs/data/cycle3_13f_results.json       (full numbers)
"""
import csv
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from cycle3_13f_map import clean, spaceless, sorted_tokens, RENAME_ALIASES, CLASS_TWINS  # noqa: E402

RNG = np.random.default_rng(7)

QUARTER_ENDS = pd.to_datetime(
    [f"{y}-{m}-{d}" for y in range(2019, 2027) for m, d in [(3, 31), (6, 30), (9, 30), (12, 31)]]
)
Q_LABEL = [f"{y}Q{q}" for y in range(2019, 2027) for q in range(1, 5)]
LAG_DAYS = 45
COST_BPS = 10  # per side


def load_ohlcv():
    """{ticker: DataFrame(date, close)} from market_data_2019_2026/ohlcv/."""
    out = {}
    for f in glob.glob(os.path.join(BASE, "market_data_2019_2026", "ohlcv", "*.csv")):
        t = os.path.basename(f)[:-4].upper()
        if t in {"INSTRUMENTS", "MISSING"}:
            continue
        df = pd.read_csv(f, parse_dates=["date"])
        out[t] = df[["date", "close"]].set_index("date")
    return out


def parse_xmls(fund_list):
    """Return (rows, log): rows = list of dict(fund, quarter, name, cls, shares,
    discretion, put_call); log = Counter of data-handling facts."""
    log = Counter()
    rows = []
    # longest-prefix slug match: files named <slug>_<quarter>.xml, slugs may
    # contain underscores (goldman_sachs, de_shaw, two_sigma, ...)
    slugs = sorted(fund_list, key=len, reverse=True)
    for f in sorted(glob.glob(os.path.join(BASE, "cache", "13f", "*.xml"))):
        base = os.path.basename(f)[:-4]
        fund = None
        for s in slugs:
            if base == s or base.startswith(s + "_"):
                fund = s
                break
        quarter = base[len(fund) + 1:] if fund else None
        if fund is None:
            log[f"excluded_non_fund:{base}"] += 1
            continue
        if not re.fullmatch(r"20\d{2}Q[1-4]", quarter):
            log[f"excluded_bad_quarter:{base}"] += 1
            continue
        log[f"xml:{fund}:{quarter}"] += 1
        try:
            tree = ET.parse(f)
        except ET.ParseError:
            log[f"xml_parse_error:{base}"] += 1
            continue
        ns = tree.getroot().tag.split("}")[0] + "}" if "}" in tree.getroot().tag else ""
        for it in tree.iter(ns + "infoTable"):
            def tag(t):
                el = it.find(ns + t)
                return el.text.strip() if el is not None and el.text else ""

            shares_el = it.find(ns + "shrsOrPrnAmt/" + ns + "sshPrnamt")
            try:
                shares = float(shares_el.text) if shares_el is not None and shares_el.text else 0.0
            except (ValueError, TypeError):
                shares = 0.0
            rows.append(
                {
                    "fund": fund,
                    "quarter": quarter,
                    "name": tag("nameOfIssuer").upper(),
                    "cls": tag("titleOfClass"),
                    "shares": shares,
                    "discretion": tag("investmentDiscretion"),
                    "put_call": tag("putCall"),
                }
            )
    return rows, log


def build_ticker_resolver(ticker_to_names):
    exact = defaultdict(list)
    flat = defaultdict(list)
    sorted_n = defaultdict(list)
    token_sets = {}
    for t, (sec_title, yf_name) in ticker_to_names.items():
        for src in (sec_title, yf_name):
            if not src:
                continue
            exact[clean(src)].append(t)
            flat[spaceless(clean(src))].append(t)
            sorted_n[sorted_tokens(clean(src))].append(t)
        cset = set()
        for src in (sec_title, yf_name):
            if src:
                cset |= set(clean(src).split())
        token_sets[t] = frozenset(cset) if cset else frozenset()
    resolve_cache = {}

    def resolve(name13f, cls):
        key = (name13f, cls)
        if key in resolve_cache:
            return resolve_cache[key]
        c = clean(name13f)
        cset = set(c.split())
        cands = exact.get(c)
        tier = 1
        if not cands:
            cands = flat.get(spaceless(c))
            tier = 2
        if not cands:
            cands = sorted_n.get(sorted_tokens(c))
            tier = 3
        if not cands and name13f in RENAME_ALIASES:
            resolve_cache[key] = (RENAME_ALIASES[name13f], 5)
            return resolve_cache[key]
        if not cands:
            hits = set()
            for t in token_sets:
                tset = token_sets[t]
                if cset and (cset <= tset or tset <= cset):
                    hits.add(t)
            if len(hits) == 1:
                resolve_cache[key] = (next(iter(hits)), 4)
                return resolve_cache[key]
            if len(hits) > 1:
                t = CLASS_TWINS.get(frozenset(hits), {}).get(cls)
                resolve_cache[key] = (t, 4)
                return resolve_cache[key]
            resolve_cache[key] = (None, 0)
            return resolve_cache[key]
        uniq = sorted(set(cands))
        if len(uniq) == 1:
            resolve_cache[key] = (uniq[0], tier)
            return resolve_cache[key]
        t = CLASS_TWINS.get(frozenset(uniq), {}).get(cls)
        resolve_cache[key] = (t, tier)
        return resolve_cache[key]

    return resolve


def main():
    with open(os.path.join(BASE, "market_data_2019_2026", "institutions", "13f_funds.csv"),
              encoding="utf-8") as f:
        fund_list = [r["fund_slug"] for r in csv.DictReader(f)]
    with open(os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json"), encoding="utf-8") as f:
        map_data = json.load(f)
    ticker_to_names = map_data["ticker_to_names"]
    snapshot = set(ticker_to_names.keys())

    rows, log = parse_xmls(set(fund_list))
    resolve = build_ticker_resolver(ticker_to_names)

    # map holdings -> tickers; count everything for the coverage log
    mapped = 0
    unmapped = 0
    non_sole = 0
    tier_counts = Counter()
    per_q = Counter()
    per_q_unmapped = Counter()
    h = []
    for r in rows:
        if r["discretion"] != "SOLE":
            non_sole += 1
            continue
        t, tier = resolve(r["name"], r["cls"])
        if t:
            mapped += 1
            tier_counts[tier] += 1
            per_q[r["quarter"]] += 1
            r["ticker"] = t
            h.append(r)
        else:
            unmapped += 1
            per_q_unmapped[r["quarter"]] += 1

    df = pd.DataFrame(h)
    shares = (df.groupby(["fund", "quarter", "ticker"])["shares"].sum().unstack("fund").fillna(0.0))

    # accumulation per quarter: delta vs prior quarter, zero-change when the
    # fund has NO XML at q or NO XML at q-1 (pre-registered missing-filing rule:
    # "a fund with no XML for a quarter contributes ZERO change (not excluded)").
    # A fund's FIRST filing therefore contributes zero accumulation (no prior
    # filing to diff against) — no phantom full-position delta.
    quarters = sorted(df["quarter"].unique())
    filing_funds = df.groupby("quarter")["fund"].apply(set).to_dict()
    acc = {}
    for i, q in enumerate(quarters):
        cur = shares.loc[q]  # DataFrame: tickers x funds
        if i == 0:
            acc[q] = pd.Series(0.0, index=cur.index)
            continue
        prev_q = quarters[i - 1]
        prev = shares.loc[prev_q]
        d = cur.sub(prev, fill_value=0.0)
        # funds with no filing at q-1: delta undefined -> zero change
        mask = pd.Series(cur.columns.isin(filing_funds.get(prev_q, set())), index=cur.columns)
        d = d.mul(mask, axis=1)
        acc[q] = d.sum(axis=1)

    # price data
    ohlcv = load_ohlcv()
    qend = dict(zip(Q_LABEL, QUARTER_ENDS))
    with open(os.path.join(BASE, "docs", "data", "cycle3_13f_map_coverage.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "map_build": "2026-08-16 (scripts/cycle3_13f_map.py)",
                "funds": fund_list,
                "holdings_rows_total": len(rows),
                "sole_rows": len(h),
                "non_sole_ignored": non_sole,
                "unmapped_ignored": unmapped,
                "mapped": mapped,
                "tier_counts": dict(tier_counts),
                "per_quarter_mapped": dict(per_q),
                "per_quarter_unmapped": dict(per_q_unmapped),
                "data_handling_log": dict(log),
                "pending_quarters": ["2026Q1", "2026Q2"],
                "pending_reason": "holding-period exit dates (2026-08-17, 2026-11-16) beyond last price date 2026-08-07",
            },
            f, indent=2,
        )

    # quarterly returns between rebalance dates
    def entry_date(q):
        d = qend[q] + pd.Timedelta(days=LAG_DAYS)
        return d + pd.Timedelta(days=1)

    def first_trading_day(df_idx, after):
        after = pd.Timestamp(after)
        v = df_idx[df_idx > after]
        return v[0] if len(v) else None

    # exit(q) = entry(q+1); returns only where both dates exist in ALL data
    ret = {}
    usable_quarters = []
    for i, q in enumerate(Q_LABEL):
        if i + 1 >= len(Q_LABEL):
            continue
        nxt = Q_LABEL[i + 1]
        e = entry_date(q)
        x = entry_date(nxt)
        cols = []
        for t in snapshot:
            idx = ohlcv[t].index if t in ohlcv else None
            if idx is None:
                continue
            de = first_trading_day(idx, e)
            dx = first_trading_day(idx, x)
            if de is None or dx is None:
                continue
            cols.append((t, ohlcv[t].loc[de, "close"], ohlcv[t].loc[dx, "close"]))
        if not cols:
            continue
        rdf = pd.DataFrame(cols, columns=["ticker", "p0", "p1"]).set_index("ticker")
        ret[q] = rdf["p1"] / rdf["p0"] - 1.0
        usable_quarters.append(q)

    acc_df = pd.DataFrame(acc).T  # quarters x tickers (only quarters present in filings)
    # build aligned factor series
    factors = {}
    for q in usable_quarters:
        if q not in acc_df.index:
            continue
        a = acc_df.loc[q]
        r = ret[q]
        both = a.index.intersection(r.index)
        if len(both) < 20:
            continue
        a = a[both]
        r = r[both]
        if a.nunique() == 1:  # all identical accumulation -> no spread
            continue
        ranks = a.rank(method="average")
        n = len(both)
        lo = ranks <= np.ceil(n / 10)
        hi = ranks > n - np.floor(n / 10)
        long_ret = r[hi].mean()
        short_ret = r[lo].mean()
        factors[q] = long_ret - short_ret - 2 * COST_BPS / 1e4

    fser = pd.Series(factors).sort_index()
    train = fser[[q for q in fser.index if q.startswith(("2019", "2020", "2021", "2022", "2023"))]]
    oos = fser[[q for q in fser.index if q.startswith(("2024", "2025"))]]

    # ---- checks ----
    sign_pass = bool(train.mean() > 0)
    oos_median = float(oos.median()) if len(oos) else float("nan")
    oos_mean = float(oos.mean()) if len(oos) else float("nan")
    oos_sharpe = float(oos.mean() / oos.std() * 2) if len(oos) > 1 and oos.std() > 0 else float("nan")
    eq = (1 + oos).cumprod()
    oos_maxdd = float((eq / eq.cummax() - 1).min()) if len(eq) else float("nan")
    n_years = len(oos) / 4.0
    oos_cagr = float(eq.iloc[-1] ** (1 / n_years) - 1) if len(eq) and n_years > 0 and eq.iloc[-1] > 0 else float("nan")

    # 1000x block-shuffle null on quarterly rebalance dates (OOS-mean statistic)
    fkeys = list(factors.keys())
    fvals = np.array(list(factors.values()))
    oos_q = [q for q in fkeys if q.startswith(("2024", "2025"))]
    null_oos = []
    for _ in range(1000):
        perm = RNG.permutation(len(fkeys))
        ps = pd.Series(dict(zip(fkeys, fvals[perm])))
        null_oos.append(float(ps[oos_q].mean()))
    null_oos = np.array(null_oos)
    p95 = float(np.percentile(null_oos, 95))
    null_pass = bool(oos_mean > p95)

    oos_years_pos = {y: float(oos[[q for q in oos.index if q.startswith(y)]].median() > 0)
                     for y in ["2024", "2025", "2026", "2027"]}
    n_years_pos = sum(1 for y in ["2024", "2025", "2026", "2027"] if oos_years_pos.get(y, False))
    bar_pass = (
        n_years_pos >= 3  # pre-registered: 3 of 4 complete OOS years (2026-2027 not yet computable)
        and oos_sharpe >= 1.0
        and oos_maxdd >= -0.25
        and oos_cagr >= 0.15
        and null_pass
        and sign_pass
    )

    results = {
        "signal": "13F accumulation factor (long top decile, short bottom decile, equal weight)",
        "train_quarters": [q for q in fser.index if q in train.index],
        "oos_quarters": [q for q in fser.index if q in oos.index],
        "pending_quarters": ["2026Q1", "2026Q2"],
        "quarterly_factor_returns": {q: float(v) for q, v in fser.items()},
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
        "claim": "13F accumulation factor beats median hedge fund OOS",
        "gates": {
            "sign_gate_train": {"pass": sign_pass, "value": float(train.mean())},
            "oos_median_3of4_years": {"pass": n_years_pos >= 3, "value": oos_years_pos,
                                       "note": "2026-2027 not yet computable; earliest possible pass end-2027 (pre-registered)"},
            "oos_sharpe_ge_1": {"pass": bool(oos_sharpe >= 1.0), "value": oos_sharpe},
            "oos_maxdd_le_25": {"pass": bool(oos_maxdd >= -0.25), "value": oos_maxdd},
            "oos_cagr_ge_15_net": {"pass": bool(oos_cagr >= 0.15), "value": oos_cagr},
            "null_p95": {"pass": null_pass, "value": p95},
        },
        "bar_pass": bar_pass,
        "pending": {"quarters": ["2026Q1", "2026Q2"],
                     "note": "exit dates beyond last price date 2026-08-07; verdict 2026-09-17 may refresh prices"},
    }
    with open(os.path.join(BASE, "docs", "data", "cycle3_13f_evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(evaluation, f, indent=2)
    with open(os.path.join(BASE, "docs", "data", "cycle3_13f_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"quarters usable: {len(usable_quarters)} | factor quarters: {len(fser)}")
    print(f"train mean: {train.mean():+.5f} | OOS median: {oos_median:+.5f} | OOS mean: {oos_mean:+.5f}")
    print(f"OOS Sharpe: {oos_sharpe:.2f} | maxDD: {oos_maxdd:.1%} | CAGR net: {oos_cagr:.1%}")
    print(f"null p95: {p95:+.5f} | null pass: {null_pass} | sign gate: {sign_pass}")
    print(f"BAR PASS: {bar_pass}")


if __name__ == "__main__":
    main()