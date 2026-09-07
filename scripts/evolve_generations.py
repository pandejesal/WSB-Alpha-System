#!/usr/bin/env python3
"""Generational selection for the evolve registry: repair, purge, prune, breed.

Repair:  strategies/registry.json may carry a truncated fragment from past
  concurrent writes (JSON 'Extra data'). The valid prefix is kept; the
  fragment is quarantined to docs/data/registry_fragment_<ts>.json.
Purge:   entries with stub signatures (gates '5/5' + minerva metrics,
  method != 'evolve_real') are RANDOM ROLLS from evolve_continuous.py,
  not backtests. They are moved to docs/data/registry_purged_stub.json,
  never silently dropped.
Prune (death): survivors ranked by TRACK-CLEAR COUNT (2026-09-06) — the
  number of gatespec38 tracks each entry fully clears — tiebreak OOS Sharpe;
  top K keep status paper, the rest are marked retired (record kept, never
  deleted). Entries clearing the most tracks breed the next generation;
  single-track and zero-track entries retire.
Breed:   top breeders' params are mutated into next-gen proposals at
  docs/data/next_gen_proposals.jsonl for the evolve loop to consume.

Paper only. Nothing here places orders or touches live state.
"""
import json
import os
import random
import sys
import pathlib
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest.gatespec38_tracks import check_track  # noqa: E402

REG = ROOT / "strategies/registry.json"
DATA = ROOT / "docs" / "data"
KEEP_TOP = 25
N_PROPOSALS = 20


def log(msg):
    print(msg, flush=True)


def load_repair():
    raw = REG.read_text(encoding="utf-8")
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as e:
        log(f"registry corrupt ({e}); repairing: keeping valid prefix")
        obj, idx = json.JSONDecoder().raw_decode(raw)
        frag = raw[idx:].strip()
        if frag:
            fp = DATA / f"registry_fragment_{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
            fp.write_text(frag, encoding="utf-8")
            log(f"fragment quarantined to {fp.name} ({len(frag)} chars)")
        return obj, frag


