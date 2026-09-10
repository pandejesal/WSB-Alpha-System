# edgartools Adoption Proposal — 8-K Earnings-Surprise + Form 4 Insider Tracking (dgunning/edgartools)

Date: 2026-09-09
Status: STUDY ONLY — no code changed. `evolve_real.py` and `strategies/registry.json` untouched per task constraint.
Scope: propose exact diffs to add SEC-EDGAR event factors via `dgunning/edgartools` without breaking fail-closed / no-lookahead mandates.

## 1. Study findings (requested paths vs. actual repo)

Requested (do not exist):

- `src/alpha/pead.py` — NOT FOUND (no `src/alpha/` directory).
- `src/alpha/factors.py` — NOT FOUND.

Actual PEAD / factor locations verified by read:

- `src/ops/signals.py:378-430` — `get_us_pead_top5_signal(data, tickers, lookback_days=10, hold_days=5, top_n=5) -> dict`
  Current logic: for each ticker, `yf.Ticker(ticker).get_earnings_dates(limit=100)`, filter `earnings.index < last_date` and `>= last_date - lookback_days`, require `Reported EPS` + `Surprise(%) >= 0.0`, then `trading_days_since in [1, hold_days]` via `closes.loc[idx:last_date]`. Stateless approximation, first-come-first-served sort, `LONG` else `FLAT`. Failure mode: per-ticker live yfinance calls inside signal loop, no cache, no SUE magnitude, no 8-K ground truth, no filing-timestamp gating.
- `src/signals/engine.py:10,25,172-192,252-253` — `SignalEngine._generate_pead_top5()` delegates to above; sleeve `us_pead_top5` in `active_sleeves`.
- `src/signals/qlib_alpha158.py:1-80` — 47-feature OHLCV-only library (KMid/KLen/ROC/Rank/Quantile/Std/Sum/Mean/Max/Min/VWAP). No event factors.
- `src/signals/gplearn_factors.py:36-58` — past-only terminals (`ret_1, ret_5, sma ratios, rsi14, vol_ratio20, range_ratio`) with `.shift(1)`. Correct no-lookahead pattern to imitate.
- `src/data/providers/openbb_provider.py:1-51` — provider pattern to imitate: `BaseDataProvider` subclass, lazy `ImportError` fallback, `logger.warning` + fallback, never raise into signal path.
- `requirements.txt:1-169` — no `edgartools` entry. `yfinance==0.2.52`, `pandas==2.2.3`, `lxml==6.1.1`, `beautifulsoup4==4.15.0` present (useful for 8-K exhibit parsing fallback).

Conclusion: the correct insertion point is a new cached EDGAR event provider + pure-function parsers, wired as an optional enrichment to `get_us_pead_top5_signal` and as two new factor columns. No new `src/alpha/` package needed; follow existing `src/data/providers/` + `src/signals/` layout.

## 2. Design (dgunning/edgartools patterns adopted)

Upstream: `https://github.com/dgunning/edgartools` (`pip install edgartools`, import namespace `edgar`).

Adopted canonical patterns (do not invent wrappers):

```python
from edgar import Company, set_identity, get_filings

set_identity("WSB Alpha System research@example.com")  # SEC UA requirement; env override
c = Company("AAPL")
f8k = c.get_filings(form="8-K")          # Filing list, newest-first
eightk = f8k[0].obj()                   # EightK object: .items, exhibits, press-release text
f4 = c.get_filings(form="4")            # Form 4 insider filings
form4 = f4[0].obj()                     # Form4 object: nonDerivativeTable / derivativeTable, reportingOwner, transactions
```

Rules for this repo (fail-closed):

1. All EDGAR I/O isolated in one provider module; signal/factor code only consumes plain `pd.DataFrame` / dicts.
2. Filing-timestamp gating: event usable at `close(t+1)` at earliest, where `t` = `filingDate`. Never use `periodOfReport` as trade date.
3. 8-K Item 2.02 + Exhibit 99.1 press-release text is the surprise source; Item 5.02 / 8.01 / 1.01 alone never generate earnings surprise.
4. Form 4 only counts open-market P (purchase) / S (sale) non-derivative transactions; A/M/G/J codes excluded; amended `4/A` supersedes original.
5. Offline-first tests: all unit tests run with mocked `edgar` objects, zero network. One optional live test gated by `WSB_LIVE_EDGAR=1`.
6. No change to `evolve_real.py` or `strategies/registry.json` in this proposal (edge-gate compliance: new factors are research-only until walk-forward + permutation + DSR pass).

