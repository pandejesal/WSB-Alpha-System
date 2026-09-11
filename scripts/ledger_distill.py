#!/usr/bin/env python3
"""Ledger-to-brief distillation (E-self-1, EVOQUANT distill step).

Reads run-logs/trials.jsonl via TrialLedger and writes
docs/data/ledger_digest.json:
  - per-family trial counts + REJECTED rate (conviction signal)
  - blocked_combos: family+param_hash with >=2 REJECTIONS (breeders skip these)

Fail-closed: missing/empty ledger -> digest with zero counts (never raises).
Called manually or pre-breed; breed_proposals() consults blocked_combos.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backtest.defend.trial_ledger import TrialLedger

DIGEST_PATH = ROOT / "docs" / "data" / "ledger_digest.json"
BLOCK_THRESHOLD = 2  # rejections before a combo is blocked


# _normalize_metrics strips everything but sharpe/profit_factor/max_dd at write time,
# so family never survives in metrics — derive it from the strategy_id prefix.
_KNOWN_FAMILIES = (
    "spy_sma", "spy_rsi2", "spy_ltrend", "us_momentum", "us_lowvol", "us_ltrend",
    "btc_vol", "btc_donchian", "btc_regime", "gap_mr", "momentum", "trend",
    "mean_reversion", "vol_targeting", "low_vol", "event_driven", "breakout_burst",
    "risk_sizing", "quality_low_vol", "factor_momentum",
)


def _family_of(t) -> str:
    fam = (t.metrics or {}).get("family")
    if fam:
        return str(fam)
    sid = t.strategy_id or ""
    best = ""
    for f in _KNOWN_FAMILIES:
        if sid.startswith(f) and len(f) > len(best):
            best = f
    return best or "unknown"


def _param_hash(params: dict) -> str:
    canon = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()[:12]


def distill(ledger_path: str = "run-logs/trials.jsonl") -> dict:
    ledger = TrialLedger(path=ledger_path)
    trials = ledger.load_trials()
    families: dict[str, dict] = {}
    blocked: list[dict] = []
    rej_combos: Counter = Counter()
    for t in trials:
        fam = _family_of(t)
        f = families.setdefault(fam, {"n": 0, "rejected": 0, "promoted": 0})
        f["n"] += 1
        if t.status == "REJECTED":
            f["rejected"] += 1
            rej_combos[(fam, _param_hash(t.params or {}))] += 1
        elif t.status == "PROMOTED":
            f["promoted"] += 1
    for (fam, ph), n in rej_combos.items():
        if n >= BLOCK_THRESHOLD:
            blocked.append({"family": fam, "param_hash": ph, "rejections": n})
    for fam, f in families.items():
        f["reject_rate"] = round(f["rejected"] / f["n"], 3) if f["n"] else 0.0
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_trials": len(trials),
        "corrupt_lines": ledger.corrupt_lines,
        "families": families,
        "blocked_combos": blocked,
    }


def main() -> int:
    digest = distill()
    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DIGEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(digest, indent=2), encoding="utf-8")
    tmp.replace(DIGEST_PATH)
    print(f"distilled {digest['n_trials']} trials -> {DIGEST_PATH} "
          f"({len(digest['blocked_combos'])} blocked combos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