def oos_sharpe(s):
    m = s.get("metrics", {}) or {}
    for k in ("oos_sharpe", "sharpe"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return -9.0


def is_stub(s):
    if s.get("method") == "evolve_real":
        return False
    if s.get("gates_passed") != "5/5":
        return False
    return "minerva" in json.dumps(s.get("metrics", {}))


def track_clears(s) -> tuple:
    """(tracks_cleared_count, [track names]) for a registry entry.

    Builds the metrics dict check_track() expects from stored metrics;
    missing tmin (pre-2026-09-06 entries) defaults to 0 via _normalize_metric,
    so unverifiable TIM simply fails tmin tracks — honest, never assumed.
    """
    m = s.get("metrics", {}) or {}
    metrics = {
        "sharpe": m.get("sharpe", -9.0),
        "max_dd": m.get("max_dd", 9.0),
        "oos": m.get("oos_sharpe", m.get("oos", -9.0)),
        "excess": m.get("excess_spy", m.get("excess", -999.0)),
        "dsr": m.get("dsr", 0.0),
        "trips": m.get("round_trips", m.get("trips", 0)),
        "tmin": m.get("tmin", 0.0),
    }
    try:
        names = check_track(metrics)
    except Exception:
        names = []
    return len(names), names


def fitness(s) -> tuple:
    """Sort key: most tracks cleared first, OOS Sharpe tiebreak."""
    n, _ = track_clears(s)
    return (n, oos_sharpe(s))


def main():
    rng = random.Random(7)
    obj, _ = load_repair()
    strategies = obj.get("strategies", [])
    log(f"loaded {len(strategies)} entries")

    # dedupe by id: keep best OOS sharpe
    best = {}
    for s in strategies:
        i = s.get("id", "?")
        if i not in best or oos_sharpe(s) > oos_sharpe(best[i]):
            best[i] = s
    log(f"deduped to {len(best)} unique ids")

    curated, real, stub = [], [], []
    for s in best.values():
        if is_stub(s):
            stub.append(s)
        elif s.get("method") == "evolve_real" or s.get("gates_passed") == "REAL-4/4":
            real.append(s)
        else:
            curated.append(s)  # original YAMLs, ported, pending — never purge
    log(f"curated={len(curated)} real={len(real)} stub-poison={len(stub)}")
    if stub:
        pp = DATA / "registry_purged_stub.json"
        pp.write_text(json.dumps(stub, indent=1), encoding="utf-8")
        log(f"purged {len(stub)} stub entries -> {pp.name}")

    survivors = curated + real
    # Track-count fitness: most gates cleared first, OOS Sharpe tiebreak.
    for s in survivors:
        n, names = track_clears(s)
        (s.get("metrics", {}) or {})["tracks_cleared"] = n
        if names:
            (s.get("metrics", {}) or {})["tracks"] = names
    from collections import Counter
    log(f"track-clear distribution: {dict(sorted(Counter((s.get('metrics', {}) or {}).get('tracks_cleared', 0) for s in survivors).items()))}")
    survivors.sort(key=fitness, reverse=True)
    for i, s in enumerate(survivors):
        if s.get("status") in ("retired",):
            continue
        if i < len(curated) + KEEP_TOP or s in curated:
            if s.get("status") not in ("paper", "ported", "pending_approval", "inactive"):
                s["status"] = "paper"
        else:
            # death: only real evolved entries retire; curated originals stay
            if s.get("method") == "evolve_real":
                s["status"] = "retired"
    alive = [s for s in survivors if s.get("status") != "retired"]
    dead = [s for s in survivors if s.get("status") == "retired"]
    log(f"alive={len(alive)} retired={len(dead)}")

    # breed next generation from multi-track clearers first: entries
    # clearing >=2 tracks, then single-track by fitness, else alive fallback
    # (keeps the loop fed while nothing clears yet — expected, not broken).
    real_sorted = [s for s in survivors if s.get("method") == "evolve_real"]
    multi = [s for s in real_sorted
             if (s.get("metrics", {}) or {}).get("tracks_cleared", 0) >= 2]
    single = [s for s in real_sorted
              if (s.get("metrics", {}) or {}).get("tracks_cleared", 0) == 1]
    breeders = (multi + single)[:5] or alive[:5]
    log(f"breeders: {len(multi)} multi-track + {len(single)} single-track "
        f"-> using {len(breeders)}")
    props = []
    for b in breeders:
        params = dict((b.get("metrics", {}) or {}).get("params", {}))
        for _ in range(max(1, N_PROPOSALS // max(1, len(breeders)))):
            child = {}
            for k, v in params.items():
                if isinstance(v, bool):
                    child[k] = v
                elif isinstance(v, int):
                    child[k] = max(1, int(v * rng.uniform(0.7, 1.3)))
                elif isinstance(v, float):
                    child[k] = round(v * rng.uniform(0.7, 1.3), 4)
                else:
                    child[k] = v
            props.append({"family": b.get("family"), "bred_from": b.get("id"),
                          "params": child, "parent_oos": oos_sharpe(b)})
    pf = DATA / "next_gen_proposals.jsonl"
    # Append (never wipe): Prime/other breeders may have unconsumed lines.
    # Cap at 200 lines (keep newest); preserve the consume pointer so the
    # loop continues where it left off instead of re-scoring old lines.
    try:
        old_lines = pf.read_text(encoding="utf-8").splitlines() if pf.exists() else []
    except OSError:
        old_lines = []
    keep = [line for line in old_lines if line.strip()]
    merged = (keep + [""] if keep else []) + [json.dumps(p) for p in props]
    merged = [line for line in merged if line.strip()][-200:]
    with open(pf, "w", encoding="utf-8") as f:
        for line in merged:
            f.write(line + "\n")
    log(f"bred {len(props)} next-gen proposals appended ({len(merged)} total) -> {pf.name}")
    try:
        ptr = DATA / "next_gen_consumed.txt"
        new_mtime = str(pf.stat().st_mtime)
        if ptr.exists():
            parts = ptr.read_text(encoding="utf-8").strip().split()
            idx = int(parts[1]) if len(parts) == 2 else 0
            # clamp: consumed idx refers to old lines; appended file keeps
            # old lines at head (unless capped) so idx stays valid.
            idx = min(idx, max(0, len(merged) - len(props)))
            ptr.write_text(f"{new_mtime} {idx}", encoding="utf-8")
    except Exception as e:
        log(f"pointer preserve skipped: {e}")

    obj["strategies"] = survivors
    obj.setdefault("generations", {}).update({
        "last_prune": datetime.now(timezone.utc).isoformat(),
        "alive": len(alive), "retired": len(dead),
        "purged_stub": len(stub), "keep_top": KEEP_TOP,
    })
    tmp = REG.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    os.replace(tmp, REG)  # atomic: concurrent readers never see a half-write
    # validate
    json.loads(REG.read_text(encoding="utf-8"))
    log("registry rewritten + validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
