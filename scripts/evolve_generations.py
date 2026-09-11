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
import pathlib
import random
import sys
import threading
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest.gatespec38_tracks import check_track, recompute_dsr

REG = ROOT / "strategies/registry.json"
# S5: intra-process guard for the registry rewrite. FileLock excludes across
# processes, but on Windows same-process threads share the lock owner, so
# threads are serialized here; FileLock below covers separate processes.
_REGISTRY_WRITE_LOCK = threading.Lock()
DATA = ROOT / "docs" / "data"
KEEP_TOP = 25
N_PROPOSALS = 20


def log(msg):
    print(msg, flush=True)


def load_repair():
    raw = REG.read_text(encoding="utf-8")
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            log(f"registry legacy list form ({len(obj)} entries) — wrapping to object")
            obj = {"strategies": obj}
        return obj, None
    except json.JSONDecodeError as e:
        log(f"registry corrupt ({e}); repairing: keeping valid prefix")
        obj, idx = json.JSONDecoder().raw_decode(raw)
        frag = raw[idx:].strip()
        if frag:
            fp = DATA / f"registry_fragment_{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
            fp.write_text(frag, encoding="utf-8")
            log(f"fragment quarantined to {fp.name} ({len(frag)} chars)")
        if isinstance(obj, list):
            obj = {"strategies": obj}
        return obj, frag


def oos_sharpe(s):
    m = s.get("metrics", {}) or {}
    for k in ("oos_sharpe", "sharpe"):
        v = m.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return -9.0


def canonical_params_hash(s) -> str:
    """W3: (family, canonical_params_json_hash) — params if present else filtered metrics."""
    m = s.get("metrics") or {}
    params = m.get("params")
    if params is not None:
        return json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    filtered = {k: v for k, v in m.items() if k not in ("tracks_cleared", "tracks")}
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def is_stub(s):
    if s.get("method") == "evolve_real":
        return False
    if s.get("gates_passed") != "5/5":
        return False
    return "minerva" in json.dumps(s.get("metrics", {}))


def _resolve_dsr(m: dict) -> float:
    """Resolve DSR using per-family N (W1 fix) — prefers dsr_fam, else recompute.

    W1 moved DSR gate from global TRIAL_COUNT(~10k) to per-family FAM_TRIALS(~500-1000).
    Stored dsr may be global-N (stale, ~0.02 for sharpe~0.9). Prefer the per-family
    value: dsr_fam if present, else recompute via recompute_dsr(T=1910, sharpe, N_family)
    when fam_trials is available. Falls back to stored dsr only if neither exists.
    Never assumes; missing N returns stored dsr (honest, may still fail gate).
    """
    if "dsr_fam" in m and isinstance(m["dsr_fam"], (int, float)):
        return float(m["dsr_fam"])
    if "fam_trials" in m and "sharpe" in m:
        try:
            n = max(1, int(m["fam_trials"]))
            sharpe = float(m["sharpe"])
            rec = recompute_dsr(1910, sharpe, n)
            if 0.0 <= rec <= 1.0:
                return float(rec)
        except Exception:
            pass
    v = m.get("dsr", 0.0)
    try:
        return float(v)
    except Exception:
        return 0.0


def track_clears(s) -> tuple:
    """(tracks_cleared_count, [track names]) for a registry entry.

    Builds the metrics dict check_track() expects from stored metrics;
    missing tmin (pre-2026-09-06 entries) defaults to 0 via _normalize_metric,
    so unverifiable TIM simply fails tmin tracks — honest, never assumed.

    W4 fix: DSR is resolved via per-family N (dsr_fam or recomputed with
    T=1910 and fam_trials) so the field is no longer vestigial {0:3904}.
    Gate thresholds themselves are unchanged (Do NOT touch).
    """
    m = s.get("metrics", {}) or {}
    raw_dd = m.get("max_dd", 9.0)
    try:
        dd = abs(float(raw_dd)) if isinstance(raw_dd, (int, float)) else 9.0
    except Exception:
        dd = 9.0
    metrics = {
        "sharpe": m.get("sharpe", -9.0),
        "max_dd": dd,
        "oos": m.get("oos_sharpe", m.get("oos", -9.0)),
        "excess": m.get("excess_spy", m.get("excess", -999.0)),
        "dsr": _resolve_dsr(m),
        "trips": m.get("round_trips", m.get("trips", 0)),
        "tmin": m.get("tmin", 0.0),
    }
    try:
        names = check_track(metrics)
    except Exception:
        names = []
    return len(names), names


