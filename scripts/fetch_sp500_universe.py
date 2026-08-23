"""Phase 2 (Cycle 2): fetch the S&P 500 universe snapshot + full OHLCV.

Steps:
1. S&P 500 constituents from the canonical Wikipedia list (yfinance has no
   constituents endpoint; source recorded in the snapshot appendix).
2. Download daily OHLCV 2019-01-01..2026-08-07 for every constituent
   (auto_adjust=True, same format as market_data_2019_2026/ohlcv).
3. Pre-registered liquidity floor (fixed in factor_claim_preregistration.md):
   - avg daily dollar volume >= $10M over the last 60 trading days
   - < 5% of trading bars missing over 2019-01-01..2026-08-07
     (reference calendar = ^GSPC)
   - mean close >= $2
4. Write snapshot JSON (docs/data/snapshot_SP500.json), CSVs, exclusion list.
Does NOT run any backtest. Snapshot appendix to pre-registration doc is
appended by the caller after this script succeeds.
"""
import io
import json
import os
import sys
import time

import pandas as pd
import requests
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

START = "2019-01-01"
END = "2026-08-09"          # exclusive end -> data through 2026-08-07/08
DATA_DIR = "market_data_2019_2026/ohlcv"
SNAPSHOT_JSON = "docs/data/snapshot_SP500.json"
CHUNK = 80
SLEEP_S = 3.0
MIN_DOLVOL = 10_000_000.0
MAX_MISSING_FRAC = 0.05
MIN_PRICE = 2.0


def get_constituents():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/126.0 Safari/537.36"}
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    df.columns = [str(c).strip() for c in df.columns]
    sym_col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    symbols = df[sym_col].astype(str).str.strip().tolist()
    clean = []
    for s in symbols:
        if not s or s.lower() == "nan":
            continue
        if "." in s:  # BRK.B -> BRK-B for yfinance
            s = s.replace(".", "-")
        clean.append(s)
    return clean


def download_chunk(tickers):
    data = yf.download(tickers, start=START, end=END, progress=False,
                       auto_adjust=True, threads=False, group_by="ticker")
    return data


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs("docs/data", exist_ok=True)

    print("Fetching S&P 500 constituents (Wikipedia canonical list)...")
    constituents = get_constituents()
    print(f"  constituents: {len(constituents)}")

    ref = yf.download("^GSPC", start=START, end=END, progress=False,
                      auto_adjust=True, threads=False)
    ref_dates = set(pd.DatetimeIndex(ref.index).strftime("%Y-%m-%d"))
    print(f"  reference calendar (^GSPC): {len(ref_dates)} trading days")

    rows = {}
    failed = {}
    for i in range(0, len(constituents), CHUNK):
        chunk = constituents[i:i + CHUNK]
        try:
            data = download_chunk(chunk)
        except Exception as e:
            print(f"  chunk FAILED ({len(chunk)}): {e}; will retry individually")
            for t in chunk:
                try:
                    sub = yf.download(t, start=START, end=END, progress=False,
                                      auto_adjust=True, threads=False)
                    if sub.empty:
                        failed[t] = "empty"
                    else:
                        rows[t] = sub
                except Exception as e2:
                    failed[t] = str(e2)
            time.sleep(SLEEP_S)
            continue
        if data.empty:
            for t in chunk:
                failed[t] = "empty-chunk"
            time.sleep(SLEEP_S)
            continue
        if isinstance(data.columns, pd.MultiIndex):
            for t in chunk:
                try:
                    sub = data[t].dropna(subset=["Close"])
                    if sub.empty:
                        failed[t] = "empty"
                    else:
                        rows[t] = sub
                except KeyError:
                    failed[t] = "missing-column"
        else:
            # single-ticker fallback path
            for t in chunk:
                try:
                    sub = data[[c for c in data.columns if c == t]].dropna(
                        subset=["Close"])
                    if sub.empty:
                        failed[t] = "empty"
                    else:
                        rows[t] = sub
                except KeyError:
                    failed[t] = "missing-column"
        print(f"  chunk {i // CHUNK + 1}: {len(chunk)} tickers, "
              f"{len(rows)} total ok so far")
        time.sleep(SLEEP_S)

    print(f"\nDownloaded {len(rows)} / {len(constituents)}; failed: {len(failed)}")

    included, excluded = [], {}
    for t, sub in rows.items():
        dts = pd.DatetimeIndex(sub.index)
        n = len(dts)
        missing_frac = 1.0 - n / len(ref_dates)
        last60 = sub.tail(60)
        avg_dolvol = float((last60["Close"] * last60["Volume"]).mean())
        mean_price = float(last60["Close"].mean())
        if avg_dolvol < MIN_DOLVOL:
            excluded[t] = f"dolvol ${avg_dolvol:,.0f} < $10M"
        elif missing_frac > MAX_MISSING_FRAC:
            excluded[t] = f"missing {missing_frac:.1%} > 5%"
        elif mean_price < MIN_PRICE:
            excluded[t] = f"price ${mean_price:.2f} < $2"
        else:
            included.append(t)
    for t, reason in failed.items():
        excluded[t] = f"fetch-failed: {reason}"

    included = sorted(included)
    snapshot = {
        "snapshot_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "source": "Wikipedia 'List of S&P 500 companies' (canonical list; "
                  "yfinance has no constituents endpoint)",
        "data_window": {"start": START, "end": "2026-08-07"},
        "constituents_total": len(constituents),
        "included_count": len(included),
        "excluded_count": len(excluded),
        "floor_rules": {"min_avg_dolvol_60d": MIN_DOLVOL,
                        "max_missing_frac": MAX_MISSING_FRAC,
                        "min_price": MIN_PRICE},
        "reference_calendar": "^GSPC",
        "reference_trading_days": len(ref_dates),
        "included": included,
        "excluded": {k: v for k, v in sorted(excluded.items())},
    }
    with open(SNAPSHOT_JSON, "w") as f:
        json.dump(snapshot, f, indent=2)

    ok_written = 0
    for t in included:
        sub = rows[t]
        out = pd.DataFrame({
            "date": pd.DatetimeIndex(sub.index).strftime("%Y-%m-%d"),
            "open": sub["Open"].round(8),
            "high": sub["High"].round(8),
            "low": sub["Low"].round(8),
            "close": sub["Close"].round(8),
            "volume": sub["Volume"].astype("int64"),
            "source": "yfinance",
        })
        out.to_csv(os.path.join(DATA_DIR, f"{t}.csv"), index=False)
        ok_written += 1

    gap_rows = []
    for t in included:
        sub = rows[t]
        n = len(sub)
        missing = len(ref_dates) - n
        last_close = float(sub["Close"].iloc[-1])
        gap_rows.append({"ticker": t, "rows": n, "missing_bars": missing,
                         "missing_frac": round(1 - n / len(ref_dates), 4),
                         "last_close": round(last_close, 2)})
    gap_df = pd.DataFrame(gap_rows).sort_values("missing_bars", ascending=False)
    gap_df.to_csv("docs/data/gap_report.csv", index=False)

    print(f"\nWrote {ok_written} CSVs to {DATA_DIR}")
    print(f"Included: {len(included)} | Excluded: {len(excluded)}")
    print("Exclusions:")
    for t, reason in sorted(excluded.items()):
        print(f"  {t}: {reason}")
    max_miss = gap_df["missing_bars"].max()
    print(f"\nGap report: worst missing_bars among included = {max_miss}")
    print(f"Saved {SNAPSHOT_JSON} and docs/data/gap_report.csv")


if __name__ == "__main__":
    main()
