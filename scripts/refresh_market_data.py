"""Weekly maintenance: extend local OHLCV CSVs to the current date.

Idempotent by design: for each CSV in market_data_2019_2026/ohlcv, fetch
yfinance bars from (last local date + 1) through today, append only new
rows, drop duplicates on date, sort, rewrite. Re-running is a no-op.

Usage:
  python scripts/refresh_market_data.py                 # all CSVs
  python scripts/refresh_market_data.py --tickers AAPL MSFT
  python scripts/refresh_market_data.py --dry-run --tickers AAPL MSFT  # report only
"""
import argparse
import glob
import os
import sys

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = "market_data_2019_2026/ohlcv"


def refresh_one(path, dry_run=False, max_missing=5):
    ticker = os.path.splitext(os.path.basename(path))[0]
    local = pd.read_csv(path, parse_dates=["date"])
    if local.empty:
        return ticker, "EMPTY-LOCAL", 0
    last_date = local["date"].max()
    today = pd.Timestamp.today().normalize()
    if last_date >= today:
        return ticker, "UP-TO-DATE", 0
    start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end = (today + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    new = yf.download(ticker, start=start, end=end, progress=False,
                      auto_adjust=True, threads=False)
    if new.empty:
        return ticker, "NO-NEW-BARS", 0
    if isinstance(new.columns, pd.MultiIndex):
        new.columns = new.columns.get_level_values(0)
    out = pd.DataFrame({
        "date": pd.DatetimeIndex(new.index).strftime("%Y-%m-%d"),
        "open": pd.Series(new["Open"].to_numpy().reshape(-1)).astype(float).round(8),
        "high": pd.Series(new["High"].to_numpy().reshape(-1)).astype(float).round(8),
        "low": pd.Series(new["Low"].to_numpy().reshape(-1)).astype(float).round(8),
        "close": pd.Series(new["Close"].to_numpy().reshape(-1)).astype(float).round(8),
        "volume": pd.Series(new["Volume"].to_numpy().reshape(-1)).astype("int64"),
        "source": "yfinance",
    })
    merged = pd.concat([local, out], ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"]).dt.strftime("%Y-%m-%d")
    before = len(merged)
    merged = merged.drop_duplicates(subset="date", keep="last")
    merged = merged.sort_values("date").reset_index(drop=True)
    added = before - len(merged)
    if not dry_run and added > 0:
        merged.to_csv(path, index=False)
    return ticker, "OK", added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="*", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.tickers:
        paths = [os.path.join(DATA_DIR, f"{t}.csv") for t in args.tickers]
    else:
        paths = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    missing = [p for p in paths if not os.path.exists(p)]
    for p in missing:
        print(f"  MISSING FILE: {p}")
    paths = [p for p in paths if os.path.exists(p)]

    total_added = 0
    for p in paths:
        ticker, status, added = refresh_one(p, dry_run=args.dry_run)
        total_added += added
        print(f"  {ticker:<6} {status:<12} added={added}")
    mode = "DRY-RUN" if args.dry_run else "WRITE"
    print(f"\n[{mode}] files={len(paths)} total_added={total_added}")


if __name__ == "__main__":
    main()
