import os
import re
import sys
import time
import json
import csv
import random
import urllib.parse
import xml.etree.ElementTree as ET

import requests

BASE_DIR = r"C:\Users\DELL\Documents\Default Project\WSB-Alpha-System-latest"
MARKET_DIR = os.path.join(BASE_DIR, "market_data_2019_2026", "institutions")
FH_DIR = os.path.join(MARKET_DIR, "13f")
CACHE_DIR = os.path.join(BASE_DIR, "cache", "13f")
RUNLOG_DIR = os.path.join(BASE_DIR, "launch", "runlog")
STATE_PATH = os.path.join(RUNLOG_DIR, "B.state.json")
DONE_PATH = os.path.join(RUNLOG_DIR, "B.done")
TICKERS_PATH = os.path.join(BASE_DIR, "cache", "company_tickers.json")
FUNDS_CSV = os.path.join(MARKET_DIR, "13f_funds.csv")
ISSUES_CSV = os.path.join(MARKET_DIR, "13f_issues.csv")

HEADERS = {"User-Agent": "WSBAlphaSystemAdmin AdminContact@wsbalphasystem.com"}
MIN_SLEEP, MAX_SLEEP = 1.0, 1.35
SEARCH_SLEEP = 3.2
QR_DISPLAY = ["2019Q1", "2019Q2", "2019Q3", "2019Q4", "2020Q1", "2020Q2", "2020Q3", "2020Q4",
              "2021Q1", "2021Q2", "2021Q3", "2021Q4", "2022Q1", "2022Q2", "2022Q3", "2022Q4",
              "2023Q1", "2023Q2", "2023Q3", "2023Q4", "2024Q1", "2024Q2", "2024Q3", "2024Q4",
              "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2"]
CUTOFF_DATE = "2026-08-09"

# FUNDS.md (run-2026-08-10 archive): 40 resolved flagship 13F filers; CIK re-verified against EDGAR at runtime.
FUNDS = [
    ("renaissance", "Renaissance Technologies LLC", "0001037389"),
    ("bridgewater", "Bridgewater Associates LP", "0001350694"),
    ("point72", "Point72 Asset Management LP", "0001603466"),
    ("citadel", "Citadel Advisors LLC", "0001423053"),
    ("millennium", "Millennium Management LLC", "0001278384"),
    ("tiger_global", "Tiger Global Management LLC", "0001383792"),
    ("soros", "Soros Fund Management LLC", "0001029160"),
    ("aqr", "AQR Capital Management LLC", "0001167557"),
    ("de_shaw", "D.E. Shaw & Co. LP", "0001009207"),
    ("two_sigma", "Two Sigma Investments, LP", "0001179392"),
    ("viking", "Viking Global Investors LP", "0001103804"),
    ("lone_pine", "Lone Pine Capital LLC", "0001061165"),
    ("pershing_square", "Pershing Square Capital Management LP", "0001336528"),
    ("appaloosa", "Appaloosa LP", "0001656456"),
    ("coatue", "Coatue Management LLC", "0001135761"),
    ("third_point", "Third Point LLC", "0001104188"),
    ("tci", "TCI Fund Management Ltd", "0001647251"),
    ("berkshire", "Berkshire Hathaway Inc", "0001067983"),
    ("greenlight", "Greenlight Capital Inc", "0001079112"),
    ("baupost", "Baupost Group LLC", "0001061768"),
    ("elliott", "Elliott Investment Management L.P.", "0001791786"),
    ("valueact", "ValueAct Holdings LP", "0001418814"),
    ("canyon", "Canyon Capital Advisors LLC", "0001053158"),
    ("farallon", "Farallon Capital Management LLC", "0001033230"),
    ("magnetar", "Magnetar Financial LLC", "0001362985"),
    ("king_street", "King Street Capital Management LP", "0001218199"),
    ("davidson_kempner", "Davidson Kempner Capital Management LP", "0001202273"),
    ("goldentree", "GoldenTree Asset Management LP", "0001275815"),
    ("jane_street", "Jane Street Group, LLC", "0001595888"),
    ("susquehanna", "Susquehanna International Group Ltd.", "0001765924"),
    ("balyasny", "Balyasny Asset Management L.P.", "0001218710"),
    ("anchorage", "Anchorage Capital Group, L.L.C.", "0001300714"),
    ("oaktree", "Oaktree Capital Management LP", "0000949509"),
    ("silver_lake", "Silver Lake Group, L.L.C.", "0001418226"),
    ("sequoia", "SC US (TTGP), LTD.", "0001607841"),
    ("artisan", "Artisan Partners Limited Partnership", "0001466153"),
    ("fisher", "Fisher Asset Management, LLC", "0000850529"),
    ("jennison", "Jennison Associates LLC", "0000053915"),
    ("wellington", "Wellington Management Group LLP", "0000902219"),
    ("geode", "Geode Capital Management LLC", "0001214717"),
]

