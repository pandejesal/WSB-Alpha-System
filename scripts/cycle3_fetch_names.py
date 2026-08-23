import json
import os
import time

import yfinance as yf

BASE = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest"
CACHE = os.path.join(BASE, "cache", "snapshot_names.json")
NORM = os.path.join(BASE, "cache", "snapshot_normmap.json")

snap = []
with open(os.path.join(BASE, "docs", "data", "factor_claim_preregistration.md"), encoding="utf-8") as fh:
    in_list = False
    for line in fh:
        s = line.strip()
        if s.startswith("Included tickers (481)"):
            in_list = True
            continue
        if in_list:
            if s.startswith("Excluded"):
                break
            snap += s.split()
snap = sorted(set(t.upper() for t in snap if t))

name_map = {}
if os.path.exists(CACHE):
    with open(CACHE, encoding="utf-8") as f:
        name_map = json.load(f)
name_map = {t: v for t, v in name_map.items() if v}

todo = [t for t in snap if t not in name_map]
print(f"total {len(snap)} | cached {len(name_map)} | todo {len(todo)}", flush=True)

for i, t in enumerate(todo):
    try:
        info = yf.Ticker(t).get_info()
        nm = info.get("longName") or info.get("shortName") or ""
        if nm:
            name_map[t] = nm
    except Exception:
        pass
    if (i + 1) % 25 == 0:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(name_map, f)
        print(f"  saved at {len(name_map)}/{len(snap)}", flush=True)
    time.sleep(0.2)

with open(CACHE, "w", encoding="utf-8") as f:
    json.dump(name_map, f)
print(f"done: {len(name_map)}/{len(snap)} names", flush=True)