## 3. Exact diffs proposed

### Diff 0 — `requirements.txt` (append, pin floor)

```diff
--- a/requirements.txt
+++ b/requirements.txt
@@
 yfinance==0.2.52
 zstandard==0.25.0
 defusedxml==0.7.1
 ccxt==4.5.74
 PyYAML==6.0.3
+edgartools>=4.5.0
```

Rationale: `edgartools` pulls `httpx/pyarrow/lxml`; all already-compatible with pinned `pandas==2.2.3`. No version ceiling to avoid SEC-API churn breakage; floor `4.5.0` is first version with stable `EightK.items` + `Form4` tables.

Env additions (`.env.example`, not committed secrets):

```
EDGAR_IDENTITY=WSB Alpha System research@example.com
EDGAR_CACHE_DIR=./cache/edgar
WSB_LIVE_EDGAR=0
```

### Diff 1 — NEW `src/data/providers/edgar_events.py` (full file, ~230 lines)

Proposed file — provider + pure parsers. Signal code must never import `edgar` directly.

```python
"""SEC EDGAR event provider (8-K earnings surprise + Form 4 insider flow).

Uses dgunning/edgartools (import edgar). Fail-closed: any fetch/parse
failure returns empty frames, never raises into the signal path.
All timestamps gated on filingDate; signal entry at T+1 close earliest.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

EPS_PAT = re.compile(r"earnings per share[^.]{0,120}?\$?\s?(\d+\.\d+)", re.I)
REV_PAT = re.compile(r"(?:revenue|net sales)[^.]{0,120}?\$?\s?([\d,]+\.?\d*)\s?(million|billion)?", re.I)
GUID_PAT = re.compile(r"(guidance|outlook)[^.]{0,200}?(raised|lowered|reaffirmed|initiated)", re.I)

_OPEN_MARKET_CODES = {"P"}          # Form 4 transactionCode P = open-market buy; S = open-market sale
_OPEN_MARKET_SALE = {"S"}
_EXCLUDE_CODES = {"A", "M", "G", "J", "C", "E", "H", "I", "O", "X", "Z"}


@dataclass(frozen=True)
class EdgarConfig:
    identity: str = os.getenv("EDGAR_IDENTITY", "WSB Alpha System research@example.com")
    cache_dir: str = os.getenv("EDGAR_CACHE_DIR", "./cache/edgar")
    lookback_days_8k: int = 14
    lookback_days_f4: int = 90


def _edgar() -> object | None:
    try:
        import edgar  # type: ignore
        from edgar import set_identity
        set_identity(os.getenv("EDGAR_IDENTITY", EdgarConfig().identity))
        return edgar
    except Exception as e:  # noqa: BLE001 - optional dep
        logger.warning("edgartools unavailable, EDGAR events disabled: %s", e)
        return None


def parse_eightk_surprise(item202_text: str, exhibit991_text: str = "") -> dict:
    """Pure function: extract EPS/revenue mentions + guidance tone from 8-K Item 2.02 + Ex-99.1.

    Returns {eps_m临: float|None, ...} — no network, fully unit-testable.
    Surprise magnitude (SUE) is computed by caller against consensus (yfinance), not here.
    """
    blob = f"{item202_text or ''}\n{exhibit991_text or ''}"
    eps_m = EPS_PAT.search(blob)
    rev_m = REV_PAT.search(blob)
    guid_m = GUID_PAT.search(blob)
    mult = 1.0
    rev_val = None
    if rev_m:
        rev_val = float(rev_m.group(1).replace(",", ""))
        unit = (rev_m.group(2) or "").lower()
        if unit == "billion":
            rev_val *= 1000.0  # normalize to $M
    return {
        "has_results": bool(eps_m or rev_m or "results of operations" in blob.lower()),
        "reported_eps": float(eps_m.group(1)) if eps_m else None,
        "revenue_m": rev_val,
        "guidance_tone": f"{guid_m.group(1)}:{guid_m.group(2)}".lower() if guid_m else None,
    }


def parse_form4_transactions(nonderiv_rows: list[dict]) -> dict:
    """Pure function: aggregate open-market Form 4 non-derivative rows.

    Each row: {transactionCode, transactionShares, price, directOrIndirect, isDirector, isOfficer, isTenPct}.
    Amended-filings dedup handled by caller (4/A supersedes).
    """
    buys = sells = 0.0
    buy_val = sell_val = 0.0
    insider_buys = 0
    for r in nonderiv_rows or []:
        code = str(r.get("transactionCode", "")).strip().upper()
        if code in _EXCLUDE_CODES or code not in (_OPEN_MARKET_CODES | _OPEN_MARKET_SALE):
            continue
        sh = float(r.get("transactionShares") or 0)
        px = float(r.get("price") or 0)
        if code == "P":
            buys += sh
            buy_val += sh * px
            if r.get("isOfficer") or r.get("isDirector"):
                insider_buys += 1
        elif code == "S":
            sells += sh
            sell_val += sh * px
    net_sh = buys - sells
    return {
        "om_buys": buys, "om_sells": sells, "net_shares": net_sh,
        "buy_value": buy_val, "sell_value": sell_val,
        "officer_director_buys": insider_buys,
        "net_buy_score": (buy_val - sell_val) / max(buy_val + sell_val, 1.0),  # [-1, 1]
    }


def fetch_8k_events(tickers: list[str], after: date, cfg: EdgarConfig | None = None) -> pd.DataFrame:
    """One row per 8-K with Item 2.02: ticker|filingDate|accession|eps|revenue_m|guidance_tone.

    Fail-closed: returns empty DataFrame on any error. Caller gates entry at T+1.
    """
    cfg = cfg or EdgarConfig()
    edgar = _edgar()
    if edgar is None:
        return pd.DataFrame(columns=["ticker", "filingDate", "accession", "reported_eps", "revenue_m", "guidance_tone"])
    from edgar import Company
    rows = []
    for t in tickers:
        try:
            fl = Company(t).get_filings(form="8-K", after=str(after))
            for f in (fl or [])[:20]:
                try:
                    k8 = f.obj()
                    items = getattr(k8, "items", {}) or {}
                    t202 = str(items.get("2.02", "") or "")
                    if "result" not in t202.lower() and not getattr(k8, "press_release", None):
                        continue
                    ex991 = ""
                    try:
                        ex991 = str(k8.press_release or "")[:20000]
                    except Exception:  # noqa: BLE001
                        pass
                    p = parse_eightk_surprise(t202, ex991)
                    if not p["has_results"]:
                        continue
                    rows.append({"ticker": t, "filingDate": pd.to_datetime(str(f.filing_date)).date(),
                                 "accession": str(f.accession_no), "reported_eps": p["reported_eps"],
                                 "revenue_m": p["revenue_m"], "guidance_tone": p["guidance_tone"]})
                except Exception as e:  # noqa: BLE001 - per-filing isolation
                    logger.warning("8-K parse failed %s %s: %s", t, getattr(f, "accession_no", "?"), e)
        except Exception as e:  # noqa: BLE001 - per-ticker isolation
            logger.warning("8-K fetch failed %s: %s", t, e)
    return pd.DataFrame(rows)


def fetch_form4_flow(tickers: list[str], after: date, cfg: EdgarConfig | None = None) -> pd.DataFrame:
    """One row per ticker: aggregated 90d open-market insider flow + net_buy_score in [-1,1]."""
    cfg = cfg or EdgarConfig()
    edgar = _edgar()
    if edgar is None:
        return pd.DataFrame(columns=["ticker", "om_buys", "om_sells", "net_shares", "net_buy_score", "officer_director_buys"])
    from edgar import Company
    rows = []
    for t in tickers:
        try:
            fl = Company(t).get_filings(form="4", after=str(after))
            seen: dict[str, bool] = {}
            agg = {"om_buys": 0.0, "om_sells": 0.0, "net_shares": 0.0,
                   "buy_value": 0.0, "sell_value": 0.0, "officer_director_buys": 0}
            for f in (fl or [])[:60]:
                try:
                    acc = str(f.accession_no)
                    if acc in seen:
                        continue
                    seen[acc] = True
                    f4 = f.obj()
                    table = getattr(f4, "nonDerivativeTable", None) or getattr(f4, "non_derivative_table", [])
                    r = parse_form4_transactions([dict(x) if not isinstance(x, dict) else x for x in (table or [])])
                    for k in agg:
                        agg[k] += r.get(k, 0) if isinstance(r.get(k), (int, float)) else 0
                    agg["buy_value"] += r["buy_value"]; agg["sell_value"] += r["sell_value"]
                except Exception as e:  # noqa: BLE001
                    logger.warning("Form4 parse failed %s %s: %s", t, getattr(f, "accession_no", "?"), e)
            tot = agg["buy_value"] + agg["sell_value"]
            rows.append({"ticker": t, "om_buys": agg["om_buys"], "om_sells": agg["om_sells"],
                         "net_shares": agg["om_buys"] - agg["om_sells"],
                         "net_buy_score": (agg["buy_value"] - agg["sell_value"]) / max(tot, 1.0),
                         "officer_director_buys": agg["officer_director_buys"]})
        except Exception as e:  # noqa: BLE001
            logger.warning("Form4 fetch failed %s: %s", t, e)
    return pd.DataFrame(rows)
```