# Backup list: well-known large 13F-HR filers, used to replace primary funds that turn
# out to be non-filers in the 2019Q1-2026Q2 window (verified against EDGAR at runtime).
BACKUP_FUNDS = [
    ("blackrock", "BlackRock Inc", "0001364742"),
    ("vanguard", "Vanguard Group Inc", "0000102909"),
    ("state_street", "State Street Corp", "0000093751"),
    ("fmr", "FMR LLC", "0000031506"),
    ("morgan_stanley", "Morgan Stanley", "0000895421"),
    ("goldman_sachs", "Goldman Sachs Group Inc", "0000886982"),
    ("t_rowe", "T. Rowe Price Associates Inc", "0001116597"),
    ("capital_world", "Capital World Investors", "0000233316"),
    ("northern_trust", "Northern Trust Corp", "0000073124"),
    ("jp_morgan", "JPMorgan Chase & Co", "0000019617"),
]

is_windows = os.name == "nt"
_lock_file = os.path.join(CACHE_DIR, ".rate_lock")


def rate_limit():
    """Global 1 req/s pacing across all EDGAR endpoints (wall-clock, stale-safe)."""
    t = time.time()
    last = 0.0
    if os.path.exists(_lock_file):
        try:
            with open(_lock_file, "r") as f:
                last = float(f.read().strip() or "0")
        except Exception:
            last = 0.0
    if last and t - last > 30:
        last = 0.0  # stale lock from another boot/session: reset
    wait = last + random.uniform(MIN_SLEEP, MAX_SLEEP) - t
    if wait > 3.0:
        wait = random.uniform(MIN_SLEEP, MAX_SLEEP)
    if wait > 0:
        time.sleep(wait)
    with open(_lock_file, "w") as f:
        f.write(str(time.time()))


