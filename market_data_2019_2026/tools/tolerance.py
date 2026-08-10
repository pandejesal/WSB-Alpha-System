#!/usr/bin/env python3
"""WORKER A - GDELT tolerance probe. Sends 6 TimelineVol requests with the
FIXED parenthesized query format at a given spacing and reports each status.
Usage: python tolerance.py [spacing_seconds]"""
import time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research harvest; keyless) GDELT"}
API = "https://api.gdeltproject.org/api/v2/doc/doc"
SYM_Q = [
    ("SPY", '(SPY OR "S&P 500")'),
    ("AAPL", "(AAPL OR Apple)"),
    ("MSFT", "(MSFT OR Microsoft)"),
    ("NVDA", "(NVDA OR Nvidia)"),
    ("GLD", '(GLD OR "gold ETF")'),
    ("TSLA", "(TSLA OR Tesla)"),
]
TS = "&startdatetime=20190101000000&enddatetime=20190131235959"


def probe_one(sym, query):
    url = API + "?query=" + urllib.parse.quote(query) + "&mode=TimelineVol&format=json&sourcelang=eng" + TS
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read().decode("utf-8", "replace")
            status = r.status
        dt = time.time() - t0
        has_tl = '"timeline"' in body
        return f"{sym}: HTTP {status} has_timeline={has_tl} ({dt:.1f}s)"
    except Exception as e:
        return f"{sym}: EXC {type(e).__name__} {str(e)[:90]} ({time.time()-t0:.1f}s)"


if __name__ == "__main__":
    import sys
    spacing = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    print(f"spacing={spacing}s", flush=True)
    for i, (sym, q) in enumerate(SYM_Q):
        print(probe_one(sym, q), flush=True)
        if i < len(SYM_Q) - 1:
            time.sleep(spacing)
    print("TOLERANCE PROBE DONE", flush=True)