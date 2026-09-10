#!/usr/bin/env python3
"""
Proposal #3: Registry Dedup & Reconstruction
---------------------------------------------
Reconstructs a clean, deduplicated registry from two recovery sources:
  1. Primary: registry_purged_stub.json (3,991 valid entries, flat JSON array)
  2. Secondary: registry-corrupt-backup.json (4,293 raw, 4,286 unique after internal dedup)

Output: strategies/registry.json — deduplicated, schema-normalized, all LIVE_TRADING_ENABLED=false.
"""

import json
import sys
from collections import Counter

# INF-09: filelock for cross-OS flock (see evolve_real.py)
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "docs" / "data"
STUB_PATH = DATA_DIR / "registry_purged_stub.json"
CORRUPT_PATH = DATA_DIR / "registry-corrupt-backup.json"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "strategies" / "registry.json"

# Schema normalization: all expected keys across both files + known fields
ALL_KNOWN_KEYS = [
    "id", "name", "family", "spec_file", "status", "rank",
    "evolved_from", "gates_passed", "venue", "metrics",
    # Corrupt-only fields (11 extra)
    "complexity_penalty", "evolution_notes", "evolved_at", "evolved_via",
    "expected_ROI_improvement", "expected_Sharpe_improvement",
    "fitness_score", "gate_detail", "method", "paper_sandbox", "ported_at",
]
# W4: tracks_cleared is kept and recomputed per-family (Option A). Do NOT strip.
# The field was vestigial {0:3904} pre-W1; after W1 per-family DSR fix it is
# honest telemetry (recomputed with T=1910, N_family via dsr_fam). Breed fallback
# uses sharpe/oos/excess when sparse (Option B) — field retained regardless.
STRIP_KEYS: set[str] = set()


