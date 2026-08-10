#!/usr/bin/env python3
"""WORKER C - Anomaly scan over OHLCV CSVs (degraded mode).

Computes r_t = close_t/close_{t-1} - 1, sigma20 = rolling 20-day std of r
(min 20 obs), z = r/sigma20. EVENT iff |z|>=3 OR |r| >= amp threshold
(INDEX 2%, EQUITY 3%, CRYPTO 5%). Outputs events_all.json (cap 120, sorted
by |z| desc) and scan_summary.csv.
"""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # market_data_2019_2026
OHLCV = os.path.join(ROOT, "ohlcv")
OUT = os.path.join(ROOT, "events")
CAP = 120
MIN_BARS = 1400

AMP = {"INDEX": 0.02, "EQUITY": 0.03, "CRYPTO": 0.05}


def load_instruments():
    kind = {}
    with open(os.path.join(OHLCV, "instruments.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kind[row["symbol"].strip()] = row["kind"].strip()
    return kind


def load_ohlcv(path):
    """Return list of dict rows, sorted by date ascending."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                rows.append(
                    {
                        "date": row["date"].strip(),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]) if row.get("volume") not in (None, "") else 0.0,
                    }
                )
            except (ValueError, KeyError):
                continue
    rows.sort(key=lambda r: r["date"])
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    kind_of = load_instruments()
    symbols = sorted(
        s for s in kind_of
        if s + ".csv" in os.listdir(OHLCV) or (s == "^VIX" and os.path.exists(os.path.join(OHLCV, "^VIX.csv")))
    )
    # normalize symbol->filename mapping (handle ^VIX literal)
    csv_files = {os.path.splitext(f)[0]: f for f in os.listdir(OHLCV) if f.endswith(".csv")}

    all_events = []
    summary = []

    for sym in symbols:
        path = os.path.join(OHLCV, csv_files.get(sym, sym + ".csv"))
        if not os.path.exists(path):
            summary.append({"symbol": sym, "bars": 0, "hits_raw": 0, "kept": 0})
            continue
        bars = load_ohlcv(path)
        n = len(bars)
        if n < MIN_BARS:
            summary.append({"symbol": sym, "bars": n, "hits_raw": 0, "kept": 0})
            continue
        closes = [b["close"] for b in bars]
        r = [None]
        for i in range(1, n):
            prev = closes[i - 1]
            r.append((closes[i] / prev - 1.0) if prev else None)
        # sigma20 with min 20 obs (ddof=1, as pandas default)
        sigma = [None] * n
        for i in range(19, n):
            window = [r[j] for j in range(i - 19, i + 1) if r[j] is not None]
            if len(window) >= 20:
                mean = sum(window) / len(window)
                var = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
                sigma[i] = var ** 0.5
        amp = AMP.get(kind_of[sym], 0.03)
        sym_events = []
        for i in range(n):
            ri = r[i]
            si = sigma[i]
            if ri is None or si is None or si <= 0:
                continue
            z = ri / si
            hit = None
            if abs(z) >= 3.0:
                hit = "z"
            elif abs(ri) >= amp:
                hit = "amp"
            if not hit:
                continue
            sym_events.append(
                {
                    "symbol": sym,
                    "date": bars[i]["date"],
                    "r": ri,
                    "sigma20": si,
                    "z": z,
                    "threshold_hit": hit,
                    "kind": "positive" if ri >= 0 else "negative",
                }
            )
        summary.append({"symbol": sym, "bars": n, "hits_raw": len(sym_events), "kept": 0})
        all_events.extend(sym_events)

    all_events.sort(key=lambda e: abs(e["z"]), reverse=True)
    kept = all_events[:CAP]
    kept_ids = {(e["symbol"], e["date"]) for e in kept}
    for s in summary:
        s["kept"] = sum(1 for e in kept if e["symbol"] == s["symbol"])

    with open(os.path.join(OUT, "events_all.json"), "w", encoding="utf-8") as f:
        json.dump(kept, f, indent=2)
    with open(os.path.join(OUT, "scan_summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "bars", "hits_raw", "kept"])
        w.writeheader()
        w.writerows(summary)

    print("EVENTS:", len(kept), "| RAW:", len(all_events), "| symbols scanned:", len(symbols))
    # quick distortion guard: note any symbol with extreme single-day moves
    big = [e for e in kept if abs(e["r"]) >= 0.5]
    if big:
        print("WARN big-move events (|r|>=0.5):", [(e["symbol"], e["date"], round(e["r"], 3)) for e in big])
    return 0


if __name__ == "__main__":
    sys.exit(main())