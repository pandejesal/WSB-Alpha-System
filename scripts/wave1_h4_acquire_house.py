"""Wave-1 H4 Arm P dataset acquisition — US House STOCK Act PTR filings.

PAPER-ONLY / FAIL-CLOSED: this script only downloads public disclosure data and
writes local CSV/JSON artifacts. It enables no execution of any kind.

Provenance (prereg docs/data/wave1_h4_poltrade_cramer_prereg.md, Amendment A1):
official House Clerk sources, plain GET, no auth:
  index:  https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{YEAR}FD.zip
  filing: https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{DocID}.pdf
Retrieved starting 2026-08-25. Free tier only; no secrets used or stored.

Serial, resumable, polite. Outputs under data/h4_raw/ (gitignored).
"""

import argparse
import csv
import hashlib
import io
import json
import random
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

BASE = "https://disclosures-clerk.house.gov/public_disc"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
BANDS = {
    (1001, 15000): (1001, 15000),
    (15001, 50000): (15001, 50000),
    (50001, 100000): (50001, 100000),
    (100001, 250000): (100001, 250000),
    (250001, 500000): (250001, 500000),
    (500001, 1000000): (500001, 1000000),
    (1000001, 5000000): (1000001, 5000000),
    (5000001, 25000000): (5000001, 25000000),
}
DATE = r"\d{2}/\d{2}/\d{4}"
PAIR_RE = re.compile(
    rf"({DATE})[^$]{{0,80}}?({DATE})[^$]{{0,12}}?\$\s*([\d,]+)\s*-\s*\$\s*([\d,]+)",
    re.S,
)
TICKER_RE = re.compile(r"\(([A-Za-z][A-Za-z.\-]{0,7})\)\s*\[[A-Za-z]{1,4}\]\s*$")
TYPE_WORD_RE = re.compile(
    r"(sale\s*\(partial\)|sale\s*\(full\)|sale|purchase|exchange)$", re.I
)
TYPE_LETTER_RE = re.compile(r"\b([PSDE])\s*(?:\(\s*(partial|full)\s*\))?$", re.I)
OWNER_GLUED_RE = re.compile(r"^(SP|JT|DC|SC)(?=[A-Za-z])")
OWNER_RE = re.compile(r"^(SP|JT|DC|SC)\b")
NOISE_RES = [
    re.compile(p, re.I)
    for p in (
        r"notification\s*date",
        r"amount\s*cap\.\s*gains\s*>\s*\$?\s*200\?",
        r"transactions?\s*i?\s*owner",
        r"asset\s*transaction\s*type\s*date",
        r"filing\s*status:",
    )
]
TYPE_NORM = {"P": "purchase", "S": "sale_full", "D": "sale_partial",
             "E": "exchange", "SALE (PARTIAL)": "sale_partial",
             "SALE (FULL)": "sale_full", "SALE": "sale_full",
             "PURCHASE": "purchase", "EXCHANGE": "exchange"}


def http_get(url: str, timeout: int = 30, attempts: int = 3) -> bytes:
    backoffs = [2, 4, 8]
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status >= 500:
                    raise IOError(f"http {r.status}")
                return r.read()
        except Exception as e:  # noqa: BLE001 - recorded, not fatal
            last = e
            if i < attempts - 1:
                time.sleep(backoffs[min(i, len(backoffs) - 1)])
    raise RuntimeError(f"GET failed after {attempts} attempts: {url}: {last}")


def load_index(year: int, workdir: Path, sleep_fn) -> list[dict]:
    zpath = workdir / f"{year}FD.zip"
    if not zpath.exists():
        zpath.write_bytes(http_get(f"{BASE}/financial-pdfs/{year}FD.zip"))
        sleep_fn()
    with zipfile.ZipFile(zpath) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
        root = ET.fromstring(z.read(name))
    rows = []
    for r in root:
        if (r.findtext("FilingType") or "").strip() != "P":
            continue
        fd = (r.findtext("FilingDate") or "").strip()
        try:
            fdate = datetime.strptime(fd, "%m/%d/%Y").date()
        except ValueError:
            continue
        if fdate < datetime(2018, 11, 1).date():
            continue
        docid = (r.findtext("DocID") or "").strip()
        if not docid.isdigit():
            continue
        rows.append({
            "docid": docid,
            "year": fdate.year,
            "filing_date_iso": fdate.isoformat(),
            "member_last": (r.findtext("Last") or "").strip(),
            "member_first": (r.findtext("First") or "").strip(),
            "state_district": (r.findtext("StateDst") or "").strip(),
        })
    rows.sort(key=lambda x: (x["filing_date_iso"], x["docid"]))
    return rows