def get(url, tries=4, search=False):
    for attempt in range(tries):
        rate_limit()
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(12 + attempt * 4)
                continue
            if r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
        except Exception as e:
            print(f"    [req-error] {url[:100]} : {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    return None


def local_name(tag):
    return tag.rsplit("}", 1)[-1].lower()


def quarter_of(period):
    """period like '2019-03-31' -> '2019Q1'."""
    try:
        y, m, d = period.split("-")
        q = (int(m) - 1) // 3 + 1
        return f"{y}Q{q}"
    except Exception:
        return None


def infer_quarter_from_filing_date(filing_date):
    try:
        y, m, d = filing_date.split("-")
        ref = time.strptime(filing_date, "%Y-%m-%d")
        ts = time.mktime(ref) - 60 * 24 * 3600
        y, m, d = time.strptime(time.strftime("%Y-%m-%d", time.localtime(ts)), "%Y-%m-%d")[:3]
        return f"{y}Q{(m - 1) // 3 + 1}"
    except Exception:
        return None


def _norm_title(t):
    s = re.sub(r"\s+", " ", t.upper()).strip()
    s = re.sub(r"[.,]+$", "", s)
    for suf in (" DEL", " NEW", " COM", " L P", " LTD"):
        if s.endswith(suf):
            s = s[: -len(suf)]
    s = s.replace("CORPORATION", "CORP")
    return s


def load_tickers():
    """Map canonical issuer title -> ticker from company_tickers.json.

    Handles both legacy {ticker: meta} and current {index: meta} layouts.
    """
    tickers = {}
    if os.path.exists(TICKERS_PATH):
        with open(TICKERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        r = get("https://www.sec.gov/files/company_tickers.json", tries=3)
        if r is not None:
            data = r.json()
            with open(TICKERS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f)
        else:
            data = None
    if not isinstance(data, (list, dict)):
        return tickers
    items = data if isinstance(data, list) else data.values()
    for meta in items:
        if not isinstance(meta, dict) or "ticker" not in meta:
            continue
        t = str(meta.get("ticker", "")).strip().upper()
        title = str(meta.get("title", "")).strip()
        if not t or not title:
            continue
        tickers[_norm_title(title)] = t
    print(f"ticker names loaded: {len(tickers)}", flush=True)
    return tickers


def search_cik_by_name(name):
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company="
           + urllib.parse.quote(name) + "&type=13F&dateb=&owner=include&count=40&output=atom")
    r = get(url, search=True)
    if r is None:
        return None, "search_http_error"
    try:
        root = ET.fromstring(r.content)
        for comp in root.iter():
            if local_name(comp.tag) in ("companyinfo", "company-info"):
                cik = comp.findtext("{http://www.sec.gov/cik}cik")
                if cik is None:
                    for child in comp:
                        if local_name(child.tag) == "cik":
                            cik = child.text
                if cik:
                    return cik.strip().zfill(10), None
        return None, "search_no_match"
    except Exception as e:
        return None, f"search_parse_error:{e}"


def fetch_submissions_raw(cik):
    path = os.path.join(CACHE_DIR, f"submissions_{cik}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    r = get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if r is None:
        return None
    data = r.json()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def pick_filings(sub_raw):
    """Return dict quarter -> filing dict {form, accn, doc, filing_date, period, quarter}."""
    recent = sub_raw.get("filings", {}).get("recent", {})
    if not isinstance(recent, dict) or not recent.get("form"):
        recent = {}
    by_quarter = _scan_filings(recent)
    # If quarters are missing, paginate the archived files section (mega-filers'
    # `recent` array is capped at 1000 filings, hiding older 13F-HRs).
    missing = [q for q in QR_DISPLAY if q not in by_quarter]
    if missing:
        merged = _scan_filings(_merge_archives(sub_raw, recent))
        for q in QR_DISPLAY:
            if q not in by_quarter and q in merged:
                by_quarter[q] = merged[q]
    return by_quarter


def _scan_filings(arr):
    """Scan a flat recent/archive filing array into quarter -> preferred filing."""
    by_quarter = {}
    forms = arr.get("form", [])
    n = len(forms)
    for i in range(n):
        form = str(forms[i] or "").upper()
        if form not in ("13F-HR", "13F-HR/A", "13F-NT", "13F-NT/A"):
            continue
        fdates = arr.get("filingDate") or []
        filing_date = fdates[i] if i < len(fdates) else ""
        if not filing_date or filing_date > CUTOFF_DATE:
            continue
        por = arr.get("periodOfReport") or arr.get("reportDate") or []
        period = por[i] if i < len(por) else ""
        q = quarter_of(period) or infer_quarter_from_filing_date(filing_date)
        if q not in QR_DISPLAY:
            continue
        accns = arr.get("accessionNumber") or []
        docs = arr.get("primaryDocument") or []
        cand = {
            "form": form,
            "accn": accns[i] if i < len(accns) else "",
            "doc": docs[i] if i < len(docs) else "",
            "filing_date": filing_date,
            "period": period,
            "quarter": q,
        }
        existing = by_quarter.get(q)
        if existing is None:
            by_quarter[q] = cand
        else:
            pref = 0 if form == "13F-HR" else 1
            old_pref = 0 if existing["form"] == "13F-HR" else 1
            if pref < old_pref or (pref == old_pref and filing_date > existing["filing_date"]):
                by_quarter[q] = cand
    return by_quarter


def _merge_archives(sub_raw, recent):
    """Merge paginated submissions archive pages into a flat array spanning the full
    filing history. Cached to disk like fetch_submissions_raw."""
    CAND_KEYS = ["accessionNumber", "form", "filingDate", "primaryDocument"]
    merged = {k: [] for k in CAND_KEYS}
    merged["reportDate"] = []
    merged["periodOfReport"] = []
    seen = set()

    def period_at(src, i):
        rd = src.get("reportDate") or src.get("periodOfReport") or []
        return rd[i] if i < len(rd) else None

    def append_rows(src):
        forms = src.get("form", [])
        for i in range(len(forms)):
            accns = src.get("accessionNumber") or []
            accn = accns[i] if i < len(accns) else ""
            if accn in seen:
                continue
            seen.add(accn)
            for k in CAND_KEYS:
                vals = src.get(k, [])
                merged[k].append(vals[i] if i < len(vals) else None)
            per = period_at(src, i)
            merged["reportDate"].append(per)
            merged["periodOfReport"].append(per)

    append_rows(recent)
    for f in sub_raw.get("filings", {}).get("files", []) or []:
        name = str(f.get("name", ""))
        fto = str(f.get("filingTo", "") or "")
        if fto and fto < "2019-01-01":
            continue
        url = "https://data.sec.gov/submissions/" + name
        path = os.path.join(CACHE_DIR, "arch_" + name.replace("/", "_"))
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                d = json.load(fh)
        else:
            r = get(url)
            if r is None:
                continue
            d = r.json()
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(d, fh)
            except Exception:
                pass
        append_rows(d)
    return merged


def fetch_document(cik, accn, doc, cache_path):
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return f.read(), True
    accn_clean = accn.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn_clean}/{doc}"
    r = get(url)
    if r is None:
        return None, False
    with open(cache_path, "wb") as f:
        f.write(r.content)
    return r.content, False


def index_lookup(cik, accn):
    """Find the info-table XML in the filing index if primary doc has no table."""
    accn_clean = accn.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn_clean}/"
    r = get(url)
    if r is None:
        return None
    candidates = []
    for m in re.finditer(r'href="([^"]+)"', r.text):
        href = m.group(1)
        low = href.lower()
        if low.endswith(".xml") and ("informationtable" in low or "infotable" in low or "13f" in low):
            candidates.append(href)
        elif low.endswith((".htm", ".html")) and low.split("/")[-1].endswith(("13f", "infotable", "informationtable")):
            candidates.append(href)
    if not candidates:
        for m in re.finditer(r'href="([^"]+)"', r.text):
            low = m.group(1).lower()
            if low.endswith(".xml"):
                candidates.append(m.group(1))
    if not candidates:
        return None

    def score(h):
        low = h.lower()
        s = 0
        if "informationtable" in low:
            s += 4
        elif "infotable" in low:
            s += 3
        elif "13f" in low:
            s += 2
        if low.endswith(".xml"):
            s += 1
        return s

    best = max(candidates, key=score)
    if best.startswith("http"):
        return best
    if best.startswith("/"):
        return "https://www.sec.gov" + best
    return url + best.lstrip("/")


