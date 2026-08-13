"""Persistent, content-hashed trial ledger + Deflated Sharpe Ratio guard.

Implements P2-item-9 (web-research/synthesis.md): stop Repeated-Kelly
drifting by persisting a hashed trial record for every experiment and by
applying a multiple-comparison adjustment before any promotion.

See web-research/quant-validation-best-practices.md:
  * section 1 (DSR row) + section 8.1 "Honest trial ledger + DSR" — every
    tuning round is a trial; count N honestly (losers included) and correct
    the reported Sharpe for the number of trials N.
  * the False Strategy Theorem note in the TL;DR — "best of N" backtests
    look great by construction; the DSR is the closed-form correction.

Layout
------
* ``TrialLedger`` — append / load / status-update of ``run-logs/trials.jsonl``
  (JSONL, one trial per line).  Each row carries a ``sha256`` content hash
  over the canonicalized (strategy_id, params, data_range) so an identical
  experiment is detected and skipped instead of being logged twice.
* ``deflated_sharpe_ratio(T, SR, N)`` — the Bailey & Lopez de Prado (2014)
  Deflated Sharpe Ratio, normal-returns variant (skew 0, kurtosis 3):

      DSR = Phi( z - E[max Z_N] )
      z   = SR * sqrt(T - 1) / sqrt(1 + SR^2 / 2)
      E[max Z_N] ~= (1 - g) * Phi^-1(1 - 1/N) + g * Phi^-1(1 - 1/(N*e))

  with g = Euler-Mascheroni constant, e = Euler's number.  N = number of
  trials (all configs tried, discarded ones included); N = 1 collapses to
  the Probabilistic Sharpe Ratio (PSR) special case.
* ``deflated_sharpe_threshold(T, N, confidence)`` — the minimum Sharpe a
  candidate must exceed to survive the N-trial selection bias at a given
  confidence; this is the "shrunk Sharpe" reported by the CLI.

Conventions: ``SR`` is the per-observation (non-annualized) Sharpe of the
T-observation sample, exactly as in the paper; if a stored Sharpe is
annualized by sqrt(252), divide by sqrt(252) before calling.

Dependencies: stdlib only (argparse, dataclasses, hashlib, json, logging,
math, os, sys, time).  No third-party imports.

CLI::
    python -m src.backtest.defend.trial_ledger \
        --ingest docs/data/strategy_rankings.json --max-deflate 36
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import sys
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

_EULER_MASCHERONI = 0.57721566490153286060651209
_SQRT_2 = math.sqrt(2.0)

STATUSES = ("PENDING", "INCUBATING", "PROMOTED", "REJECTED")

METRIC_KEYS = ("sharpe", "profit_factor", "max_dd")

logger = logging.getLogger("src.backtest.defend.trial_ledger")


# ---------------------------------------------------------------------------
# Trial record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Trial:
    """One row of the trial ledger (one line in run-logs/trials.jsonl)."""

    sha256: str
    timestamp: str
    strategy_id: str
    params: dict[str, Any]
    metrics: dict[str, Any]
    data_range: str
    provider: str
    status: str = "PENDING"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> Trial:
        """Build a Trial from a JSON row; missing fields fall back to
        defaults so older or hand-written ledger lines still load."""
        return cls(
            sha256=row.get("sha256", ""),
            timestamp=row.get("timestamp", ""),
            strategy_id=row.get("strategy_id", ""),
            params=row.get("params", {}),
            metrics=row.get("metrics", {}),
            data_range=row.get("data_range", ""),
            provider=row.get("provider", ""),
            status=row.get("status", "PENDING"),
        )


# ---------------------------------------------------------------------------
# Canonicalization helpers
# ---------------------------------------------------------------------------
def _jsonable(obj: Any) -> Any:
    """Recursively coerce a value into JSON-serializable types.

    dict keys are stringified, tuples become lists, sets become sorted
    lists so equal-but-differently-ordered containers produce the same
    canonical payload and therefore the same trial hash.
    """
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, set):
        return sorted((_jsonable(v) for v in obj), key=repr)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    raise TypeError(f"field value of type {type(obj).__name__} is not JSON-serializable")


def _canonical_json(value: Any) -> str:
    """Deterministic JSON encoding (sorted keys, tight separators)."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_jsonable,
    )


