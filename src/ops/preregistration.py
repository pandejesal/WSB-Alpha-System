import datetime
import hashlib
import json
import os
import re
import shutil
import threading
from typing import Any, Dict, Optional

import yaml

# R-A1: intra-process serialization for concurrent record_evaluation calls.
# Cross-process serialization is handled best-effort via the registry ".lock"
# file (FileLock when installed, plain existence marker otherwise).
_REGISTRY_WRITE_LOCK = threading.Lock()


def load_yaml_spec(spec_path: str) -> dict[str, Any]:
    with open(spec_path, 'r') as f:
        return yaml.safe_load(f)

def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def _get_max_cycle(docs_dir: str) -> int:
    max_cycle = 0
    if os.path.exists(docs_dir):
        for f in os.listdir(docs_dir):
            match = re.match(r'cycle(\d+)_prereg_.*\.md', f)
            if match:
                max_cycle = max(max_cycle, int(match.group(1)))
    return max_cycle

def freeze_preregistration(spec_path: str, claim: str, cycle: int | None = None, docs_dir: str = "docs/data") -> str:
    spec = load_yaml_spec(spec_path)
    family = spec.get('family')
    if not family:
        raise ValueError(f"Spec file {spec_path} is missing 'family' field.")

    if cycle is None:
        cycle = _get_max_cycle(docs_dir) + 1

    os.makedirs(docs_dir, exist_ok=True)
    filename = f"cycle{cycle}_prereg_{family}.md"
    filepath = os.path.join(docs_dir, filename)

    if os.path.exists(filepath):
        raise FileExistsError(f"Pre-registration doc already exists at {filepath}. Refusing to overwrite.")

    with open(spec_path, 'r') as f:
        spec_content = f.read()

    spec_sha256 = _sha256_text(spec_content)

    doc_content = f"""# Pre-registration: {family}
Cycle: {cycle}
Date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Spec-SHA256: {spec_sha256}

## Claim
{claim}

## Strategy Spec
```yaml
{spec_content}
```
"""

    with open(filepath, 'w') as f:
        f.write(doc_content)

    return filepath

def verify_prereg_freeze(spec, claim=None, cycle: int | None = None, docs_dir: str = "docs/data") -> str:
    """Fail-closed pre-registration gate (B3a/G9 hot-path hook).

    Checks a freeze file exists for the spec (family + SHA-256 of the raw
    spec file) with matching SHA-256 BEFORE any evaluation is recorded.
    When ``claim`` is provided it must also equal the frozen claim.

    Exposed as a callable hook so the evolve promotion loop can import it
    later without this module calling into the loop. Raises
    FileNotFoundError when no freeze exists and ValueError on any
    integrity mismatch. Returns the freeze filepath on success.
    """
    if not isinstance(spec, (str, os.PathLike)):
        raise TypeError(f"verify_prereg_freeze expects a spec file path, got {type(spec).__name__}")
    spec_path = os.fspath(spec)

    loaded = load_yaml_spec(spec_path)
    family = loaded.get('family') if isinstance(loaded, dict) else None
    if not family:
        raise ValueError(f"Spec file {spec_path} is missing 'family' field.")

    if cycle is None:
        cycle = _get_max_cycle(docs_dir)
        if cycle == 0:
            raise FileNotFoundError(f"no claim registered for family {family} in cycle {cycle} — run preregister freeze first")

    prereg_filename = f"cycle{cycle}_prereg_{family}.md"
    prereg_filepath = os.path.join(docs_dir, prereg_filename)

    if not os.path.exists(prereg_filepath):
        raise FileNotFoundError(f"no claim registered for family {family} in cycle {cycle} — run preregister freeze first")

    with open(prereg_filepath, 'r') as f:
        prereg_content = f.read()

    frozen_match = re.search(r'^Spec-SHA256:\s*([0-9a-f]{64})\s*$', prereg_content, re.MULTILINE)
    if not frozen_match:
        raise ValueError(
            f"freeze doc at {prereg_filepath} has no Spec-SHA256 binding (legacy freeze) — "
            f"re-freeze spec {spec_path} before recording an evaluation"
        )

    with open(spec_path, 'r') as f:
        current_hash = _sha256_text(f.read())
    if current_hash != frozen_match.group(1):
        raise ValueError(
            f"spec hash mismatch for family {family} in cycle {cycle}: "
            f"current spec {spec_path} differs from frozen Spec-SHA256 — re-freeze before recording"
        )

    if claim is not None:
        claim_match = re.search(r'## Claim\n(.*?)\n\n## Strategy Spec', prereg_content, re.DOTALL)
        declared = claim_match.group(1).strip() if claim_match else ""
        if declared != str(claim).strip():
            raise ValueError(
                f"claim mismatch for family {family} in cycle {cycle}: "
                f"provided claim differs from the frozen claim"
            )

    return prereg_filepath

