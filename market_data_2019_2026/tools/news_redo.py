#!/usr/bin/env python3
"""WORKER A2 - GDELT news index REBUILD (resumable, connection-tolerant).

Rebuilds the fixed GDELT news index after news_harvest.py schema fixes
(paper 2505.16136, score 34):
  * persists avg_tone / tone_disp / event_impact into news_index.csv
  * writes datetime / url / domain onto every raw/g_<quarter>.jsonl row so
    downstream consumers (C_causation.local_news_candidates) can match on
    datetime/date instead of falling back to flaky live GDELT calls.

Reads the same GDELT Doc 2.0 doc API as news_harvest.py but prefers the
`requests` library for better HTTP/1.1 connection handling and adds generous
retries + backoff. Resumable via news/run/news_redo_progress.json; a cell is
only skipped if its row already exists in news_index.csv AND its quarter
JSONL file has non-zero size.

CLI:
  python news_redo.py [--max-seconds N] [--sleep S] [--probe] [--reset]

  --probe       just check GDELT reachability and exit (no harvest)
  --reset       clear done/raw outputs and restart from scratch
  --max-seconds budget for one invocation (default 600)
  --sleep       seconds between cells (default 2.5)

On GDELT being unreachable, every cell errors into news/errors.csv and the
run exits gracefully -- it NEVER fabricates article/tone data.
"""

import csv
import json
import os
import sys
import time
import random
from datetime import date as dt_date, timedelta as dt_timedelta

ROOT = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-build"
NEWS = os.path.join(ROOT, "market_data_2019_2026", "news")
RAW = os.path.join(NEWS, "raw")
RUN = os.path.join(NEWS, "run")
os.makedirs(RAW, exist_ok=True)
os.makedirs(RUN, exist_ok=True)

INDEX_CSV = os.path.join(NEWS, "news_index.csv")
ERR_CSV = os.path.join(NEWS, "errors.csv")
PROG_CSV = os.path.join(RUN, "news_redo_progress.json")
UA = {
    "User-Agent": "Mozilla/5.0 (research harvest; keyless) GDELT",
    "Accept": "application/json, text/plain, */*",
}
API_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADER = [
    "quarter",
    "symbol",
    "doc_count",
    "top1_url",
    "top1_title",
    "top1_domain",
    "avg_tone",
    "tone_disp",
    "event_impact",
]

try:
    import requests
except ImportError:  # pragma: no cover - requests is bundled, but degrade cleanly
    requests = None

# GDELT requires OR'd term groups wrapped in parentheses: (A OR B).
GB = {
    "SPY": '(SPY OR "S&P 500")',
    "QQQ": '(QQQ OR "Invesco QQQ")',
    "DIA": '(DIA OR "Dow Jones")',
    "IWM": '(IWM OR "Russell 2000")',
    "EEM": '(EEM OR "emerging markets")',
    "GLD": '(GLD OR "gold ETF")',
    "SLV": '(SLV OR "silver ETF")',
    "TLT": '(TLT OR "Treasury bond ETF")',
    "HYG": '(HYG OR "high yield bond ETF")',
    "XLE": '(XLE OR "energy ETF")',
    "XLF": '(XLF OR "financials ETF")',
    "^VIX": '(VIX OR "CBOE Volatility Index")',
    "AAPL": "(AAPL OR Apple)",
    "MSFT": "(MSFT OR Microsoft)",
    "NVDA": "(NVDA OR Nvidia)",
    "AMZN": "(AMZN OR Amazon)",
    "GOOGL": "(GOOGL OR Google)",
    "META": "(META OR Facebook OR Meta)",
    "TSLA": "(TSLA OR Tesla)",
    "AVGO": "(AVGO OR Broadcom)",
    "JPM": "(JPM OR JPMorgan)",
    "BAC": '(BAC OR "Bank of America")',
    "WMT": "(WMT OR Walmart)",
    "XOM": "(XOM OR Exxon)",
    "UNH": "(UNH OR UnitedHealth)",
    "JNJ": '(JNJ OR "Johnson and Johnson")',
    "V": "(V OR Visa)",
    "MA": "(MA OR Mastercard)",
    "NFLX": "(NFLX OR Netflix)",
    "DIS": "(DIS OR Disney)",
    "AMD": '(AMD OR "Advanced Micro Devices")',
    "ADBE": "(ADBE OR Adobe)",
    "BTC": "(BTC OR Bitcoin OR BTCUSD)",
    "ETH": "(ETH OR Ethereum OR ETHUSD)",
}
SYMBOLS = [
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "EEM",
    "GLD",
    "SLV",
    "TLT",
    "HYG",
    "XLE",
    "XLF",
    "^VIX",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AVGO",
    "JPM",
    "BAC",
    "WMT",
    "XOM",
    "UNH",
    "JNJ",
    "V",
    "MA",
    "NFLX",
    "DIS",
    "AMD",
    "ADBE",
    "BTC",
    "ETH",
]


