import csv, os

ROOT = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest"
OHLCV = os.path.join(ROOT, "market_data_2019_2026", "ohlcv")

inst_path = os.path.join(OHLCV, "instruments.csv")
rows = []
with open(inst_path, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append((row.get("symbol"), row.get("kind"), row.get("note")))
print(f"INSTRUMENTS rows={len(rows)}")
kinds = {}
for s, k, _ in rows:
    kinds[k] = kinds.get(k, 0) + 1
print(f"  kinds={kinds}")

symbols = [r[0] for r in rows]
bad = []
counts = {}
for s in symbols:
    p = os.path.join(OHLCV, s + ".csv")
    if not os.path.exists(p):
        bad.append((s, "NO FILE"))
        continue
    with open(p, encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, None)
        n = 0
        last = None
        incr = True
        for row in r:
            if len(row) < 7:
                bad.append((s, f"short row@{n} cols={len(row)}"))
                break
            n += 1
            d = row[0]
            if last and d <= last:
                incr = False
            try:
                lo = float(row[3]); hi = float(row[2]); cl = float(row[4])
                if hi < lo or lo < 0:
                    bad.append((s, f"H/L violation row {n}"))
                    break
            except ValueError:
                pass
            last = d
    counts[s] = (n, header, row[0] if n else None)

print("OHLCV files present:", len([s for s in symbols if os.path.exists(os.path.join(OHLCV, s + '.csv'))]), "/", len(symbols))
for s in sorted(symbols):
    n, hdr, last = counts.get(s, (None, None, None))
    print(f"  {s:6s} rows={n} last={last}")

print("\nPROBLEMS:")
for b in bad:
    print("  ", b)

mp = os.path.join(OHLCV, "missing.csv")
if os.path.exists(mp):
    c = sum(1 for _ in open(mp, encoding="utf-8")) - 1
    print("\nmissing.csv rows:", c)
else:
    print("\nmissing.csv: NO FILE")