def _content_hash(strategy_id: str, params: dict[str, Any], data_range: str) -> str:
    """sha256 hex digest of the canonicalized strategy + params + range."""
    payload = _canonical_json(
        {"strategy_id": strategy_id, "params": params, "data_range": data_range}
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _normalize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    """Extract {sharpe, profit_factor, max_dd} as finite floats (or None)
    plus the optional trade count used for the DSR normalization.

    Aliases accepted per the docs/data/strategy_rankings.json shape:
    ``max_dd`` <- ``max_dd`` | ``max_drawdown_pct``.  Non-numeric and
    non-finite (NaN/inf) values degrade gracefully to None so a corrupt
    metric never crashes the ledger.
    """
    aliases = {
        "sharpe": ("sharpe",),
        "profit_factor": ("profit_factor",),
        "max_dd": ("max_dd", "max_drawdown_pct", "max_drawdown"),
    }
    out: dict[str, Any] = {}
    for key, keys in aliases.items():
        value: float | None = None
        for k in keys:
            raw = metrics.get(k)
            if raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = None
                break
            if not math.isfinite(value):
                value = None
                break
            break
        out[key] = value
    raw_trades = metrics.get("total_trades")
    trades: int | None = None
    if raw_trades is not None:
        try:
            trades = int(float(raw_trades))
        except (TypeError, ValueError):
            trades = None
    if trades is not None:
        out["total_trades"] = trades
    return out


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------
class TrialLedger:
    """Append-only JSONL trial register with content-hash deduplication.

    * ``append_experiment`` appends one line per run to
      ``run-logs/trials.jsonl`` (the folder is created when missing).  An
      identical content hash (same strategy_id + canonical params + same
      data_range) is warned about and skipped — no duplicate rows.
    * ``load_trials`` reads every row back; a corrupt JSONL line is logged
      and skipped (the count lands in ``ledger.corrupt_lines``).
    * ``update_status`` rewrites a row in place (read-modify-write of the
      JSONL file) through the PENDING -> INCUBATING -> PROMOTED/REJECTED
      lifecycle.
    """

    def __init__(
        self,
        path: str = "run-logs/trials.jsonl",
        logger: logging.Logger | None = None,
    ) -> None:
        self.path = path
        self.logger = logger or logging.getLogger("src.backtest.defend.trial_ledger")
        self.corrupt_lines = 0

    # -- readers -----------------------------------------------------------
    def _iter_rows(self) -> Iterable[Trial]:
        """Yield Trial rows; corrupt lines are logged and skipped."""
        self.corrupt_lines = 0
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    yield Trial.from_dict(json.loads(stripped))
                except (ValueError, TypeError) as exc:
                    self.corrupt_lines += 1
                    self.logger.warning(
                        "corrupt trial line %d in %s (%s); skipped",
                        line_no, self.path, exc,
                    )

    def load_trials(self) -> list[Trial]:
        """All ledger rows in file order ([] when the ledger does not exist)."""
        return list(self._iter_rows())

    # -- writers -----------------------------------------------------------
    def append_experiment(
        self,
        strategy_id: str,
        params: dict[str, Any],
        data_range: str,
        metrics: dict[str, Any],
        provider: str,
    ) -> str | None:
        """Persist one trial (status PENDING).  Returns the sha256 hex digest,
        or None when the trial content hash was already logged (skipped)."""
        if not isinstance(strategy_id, str) or not strategy_id.strip():
            raise ValueError("strategy_id must be a non-empty string")

        params = _jsonable(params)  # validate JSON-serializability early
        metrics = _normalize_metrics(metrics)
        sha = _content_hash(strategy_id, params, data_range)

        existing = {row.sha256 for row in self._iter_rows()}
        if sha in existing:
            self.logger.warning(
                "duplicate trial %s (strategy_id=%r) skipped; already logged",
                sha, strategy_id,
            )
            return None

        trial = Trial(
            sha256=sha,
            timestamp=_utcnow(),
            strategy_id=strategy_id,
            params=params,
            metrics=metrics,
            data_range=str(data_range),
            provider=str(provider),
            status="PENDING",
        )
        parent = os.path.dirname(os.path.abspath(self.path)) or os.curdir
        os.makedirs(parent, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(trial.to_dict(), separators=(",", ":"), allow_nan=False) + "\n"
            )
        return sha

    def update_status(self, sha: str, status: str) -> bool:
        """Move a trial through {PENDING, INCUBATING, PROMOTED, REJECTED}.

        Read-modify-write the JSONL in place.  Returns True when the row was
        found and rewritten, False otherwise.  Corrupt or unrelated lines
        are preserved verbatim.
        """
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES!r}")
        if not isinstance(sha, str) or len(sha) != 64:
            raise ValueError("sha must be a 64-character sha256 hex digest")
        if not os.path.exists(self.path):
            self.logger.warning("update_status: ledger %s does not exist", self.path)
            return False

        tmp_path = self.path + ".tmp"
        found = False
        with open(self.path, "r", encoding="utf-8") as fh, \
                open(tmp_path, "w", encoding="utf-8") as out:
            for line in fh:
                stripped = line.strip("\n")
                row_text = stripped.strip()
                if not row_text:
                    out.write("\n")
                    continue
                try:
                    row = json.loads(row_text)
                except (ValueError, TypeError):
                    out.write(stripped + "\n")  # preserve corrupt lines verbatim
                    continue
                if isinstance(row, dict) and row.get("sha256") == sha:
                    row["status"] = status
                    out.write(
                        json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n"
                    )
                    found = True
                else:
                    out.write(stripped + "\n")
        os.replace(tmp_path, self.path)

        if not found:
            self.logger.warning("update_status: no trial with sha256 %s found", sha)
        return found