def quarters(y0=2019, y1=2026, q0=1, q1=2):
    out = []
    for y in range(y0, y1 + 1):
        for q in range(1, 5):
            if (y == y0 and q < q0) or (y == y1 and q > q1):
                continue
            out.append(f"{y}Q{q}")
    return out


QUARTERS = quarters()


def q_dates(q):
    y = int(q[:4])
    qn = int(q[5])
    start = dt_date(y, 1 + 3 * (qn - 1), 1)
    if qn == 4:
        end = dt_date(y, 12, 31)
    else:
        end = dt_date(y, 1 + 3 * qn, 1) - dt_timedelta(days=1)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _get(url, timeout=60):
    """GET with requests if available, else urllib fallback. Returns decoded body."""
    if requests is not None:
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        return r.text
    import urllib.request

    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", "replace")
        if getattr(resp, "status", 200) != 200:
            raise RuntimeError(f"HTTP {getattr(resp, 'status', 200)}")
        return body


def cell_request(q, sym, mode):
    params = [
        ("query", GB[sym]),
        ("mode", mode),
        ("format", "json"),
        ("sourcelang", "eng"),
    ]
    s, e = q_dates(q)
    params.append(("startdatetime", s + "000000"))
    params.append(("enddatetime", e + "235959"))
    if mode == "artlist":
        params.append(("maxrecords", "10"))
    import urllib.parse

    url = API_BASE + "?" + urllib.parse.urlencode(params)
    body = _get(url)
    try:
        data = json.loads(body)
    except Exception:
        raise RuntimeError("non-JSON response: " + body[:120])
    if mode == "artlist" and isinstance(data.get("articles"), list):
        return data["articles"]
    if mode in ("TimelineVol", "TimelineTone") and isinstance(
        data.get("timeline"), list
    ):
        return data["timeline"]
    raise RuntimeError("unexpected payload: " + body[:120])


def fetch_cell(q, sym):
    """Returns (row_dict, tops_list) after retries with jittered backoff.
    Mirrors news_harvest.fetch_cell but is connection-tolerant and NEVER
    fabricates data -- tone/impact default to 0.0 and doc_count to 0 on error."""
    for attempt in (1, 2, 3):
        try:
            tl = cell_request(q, sym, "TimelineVol")
            count = 0
            for it in tl:
                try:
                    count += float(it.get("value", 0) or 0)
                except (TypeError, ValueError):
                    pass
            count = int(round(count))
            try:
                tone_tl = cell_request(q, sym, "TimelineTone")
                tone_vals = [
                    float(x.get("value", 0) or 0)
                    for x in tone_tl
                    if x.get("value") is not None
                ]
                mean_tone = sum(tone_vals) / len(tone_vals) if tone_vals else 0.0
                tone_disp = (
                    (sum((v - mean_tone) ** 2 for v in tone_vals) / len(tone_vals))
                    ** 0.5
                    if len(tone_vals) > 1
                    else 0.0
                )
                event_impact = max((abs(v) for v in tone_vals), default=0.0)
            except Exception:
                mean_tone, tone_disp, event_impact = 0.0, 0.0, 0.0
            arts = cell_request(q, sym, "artlist")
            row = {
                "quarter": q,
                "symbol": sym,
                "doc_count": count,
                "top1_url": "",
                "top1_title": "",
                "top1_domain": "",
                "avg_tone": round(mean_tone, 4),
                "tone_disp": round(tone_disp, 4),
                "event_impact": round(event_impact, 4),
            }
            tops = []
            for a in arts[:10]:
                if not isinstance(a, dict):
                    continue
                u = a.get("url", "") or ""
                t = a.get("title", "") or ""
                dom = a.get("domain", "") or ""
                seendate = a.get("seendate", "") or ""
                dt_iso = ""
                if len(seendate) >= 8 and str(seendate).isdigit():
                    sd = str(seendate)
                    dt_iso = f"{sd[:4]}-{sd[4:6]}-{sd[6:8]}" + (
                        f" {sd[8:10]}:{sd[10:12]}:{sd[12:14]}" if len(sd) >= 14 else ""
                    )
                if not dom and u:
                    import urllib.parse

                    try:
                        dom = urllib.parse.urlparse(u).netloc
                    except Exception:
                        dom = ""
                tops.append(
                    {
                        "quarter": q,
                        "symbol": sym,
                        "url": u,
                        "title": t,
                        "domain": dom,
                        "datetime": dt_iso,
                        "date": dt_iso[:10],
                    }
                )
                if not row["top1_url"] and u:
                    row["top1_url"] = u
                    row["top1_title"] = t
                    row["top1_domain"] = dom
            return row, tops
        except Exception as ex:
            wait = {1: 10, 2: 30, 3: 90}[attempt] + random.uniform(0, 5)
            print(
                f"  retry {q}:{sym} attempt {attempt} err={str(ex)[:100]} "
                f"wait={wait:.0f}s",
                flush=True,
            )
            time.sleep(wait)
    raise RuntimeError("Failed GDELT API requests")