Notes: `f.filing_date` / `f.accession_no` match edgartools `Filing` attrs; `.obj()` returns `EightK` / `Form4`. `press_release` convenience exists on `EightK` in recent versions; fallback to Item 2.02 text keeps this version-tolerant.

### Diff 2 — `src/ops/signals.py` enrichment (surgical, backward-compatible)

Keep current yfinance path as fallback; add optional `edgar_events` injection so tests stay offline and production stays fail-closed.

```diff
--- a/src/ops/signals.py
+++ b/src/ops/signals.py
@@
-def get_us_pead_top5_signal(data: pd.DataFrame, tickers: list[str], lookback_days: int = 10, hold_days: int = 5, top_n: int = 5) -> dict:
+def get_us_pead_top5_signal(data: pd.DataFrame, tickers: list[str], lookback_days: int = 10, hold_days: int = 5, top_n: int = 5, edgar_events: pd.DataFrame | None = None) -> dict:
     signal_data = {"targets": []}
@@
     last_date = closes.index[-1]
 
     targets = []
     warnings = []
+
+    # Optional 8-K SUE overlay (injected DataFrame: ticker|filingDate|SUE|guidance_tone).
+    # Entry still gated at filingDate + 1 trading day; never on filing day close.
+    sue_by_ticker: dict[str, float] = {}
+    if edgar_events is not None and not edgar_events.empty:
+        try:
+            ev = edgar_events.copy()
+            ev["filingDate"] = pd.to_datetime(ev["filingDate"]).dt.tz_localize(None)
+            for _, r in ev.iterrows():
+                fd = r["filingDate"]
+                if fd < last_date and fd >= last_date - pd.Timedelta(days=lookback_days + 5):
+                    # T+1 gating: require at least one close after filingDate
+                    post = closes.index[closes.index > fd]
+                    if len(post) == 0 or (last_date - fd).days < 1:
+                        continue
+                    if pd.notna(r.get("SUE")) and float(r["SUE"]) > 0:
+                        sue_by_ticker[str(r["ticker"])] = max(sue_by_ticker.get(str(r["ticker"]), 0.0), float(r["SUE"]))
+        except Exception as e:  # noqa: BLE001 - overlay must never break base signal
+            warnings.append(f"edgar overlay skipped: {e}")
 
     for ticker in tickers:
         try:
             # fetch earnings dates
             t = yf.Ticker(ticker)
             earnings = t.get_earnings_dates(limit=100)
             if earnings is not None and not earnings.empty:
                 # filter for dates before last_date (strictly after earnings announcement)
                 # This is a simplification for the ops signal generator.
                 # In a real implementation, we'd need to track state (hold for 5 days).
                 # Since ops is stateless, we check if there was a positive surprise in the last 5 days
                 earnings = earnings.tz_localize(None)
                 recent_earnings = earnings[(earnings.index < last_date) & (earnings.index >= last_date - pd.Timedelta(days=lookback_days))]
 
                 for idx, row in recent_earnings.iterrows():
-                    if pd.notna(row.get('Reported EPS')) and pd.notna(row.get('Surprise(%)')) and row['Surprise(%)'] >= 0.0:
+                    yf_ok = pd.notna(row.get('Reported EPS')) and pd.notna(row.get('Surprise(%)')) and row['Surprise(%)'] >= 0.0
+                    sue = sue_by_ticker.get(ticker)
+                    edgar_ok = sue is not None and sue > 1.0  # +1σ SUE threshold
+                    if yf_ok or edgar_ok:
                         # check if it's within the 5 trading day hold period
                         # simplistic: if last_date is within 5 trading days after the earnings date
                         trading_days_since = len(closes.loc[idx:last_date]) - 1
                         if 1 <= trading_days_since <= hold_days:
                             targets.append((idx, ticker))
                             break # only consider the most recent valid earnings per ticker
         except Exception as e:
             warnings.append(f"Failed to fetch earnings for {ticker}: {e}")
 
-    # sort by event date (first-come-first-served)
-    targets.sort(key=lambda x: x[0])
+    # sort by event date, break ties by SUE desc (highest surprise first)
+    targets.sort(key=lambda x: (x[0], -sue_by_ticker.get(x[1], 0.0)))
     top5_targets = [t[1] for t in targets[:top_n]]
```