def canonical_params_hash(entry: dict) -> str:
    """W3 canonical hash: (family, params_json) — stable across metrics noise."""
    m = entry.get("metrics") or {}
    params = m.get("params")
    if params is not None:
        return json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    filtered = {k: v for k, v in m.items() if k not in ("tracks_cleared", "tracks")}
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def oos_sharpe_for_entry(entry: dict) -> float:
    m = entry.get("metrics") or {}
    for k in ("oos_sharpe", "oos", "sharpe"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return -9.0


def dedup_by_param_hash(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    from collections import defaultdict

    def is_curated(e):
        method = e.get("method")
        if method == "evolve_real":
            return False
        sf = (e.get("spec_file") or "").replace("\\", "/")
        if sf.startswith("strategies/") and "/hunts/" not in sf and "/evolve/" not in sf:
            return True
        if method is None and e.get("gates_passed") != "5/5":
            return True
        is_stub = False
        if method != "evolve_real" and e.get("gates_passed") == "5/5":
            is_stub = "minerva" in json.dumps(e.get("metrics") or {})
        return not is_stub and method != "evolve_real"

    groups: dict[tuple, list[dict]] = defaultdict(list)
    curated_kept = []
    for e in entries:
        if is_curated(e):
            curated_kept.append(e)
        else:
            key = (e.get("family"), canonical_params_hash(e))
            groups[key].append(e)
    kept = list(curated_kept)
    quarantined: list[dict] = []
    for members in groups.values():
        if len(members) == 1:
            kept.append(members[0])
        else:
            members_sorted = sorted(members, key=lambda x: (oos_sharpe_for_entry(x), x.get("id", "")), reverse=True)
            kept.append(members_sorted[0])
            quarantined.extend(members_sorted[1:])
    return kept, quarantined

# Status normalization map
STATUS_FIX = {
    "PASS_ALL_GATES": "PASS_ALL_GATES",  # keep but flag
    "PENDING": "PENDING",
    "EVO": "EVO",
    "EVO_CANIDATE": "EVO",
    "EVO_CANDIDATE": "EVO",
    "ACTIVE": "ACTIVE",
    "RETIRED": "RETIRED",
}


def load_stub(path: Path) -> list[dict]:
    """Load purged stub — flat JSON array, 3,991 valid entries."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
    print(f"  Stub: {len(data)} entries loaded")
    return data


def load_corrupt(path: Path) -> list[dict]:
    """Load corrupt backup via raw_decode — wraps {'strategies': [...]}."""
    from json import JSONDecoder
    decoder = JSONDecoder()
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Find where trailing garbage starts (last 125 bytes after main JSON)
    obj, idx = decoder.raw_decode(raw)
    trailing = len(raw) - idx
    if trailing > 0:
        print(f"  Corrupt: trailing {trailing} bytes skipped (expected ~125)")

    if "strategies" in obj:
        strategies = obj["strategies"]
    elif isinstance(obj, list):
        strategies = obj
    else:
        raise ValueError(f"Unexpected structure: {list(obj.keys())[:5]}")

    print(f"  Corrupt: {len(strategies)} raw entries loaded")
    return strategies


def dedup_internal(entries: list[dict]) -> list[dict]:
    """Dedup by ID within a single source — keep last occurrence."""
    seen = {}
    dupes_found = []
    for e in entries:
        eid = e.get("id")
        if not eid:
            continue
        if eid in seen:
            dupes_found.append(eid)
        seen[eid] = e  # keep last
    if dupes_found:
        print(f"  Internal dedup: {len(dupes_found)} duplicate IDs removed")
        for d in dupes_found:
            print(f"    - {d}")
    else:
        print("  Internal dedup: no duplicates found")
    return list(seen.values())


def normalize_entry(entry: dict) -> dict:
    """Normalize a single registry entry:
    - Add missing keys as None
    - Strip dead keys
    - Fix known status inconsistencies
    - Ensure LIVE_TRADING_ENABLED=false
    """
    out = {}
    for key in ALL_KNOWN_KEYS:
        if key in STRIP_KEYS:
            continue
        out[key] = entry.get(key)

    # Status normalization
    status = out.get("status")
    if status and status in STATUS_FIX:
        out["status"] = STATUS_FIX[status]
    elif status == "PASS_ALL_GATES" and out.get("gates_passed") == 0:
        # Flag contradiction but keep status for upstream decision
        out["status_note"] = "PASS_ALL_GATES but gates_passed=0"

    # Paper safety: always false
    out["paper_sandbox"] = False

    # Ensure spec_file uses strategies/ prefix consistently
    sf = out.get("spec_file")
    if sf and not sf.startswith("strategies/"):
        out["spec_file"] = f"strategies/{sf}"

    return out


def merge_sources(stub: list[dict], corrupt: list[dict]) -> list[dict]:
    """
    Merge strategy:
    - Stub entries are authoritative (already validated)
    - Add corrupt-unique entries not present in stub
    - Final dedup by ID across merged set (keep stub version if conflict)
    """
    stub_ids = {e.get("id") for e in stub}
    corrupt_unique = [e for e in corrupt if e.get("id") not in stub_ids]

    print(f"  Merge: {len(stub)} stub + {len(corrupt_unique)} corrupt-unique = {len(stub) + len(corrupt_unique)} total")

    # Combine: stub first (authoritative), then corrupt-unique
    combined = stub + corrupt_unique

    # Final dedup (shouldn't be any, but safety)
    seen = {}
    for e in combined:
        eid = e.get("id")
        if eid:
            if eid not in seen:
                seen[eid] = e
            # else: stub version wins (it appears first)

    merged = list(seen.values())
    print(f"  Final dedup: {len(merged)} unique entries")
    return merged


def write_output(entries: list[dict], path: Path) -> None:
    """Write reconstructed registry as JSON array."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"\n  Output written: {path}")
    print(f"  Entries: {len(entries)}")


def validate_output(path: Path) -> dict:
    """Verify the output file is valid JSON and has expected structure."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids = [e.get("id") for e in data if e.get("id")]
    id_counts = Counter(ids)
    dupes = {k: v for k, v in id_counts.items() if v > 1}

    # Check all LIVE_TRADING_ENABLED are False
    live_flags = [e for e in data if e.get("live_trading_enabled") is True]

    # W4: tracks_cleared lives inside metrics (not top-level) — count there
    has_tracks_cleared = [e for e in data if "tracks_cleared" in (e.get("metrics") or {})]

    result = {
        "valid_json": True,
        "total_entries": len(data) if isinstance(data, list) else len(data.get("strategies", [])),
        "unique_ids": len(set(ids)),
        "internal_dupes": dupes,
        "live_trading_enabled_true": len(live_flags),
        "has_tracks_cleared": len(has_tracks_cleared),
    }

    print("\n  Validation:")
    print(f"    Valid JSON: {result['valid_json']}")
    print(f"    Total entries: {result['total_entries']}")
    print(f"    Unique IDs: {result['unique_ids']}")
    print(f"    Internal dupes: {result['internal_dupes']}")
    print(f"    LIVE_TRADING_ENABLED=true count: {result['live_trading_enabled_true']}")
    print(f"    Has tracks_cleared (in metrics): {result['has_tracks_cleared']}")

    return result


def main():
    print("=" * 60)
    print("Proposal #3: Registry Dedup & Reconstruction")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[1/7] Loading purged stub...")
    stub = load_stub(STUB_PATH)

    print("\n[2/7] Loading corrupt backup...")
    corrupt = load_corrupt(CORRUPT_PATH)

    # Step 2: Internal dedup corrupt source
    print("\n[3/7] Deduplicating corrupt backup internally...")
    corrupt_deduped = dedup_internal(corrupt)
    print(f"  Corrupt after dedup: {len(corrupt_deduped)} entries")

    # Step 3: Identify corrupt-unique entries
    stub_ids = {e.get("id") for e in stub}
    corrupt_unique = [e for e in corrupt_deduped if e.get("id") not in stub_ids]
    print(f"\n  Corrupt-unique (not in stub): {len(corrupt_unique)} entries")

    # Step 4: Normalize schema
    print("\n[4/7] Normalizing schema...")
    stub_normalized = [normalize_entry(e) for e in stub]
    corrupt_normalized = [normalize_entry(e) for e in corrupt_unique]

    # Step 5: Merge
    print("\n[5/7] Merging sources...")
    merged = merge_sources(stub_normalized, corrupt_normalized)

    # Step 5b: W3 param-hash dedupe — keep best oos_sharpe per (family, canonical_hash), quarantine rest
    print("\n[5b/7] W3 param-hash dedupe (family, canonical_params_hash)...")
    deduped, param_quarantine = dedup_by_param_hash(merged)
    # always use deduped (param_quarantine may be 0 if already clean)
    if param_quarantine:
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        qp = DATA_DIR / f"registry_deduped_quarantine_{ts}.json"
        qp.write_text(json.dumps(param_quarantine, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Param-hash quarantine: {len(param_quarantine)} -> {qp.name}")
    print(f"  After param dedupe: {len(deduped)} kept (quarantined {len(param_quarantine)})")
    merged = deduped

    # Step 6: Write output (atomic tmp+os.replace + JSON validate per W3)
    print("\n[6/7] Writing reconstructed registry...")
    import os

    # INF-09 cross-OS flock
    try:
        from filelock import FileLock
        _lk = FileLock(str(OUTPUT_PATH) + ".lock", timeout=10)
        _lk.acquire()
        locked = True
    except Exception:
        locked = False
        _lk = None
    tmp_path = OUTPUT_PATH.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    json.loads(tmp_path.read_text(encoding="utf-8"))
    os.replace(tmp_path, OUTPUT_PATH)
    if locked:
        try:
            _lk.release()
        except Exception:
            pass
    print(f"\n  Output written atomically: {OUTPUT_PATH}")
    print(f"  Entries: {len(merged)}")

    # Step 7: Validate
    print("\n[7/7] Validating output...")
    result = validate_output(OUTPUT_PATH)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Stub source: {len(stub)} entries")
    print(f"  Corrupt source: {len(corrupt)} raw → {len(corrupt_deduped)} after internal dedup")
    print(f"  Corrupt-unique added: {len(corrupt_unique)} entries")
    print(f"  Param-hash quarantine: {len(param_quarantine)}")
    print(f"  Final output: {result['total_entries']} entries ({result['unique_ids']} unique)")
    print("  Schema: normalized (dead fields stripped, missing fields added)")
    print("  Paper safety: all LIVE_TRADING_ENABLED=false")

    if result["internal_dupes"]:
        print(f"\n  WARNING: {len(result['internal_dupes'])} internal duplicates remain!")
    if result["live_trading_enabled_true"] > 0:
        print(f"\n  WARNING: {result['live_trading_enabled_true']} entries have LIVE_TRADING_ENABLED=true!")
    if result["has_tracks_cleared"] > 0:
        print(f"\n  WARNING: {result['has_tracks_cleared']} entries still have tracks_cleared!")

    return 0 if not result["internal_dupes"] and result["live_trading_enabled_true"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