# ---------------------------------------------------------------------------
# Deflated Sharpe Ratio (multiple-comparison guard)
# ---------------------------------------------------------------------------
def normal_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""
    return 0.5 * (1.0 + math.erf(x / _SQRT_2))


def inverse_normal_cdf(p: float) -> float:
    """Standard normal quantile (Acklam's rational approximation, ~1e-9).

    ``normal_cdf(inverse_normal_cdf(p)) == p`` across the practical tail
    range used by DSR (1 - 1/N for N up to ~1e6).
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"p must be in (0, 1), got {p!r}")

    def _poly(x: float, coeffs: list[float]) -> float:
        """Horner evaluation with coeffs[0] as the highest power."""
        result = coeffs[0]
        for coeff in coeffs[1:]:
            result = result * x + coeff
        return result

    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return _poly(q, c) / (_poly(q, d) * q + 1.0)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return q * _poly(r, a) / (_poly(r, b) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -_poly(q, c) / (_poly(q, d) * q + 1.0)


def expected_max_std_normal(n_trials: int) -> float:
    """E[max of n_trials iid standard normals], Bailey & Lopez de Prado's
    ``E[max Z_N]`` approximation (Euler-Mascheroni-blended two quantiles)."""
    if n_trials <= 1:
        return 0.0
    gamma = _EULER_MASCHERONI
    return (1.0 - gamma) * inverse_normal_cdf(1.0 - 1.0 / n_trials) + \
        gamma * inverse_normal_cdf(1.0 - 1.0 / (n_trials * math.e))


def deflated_sharpe_ratio(T: int, SR: float, N: int) -> float:
    """Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio, normal variant.

    DSR = Phi( SR * sqrt(T - 1) / sqrt(1 + SR^2/2) - E[max Z_N] )

    ``T`` — number of observations (trade count for a trade-level Sharpe, or
    per-bar count for a bar-level Sharpe); ``SR`` — per-observation Sharpe;
    ``N`` — number of trials behind the reported best (all configs tried,
    losers included).  Returns the probability that the true Sharpe is
    positive after correcting for the N-trial selection bias.
    """
    if T <= 1:
        raise ValueError(f"T (observation/trade count) must be > 1, got {T!r}")
    if N < 1:
        raise ValueError(f"N (trial count) must be >= 1, got {N!r}")
    SR = float(SR)
    z = SR * math.sqrt(T - 1.0) / math.sqrt(1.0 + 0.5 * SR * SR)
    return normal_cdf(z - expected_max_std_normal(int(N)))


def deflated_sharpe_threshold(T: int, N: int, confidence: float = 0.95) -> float:
    """Minimum Sharpe a candidate must exceed to survive N trials at
    ``confidence`` (the DSR "break-even" value).  Returns ``math.inf`` when
    the observation count T is too small for the target to be reachable."""
    if T <= 1:
        raise ValueError(f"T must be > 1, got {T!r}")
    if N < 1:
        raise ValueError(f"N must be >= 1, got {N!r}")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence!r}")
    z_star = inverse_normal_cdf(confidence) + expected_max_std_normal(int(N))
    denominator_sq = (float(T) - 1.0) - 0.5 * z_star * z_star
    if denominator_sq <= 0.0:
        return float("inf")
    return z_star / math.sqrt(denominator_sq)


# ---------------------------------------------------------------------------
# CLI: ingest a rankings file and shrink the best Sharpe by the N-trial guard
# ---------------------------------------------------------------------------
def build_argparse_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.backtest.defend.trial_ledger",
        description=(
            "Persist experiment trials into a hashed JSONL ledger "
            "(run-logs/trials.jsonl) and apply the Bailey & Lopez de Prado "
            "Deflated Sharpe multiple-comparison guard to the best trial.\n\n"
            "The rankings JSON is read-only here: nothing is written back to it."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ingest", metavar="PATH", default="docs/data/strategy_rankings.json",
        help="JSON array of ranked experiments to log and deflate "
             "(default: docs/data/strategy_rankings.json)",
    )
    parser.add_argument(
        "--max-deflate", metavar="N", type=int, default=None,
        help="number of trials N for the multiple-comparison adjustment "
             "(default: the number of ingested trials)",
    )
    parser.add_argument(
        "--obs", metavar="T", type=int, default=2500,
        help="observation/trade count fallback when a trial carries no "
             "usable trade count (default: 2500)",
    )
    parser.add_argument(
        "--confidence", metavar="P", type=float, default=0.95,
        help="DSR confidence level for the break-even Sharpe (default: 0.95)",
    )
    parser.add_argument(
        "--ledger", metavar="PATH", default="run-logs/trials.jsonl",
        help="ledger file to append to (default: run-logs/trials.jsonl)",
    )
    parser.add_argument(
        "--top", metavar="K", type=int, default=5,
        help="rows in the human table (default: 5)",
    )
    return parser


def _ingest_rankings(ledger: TrialLedger, ingest_path: str) -> tuple[int, int]:
    """Append every ranking entry as one PENDING trial.

    Returns (newly appended, skipped) where skipped covers duplicates and
    unloggable entries — no entry ever crashes the ingest pass.
    """
    if not os.path.exists(ingest_path):
        raise FileNotFoundError(f"--ingest file not found: {ingest_path}")
    with open(ingest_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise TypeError("--ingest file must contain a JSON array of records")

    base = os.path.basename(ingest_path)
    new_count = 0
    skipped = 0
    for index, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            logger.warning("--ingest entry %d is not an object; skipped", index)
            skipped += 1
            continue
        strategy_id = str(entry.get("id") or entry.get("name") or "").strip()
        if not strategy_id:
            logger.warning("--ingest entry %d has no id/name; skipped", index)
            skipped += 1
            continue
        params = entry.get("parameters") or {}
        metrics = entry.get("metrics") or {}
        data_range = str(entry.get("data_range", "n/a"))
        try:
            outcome = ledger.append_experiment(
                strategy_id=strategy_id,
                params=params,
                data_range=data_range,
                metrics=metrics,
                provider=f"rankings:{base}",
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "--ingest entry %d (%s) could not be logged: %s; skipped",
                index, strategy_id, exc,
            )
            skipped += 1
            continue
        if outcome is None:
            skipped += 1
        else:
            new_count += 1
    return new_count, skipped


def _trial_sharpe(trial: Trial) -> float | None:
    value = trial.metrics.get("sharpe")
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _trial_trades(trial: Trial) -> int | None:
    """Usable trade count from the ledger row (>= 2), else None."""
    raw = trial.metrics.get("total_trades")
    if raw is None:
        return None
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return None
    return value if value >= 2 else None


def main(argv: list[str] | None = None) -> int:
    args = build_argparse_parser().parse_args(argv)

    if args.max_deflate is not None and args.max_deflate < 1:
        print("error: --max-deflate must be >= 1", file=sys.stderr)
        return 2
    if args.obs < 2:
        print("error: --obs must be >= 2", file=sys.stderr)
        return 2
    if not 0.0 < args.confidence < 1.0:
        print("error: --confidence must be in (0, 1)", file=sys.stderr)
        return 2

    ledger = TrialLedger(path=args.ledger)

    try:
        new_count, skipped = _ingest_rankings(ledger, args.ingest)
    except (OSError, ValueError) as exc:
        print(f"ingest failed: {exc}", file=sys.stderr)
        return 1

    trials = ledger.load_trials()
    n_trials = args.max_deflate if args.max_deflate is not None else len(trials)

    print(f"ingest: {len(trials)} trial(s) read from {args.ingest} -> {args.ledger} "
          f"(new: {new_count}, duplicates skipped: {skipped})")
    print()
    print("Multiple-comparison guard - Deflated Sharpe Ratio "
          "(Bailey & Lopez de Prado 2014, normal-returns variant)")
    print(f"N (trials) = {n_trials:d} | confidence = {args.confidence:.2f} | "
          f"observation fallback = {args.obs:d}")
    print()

    ranked = sorted(
        trials, key=lambda t: (_trial_sharpe(t) if _trial_sharpe(t) is not None else float("-inf")),
        reverse=True,
    )

    def _dsr_row(trial: Trial) -> tuple[str, str, str, str, str, str]:
        sharpe = _trial_sharpe(trial)
        if sharpe is None:
            return "-", "-", "-", "-", "n/a"
        trades = _trial_trades(trial)
        t_used = trades if trades is not None else args.obs
        dsr = deflated_sharpe_ratio(t_used, sharpe, n_trials)
        breakeven = deflated_sharpe_threshold(t_used, n_trials, args.confidence)
        verdict = "PASS" if sharpe >= breakeven else "FAIL"
        be = f"{breakeven:.4f}" if math.isfinite(breakeven) else "inf"
        return (f"{sharpe:8.4f}", f"{trades:d}" if trades is not None else "-",
                f"{t_used:d}", f"{dsr:.4f}", be, verdict)

    header = (
        f"  {'rank':<4} {'strategy_id':<12} {'sharpe':>8} {'trades':>6} {'T-used':>6} "
        f"{'DSR(N)':>7} {'break-even':>9} {'verdict':>6}"
    )
    print(header)
    print("-" * len(header))
    for rank, trial in enumerate(ranked[: args.top], start=1):
        row = _dsr_row(trial)
        print(
            f"  {rank:<4d} {trial.strategy_id[:12]:<12} {row[0]:>8} {row[1]:>6} "
            f"{row[2]:>6} {row[3]:>7} {row[4]:>9} {row[5]:>6}"
        )

    if ranked:
        best = ranked[0]
        best_sharpe = _trial_sharpe(best)
        best_trades = _trial_trades(best)
        best_t = best_trades if best_trades is not None else args.obs
        print()
        print(f"Best trial   : {best.strategy_id}")
        if best_sharpe is None:
            print("  no usable sharpe in metrics; DSR not computed")
        else:
            dsr = deflated_sharpe_ratio(best_t, best_sharpe, n_trials)
            breakeven = deflated_sharpe_threshold(best_t, n_trials, args.confidence)
            print(f"  raw Sharpe : {best_sharpe:8.4f}   (T = {best_t:d})")
            print(f"  deflated   : {dsr:8.4f}   (DSR, prob true SR > 0 after "
                  f"{n_trials:d}-trial correction)")
            print(f"  break-even : "
                  f"{(breakeven if math.isfinite(breakeven) else float('inf')):8.4f}   "
                  f"(min Sharpe to survive {n_trials:d} trials at {args.confidence:.2f} confidence)")
            print("  sensitivity: " + " ; ".join(
                f"N={n:d} -> {deflated_sharpe_threshold(best_t, n, args.confidence):.4f}"
                for n in sorted({1, 5, 10, n_trials, 100})
            ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