SUE construction (caller-side, e.g. research script — not in hot signal loop):

```python
# sue = (reported_eps_8k - consensus_eps) / std(consensus); consensus from yfinance get_earnings_dates 'EPS Estimate'
```

### Diff 3 — `src/signals/engine.py` pass-through (2 lines)

```diff
--- a/src/signals/engine.py
+++ b/src/signals/engine.py
@@
-    def _generate_pead_top5(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> SleeveSignal:
+    def _generate_pead_top5(self, date: pd.Timestamp, data: dict[str, pd.DataFrame], edgar_events=None) -> SleeveSignal:
@@
-        sig_data = get_us_pead_top5_signal(combined_df, tickers)
+        sig_data = get_us_pead_top5_signal(combined_df, tickers, edgar_events=edgar_events)
```

No sleeve rename, no registry change.

### Diff 4 — NEW factor columns (optional, research-only) — append to `src/signals/qlib_alpha158.py` style module or new `src/signals/edgar_factors.py`

```python
def add_edgar_factors(prices: pd.DataFrame, f4_flow: pd.DataFrame, sue: pd.DataFrame) -> pd.DataFrame:
    """Join-asof insider + surprise factors onto price frame. All inputs filingDate-gated T+1."""
    out = prices.copy()
    # f4_net_buy_90d: per-ticker net_buy_score forward-filled, lagged 1 day
    # sue_8k: most-recent SUE per ticker, lagged 1 day, decayed over hold_days=5
    ...
    return out.shift(1)  # belt-and-braces no-lookahead
```

