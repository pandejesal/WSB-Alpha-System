#!/usr/bin/env python3
"""WORKER A - GDELT news index harvest (resumable, throttled) - FIXED build.

For each of 34 symbols x 30 quarters (2019Q1..2026Q2):
  1) TimelineVol -> doc_count (sum of timeline values)
  2) artlist (top 10) -> top1 url/title/domain
Writes:
  news/news_index.csv            one row per cell (failed cells -> errors.csv, no index row)
  news/raw/g_<quarter>.jsonl     per quarter: every fetched top-doc row
  news/run/news_progress.json    {"done":[...], "next":...}
  news/errors.csv                quarter,symbol,error after 3 tries (backoff 30/60/120)
CLI:
  python news_harvest.py [--rebuild] [--max-seconds N] [--sleep S]
"""
import csv
import json
import os
import sys
import time
from datetime import date as dt_date, timedelta as dt_timedelta
import urllib.parse
import urllib.request

ROOT = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-build"
NEWS = os.path.join(ROOT, "market_data_2019_2026", "news")
RAW  = os.path.join(NEWS, "raw")
RUN  = os.path.join(NEWS, "run")
os.makedirs(RAW, exist_ok=True)
os.makedirs(RUN, exist_ok=True)

INDEX_CSV = os.path.join(NEWS, "news_index.csv")
ERR_CSV   = os.path.join(NEWS, "errors.csv")
PROG_CSV  = os.path.join(RUN, "news_progress.json")
UA        = {"User-Agent": "Mozilla/5.0 (research harvest; keyless) GDELT"}
API_BASE  = "https://api.gdeltproject.org/api/v2/doc/doc"

