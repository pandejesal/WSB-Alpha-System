"""Build CUSIP-independent ticker map for the 13F claim (Cycle 3).

Method (pre-registered delta, see docs/data/cycle3_prereg_13f.md Appendix A):
  1. Primary map: SEC company_tickers.json (CIK -> ticker/title), restricted to the
     481-name frozen snapshot. Titles are canonical SEC names (e.g. 'NVIDIA CORP').
  2. Secondary map: yfinance longName for the same 481 tickers (covers renames like
     GE AEROSPACE, and 'Bank of America Corporation' style names).
  3. Normalization: uppercase, & -> AND, strip legal-suffix words (CORP, INC, CO,
     CORPORATION, INCORPORATED, COMPANY, LTD, LLC, LP, PLC, AG, NV, SA, NEW, HOLDINGS,
     GROUP, SYS, ADR, TR, FD(S), TRUST, CAP, STK), strip state markers (/DE/, /MA/,
     /NEW, /PA, ...), expand abbreviations (WHSL -> WHOLESALE, PETE -> PETROLEUM,
     INTL -> INTERNATIONAL), drop connectives (THE, AND, OF), drop share-class
     markers (CL A / CLASS B / CAP STK).
  4. Match tiers: exact clean name; spaceless clean name (handles JPMORGAN vs
     JP MORGAN); for the 3 class-twins (GOOGL/GOOG, FOXA/FOX, NWSA/NWS) disambiguate
     via the 13F titleOfClass field when both candidates match.
  5. Holdings whose issuer cannot be mapped to a snapshot ticker are IGNORED
     (per pre-registration: "any holding whose CUSIP cannot be mapped ... IGNORED").

Output: cache/cycle3_13f_ticker_map.json {ticker: [SEC title, yfinance longName]}
        + printed coverage statistics over all parsed 13F CSVs.
"""
import collections
import csv
import glob
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SUFFIX = re.compile(
    r"\b(INCORPORATED|CORPORATION|COMPANY|CORP|INC|CO|LTD|LLC|LP|PLC|AG|NV|SA|COM|NEW|"
    r"HOLDINGS|HLDGS|GROUP|GRP|SYS|ADR|TR|FDS|FD|TRUST|CAP|STK)\b"
)
CLS = re.compile(r"\b(CL|CLASS)\s*([ABC])\b")
STATE = re.compile(r"\b(DE|MA|PA|GA|NC|NJ|NY|TX|CA|IL|OH|VA|WA|MN|MD|TN|FL|CT|MO|WI|IN|UT|CO|AZ|OR|MI|AR|NE|OK|SC|AL|KY|LA|IA|MS|NH|KS|RI|VT|WV|WY|ND|SD|MT|ID|NM|NV|AK|HI)\b")
ABBR = {
    "WHSL": "WHOLESALE",
    "PETE": "PETROLEUM",
    "INTL": "INTERNATIONAL",
    "TECHNOL": "TECHNOLOGIES",
    "SYS": "SYSTEMS",
    "ENGY": "ENERGY",
    "FINL": "FINANCIAL",
    "ELEC": "ELECTRIC",
    "MACH": "MACHINERY",
    "CP": "CAPITAL",
    "COS": "COMPANIES",
    "CO": "COMPANY",
    "TRANS": "TRANSPORT",
    "SVCS": "SERVICES",
    "WASH": "WASHINGTON",
    "INDS": "INDUSTRIES",
    "INVT": "INVESTMENT",
    "RLTY": "REALTY",
    "BANCSHARES": "BANCSHARES",
    "EQ": "EQUITIES",
    "INFO": "INFORMATION",
    "SERV": "SERVICES",
    "INCM": "INCOME",
    "RLY": "REALTY",
    "STD": "STANDARD",
    "SYSTEM": "SYSTEMS",
    "COMM": "COMMUNITIES",
}
STOP = {"THE", "AND", "OF", "SHARES", "SERIES"}

# Known issuer renames / 13F-isms with NO token overlap to any SEC/yfinance name.
# Fixed pre-registered alias list (see cycle3_prereg_13f.md Appendix A delta).
RENAME_ALIASES = {
    "WABTEC": "WAB",       # Westinghouse Air Brake Technologies -> Wabtec (13F uses old name)
}


def clean(s):
    s = s.upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    s = SUFFIX.sub(" ", s)
    s = CLS.sub(" ", s)
    for k, v in ABBR.items():
        s = re.sub(r"\b" + k + r"\b", " " + v + " ", s)
    s = STATE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    toks = [t for t in s.split(" ") if t not in STOP and t not in ("A", "B", "C")]
    return " ".join(toks)


def spaceless(s):
    return s.replace(" ", "")


def sorted_tokens(s):
    return " ".join(sorted(s.split()))


def norm_class(s):
    m = CLS.search(s.upper())
    return m.group(2) if m else ""


CLASS_TWINS = {
    frozenset(["GOOGL", "GOOG"]): {"A": "GOOGL", "C": "GOOG"},
    frozenset(["FOXA", "FOX"]): {"A": "FOXA", "B": "FOX"},
    frozenset(["NWSA", "NWS"]): {"A": "NWSA", "B": "NWS"},
}