TABLE_RE = re.compile(r"<((?:\w+:)?)informationTable\b[^>]*>(.*?)</(?:\w+:)?informationTable>", re.S | re.I)


def parse_table(content):
    if not content:
        return []
    text = content.decode("utf-8", errors="replace")
    m = TABLE_RE.search(text)
    if not m:
        return None  # no informationTable -> index fallback path
    pre, frag = m.group(1), m.group(2)
    try:
        if pre:
            decls = ['xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"']
            for p in set(re.findall(r"<(\w+):", frag)):
                if p != "xsi":
                    decls.append(f'xmlns:{p}="http://www.sec.gov/edgar/document/thirteenf/informationtable"')
            root = ET.fromstring(f"<{pre}informationTable {' '.join(decls)}>{frag}</{pre}informationTable>")
        else:
            root = ET.fromstring("<informationTable>" + frag + "</informationTable>")
    except Exception:
        return None
    rows = []
    for it in root:
        if local_name(it.tag) not in ("infotable", "informationtable"):
            continue
        rec = {}
        for child in it:
            ln = local_name(child.tag)
            if ln in ("shrsorprnamt", "votingauthority"):
                for sub in child:
                    rec[local_name(sub.tag)] = (sub.text or "").strip()
            else:
                rec[ln] = (child.text or "").strip()
        if rec.get("nameofissuer"):
            rows.append(rec)
    return rows


def clean_rows(rows):
    out = []
    seen = set()
    for r in rows:
        try:
            value = int(float(r.get("value", "0") or 0))
        except Exception:
            value = 0
        if value <= 0:
            continue
        name = r.get("nameofissuer", "").strip()
        cusip = r.get("cusip", "").strip().upper()
        key = (cusip or name.upper(), name.upper())
        if key in seen:
            continue
        seen.add(key)
        ssh = r.get("sshprnamt", "").strip().replace(",", "")
        try:
            shares = float(ssh) if ssh else 0.0
        except Exception:
            shares = 0.0
        put_call = r.get("putcall", "").strip().upper()
        if put_call not in ("PUT", "CALL"):
            put_call = ""
        out.append({
            "name": name,
            "cusip": cusip,
            "value": value,
            "shares": shares,
            "put_call": put_call,
            "ticker": "",
        })
    out.sort(key=lambda x: x["value"], reverse=True)
    return out