def parse_transactions(text: str) -> list[dict]:
    out = []
    matches = list(PAIR_RE.finditer(text))
    for idx, m in enumerate(matches):
        seg_start = matches[idx - 1].end() if idx else 0
        seg = text[seg_start:m.start()]
        d1, d2 = m.group(1), m.group(2)
        amin = int(m.group(3).replace(",", ""))
        amax = int(m.group(4).replace(",", ""))
        band = BANDS.get((amin, amax))
        asset_seg = seg
        cap_flag = ""
        owner = ""
        ticker, ticker_ok = "", False
        tail = seg[-260:]
        gm = re.search(r"\b([A-Za-z])\s*$", text[m.end():m.end() + 3])
        if gm and gm.group(1).upper() == "G":
            cap_flag = gm.group(1)
        words = tail.split()
        while words and (OWNER_RE.match(words[0]) or OWNER_GLUED_RE.match(words[0])):
            om = OWNER_GLUED_RE.match(words[0])
            if om:
                owner = om.group(1)
                words[0] = words[0][om.end():]
                break
            owner = words[0]
            words = words[1:]
        core = " ".join(words).rstrip()
        wm = TYPE_WORD_RE.search(core)
        if wm:
            raw_type = wm.group(1)
            core = core[: wm.start()].rstrip()
        else:
            lm = TYPE_LETTER_RE.search(core)
            raw_type = lm.group(1) if lm else ""
            if lm:
                if lm.group(2):
                    raw_type = raw_type.upper() + " (" + lm.group(2).upper() + ")"
                core = core[: lm.start()].rstrip()
        tm = TICKER_RE.search(core)
        if tm:
            ticker = tm.group(1).upper()
            ticker_ok = True
            core = core[: tm.start()].rstrip()
        for nr in NOISE_RES:
            core = nr.sub(" ", core)
        asset_desc = re.sub(r"\s+", " ", core).strip()
        try:
            t1 = datetime.strptime(d1, "%m/%d/%Y").date().isoformat()
            t2 = datetime.strptime(d2, "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        out.append({
            "ticker": ticker,
            "ticker_confident": ticker_ok,
            "asset_desc": asset_desc,
            "tx_type_raw": raw_type,
            "tx_type_norm": TYPE_NORM.get(raw_type.strip().upper(), "other"),
            "tx_date_iso": t1,
            "notify_date_iso": t2,
            "amount_min_usd": band[0] if band else "",
            "amount_max_usd": band[1] if band else "",
            "owner_code": owner,
            "cap_gains_flag": cap_flag,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Acquire House PTR filings (H4 Arm P)")
    ap.add_argument("--years", type=int, nargs="+",
                    default=list(range(2018, 2027)))
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most N eligible filings overall")
    ap.add_argument("--polite-sleep", type=float, default=0.5)
    ap.add_argument("--workdir", default="data/h4_raw")
    args = ap.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    def sleep_fn():
        time.sleep(max(0.05, args.polite_sleep + random.uniform(-0.25, 0.25)))

    done = set()
    manifest_path = workdir / "house_manifest.jsonl"
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                if rec.get("status") in ("fetched", "parse_empty", "image_only"):
                    done.add(rec["docid"])
            except Exception:  # noqa: BLE001
                continue
    manifest = manifest_path.open("a", encoding="utf-8")

    filings_rows, tx_rows = [], []
    per_year: dict[int, dict] = {}
    processed = fetched = parse_empty = image_only = http_error = 0
    tx_total = tx_conf = 0
    t0 = time.time()

    for year in sorted(set(args.years)):
        try:
            eligible = load_index(year, workdir, sleep_fn)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] index {year} failed: {e}")
            per_year[year] = {"filings": 0, "error": str(e)}
            continue
        per_year.setdefault(year, {"filings": len(eligible), "fetched": 0,
                                   "parse_empty": 0, "image_only": 0,
                                   "http_error": 0})
        for row in eligible:
            if args.limit and processed >= args.limit:
                break
            processed += 1
            ystat = per_year[year]
            if row["docid"] in done:
                continue
            url = f"{BASE}/ptr-pdfs/{row['year']}/{row['docid']}.pdf"
            status = "fetched"
            text_chars = 0
            pdf_sha = ""
            n_tx = 0
            url_year = row["year"]
            try:
                data = None
                try:
                    data = http_get(url)
                except RuntimeError:
                    for alt in (url_year - 1, url_year + 1):
                        try:
                            data = http_get(
                                f"{BASE}/ptr-pdfs/{alt}/{row['docid']}.pdf")
                            url_year = alt
                            break
                        except RuntimeError:
                            continue
                    if data is None:
                        raise RuntimeError(
                            f"no PDF under years "
                            f"{url_year - 1}/{url_year}/{url_year + 1}")
                pdf_sha = hashlib.sha256(data).hexdigest()
                reader = PdfReader(io.BytesIO(data))
                text = "\n".join((p.extract_text() or "") for p in reader.pages)
                text_chars = len(text.strip())
                sleep_fn()
                if text_chars > 0:
                    txs = parse_transactions(text)
                    n_tx = len(txs)
                    for t in txs:
                        tx_total += 1
                        tx_conf += 1 if t["ticker_confident"] else 0
                        tx_rows.append({
                            "docid": row["docid"],
                            "filing_date_iso": row["filing_date_iso"],
                            "member_name": (row["member_first"] + " " +
                                            row["member_last"]).strip(),
                            "state_district": row["state_district"],
                            **t,
                        })
                    if n_tx == 0:
                        status = "parse_empty"
                        parse_empty += 1
                        ystat["parse_empty"] += 1
                    else:
                        fetched += 1
                        ystat["fetched"] += 1
                else:
                    status = "image_only"
                    image_only += 1
                    ystat["image_only"] += 1
            except Exception as e:  # noqa: BLE001
                status = "http_error"
                http_error += 1
                ystat["http_error"] += 1
                print(f"[warn] {row['docid']}: {e}")
            filings_rows.append({**row, "status": status,
                                 "pdf_sha256": pdf_sha,
                                 "text_chars": text_chars,
                                 "n_transactions": n_tx})
            manifest.write(json.dumps({
                "docid": row["docid"], "year": year,
                "filing_date": row["filing_date_iso"], "status": status,
                "pdf_sha256": pdf_sha, "text_chars": text_chars}) + "\n")
            manifest.flush()
            if processed % 50 == 0:
                print(f"[progress] processed={processed} tx={tx_total} "
                      f"elapsed={time.time()-t0:.0f}s", flush=True)
        if args.limit and processed >= args.limit:
            break

    manifest.close()

    def wcsv(path: Path, rows: list[dict], cols: list[str]):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    wcsv(workdir / "house_ptr_filings.csv", filings_rows,
         ["docid", "year", "filing_date_iso", "member_last", "member_first",
          "state_district", "status", "pdf_sha256", "text_chars",
          "n_transactions"])
    wcsv(workdir / "house_transactions_raw.csv", tx_rows,
         ["docid", "filing_date_iso", "member_name", "state_district",
          "ticker", "ticker_confident", "asset_desc", "tx_type_raw",
          "tx_type_norm", "tx_date_iso", "notify_date_iso", "amount_min_usd",
          "amount_max_usd", "owner_code", "cap_gains_flag"])

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_base": BASE,
        "retrieved_note": "official House Clerk PTR sources, retrieved 2026-08-25",
        "polite_sleep": args.polite_sleep,
        "runtime_seconds": round(time.time() - t0, 1),
        "filings_processed_this_run": processed,
        "totals": {"fetched": fetched, "parse_empty": parse_empty,
                   "image_only": image_only, "http_error": http_error},
        "transactions_extracted": tx_total,
        "transactions_confident_ticker": tx_conf,
        "per_year": per_year,
    }
    (workdir / "house_parse_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["totals"]), flush=True)
    print(f"transactions={tx_total} confident={tx_conf}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