def load_snapshot():
    p = os.path.join(BASE, "docs", "data", "factor_claim_preregistration.md")
    snap = set()
    in_list = False
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s.startswith("Included tickers (481)"):
                in_list = True
                continue
            if in_list:
                if s.startswith("Excluded"):
                    break
                snap.update(s.split())
    return set(t.upper() for t in snap)


def build_map():
    snap = load_snapshot()
    with open(os.path.join(BASE, "cache", "company_tickers.json"), encoding="utf-8") as f:
        sec = json.load(f)
    with open(os.path.join(BASE, "cache", "snapshot_names.json"), encoding="utf-8") as f:
        yf_names = json.load(f)

    ticker_to_names = {}
    for meta in sec.values():
        t = str(meta.get("ticker", "")).strip().upper()
        title = str(meta.get("title", "")).strip()
        if t in snap and title:
            ticker_to_names.setdefault(t, [None, None])[0] = title
    for t, long_name in yf_names.items():
        t = t.upper()
        if t in snap and long_name:
            ticker_to_names.setdefault(t, [None, None])[1] = long_name

    # name -> candidate tickers, with tier markers
    exact = collections.defaultdict(list)
    flat = collections.defaultdict(list)
    sorted_n = collections.defaultdict(list)
    token_sets = {}
    for t, (sec_title, yf_name) in ticker_to_names.items():
        for src in (sec_title, yf_name):
            if not src:
                continue
            exact[clean(src)].append(t)
            flat[spaceless(clean(src))].append(t)
            sorted_n[sorted_tokens(clean(src))].append(t)
        cset = set()
        for src in (sec_title, yf_name):
            if src:
                cset |= set(clean(src).split())
        token_sets[t] = frozenset(cset) if cset else frozenset()

    def resolve(name13f, cls):
        c = clean(name13f)
        cset = set(c.split())
        cands = exact.get(c)
        tier = 1
        if not cands:
            cands = flat.get(spaceless(c))
            tier = 2
        if not cands:
            cands = sorted_n.get(sorted_tokens(c))
            tier = 3
        if not cands and name13f in RENAME_ALIASES:
            return RENAME_ALIASES[name13f], 5, False
        if not cands:
            # tier 4: token-subset containment (handles 28-char 13F truncation)
            hits = set()
            for t in token_sets:
                tset = token_sets[t]
                if cset <= tset or tset <= cset:
                    hits.add(t)
            if len(hits) == 1:
                return next(iter(hits)), 4, False
            if len(hits) > 1:
                return CLASS_TWINS.get(frozenset(hits), {}).get(cls), 4, len(hits) > 1
            return None, 0, False
        uniq = sorted(set(cands))
        if len(uniq) == 1:
            return uniq[0], tier, False
        return CLASS_TWINS.get(frozenset(uniq), {}).get(cls), tier, len(uniq) > 1

    # coverage pass over all parsed 13F CSVs (clean cached per distinct issuer name)
    clean_cache = {}
    resolve_cache = {}
    matched_val = 0.0
    matched_rows = 0
    total_val = 0.0
    total_rows = 0
    cls_rows = 0
    matched_tickers = collections.Counter()
    tier_counts = collections.Counter()
    for f in glob.glob(os.path.join(BASE, "market_data_2019_2026", "institutions", "13f", "*.csv")):
        with open(f, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                n = row.get("name_of_issuer", "").strip().upper()
                try:
                    val = float(row.get("value_usd_thousands", 0) or 0)
                except (TypeError, ValueError):
                    val = 0.0
                total_rows += 1
                total_val += val
                cls = norm_class(row.get("title_of_class", "") or n)
                key = (n, cls)
                if key in resolve_cache:
                    t, tier, multi = resolve_cache[key]
                else:
                    c = clean_cache.get(n)
                    if c is None:
                        c = clean_cache[n] = clean(n)
                    t, tier, multi = resolve(c, cls)
                    resolve_cache[key] = (t, tier, multi)
                if t:
                    matched_rows += 1
                    matched_val += val
                    matched_tickers[t] += 1
                    tier_counts[tier] += 1
                    if multi:
                        cls_rows += 1

    out = {"ticker_to_names": ticker_to_names, "snapshot_count": len(snap)}
    with open(os.path.join(BASE, "cache", "cycle3_13f_ticker_map.json"), "w", encoding="utf-8") as f:
        json.dump(out, f)

    print(f"snapshot tickers mapped: {len(ticker_to_names)}/{len(snap)}")
    print(f"rows: {matched_rows}/{total_rows} | value: {matched_val/1e6:.1f}M "
          f"({matched_val/total_val*100:.1f}%) | class-resolved: {cls_rows}")
    print(f"tier1 (exact clean): {tier_counts[1]} rows | tier2 (spaceless): {tier_counts[2]} "
          f"| tier3 (sorted): {tier_counts[3]} | tier4 (subset): {tier_counts[4]} | tier5 (rename): {tier_counts[5]}")
    print(f"snapshot tickers covered in data: {len(matched_tickers)}/{len(snap)}")
    never = sorted(t for t in ticker_to_names if t not in matched_tickers)
    if never:
        print("NEVER REFERENCED:", never)


if __name__ == "__main__":
    build_map()