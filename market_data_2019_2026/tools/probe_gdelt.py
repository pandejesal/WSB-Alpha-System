#!/usr/bin/env python3
"""WORKER A - GDELT connectivity probe. Prints HTTP status + sample payload preview.
Probes mode=TimelineVol (counts) and mode=artlist (top docs) for a tiny quarter."""
import json, sys, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (research harvest; keyless) GDELT"}
API = "https://api.gdeltproject.org/api/v2/doc/doc"
Q = urllib.parse.quote('SPY OR "S&P 500"')
TS = "&startdatetime=20190101000000&enddatetime=20190131235959"


def hit(url, expect):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read().decode("utf-8", "replace")
            status = getattr(r, "status", 200)
        print(f"  HTTP {status} bytes={len(body)}")
        if status != 200:
            print("  BODY:", body[:200])
            return False
        try:
            data = json.loads(body)
        except Exception as e:
            print("  NON-JSON:", body[:200])
            return False
        print("  TOP KEYS:", list(data.keys())[:10])
        if expect == "timeline" and "timeline" in data:
            vals = [it.get("value", 0) for it in data["timeline"]]
            print("  timeline entries:", len(data["timeline"]), "sample values:", vals[:5])
            return True
        elif expect == "articles" and "articles" in data:
            art = data["articles"]
            print("  articles:", len(art), "sample0:", art[0] if art else None)
            return True
        else:
            print("  payload keys mismatch for expected", expect, "->", body[:200])
            return False
    except Exception as e:
        print("  EXC:", type(e).__name__, str(e)[:200])
        return False


if __name__ == "__main__":
    tl = hit(API + "?query=" + Q + "&mode=TimelineVol&format=json&sourcelang=eng" + TS, "timeline")
    art = hit(API + "?query=" + Q + "&mode=artlist&format=json&sourcelang=eng&maxrecords=10" + TS, "articles")
    print("RESULT:", "OK" if (tl and art) else "FAIL", flush=True)
    sys.exit(0 if (tl and art) else 1)