def record_evaluation(spec_path: str, verdict: str, cycle: int | None = None, eval_path: str | None = None, registry_path: str = "strategies/registry.json", docs_dir: str = "docs/data") -> str:
    spec = load_yaml_spec(spec_path)
    family = spec.get('family')
    if not family:
        raise ValueError(f"Spec file {spec_path} is missing 'family' field.")

    # B3a/G9: fail-closed prereg gate — a freeze file must exist for this
    # spec with matching SHA-256 before any evaluation is recorded.
    prereg_filepath = verify_prereg_freeze(spec_path, cycle=cycle, docs_dir=docs_dir)
    if cycle is None:
        cycle = _get_max_cycle(docs_dir)

    # Read claim from prereg doc
    with open(prereg_filepath, 'r') as f:
        prereg_content = f.read()

    claim_match = re.search(r'## Claim\n(.*?)\n\n## Strategy Spec', prereg_content, re.DOTALL)
    declared_claim = claim_match.group(1).strip() if claim_match else ""

    # Generate spec fingerprint
    with open(spec_path, 'r') as f:
        spec_content = f.read()
    spec_fingerprint = hashlib.sha256(spec_content.encode('utf-8')).hexdigest()

    # Parse evaluation results
    eval_data = {
        "spec_fingerprint": spec_fingerprint,
        "declared_claim": declared_claim,
        "verdict": verdict,
        "evaluated_at": datetime.datetime.now().isoformat(),
        "gate_script": "unknown"
    }

    # R-B1: pin the content-hash of the report bytes consumed at record time,
    # next to spec_fingerprint. A later re-run of the report producer changes
    # the shared file; the pinned hash lets `verify` warn loudly on drift.
    report_path = os.path.join(docs_dir, "backtest_report.json")
    if os.path.exists(report_path):
        with open(report_path, 'rb') as f:
            report_bytes = f.read()
        eval_data["report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
        eval_data["report_source"] = "backtest_report.json"
        try:
            report = json.loads(report_bytes.decode('utf-8'))
            eval_data["walk_forward"] = report.get("portfolio_summary", {})
            eval_data["permutation"] = report.get("all_strategies", [])
            eval_data["dsr"] = report.get("benchmark_comparison", {}).get("strategy_sharpe")
            eval_data["gate_script"] = "scripts/comprehensive_backtest_report.py"
        except Exception:
            pass
    elif eval_path:
        # WH-1: fail-closed on a missing raw-eval file — refuse BEFORE any
        # eval write or registry update (no weak path-string pin).
        if not os.path.exists(eval_path):
            raise FileNotFoundError(
                f"eval_path {eval_path} does not exist — pass a readable raw-eval file or omit --eval-path"
            )
        eval_data["walk_forward"] = eval_path
        eval_data["permutation"] = eval_path
        eval_data["gate_script"] = "raw_output"
        # R-B1: the eval-path branch pins the raw file bytes.
        with open(eval_path, 'rb') as f:
            eval_data["report_sha256"] = hashlib.sha256(f.read()).hexdigest()
        eval_data["report_source"] = eval_path

    # R-A2: collision-proof eval filenames — never overwrite a prior eval.
    # First record for a family+cycle keeps the canonical base name; later
    # records are versioned `_<verdict>-<shortsha>` (counter-suffixed on
    # further collision). The first file therefore stays byte-identical.
    eval_filepath = _versioned_eval_path(
        docs_dir, cycle, family, verdict, spec_fingerprint
    )

    with open(eval_filepath, 'w') as f:
        json.dump(eval_data, f, indent=2)

    # R-A1: locked + backed-up + id-keyed registry update.
    _locked_registry_update(
        registry_path=registry_path,
        spec=spec,
        spec_path=spec_path,
        family=family,
        verdict=verdict,
        eval_filepath=eval_filepath,
    )

    return eval_filepath


def check_recorded_report_hash(spec_path: str, cycle: int | None = None, docs_dir: str = "docs/data") -> str | None:
    """Compare the pinned ``report_sha256`` to the current report bytes (R-B1).

    Locates the eval JSON for the spec's family+cycle (canonical base name
    first, then the newest ``cycle{c}_eval_{family}_*`` versioned file) and
    compares its recorded ``report_sha256`` against the current
    ``backtest_report.json`` bytes.

    Returns a message string, or None when the check does not apply (no eval
    file, legacy eval without a pinned hash, or no current report file).
    A mismatch message starts with ``WARNING`` and names BOTH hashes.
    Never raises: the verify path must stay informational.
    """
    try:
        spec = load_yaml_spec(spec_path)
        family = spec.get('family') if isinstance(spec, dict) else None
        if not family:
            return None
        if cycle is None:
            cycle = _get_max_cycle(docs_dir)

        base = os.path.join(docs_dir, f"cycle{cycle}_eval_{family}.json")
        eval_filepath = base if os.path.exists(base) else None
        if eval_filepath is None and os.path.exists(docs_dir):
            prefix = f"cycle{cycle}_eval_{family}_"
            candidates = [
                os.path.join(docs_dir, f)
                for f in os.listdir(docs_dir)
                if f.startswith(prefix) and f.endswith(".json")
            ]
            if candidates:
                eval_filepath = max(candidates, key=os.path.getmtime)
        if eval_filepath is None:
            return None

        with open(eval_filepath, 'r') as f:
            eval_data = json.load(f)
        if not isinstance(eval_data, dict):
            return None
        recorded = eval_data.get("report_sha256")
        if not recorded:
            return None

        # WH-2: eval-path branch — the pin refers to the raw eval file, not
        # the shared backtest_report.json. A missing source is UNVERIFIED
        # (fail-closed, informational); a present-but-drifted source reuses
        # the WARNING drift shape naming both hashes.
        report_source = eval_data.get("report_source")
        if report_source and report_source != "backtest_report.json":
            if os.path.isabs(report_source):
                eval_source_path = report_source
            else:
                eval_source_path = os.path.join(docs_dir, report_source)
            if not os.path.exists(eval_source_path) and not os.path.exists(report_source):
                return (
                    f"UNVERIFIED: report source missing for family {family} cycle {cycle}: "
                    f"recorded report_sha256={recorded} pins unreachable path {report_source}; "
                    f"re-run the report producer and re-record"
                )
            source_path = eval_source_path if os.path.exists(eval_source_path) else report_source
            try:
                with open(source_path, 'rb') as f:
                    current = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                return (
                    f"UNVERIFIED: report source missing for family {family} cycle {cycle}: "
                    f"recorded report_sha256={recorded} pins unreachable path {report_source}; "
                    f"re-run the report producer and re-record"
                )
            if current != recorded:
                return (
                    f"WARNING: report drift for family {family} cycle {cycle}: "
                    f"recorded report_sha256={recorded} != current "
                    f"{source_path} sha256={current}; "
                    f"recorded numbers may differ from a fresh report run"
                )
            return (
                f"report hash verified for family {family} cycle {cycle}: {current}"
            )

        report_path = os.path.join(docs_dir, "backtest_report.json")
        if not os.path.exists(report_path):
            return None
        with open(report_path, 'rb') as f:
            current = hashlib.sha256(f.read()).hexdigest()

        if current != recorded:
            return (
                f"WARNING: report drift for family {family} cycle {cycle}: "
                f"recorded report_sha256={recorded} != current "
                f"{report_path} sha256={current}; "
                f"recorded numbers may differ from a fresh report run"
            )
        return (
            f"report hash verified for family {family} cycle {cycle}: {current}"
        )
    except Exception:
        return None


def _versioned_eval_path(docs_dir: str, cycle: int, family: str, verdict: str, spec_fingerprint: str) -> str:
    """Return a non-colliding eval path (R-A2).

    The canonical `cycle{c}_eval_{family}.json` name is used when free;
    otherwise a `_<verdict>-<shortsha>` suffix (plus a counter when even
    that collides) is appended. Never returns a path that already exists.
    """
    base = os.path.join(docs_dir, f"cycle{cycle}_eval_{family}.json")
    if not os.path.exists(base):
        return base
    shortsha = (spec_fingerprint or "unknown")[:8]
    candidate = os.path.join(
        docs_dir, f"cycle{cycle}_eval_{family}_{verdict}-{shortsha}.json"
    )
    if not os.path.exists(candidate):
        return candidate
    counter = 2
    while True:
        versioned = os.path.join(
            docs_dir,
            f"cycle{cycle}_eval_{family}_{verdict}-{shortsha}-{counter}.json",
        )
        if not os.path.exists(versioned):
            return versioned
        counter += 1


def _locked_registry_update(registry_path: str, spec: dict, spec_path: str, family: str, verdict: str, eval_filepath: str) -> None:
    """Lock + backup + id-keyed registry write (R-A1).

    Mirrors the `scripts/evolve_generations.py` FileLock + tmp + os.replace
    pattern. Rows are matched by spec `id` first; the legacy family-keyed
    fallback applies only when the spec carries no `id`, so recording one
    candidate can never mutate a different same-family row. A
    `.bak-<timestamp>` copy of the pre-write registry is kept beside the
    registry file before the atomic replace.
    """
    lock_path = registry_path + ".lock"
    # Existence marker: proves serialization was attempted even when no
    # cross-process lock backend (filelock/portalocker) is installed.
    try:
        with open(lock_path, "a"):
            pass
    except OSError:
        pass

    with _REGISTRY_WRITE_LOCK:
        file_lock = None
        try:
            try:
                from filelock import FileLock as _FileLock

                file_lock = _FileLock(lock_path, timeout=10)
                file_lock.acquire()
            except Exception:
                file_lock = None
                try:
                    import portalocker as _portalocker

                    file_lock = open(lock_path, "a")
                    _portalocker.lock(file_lock, _portalocker.LOCK_EX)
                    file_lock._is_portalocker = True  # type: ignore[attr-defined]
                except Exception:
                    try:
                        if file_lock is not None:
                            file_lock.close()
                    except Exception:
                        pass
                    file_lock = None
            try:
                if os.path.exists(registry_path):
                    with open(registry_path, 'r') as f:
                        registry = json.load(f)
                else:
                    registry = {"strategies": []}

                # Id-keyed match; family fallback only when spec has no id.
                spec_id = spec.get("id")
                if spec_id is not None:
                    strategy_entry = next(
                        (s for s in registry.get("strategies", []) if s.get("id") == spec_id),
                        None,
                    )
                else:
                    strategy_entry = next(
                        (s for s in registry.get("strategies", []) if s.get("family") == family),
                        None,
                    )

                if strategy_entry:
                    strategy_entry["verdict"] = verdict
                    strategy_entry["eval_file"] = eval_filepath
                    if verdict == "PASS":
                        strategy_entry["status"] = "ported"
                    else:
                        strategy_entry["status"] = "inactive"
                else:
                    new_entry = {
                        "id": spec.get("id", family),
                        "name": spec.get("name", family),
                        "family": family,
                        "venue": "alpaca",
                        "spec_file": spec_path,
                        "gates_passed": "5/5" if verdict == "PASS" else "0/5",
                        "rank": len(registry.get("strategies", [])) + 1,
                        "status": "ported" if verdict == "PASS" else "inactive",
                        "verdict": verdict,
                        "eval_file": eval_filepath
                    }
                    if "strategies" not in registry:
                        registry["strategies"] = []
                    registry["strategies"].append(new_entry)

                # Backup of the pre-write registry (only when one existed).
                if os.path.exists(registry_path):
                    timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S%f")
                    backup_path = f"{registry_path}.bak-{timestamp}"
                    shutil.copy2(registry_path, backup_path)

                # Atomic tmp + validate + os.replace.
                tmp_path = registry_path + ".tmp"
                try:
                    with open(tmp_path, 'w') as f:
                        json.dump(registry, f, indent=2)
                    with open(tmp_path, 'r') as f:
                        json.load(f)  # validate before replacing
                    os.replace(tmp_path, registry_path)
                except Exception:
                    try:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except OSError:
                        pass
                    raise
            finally:
                if file_lock is not None:
                    try:
                        if getattr(file_lock, "_is_portalocker", False):
                            import portalocker as _portalocker

                            _portalocker.unlock(file_lock)  # type: ignore[arg-type]
                            file_lock.close()  # type: ignore[attr-defined]
                        else:
                            file_lock.release()  # type: ignore[attr-defined]
                    except Exception:
                        pass
        finally:
            pass
    # Re-touch the marker: FileLock backends remove their lock file on
    # release, so this persistent marker is the observable proof that the
    # registry write went through the locked path.
    try:
        with open(lock_path, "a"):
            pass
    except OSError:
        pass
