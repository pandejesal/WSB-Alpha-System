"""One-time fetch of the 10 laggard-ticker OHLCV CSVs (2019-01-02 -> 2026-08-08)
into market_data_2019_2026/ohlcv, matching the existing cached format:
date,open,high,low,close,volume,source (lowercase, date=YYYY-MM-DD)."""
import os
import sys

import pandas as pd
import yfinance as yf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LAGGARDS = ["INTC", "PFE", "KO", "BA", "T", "CSCO", "VZ", "MRK", "GE", "IBM"]
DATA_DIR = "market_data_2019_2026/ohlcv"

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    data = yf.download(LAGGARDS, start="2019-01-01", end="2026-08-09",
                       progress=False, auto_adjust=True)
    for t in LAGGARDS:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                sub = data.loc[:, (slice(None), t)].copy()
                sub.columns = sub.columns.get_level_values(0)
            else:
                sub = data[[c for c in data.columns if c == t]].copy()
            sub = sub.dropna(subset=["Close"])
            if sub.empty:
                print(f"EMPTY: {t}")
                continue
            out = pd.DataFrame({
                "date": sub.index.strftime("%Y-%m-%d"),
                "open": sub["Open"].round(8),
                "high": sub["High"].round(8),
                "low": sub["Low"].round(8),
                "close": sub["Close"].round(8),
                "volume": sub["Volume"].astype("int64"),
                "source": "yfinance",
            })
            out.to_csv(os.path.join(DATA_DIR, f"{t}.csv"), index=False)
            print(f"OK {t}: {len(out)} rows, {out['date'].iloc[0]} -> {out['date'].iloc[-1]}")
        except Exception as e:
            print(f"FAIL {t}: {e}")