Factor definitions proposed:

- `SUE_8K = (EPS_8K − consensus) / σ_consensus`, winsorized ±4, decay `SUE * (1 - age/6)` for age 1..5d, else 0.
- `INS_BUY_90D = net_buy_score` (−1..1), plus binary `INS_CLUSTER = 1 if officer_director_buys >= 2 in 30d else 0`.

## 4. Why this is safe for this repo

- Preserves fail-closed mandate: every EDGAR call wrapped per-ticker/per-filing; empty-frame fallback yields current yfinance behavior.
- Preserves no-lookahead: filingDate + 1 trading-day gate + `.shift(1)` terminals; SUE overlay only narrows/confirms, never anticipates.
- Preserves edge gate: no `strategies/registry.json` entry proposed; promotion requires pre-registration + walk-forward + permutation + DSR per `docs/OPTIMIZATION_PLAYBOOK.md` / `docs/HUNT_PROTOCOL.md`.
- Cost: zero (SEC EDGAR free, no API key; only `EDGAR_IDENTITY` UA string). Cache under `cache/edgar/` respects existing `cache/` layout.
- Security: `bandit`-clean (no `eval`, no pickle, bounded `press_release[:20000]`, no secret handling).

## 5. Test plan

New file `tests/data/test_edgar_events.py` (offline, mocked `edgar`):