# NOTE: GDELT requires OR'd term groups to be wrapped in parentheses: (A OR B).
GB = {
    "SPY": '(SPY OR "S&P 500")',            "QQQ": '(QQQ OR "Invesco QQQ")',
    "DIA": '(DIA OR "Dow Jones")',          "IWM": '(IWM OR "Russell 2000")',
    "EEM": '(EEM OR "emerging markets")',   "GLD": '(GLD OR "gold ETF")',
    "SLV": '(SLV OR "silver ETF")',         "TLT": '(TLT OR "Treasury bond ETF")',
    "HYG": '(HYG OR "high yield bond ETF")', "XLE": '(XLE OR "energy ETF")',
    "XLF": '(XLF OR "financials ETF")',     "^VIX": '(VIX OR "CBOE Volatility Index")',
    "AAPL": '(AAPL OR Apple)',              "MSFT": '(MSFT OR Microsoft)',
    "NVDA": '(NVDA OR Nvidia)',             "AMZN": '(AMZN OR Amazon)',
    "GOOGL": '(GOOGL OR Google)',           "META": '(META OR Facebook OR Meta)',
    "TSLA": '(TSLA OR Tesla)',              "AVGO": '(AVGO OR Broadcom)',
    "JPM": '(JPM OR JPMorgan)',             "BAC": '(BAC OR "Bank of America")',
    "WMT": '(WMT OR Walmart)',              "XOM": '(XOM OR Exxon)',
    "UNH": '(UNH OR UnitedHealth)',         "JNJ": '(JNJ OR "Johnson and Johnson")',
    "V": '(V OR Visa)',                     "MA": '(MA OR Mastercard)',
    "NFLX": '(NFLX OR Netflix)',            "DIS": '(DIS OR Disney)',
    "AMD": '(AMD OR "Advanced Micro Devices")', "ADBE": '(ADBE OR Adobe)',
    "BTC": '(BTC OR Bitcoin OR BTCUSD)',    "ETH": '(ETH OR Ethereum OR ETHUSD)',
}
SYMBOLS = [
    "SPY","QQQ","DIA","IWM","EEM","GLD","SLV","TLT","HYG","XLE","XLF","^VIX",
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AVGO","JPM","BAC","WMT","XOM",
    "UNH","JNJ","V","MA","NFLX","DIS","AMD","ADBE","BTC","ETH",
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

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", "replace")
        status = getattr(r, "status", 200)
    if status != 200:
        raise RuntimeError(f"HTTP {status}")
    return body

def cell_request(q, sym, mode):
    params = [("query", GB[sym]), ("mode", mode), ("format", "json"),
              ("sourcelang", "eng")]
    s, e = q_dates(q)
    params.append(("startdatetime", s + "000000"))
    params.append(("enddatetime", e + "235959"))
    if mode == "artlist":
        params.append(("maxrecords", "10"))
    url = API_BASE + "?" + urllib.parse.urlencode(params)
    body = get(url)
    try:
        data = json.loads(body)
    except Exception:
        raise RuntimeError("non-JSON response: " + body[:120])
    if mode == "artlist" and isinstance(data.get("articles"), list):
        return data["articles"]
    if mode in ("TimelineVol", "TimelineTone", "TimelineLangDist") and isinstance(data.get("timeline"), list):
        return data["timeline"]
    if mode == "TimelineVol" and isinstance(data.get("timeline"), list):
        return data["timeline"]
    raise RuntimeError("unexpected payload: " + body[:120])

def fetch_cell(q, sym):
    """Returns (row_dict, tops_list) after up to 3 tries with 30/60/120 backoff. Fixed TimelineVol float aggregation and Tone capture (paper 2505.16136)."""
    for attempt in (1, 2, 3):
        try:
            tl = cell_request(q, sym, "TimelineVol")
            count = 0.0
            for it in tl:
                try:
                    # Fix: value may be float string; sum as float then int
                    count += float(it.get("value", 0) or 0)
                except (TypeError, ValueError):
                    pass
            count = int(round(count))
            # Tone for FinBERT daily indices (mean tone, dispersion) per 2505.16136
            try:
                tone_tl = cell_request(q, sym, "TimelineTone")
                tone_vals = [float(x.get("value", 0) or 0) for x in tone_tl if x.get("value") is not None]
                mean_tone = sum(tone_vals)/len(tone_vals) if tone_vals else 0.0
                tone_disp = (sum((v-mean_tone)**2 for v in tone_vals)/len(tone_vals))**0.5 if len(tone_vals)>1 else 0.0
                # eventImpact (paper 2505.16136): peak absolute tonal intensity over the window,
                # a robust proxy for the magnitude of the strongest sentiment event in the quarter.
                event_impact = max((abs(v) for v in tone_vals), default=0.0)
            except Exception:
                mean_tone, tone_disp, event_impact = 0.0, 0.0, 0.0
            arts = cell_request(q, sym, "artlist")
            row = {"quarter": q, "symbol": sym, "doc_count": count,
                   "top1_url": "", "top1_title": "", "top1_domain": "",
                   "avg_tone": round(mean_tone, 4),
                   "tone_disp": round(tone_disp, 4),
                   "event_impact": round(event_impact, 4)}
            tops = []
            for a in arts[:10]:
                if not isinstance(a, dict):
                    continue
                u = a.get("url", "") or ""
                t = a.get("title", "") or ""
                dom = a.get("domain", "") or ""
                # GDELT Doc 2.0 'seendate' is YYYYMMDDHHMMSS -> ISO for downstream consumers
                seendate = a.get("seendate", "") or ""
                dt_iso = ""
                if len(seendate) >= 8 and seendate.isdigit():
                    dt_iso = (f"{seendate[:4]}-{seendate[4:6]}-{seendate[6:8]}"
                              + (f" {seendate[8:10]}:{seendate[10:12]}:{seendate[12:14]}"
                                 if len(seendate) >= 14 else ""))
                if not dom and u:
                    try:
                        dom = urllib.parse.urlparse(u).netloc
                    except Exception:
                        dom = ""
                tops.append({"quarter": q, "symbol": sym, "url": u,
                             "title": t, "domain": dom,
                             "datetime": dt_iso, "date": dt_iso[:10]})
                if not row["top1_url"] and u:
                    row["top1_url"] = u
                    row["top1_title"] = t
                    row["top1_domain"] = dom
            return row, tops
        except Exception as ex:
            wait = {1: 30, 2: 60, 3: 120}[attempt]
            print(f"  retry {q}:{sym} attempt {attempt} err={str(ex)[:100]} wait={wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("Failed GDELT API requests")

def main():
    args = sys.argv[1:]
    REBUILD = "--rebuild" in args
    MAX_SEC = 600
    SLEEP = 2.5
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--max-seconds="):
            MAX_SEC = int(a.split("=")[1])
        elif a == "--sleep" and i + 1 < len(args):
            SLEEP = float(args[i + 1])
        i += 1

    if REBUILD:
        with open(INDEX_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["quarter","symbol","doc_count","top1_url","top1_title","top1_domain","avg_tone","tone_disp","event_impact"])
        with open(ERR_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["quarter","symbol","error"])
        for q in QUARTERS:
            open(os.path.join(RAW, f"g_{q}.jsonl"), "w", encoding="utf-8").close()
        json.dump({"done": [], "next": None}, open(PROG_CSV, "w", encoding="utf-8"))
        print("REBUILD done (outputs wiped, checkpoint reset)", flush=True)

    prog = {"done": []}
    if os.path.exists(PROG_CSV):
        try:
            prog = json.load(open(PROG_CSV, encoding="utf-8"))
        except Exception:
            prog = {"done": []}
    done = set(prog.get("done", []))

    cells = [f"{s}:{q}" for q in QUARTERS for s in SYMBOLS]
    todo = [c for c in cells if c not in done]
    print(f"total={len(cells)} done={len(done)} todo={len(todo)}", flush=True)
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
    for cell in todo:
        sym, q = cell.split(":", 1)
        try:
            row, tops = fetch_cell(q, sym)
            writer.writerow([row["quarter"], row["symbol"], row["doc_count"],
                             row["top1_url"], row["top1_title"], row["top1_domain"],
                             row["avg_tone"], row["tone_disp"], row["event_impact"]])
            idx.flush()
            with open(os.path.join(RAW, f"g_{q}.jsonl"), "a", encoding="utf-8") as jf:
                for t in tops:
                    jf.write(json.dumps(t, ensure_ascii=False) + "\n")
            n_ok += 1
        except Exception as e:
            errw.writerow([q, sym, str(e)])
            errf.flush()
            n_err += 1
            print(f"  ERR {cell} -> errors.csv ({str(e)[:80]})", flush=True)
        done.add(cell)
        json.dump({"done": sorted(done), "next": cell},
                  open(PROG_CSV, "w", encoding="utf-8"))
        processed += 1
        if processed % 25 == 0:
            print(f"  progress {processed}/{len(todo)} ok={n_ok} err={n_err} "
                  f"elapsed={int(time.time()-start)}s", flush=True)
        if time.time() - start > MAX_SEC:
            print(f"BUDGET: {processed} cells this invocation, checkpoint saved", flush=True)
            break
        time.sleep(SLEEP)

    idx.close()
    errf.close()
    print(f"INVOCATION DONE processed={processed} ok={n_ok} err={n_err}", flush=True)

if __name__ == "__main__":
    main()