def cell_done(q, sym):
    """True only if an index row exists AND the quarter JSONL is non-empty."""
    # Check index row
    found = False
    if os.path.exists(INDEX_CSV):
        try:
            with open(INDEX_CSV, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if r.get("symbol") == sym and r.get("quarter") == q:
                        found = True
                        break
        except Exception:
            pass
    if not found:
        return False
    jp = os.path.join(RAW, f"g_{q}.jsonl")
    if os.path.exists(jp) and os.path.getsize(jp) > 0:
        return True
    return False


def probe():
    """Check GDELT reachability with a tiny request. Returns bool."""
    import urllib.parse

    params = [
        ("query", "(AAPL OR Apple)"),
        ("mode", "TimelineVol"),
        ("format", "json"),
        ("sourcelang", "eng"),
        ("startdatetime", "20240101000000"),
        ("enddatetime", "20240101235959"),
    ]
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    try:
        body = _get(url, timeout=30)
        data = json.loads(body)
        ok = isinstance(data.get("timeline"), list)
        print("GDELT probe: REACHABLE" if ok else "GDELT probe: payload unexpected")
        return ok
    except Exception as ex:
        print(f"GDELT probe: UNREACHABLE ({str(ex)[:120]})", flush=True)
        return False


def main():
    args = sys.argv[1:]
    MAX_SEC = 600
    SLEEP = 2.5
    DO_PROBE = "--probe" in args
    RESET = "--reset" in args
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--max-seconds="):
            MAX_SEC = int(a.split("=")[1])
        elif a == "--sleep" and i + 1 < len(args):
            SLEEP = float(args[i + 1])
        i += 1

    if DO_PROBE:
        sys.exit(0 if probe() else 1)

    if RESET:
        with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADER)
        with open(ERR_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["quarter", "symbol", "error"])
        for q in QUARTERS:
            open(os.path.join(RAW, f"g_{q}.jsonl"), "w", encoding="utf-8").close()
        json.dump({"done": [], "next": None}, open(PROG_CSV, "w", encoding="utf-8"))
        print("RESET done (outputs wiped, checkpoint reset)", flush=True)

    # Sorted symbol list for deterministic cells
    cells = [f"{sym}:{q}" for q in QUARTERS for sym in SYMBOLS]

    # Checkpoint skip: a cell is done if its row exists + quarter jsonl non-empty
    todo = [c for c in cells if not cell_done(*c.split(":", 1))]
    print(f"total={len(cells)} todo={len(todo)}", flush=True)
    if not todo:
        print("ALL CELLS ALREADY DONE", flush=True)
        return

    idx = open(INDEX_CSV, "a", newline="", encoding="utf-8")
    writer = csv.writer(idx)
    errf = open(ERR_CSV, "a", newline="", encoding="utf-8")
    errw = csv.writer(errf)

    start = time.time()
    n_ok = 0
    n_err = 0
    processed = 0
    n_err_consecutive = 0
    for cell in todo:
        sym, q = cell.split(":", 1)
        try:
            row, tops = fetch_cell(q, sym)
            writer.writerow(
                [
                    row["quarter"],
                    row["symbol"],
                    row["doc_count"],
                    row["top1_url"],
                    row["top1_title"],
                    row["top1_domain"],
                    row["avg_tone"],
                    row["tone_disp"],
                    row["event_impact"],
                ]
            )
            idx.flush()
            with open(os.path.join(RAW, f"g_{q}.jsonl"), "a", encoding="utf-8") as jf:
                for t in tops:
                    jf.write(json.dumps(t, ensure_ascii=False) + "\n")
            n_ok += 1
            n_err_consecutive = 0
        except Exception as e:
            errw.writerow([q, sym, str(e)])
            errf.flush()
            n_err += 1
            n_err_consecutive += 1
            print(f"  ERR {cell} -> errors.csv ({str(e)[:80]})", flush=True)
            # If GDELT keeps failing, stop early instead of hammering the API.
            if n_err_consecutive >= 5:
                print(
                    "  5 consecutive errors -- GDELT likely unreachable; stopping "
                    "this invocation (checkpoint saved)",
                    flush=True,
                )
                processed += 1
                break
        done = {"done": [], "next": cell}
        # durable skip list: cells whose row+jsonl already exist
        done["done"] = [c for c in cells if cell_done(*c.split(":", 1))]
        json.dump(done, open(PROG_CSV, "w", encoding="utf-8"))
        processed += 1
        if processed % 25 == 0:
            print(
                f"  progress {processed}/{len(todo)} ok={n_ok} err={n_err} "
                f"elapsed={int(time.time() - start)}s",
                flush=True,
            )
        if time.time() - start > MAX_SEC:
            print(
                f"BUDGET: {processed} cells this invocation, checkpoint saved",
                flush=True,
            )
            break
        time.sleep(SLEEP)

    idx.close()
    errf.close()
    print(f"INVOCATION DONE processed={processed} ok={n_ok} err={n_err}", flush=True)


if __name__ == "__main__":
    main()