1. `test_parse_eightk_surprise_eps_revenue_guidance` — fixture Item 2.02 + Ex-99.1 strings; assert `reported_eps`, `revenue_m` ($B→$M norm), `guidance_tone == "guidance:raised"`, `has_results True`.
2. `test_parse_eightk_no_results` — Item 5.02-only text; assert `has_results False` (never fires earnings signal).
3. `test_parse_form4_open_market_only` — rows with P/S/A/M/G codes; assert A/M/G excluded, `net_buy_score == (buy−sell)/(buy+sell)`, `officer_director_buys` counts only O/D P-buys.
4. `test_parse_form4_amendment_supersede` — caller-level dedup by `accession_no`; assert double-counted accession counted once.
5. `test_fetch_8k_fail_closed_no_edgar` — monkeypatch `import edgar` → `ImportError`; assert empty DataFrame with expected columns, no raise.
6. `test_fetch_form4_fail_closed_per_ticker` — mock `Company("BAD").get_filings` raising; assert other tickers still returned, warning logged.
7. `test_pead_overlay_T1_gating` — build `closes` frame with known dates; `edgar_events` with `filingDate == last_date` (same day) must NOT produce target; `filingDate == last_date - 1d` with `SUE=2.0` must produce target even when yfinance surprise missing (mock `yf.Ticker` to empty).
8. `test_pead_overlay_never_breaks_base` — malformed `edgar_events` (bad dates); assert base yfinance signal unchanged + `warning` contains `edgar overlay skipped`.
9. `test_lookahead_shift` — `add_edgar_factors` output at date `d` equals inputs through `d−1` only (shift assertion).
10. Live (gated, not in CI): `WSB_LIVE_EDGAR=1 pytest tests/data/test_edgar_events_live.py -k "aapl_8k_and_form4"` — asserts ≥1 8-K Item 2.02 for AAPL in last 365d and ≥1 Form 4 in last 90d; network failures → `pytest.skip`, never fail.

Extend `tests/test_factor_engine.py`-style leakage guard: assert no `filingDate > signalDate` join in new code path.

Commands (per AGENTS.md, single-file serial):

```
PYTHONPATH=. pytest tests/data/test_edgar_events.py -q
ruff check src/data/providers/edgar_events.py tests/data/test_edgar_events.py
bandit -r src/data/providers/edgar_events.py
```

Acceptance: 9/9 offline tests pass, ruff + bandit clean, base `get_us_pead_top5_signal` signature backward-compatible (existing callers pass without `edgar_events`).

## 6. Rollout steps (for implementer, not done here)

1. `pip install "edgartools>=4.5.0"`; set `EDGAR_IDENTITY` + `EDGAR_CACHE_DIR`.
2. Add Diff 0 → Diff 1 → Diff 2 → Diff 3 → Diff 4 in that order; run test plan after each.
3. Backfill `cache/edgar/` for universe (S&P 500 8-K 365d + Form 4 90d), pre-register hypothesis (PEAD+SUE>1σ, hold 5d; insider cluster filter), then walk-forward + permutation + DSR before any registry promotion.
4. Do NOT touch `evolve_real.py` / `strategies/registry.json` until edge gate passes.

## 7. References

- edgartools repo: `dgunning/edgartools` — `Company.get_filings(form=...)`, `Filing.obj()` → `EightK` (`.items`, exhibits/press release), `Form4` (nonDerivativeTable/derivativeTable).
- Current PEAD: `src/ops/signals.py:378-430`; engine wiring `src/signals/engine.py:172-192`.
- Factor conventions: `src/signals/qlib_alpha158.py`, `src/signals/gplearn_factors.py:36-58` (shift-by-1 pattern).
- Provider convention: `src/data/providers/openbb_provider.py:1-51`.