def write_quarter_csv(slug, q, rows):
    path = os.path.join(FH_DIR, f"{slug}_{q}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name_of_issuer", "cusip", "value_usd_thousands", "shares", "put_call", "ticker"])
        for r in rows:
            w.writerow([r["name"], r["cusip"], r["value"], int(r["shares"]) if r["shares"] == int(r["shares"]) else r["shares"], r["put_call"], r["ticker"]])
    return path


def attach_tickers(rows, tickers):
    for r in rows:
        r["ticker"] = tickers.get(_norm_title(r["name"]), "")


def read_funds_csv():
    funds = {}
    if os.path.exists(FUNDS_CSV):
        with open(FUNDS_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                funds[row["fund_slug"]] = row
    return funds


def read_issues_csv():
    issues = []
    if os.path.exists(ISSUES_CSV):
        with open(ISSUES_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                issues.append((row.get("fund", ""), row.get("quarter", ""), row.get("reason", "")))
    return issues


def write_funds_csv(funds):
    with open(FUNDS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fund_slug", "fund_name", "cik", "quarters_covered", "most_valued_issuer", "top_value_usd_m"])
        for slug in [x[0] for x in FUNDS + BACKUP_FUNDS]:
            row = funds.get(slug)
            if row:
                w.writerow([row["fund_slug"], row["fund_name"], row["cik"], row["quarters_covered"],
                            row.get("most_valued_issuer", ""), row.get("top_value_usd_m", "")])


def write_issues_csv(issues):
    with open(ISSUES_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fund", "quarter", "reason"])
        w.writerows(issues)


def update_state(patch):
    try:
        st = {"status": "running", "attempts": 1, "lastError": None, "fundsDeep": 0, "universeQuarters": 30, "artifacts": [], "notes": []}
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                st.update(json.load(f))
        st.update(patch)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(st, f, indent=2)
    except Exception as e:
        print("state update error:", e)


def main():
    only = []
    limit = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == "--only" and i + 1 < len(args):
            only = [x.strip() for x in args[i + 1].split(",")]
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    os.makedirs(FH_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(RUNLOG_DIR, exist_ok=True)

    print("Loading company_tickers.json ...", flush=True)
    tickers = load_tickers()
    print(f"  {len(tickers)} ticker names loaded", flush=True)

    funds_meta = read_funds_csv()
    issues = read_issues_csv()

    processed = 0
    done_funds = 0
    for slug, name, cik in FUNDS + BACKUP_FUNDS:
        if only and slug not in only:
            continue
        if limit is not None and processed >= limit:
            break
        processed += 1
        prev = funds_meta.get(slug)
        if prev and prev.get("quarters_covered") and int(prev["quarters_covered"]) >= 28:
            print(f"[skip] {slug}: quarters_covered={prev['quarters_covered']} >= 28", flush=True)
            done_funds += 1
            continue
        if done_funds >= 40:
            print(f"[skip] {slug}: already 40 funds done", flush=True)
            break

        print(f"[fund] {slug} ({name}) cik={cik}", flush=True)
        issues = [i for i in issues if i[0] != slug]  # drop stale rows for this fund
        sub_raw = fetch_submissions_raw(cik)
        if sub_raw is None:
            cik, err = search_cik_by_name(name)
            if cik is None:
                issues.append((slug, "all", f"cik_unresolved {err}"))
                print(f"  !! CIK unresolved: {err}", flush=True)
                funds_meta[slug] = {"fund_slug": slug, "fund_name": name, "cik": "", "quarters_covered": "0",
                                    "most_valued_issuer": "", "top_value_usd_m": "0"}
                continue
            issues.append((slug, "all", f"cik_from_search replaced {name}"))
            print(f"  !! CIK replaced via search: {cik}", flush=True)
            sub_raw = fetch_submissions_raw(cik)
        if sub_raw is None:
            issues.append((slug, "all", "submissions_unavailable"))
            funds_meta[slug] = {"fund_slug": slug, "fund_name": name, "cik": cik, "quarters_covered": "0",
                                "most_valued_issuer": "", "top_value_usd_m": "0"}
            continue

        sub_name = str(sub_raw.get("name", "")).upper()
        tokens = [t for t in name.upper().replace("/", " ").split() if len(t) > 2]
        ok = any(t in sub_name for t in tokens)
        if not ok:
            new_cik, err = search_cik_by_name(name)
            if new_cik and new_cik != cik:
                issues.append((slug, "all", f"cik_mismatch {sub_name} -> search {new_cik}"))
                print(f"  !! name mismatch, trying search cik {new_cik}", flush=True)
                cik = new_cik
                sub_raw = fetch_submissions_raw(cik)
                if sub_raw is not None:
                    sub_name = str(sub_raw.get("name", "")).upper()
                    ok = any(t in sub_name for t in tokens)
        if not ok:
            reasons = "name_mismatch EDGAR=" + str(sub_raw.get("name", ""))[:60] if sub_raw is not None else "submissions_none"
            issues.append((slug, "all", f"cik_unverified_not_13f_filer {reasons}"))
            print(f"  !! NOT a verified 13F filer ({reasons}); replacing from backup funds", flush=True)
            funds_meta[slug] = {"fund_slug": slug, "fund_name": name, "cik": str(cik),
                                "quarters_covered": "0", "most_valued_issuer": "", "top_value_usd_m": "0"}
            write_funds_csv(funds_meta)
            write_issues_csv(issues)
            continue

        by_q = pick_filings(sub_raw) if sub_raw is not None else {}
        print(f"  filings matched: {len(by_q)} quarters", flush=True)

        covered = 0
        total_value = 0
        best = ("", 0)
        for q in QR_DISPLAY:
            path = os.path.join(FH_DIR, f"{slug}_{q}.csv")
            if os.path.exists(path) and os.path.getsize(path) > 100:
                # reload best/total from existing file for summary continuity
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for row in csv.DictReader(f):
                            v = int(row["value_usd_thousands"] or 0)
                            total_value += v
                            if v > best[1]:
                                best = (row["name_of_issuer"], v)
                    covered += 1
                except Exception:
                    pass
                continue
            filing = by_q.get(q)
            if filing is None:
                issues.append((slug, q, "no_filing"))
                continue
            cache_path = os.path.join(CACHE_DIR, f"{slug}_{q}.xml")
            content, cached = fetch_document(int(cik), filing["accn"], filing["doc"], cache_path)
            if content is None:
                issues.append((slug, q, f"doc_fetch_error {filing['accn']}"))
                continue
            rows = parse_table(content)
            if rows is None:
                alt = index_lookup(int(cik), filing["accn"])
                if alt:
                    r2 = get(alt)
                    if r2 is not None:
                        content = r2.content
                        with open(cache_path, "wb") as f:
                            f.write(content)
                        rows = parse_table(content)
            if rows is None:
                issues.append((slug, q, f"xml_parse_error {filing['accn']}"))
                continue
            rows = clean_rows(rows)
            attach_tickers(rows, tickers)
            if not rows:
                issues.append((slug, q, f"no_holdings {filing['form']}"))
            write_quarter_csv(slug, q, rows)
            covered += 1
            for r in rows:
                total_value += r["value"]
                if r["value"] > best[1]:
                    best = (r["name"], r["value"])
            print(f"    {q}: {len(rows)} rows ({'cache' if cached else 'fetch'})", flush=True)

        funds_meta[slug] = {"fund_slug": slug, "fund_name": name, "cik": cik,
                            "quarters_covered": str(covered),
                            "most_valued_issuer": best[0],
                            "top_value_usd_m": f"{best[1] / 1000.0:.2f}" if best[1] else "0"}
        print(f"  done: {slug} covered {covered}/30 quarters", flush=True)
        if covered >= 28:
            done_funds += 1
        write_funds_csv(funds_meta)
        write_issues_csv(issues)
        update_state({"fundsDeep": sum(1 for s in funds_meta.values() if int(s.get("quarters_covered", 0) or 0) >= 1)})

    write_funds_csv(funds_meta)
    write_issues_csv(issues)

    n_done = sum(1 for s in funds_meta.values() if int(s.get("quarters_covered", 0) or 0) >= 1)
    done = all(int(s.get("quarters_covered", 0) or 0) >= 28 for s in funds_meta.values())
    update_state({"status": "done" if done else "running", "fundsDeep": n_done,
                  "artifacts": [FUNDS_CSV, ISSUES_CSV, FH_DIR]})
    if done:
        with open(DONE_PATH, "w") as f:
            f.write("done")
    print("Resume point funds:", n_done)


if __name__ == "__main__":
    main()