def fitness(s) -> tuple:
    """Sort key: most tracks cleared first, OOS Sharpe tiebreak.

    W4: honest telemetry — tracks_cleared is recomputed per-family (see
    track_clears). When the field is sparse (still ~0 for all), breeding
    falls back to sharpe/oos/excess ranking (Option B logic) rather than
    random alive[:5]. This preserves signal even when no track clears yet.
    """
    n, _ = track_clears(s)
    return (n, oos_sharpe(s))


def main():
    rng = random.Random(7)
    obj, frag = load_repair()
    # W3: support both flat-list and wrapper-dict registry forms
    if isinstance(obj, list):
        strategies = obj
        is_wrapper = False
    else:
        strategies = obj.get("strategies", [])
        is_wrapper = True
    log(f"loaded {len(strategies)} entries (wrapper={is_wrapper})")

    # dedupe by id: keep best OOS sharpe
    best = {}
    for s in strategies:
        i = s.get("id", "?")
        if i not in best or oos_sharpe(s) > oos_sharpe(best[i]):
            best[i] = s
    log(f"deduped to {len(best)} unique ids")

    # W3: param-hash dedupe — (family, canonical_params_hash) keep best oos_sharpe, quarantine rest
    # curated (method != evolve_real and not stub) are exempt — never quarantined
    from collections import defaultdict

    # first pass to identify curated ids for exemption
    def _is_curated_for_purge(e):
        if e.get("method") == "evolve_real":
            return False
        sf = (e.get("spec_file") or "").replace("\\", "/")
        if sf.startswith("strategies/") and "/hunts/" not in sf and "/evolve/" not in sf:
            return True
        if e.get("method") is None and e.get("gates_passed") != "5/5":
            return True
        is_stub_tmp = False
        if e.get("method") != "evolve_real" and e.get("gates_passed") == "5/5":
            is_stub_tmp = "minerva" in json.dumps(e.get("metrics") or {})
        return not is_stub_tmp and e.get("method") != "evolve_real"

    param_groups: dict[tuple, list[dict]] = defaultdict(list)
    curated_for_groups = {}
    for s in best.values():
        if _is_curated_for_purge(s):
            curated_for_groups[s.get("id")] = s
        else:
            key = (s.get("family"), canonical_params_hash(s))
            param_groups[key].append(s)
    # now keep best per param group, quarantine dupes
    param_quarantine: list[dict] = []
    deduped_best: dict[str, dict] = dict(curated_for_groups)
    for key, members in param_groups.items():
        if len(members) == 1:
            deduped_best[members[0].get("id")] = members[0]
        else:
            members_sorted = sorted(members, key=lambda x: (oos_sharpe(x), x.get("id", "")), reverse=True)
            deduped_best[members_sorted[0].get("id")] = members_sorted[0]
            param_quarantine.extend(members_sorted[1:])
    if param_quarantine:
        qp = DATA / f"registry_deduped_quarantine_{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
        qp.write_text(json.dumps(param_quarantine, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"W3 param-hash quarantine: {len(param_quarantine)} -> {qp.name}")
    else:
        log("W3 param-hash dedupe: no param dupes")
    best = deduped_best
    log(f"after param-hash dedupe: {len(best)} unique (family,hash) combos")

    # B2c/G12: metric-delta dedupe — kill variant dredging (noise-drift children
    # with near-identical metrics, e.g. identical-oos groups). Non-curated
    # evolve_real entries only; curated exempt (same convention as W3 above).
    # Key = (family, round(oos_sharpe,4), round(sharpe,4)): 4-decimal rounding
    # keeps genuinely distinct variants apart while grouping noise drift.
    # Keep best oos_sharpe per key, quarantine the rest (record kept in the
    # quarantine file, never deleted).
    def _metric_delta_key(s):
        m = s.get("metrics", {}) or {}

        def _rnd(v):
            try:
                return round(float(v), 4) if isinstance(v, (int, float)) else None
            except Exception:
                return None

        return (s.get("family"), _rnd(m.get("oos_sharpe", m.get("oos"))),
                _rnd(m.get("sharpe")))

    metric_groups: dict[tuple, list[dict]] = defaultdict(list)
    metric_kept: dict[str, dict] = {}
    for s in best.values():
        if _is_curated_for_purge(s) or s.get("method") != "evolve_real":
            metric_kept[s.get("id", "?")] = s
            continue
        key = _metric_delta_key(s)
        if key[1] is None and key[2] is None:
            metric_kept[s.get("id", "?")] = s  # dataless: no signal to dedupe on
        else:
            metric_groups[key].append(s)
    metric_quarantine: list[dict] = []
    for key, members in metric_groups.items():
        if len(members) == 1:
            metric_kept[members[0].get("id")] = members[0]
        else:
            members_sorted = sorted(members, key=lambda x: (oos_sharpe(x), x.get("id", "")), reverse=True)
            metric_kept[members_sorted[0].get("id")] = members_sorted[0]
            metric_quarantine.extend(members_sorted[1:])
    if metric_quarantine:
        mq = DATA / f"registry_metricdelta_quarantine_{datetime.now(timezone.utc):%Y%m%d-%H%M%S}.json"
        mq.write_text(json.dumps(metric_quarantine, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"B2c metric-delta quarantine: {len(metric_quarantine)} -> {mq.name}")
    else:
        log("B2c metric-delta dedupe: no near-identical variants")
    best = metric_kept
    log(f"after metric-delta dedupe: {len(best)} entries")

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
    # B2c/G11: persist track_clears() recomputation into metrics.tracks_cleared
    # during prune so the field stops reading 0 everywhere. setdefault-style
    # attach: entries missing a metrics dict (or metrics=None) previously lost
    # the assignment to a throwaway temp dict. Stale track names are dropped
    # on recompute so tracks/tracks_cleared never disagree.
    for s in survivors:
        n, names = track_clears(s)
        m = s.get("metrics")
        if not isinstance(m, dict):
            m = {}
            s["metrics"] = m
        m["tracks_cleared"] = n
        if names:
            m["tracks"] = names
        elif "tracks" in m:
            del m["tracks"]
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
    # clearing >=2 tracks, then single-track by fitness. W4: when the field
    # is sparse (vestigial {0:N} or <5% clear), fall back to honest signal
    # ranking on (sharpe, oos_sharpe, excess) instead of random alive[:5]
    # (Option B). The field itself is kept and recomputed per-family (Option A
    # preferred); fallback only governs breeding when signal is dead.
    # B2c/G11: never re-breed retired (family, param_hash) — retired variants
    # stay dead even if their recomputed fitness still ranks high. Both the
    # status check and the key-set check apply; the key set is future-proof
    # against entries re-entering the pool without a status flag.
    retired_keys = {(s.get("family"), canonical_params_hash(s)) for s in survivors
                    if s.get("status") == "retired"}
    _breed_pool_pre = [s for s in survivors if s.get("method") == "evolve_real"]
    real_sorted = sorted(
        [s for s in _breed_pool_pre
         if s.get("status") != "retired"
         and (s.get("family"), canonical_params_hash(s)) not in retired_keys],
        key=fitness, reverse=True)
    log(f"B2c retired-filter: breed pool {len(_breed_pool_pre)} -> {len(real_sorted)} "
        f"({len(retired_keys)} retired keys excluded)")
    multi = [s for s in real_sorted
              if (s.get("metrics", {}) or {}).get("tracks_cleared", 0) >= 2]
    single = [s for s in real_sorted
               if (s.get("metrics", {}) or {}).get("tracks_cleared", 0) == 1]
    # W9: family-diversity cap — any single family ≤40% of breeders (prevents monoculture, Flaw F 1.1)
    def _enforce_family_cap(candidates: list, cap_frac: float = 0.40) -> list:
        if not candidates:
            return candidates
        cap = max(1, int(len(candidates) * cap_frac + 0.999))  # ceil
        # 40% of 5 => 2, of 4 =>2, of 3 =>2
        if cap >= len(candidates):
            return candidates[:5]
        counts: dict[str, int] = {}
        filtered: list = []
        for s in candidates:
            fam = s.get("family", "unknown")
            if counts.get(fam, 0) >= cap:
                continue
            counts[fam] = counts.get(fam, 0) + 1
            filtered.append(s)
            if len(filtered) >= 5:
                break
        # fill remaining slots from original order skipping over-cap families, else fallback
        if len(filtered) < min(5, len(candidates)):
            for s in candidates:
                if s in filtered:
                    continue
                fam = s.get("family", "unknown")
                if counts.get(fam, 0) >= cap:
                    continue
                counts[fam] = counts.get(fam, 0) + 1
                filtered.append(s)
                if len(filtered) >= 5:
                    break
        return filtered[:5]

    if multi or single:
        raw_breeders = (multi + single)[:10]  # oversample for cap filtering
        breeders = _enforce_family_cap(raw_breeders, 0.40)
        log(f"breeders: {len(multi)} multi-track + {len(single)} single-track "
            f"-> using {len(breeders)} (track signal; W9 family cap 40%)")
    else:
        def _fallback_key(s):
            mm = s.get("metrics", {}) or {}
            sharpe = float(mm.get("sharpe", -9.0)) if isinstance(mm.get("sharpe", None), (int, float)) else -9.0
            oos = mm.get("oos_sharpe", mm.get("oos", -9.0))
            try:
                oos_f = float(oos) if isinstance(oos, (int, float)) else -9.0
            except Exception:
                oos_f = -9.0
            excess = mm.get("excess_spy", mm.get("excess", -999.0))
            try:
                exc_f = float(excess) if isinstance(excess, (int, float)) else -999.0
            except Exception:
                exc_f = -999.0
            return (sharpe, oos_f, exc_f)
        fallback_sorted = sorted(real_sorted, key=_fallback_key, reverse=True)
        raw_fallback = fallback_sorted[:10] or alive[:10]
        breeders = _enforce_family_cap(raw_fallback, 0.40) or alive[:5]
        fb_source = "fallback sharpe/oos/excess" if fallback_sorted else "alive fallback"
        log(f"breeders: {len(multi)} multi-track + {len(single)} single-track "
            f"-> using {len(breeders)} ({fb_source}; tracks_cleared sparse) — W4 Option B + W9 cap 40%")
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

    # W4: always normalize to wrapper object {"strategies": [...], "generations": {...}}
    # so acceptance counter `obj['strategies']` works regardless of legacy list form.
    if not is_wrapper:
        obj = {"strategies": [], "generations": {}}
    obj["strategies"] = survivors  # type: ignore[index]
    obj.setdefault("generations", {}).update({  # type: ignore[attr-defined]
        "last_prune": datetime.now(timezone.utc).isoformat(),
        "alive": len(alive),
        "retired": len(dead),
        "purged_stub": len(stub),
        "keep_top": KEEP_TOP,
    })
    out_obj = obj
    # S5: INF-09 cross-OS FileLock around tmp+os.replace (mirrors
    # evolve_real.append_registry). Concurrent prune+append must not drop entries.
    lock_path = str(REG) + ".lock"
    _lock = None
    tmp = REG.with_suffix(".tmp")
    with _REGISTRY_WRITE_LOCK:  # S5: intra-process threads; FileLock covers processes
        try:
            try:
                from filelock import FileLock  # cross-OS
                _lock = FileLock(lock_path, timeout=10)
                _lock.acquire()
            except Exception:
                try:
                    import portalocker  # fallback
                    _lock = open(lock_path, "a")
                    portalocker.lock(_lock, portalocker.LOCK_EX)
                except Exception:
                    _lock = None
            tmp.write_text(json.dumps(out_obj, indent=1), encoding="utf-8")
            json.loads(tmp.read_text(encoding="utf-8"))
            os.replace(tmp, REG)  # atomic: concurrent readers never see a half-write
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            raise
        finally:
            try:
                if _lock is not None:
                    try:
                        _lock.release()  # filelock
                    except Exception:
                        try:
                            import portalocker
                            portalocker.unlock(_lock)
                        except Exception:
                            pass
                        try:
                            _lock.close()
                        except Exception:
                            pass
            except Exception:
                pass
    log("registry rewritten + validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
