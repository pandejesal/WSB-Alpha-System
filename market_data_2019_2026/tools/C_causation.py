#!/usr/bin/env python3
"""WORKER C - Causation join over kept anomaly events.

For each event in events_all.json:
  - window = [date-3d, date+3d]
  - prefer local news\\raw\\g_<quarter>.jsonl rows with matching symbol and
    datetime in window; files are expected to be empty/absent here, so the
    GDELT artlist fallback is used.
  - AT MOST ONE GDELT artlist request per event (parenthesized query
    "(SYM OR Name)"), mode=artlist, maxrecords=8, format=json,
    startdatetime/enddatetime in YYYYMMDDHHMMSS, sourcelang=eng, pacing 2.5s.
  - on failure/empty -> verdict NO_CLEAR_SOURCE, confidence LOW. NEVER
    fabricate URLs/titles.
Writes ONE md per event into causation/reports/<symbol>_<date>.md and
causation/causation_index.json (one row per kept event).
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # market_data_2019_2026
NEWS_RAW = os.path.join(ROOT, "news", "raw")
OHLCV_DIR = os.path.join(ROOT, "ohlcv")
OUT_DIR = os.path.join(ROOT, "causation")
REPORT_DIR = os.path.join(OUT_DIR, "reports")
EVENTS = os.path.join(ROOT, "events", "events_all.json")
INSTRUMENTS_CSV = os.path.join(OHLCV_DIR, "instruments.csv")
PACING = 2.5


def quarter_of(ymd):
    y, m, _ = ymd.split("-")
    q = (int(m) - 1) // 3 + 1
    return f"{y}Q{q}"


def gb_dt(dt):
    return dt.strftime("%Y%m%d%H%M%S")


def load_ohlcv_rows(symbol):
    path = os.path.join(OHLCV_DIR, symbol + ".csv")
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                rows.append(
                    {
                        "date": row["date"].strip(),
                        "open": row.get("open", ""),
                        "high": row.get("high", ""),
                        "low": row.get("low", ""),
                        "close": row.get("close", ""),
                        "volume": row.get("volume", ""),
                    }
                )
            except (ValueError, KeyError):
                continue
    rows.sort(key=lambda r: r["date"])
    return rows


def local_news_candidates(symbol, start_dt, end_dt):
    """Return rows from news/raw/g_<quarter>.jsonl for the window quarter."""
    q = quarter_of(start_dt.strftime("%Y-%m-%d"))
    path = os.path.join(NEWS_RAW, f"g_{q}.jsonl")
    if not os.path.exists(path):
        return []
    cands = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("symbol", "")).strip() != symbol:
                continue
            dt_raw = row.get("datetime", row.get("date", ""))
            if dt_raw:
                try:
                    t = datetime.strptime(str(dt_raw)[:10], "%Y-%m-%d")
                except ValueError:
                    continue
                if not (start_dt <= t <= end_dt):
                    continue
            cands.append(row)
    cands.sort(key=lambda r: str(r.get("datetime", r.get("date", ""))))
    return cands


def gdelt_artlist(symbol, name, start_dt, end_dt):
    """One GDELT artlist request. Returns list of dicts, or None on failure."""
    sym_term = symbol.lstrip("^")
    name_clean = name.replace('"', "").replace(",", "")
    query = f"({sym_term} OR \"{name_clean}\")"
    qs = urllib.parse.urlencode(
        {
            "query": query,
            "mode": "artlist",
            "maxrecords": "8",
            "format": "json",
            "startdatetime": gb_dt(start_dt),
            "enddatetime": gb_dt(end_dt),
            "sourcelang": "eng",
        }
    )
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + qs
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WSB-Alpha-WorkerC/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return None
    arts = data.get("articles") or []
    out = []
    for a in arts:
        out.append(
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "datetime": a.get("seendate", ""),
                "domain": a.get("domain", ""),
            }
        )
    return out


def classify(cands, symbol, name):
    if not cands:
        return "NO_CLEAR_SOURCE", "LOW", "no news candidate found in window"
    alive = [c for c in cands if c.get("title", "").strip()]
    if not alive:
        return "NO_CLEAR_SOURCE", "LOW", "candidate rows lacked titles"
    name_l = name.lower()
    sym_l = symbol.lstrip("^").lower()
    tokens = set(w for w in (name_l + " " + sym_l).split() if len(w) > 3)
    hits = 0
    for c in alive[:3]:
        tl = c.get("title", "").lower()
        if any(t in tl for t in tokens):
            hits += 1
    if hits >= 2:
        return "LIKELY_DRIVER", "HIGH", "top candidates directly reference the instrument"
    if hits >= 1:
        return "LIKELY_DRIVER", "MED", "top candidate plausibly relates to the instrument"
    if len(alive) <= 2:
        return "MIXED", "LOW", "few weak/unrelated candidates in window"
    return "MIXED", "MED", "multiple candidates without clear driver"


def main():
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(EVENTS, "r", encoding="utf-8") as f:
        events = json.load(f)

    instruments = {}
    with open(INSTRUMENTS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            instruments[row["symbol"].strip()] = row.get("note", "").strip()

    index_rows = []
    failures = 0
    for i, ev in enumerate(events):
        sym = ev["symbol"]
        ymd = ev["date"]
        start_dt = datetime.strptime(ymd, "%Y-%m-%d") - timedelta(days=3)
        end_dt = datetime.strptime(ymd, "%Y-%m-%d") + timedelta(days=3)
        end_dt = end_dt.replace(hour=23, minute=59, second=59)

        cands = local_news_candidates(sym, start_dt, end_dt)
        if not cands:
            time.sleep(PACING)
            cands = gdelt_artlist(sym, instruments.get(sym, sym), start_dt, end_dt)
            if cands is None:
                cands = []
                failures += 1

        verdict, conf, rationale = classify(cands, sym, instruments.get(sym, sym))

        bars = load_ohlcv_rows(sym)
        idx = next((k for k, b in enumerate(bars) if b["date"] == ymd), -1)
        ctx = bars[max(0, idx - 5): idx + 6] if idx >= 0 else bars[-11:]

        md = [
            f"# Causation report — {sym} {ymd}",
            "",
            f"- symbol: {sym}",
            f"- date: {ymd}",
            f"- z: {ev['z']:.3f}",
            f"- r: {ev['r'] * 100:.2f}%",
            f"- sigma20: {ev['sigma20']:.5f}",
            f"- threshold_hit: {ev['threshold_hit']}",
            "",
            "## Price context (+/- 5 bars)",
            "",
            "| date | open | high | low | close | volume |",
            "|---|---|---|---|---|---|",
        ]
        for b in ctx:
            md.append(f"| {b['date']} | {b['open']} | {b['high']} | {b['low']} | {b['close']} | {b['volume']} |")

        md += ["", "## Candidate news (top <= 8)", ""]
        for c in cands[:8]:
            md.append(f"- **{c.get('title', '').strip()}**")
            md.append(f"  - domain: {c.get('domain', '').strip()}")
            md.append(f"  - url: {c.get('url', '').strip()}")
            md.append(f"  - datetime: {c.get('datetime', '').strip()}")
        md += [
            "",
            f"- verdict: {verdict}",
            f"- confidence: {conf}",
            f"- rationale: {rationale}",
            "",
        ]

        fname = f"{sym}_{ymd}.md".replace("/", "_").replace(":", "_")
        with open(os.path.join(REPORT_DIR, fname), "w", encoding="utf-8") as f:
            f.write("\n".join(md))

        top1 = cands[:1]
        index_rows.append(
            {
                "symbol": sym,
                "date": ymd,
                "z": ev["z"],
                "verdict": verdict,
                "confidence": conf,
                "top1_title": top1[0].get("title", "").strip() if top1 else "",
                "top1_domain": top1[0].get("domain", "").strip() if top1 else "",
            }
        )
        if (i + 1) % 20 == 0:
            print(f"progress {i + 1}/{len(events)}")

    with open(os.path.join(OUT_DIR, "causation_index.json"), "w", encoding="utf-8") as f:
        json.dump(index_rows, f, indent=2)

    print(f"REPORTS: {len(index_rows)} | EVENTS: {len(events)} | FAILED_REQS: {failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())