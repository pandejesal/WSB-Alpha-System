"""Compute-only option-implied crash risk signals.

Derives a crash-risk score from three option-implied inputs:

* IV skew: OTM put implied volatility minus ATM implied volatility
* Put-call skew: put implied volatility divided by call implied volatility
* Term-structure slope: back-month implied volatility minus front-month

The module is deliberately compute-only: it never touches a broker, an
options chain feed, or the network. Callers are responsible for sourcing
the implied-volatility inputs. All functions are pure and numpy-only.

Fail-closed contract (see AGENTS.md):

* ``evaluate_crash_risk`` raises ``ValueError`` on invalid or empty input.
* ``crash_risk_gate`` never raises; invalid input yields a neutral
  ``NO_SIGNAL`` verdict with ``trade_allowed=False``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Calibration constants
# ---------------------------------------------------------------------------

# Default IV-skew calibration range, in percentage points of implied
# volatility (OTM put IV minus ATM IV).
DEFAULT_IV_SKEW_LOW = 2.0
DEFAULT_IV_SKEW_HIGH = 8.0

# Default put/call implied-volatility ratio calibration range.
DEFAULT_PUT_CALL_LOW = 1.0
DEFAULT_PUT_CALL_HIGH = 1.5

# Default term-structure slope calibration range, in percentage points
# (back-month IV minus front-month IV).
DEFAULT_TERM_SLOPE_LOW = -2.0
DEFAULT_TERM_SLOPE_HIGH = 2.0

# Default component weights for the composite score.
DEFAULT_WEIGHTS: tuple[float, float, float] = (0.4, 0.3, 0.3)

# Default classification thresholds on the 0-100 composite score.
DEFAULT_LOW_THRESHOLD = 40.0
DEFAULT_MODERATE_THRESHOLD = 60.0
DEFAULT_HIGH_THRESHOLD = 80.0

# Scores at or above this threshold block trading.
DEFAULT_GATE_THRESHOLD = 60.0

# Verdict levels.
LEVEL_LOW = "LOW"
LEVEL_MODERATE = "MODERATE"
LEVEL_ELEVATED = "ELEVATED"
LEVEL_HIGH = "HIGH"
LEVEL_NO_SIGNAL = "NO_SIGNAL"

# A scalar, a numpy array, or a sequence of numbers.
Numeric = float | np.ndarray | Sequence[float]

__all__ = [
    "DEFAULT_IV_SKEW_LOW",
    "DEFAULT_IV_SKEW_HIGH",
    "DEFAULT_PUT_CALL_LOW",
    "DEFAULT_PUT_CALL_HIGH",
    "DEFAULT_TERM_SLOPE_LOW",
    "DEFAULT_TERM_SLOPE_HIGH",
    "DEFAULT_WEIGHTS",
    "DEFAULT_LOW_THRESHOLD",
    "DEFAULT_MODERATE_THRESHOLD",
    "DEFAULT_HIGH_THRESHOLD",
    "DEFAULT_GATE_THRESHOLD",
    "LEVEL_LOW",
    "LEVEL_MODERATE",
    "LEVEL_ELEVATED",
    "LEVEL_HIGH",
    "LEVEL_NO_SIGNAL",
    "Numeric",
    "CrashRiskVerdict",
    "compute_iv_skew",
    "compute_put_call_skew",
    "compute_term_structure_slope",
    "iv_skew_score",
    "put_call_skew_score",
    "term_slope_score",
    "crash_risk_score",
    "classify_crash_risk",
    "evaluate_crash_risk",
    "crash_risk_gate",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _as_float_array(value: Any, name: str) -> np.ndarray:
    """Coerce *value* to a float ndarray, rejecting invalid input.

    Raises ``ValueError`` for None, strings, bytes, dicts, booleans,
    empty arrays, and non-finite values.
    """
    if value is None:
        raise ValueError(f"{name} must not be None")
    if isinstance(value, (str, bytes, dict, bool)):
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}")
    try:
        arr = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric, got {type(value).__name__}") from exc
    if arr.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _validate_iv(value: Any, name: str) -> np.ndarray:
    """Coerce an implied-volatility input, requiring non-negative values."""
    arr = _as_float_array(value, name)
    if np.any(arr < 0):
        raise ValueError(f"{name} must be non-negative")
    return arr


def _to_output(arr: np.ndarray) -> float | np.ndarray:
    """Return a Python float for 0-d arrays, otherwise the ndarray."""
    if arr.ndim == 0:
        return float(arr)
    return arr


def _validate_weights(weights: Sequence[float]) -> np.ndarray:
    """Validate and normalize the three component weights."""
    if weights is None:
        raise ValueError("weights must not be None")
    arr = np.asarray(weights, dtype=float)
    if arr.shape != (3,):
        raise ValueError("weights must contain exactly three values")
    if not np.all(np.isfinite(arr)):
        raise ValueError("weights must contain only finite values")
    if np.any(arr < 0):
        raise ValueError("weights must be non-negative")
    total = float(np.sum(arr))
    if total <= 0:
        raise ValueError("weights must not all be zero")
    return arr / total


def _score_from_range(
    value: np.ndarray,
    low: float,
    high: float,
    name: str,
    invert: bool = False,
) -> np.ndarray:
    """Map *value* onto a 0-100 scale between *low* and *high*."""
    if not np.isfinite(low) or not np.isfinite(high):
        raise ValueError(f"{name}: calibration bounds must be finite")
    if low >= high:
        raise ValueError(f"{name}: low bound must be strictly below high bound")
    clipped = np.clip(value, low, high)
    if invert:
        return (high - clipped) / (high - low) * 100.0
    return (clipped - low) / (high - low) * 100.0


# ---------------------------------------------------------------------------
# Indicator computations
# ---------------------------------------------------------------------------


def compute_iv_skew(atm_iv: Any, otm_put_iv: Any) -> float | np.ndarray:
    """Return OTM put IV minus ATM IV, in percentage points."""
    atm = _validate_iv(atm_iv, "atm_iv")
    put = _validate_iv(otm_put_iv, "otm_put_iv")
    try:
        result = put - atm
    except ValueError as exc:
        raise ValueError(
            "compute_iv_skew: atm_iv and otm_put_iv have incompatible shapes"
        ) from exc
    return _to_output(result)


def compute_put_call_skew(put_iv: Any, call_iv: Any) -> float | np.ndarray:
    """Return put IV divided by call IV (a ratio)."""
    put = _validate_iv(put_iv, "put_iv")
    call = _validate_iv(call_iv, "call_iv")
    if np.any(call == 0):
        raise ValueError("call_iv must be strictly positive")
    try:
        result = put / call
    except ValueError as exc:
        raise ValueError(
            "compute_put_call_skew: put_iv and call_iv have incompatible shapes"
        ) from exc
    return _to_output(result)


def compute_term_structure_slope(front_iv: Any, back_iv: Any) -> float | np.ndarray:
    """Return back-month IV minus front-month IV, in percentage points."""
    front = _validate_iv(front_iv, "front_iv")
    back = _validate_iv(back_iv, "back_iv")
    try:
        result = back - front
    except ValueError as exc:
        raise ValueError(
            "compute_term_structure_slope: front_iv and back_iv have incompatible shapes"
        ) from exc
    return _to_output(result)


# ---------------------------------------------------------------------------
# Sub-scores (0-100)
# ---------------------------------------------------------------------------


def iv_skew_score(
    iv_skew: Any,
    low: float = DEFAULT_IV_SKEW_LOW,
    high: float = DEFAULT_IV_SKEW_HIGH,
) -> float | np.ndarray:
    """Score IV skew on a 0-100 scale (higher skew scores higher)."""
    arr = _as_float_array(iv_skew, "iv_skew")
    return _to_output(_score_from_range(arr, low, high, "iv_skew"))


def put_call_skew_score(
    put_call_skew: Any,
    low: float = DEFAULT_PUT_CALL_LOW,
    high: float = DEFAULT_PUT_CALL_HIGH,
) -> float | np.ndarray:
    """Score the put/call IV ratio on a 0-100 scale (higher ratio scores higher)."""
    arr = _as_float_array(put_call_skew, "put_call_skew")
    if np.any(arr <= 0):
        raise ValueError("put_call_skew must be strictly positive")
    return _to_output(_score_from_range(arr, low, high, "put_call_skew"))


def term_slope_score(
    term_slope: Any,
    low: float = DEFAULT_TERM_SLOPE_LOW,
    high: float = DEFAULT_TERM_SLOPE_HIGH,
) -> float | np.ndarray:
    """Score the term-structure slope on a 0-100 scale (lower slope scores higher)."""
    arr = _as_float_array(term_slope, "term_slope")
    return _to_output(_score_from_range(arr, low, high, "term_slope", invert=True))


# ---------------------------------------------------------------------------
# Composite score and classification
# ---------------------------------------------------------------------------


def crash_risk_score(
    iv_skew: Any,
    put_call_skew: Any,
    term_slope: Any,
    weights: Sequence[float] = DEFAULT_WEIGHTS,
) -> float | np.ndarray:
    """Return the weighted crash-risk score (0-100) from the three sub-scores.

    Inputs are the 0-100 sub-scores produced by ``iv_skew_score``,
    ``put_call_skew_score``, and ``term_slope_score``.
    """
    w = _validate_weights(weights)
    skew = _as_float_array(iv_skew, "iv_skew")
    pcs = _as_float_array(put_call_skew, "put_call_skew")
    slope = _as_float_array(term_slope, "term_slope")
    try:
        result = w[0] * skew + w[1] * pcs + w[2] * slope
    except ValueError as exc:
        raise ValueError("crash_risk_score: inputs have incompatible shapes") from exc
    return _to_output(result)


def classify_crash_risk(
    score: Any,
    low: float = DEFAULT_LOW_THRESHOLD,
    moderate: float = DEFAULT_MODERATE_THRESHOLD,
    high: float = DEFAULT_HIGH_THRESHOLD,
) -> str:
    """Classify a single crash-risk score into a level."""
    if not np.isfinite(low) or not np.isfinite(moderate) or not np.isfinite(high):
        raise ValueError("classification thresholds must be finite")
    if not (0.0 <= low < moderate < high <= 100.0):
        raise ValueError("thresholds must satisfy 0 <= low < moderate < high <= 100")
    arr = _as_float_array(score, "score")
    if arr.size != 1:
        raise ValueError("score must be a single value")
    value = float(arr)
    if value < low:
        return LEVEL_LOW
    if value < moderate:
        return LEVEL_MODERATE
    if value < high:
        return LEVEL_ELEVATED
    return LEVEL_HIGH


# ---------------------------------------------------------------------------
# Verdict, strict evaluation, and fail-closed gate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CrashRiskVerdict:
    """Result of a crash-risk evaluation."""

    score: float | None
    level: str
    trade_allowed: bool
    iv_skew: float | None = None
    put_call_skew: float | None = None
    term_slope: float | None = None
    components: dict[str, float] = field(default_factory=dict)


def evaluate_crash_risk(
    iv_skew: Any,
    put_call_skew: Any,
    term_slope: Any,
    weights: Sequence[float] = DEFAULT_WEIGHTS,
    gate_threshold: float = DEFAULT_GATE_THRESHOLD,
    low: float = DEFAULT_LOW_THRESHOLD,
    moderate: float = DEFAULT_MODERATE_THRESHOLD,
    high: float = DEFAULT_HIGH_THRESHOLD,
) -> CrashRiskVerdict:
    """Evaluate crash risk from raw option-implied inputs (strict).

    Raises ``ValueError`` on invalid or empty input.
    """
    if not np.isfinite(gate_threshold):
        raise ValueError("gate_threshold must be finite")
    skew = iv_skew_score(iv_skew)
    pcs = put_call_skew_score(put_call_skew)
    slope = term_slope_score(term_slope)
    score = crash_risk_score(skew, pcs, slope, weights=weights)
    if np.ndim(score) != 0:
        raise ValueError("evaluate_crash_risk requires scalar inputs")
    score_f = float(score)
    level = classify_crash_risk(score_f, low=low, moderate=moderate, high=high)
    return CrashRiskVerdict(
        score=score_f,
        level=level,
        trade_allowed=score_f < gate_threshold,
        iv_skew=float(skew),
        put_call_skew=float(pcs),
        term_slope=float(slope),
        components={
            "iv_skew_score": float(skew),
            "put_call_skew_score": float(pcs),
            "term_slope_score": float(slope),
        },
    )


def crash_risk_gate(
    iv_skew: Any = None,
    put_call_skew: Any = None,
    term_slope: Any = None,
    weights: Sequence[float] = DEFAULT_WEIGHTS,
    gate_threshold: float = DEFAULT_GATE_THRESHOLD,
    low: float = DEFAULT_LOW_THRESHOLD,
    moderate: float = DEFAULT_MODERATE_THRESHOLD,
    high: float = DEFAULT_HIGH_THRESHOLD,
) -> CrashRiskVerdict:
    """Evaluate crash risk without raising (fail-closed).

    Any invalid or missing input yields a neutral ``NO_SIGNAL`` verdict
    with ``trade_allowed=False``.
    """
    try:
        return evaluate_crash_risk(
            iv_skew,
            put_call_skew,
            term_slope,
            weights=weights,
            gate_threshold=gate_threshold,
            low=low,
            moderate=moderate,
            high=high,
        )
    except ValueError:
        return CrashRiskVerdict(
            score=None,
            level=LEVEL_NO_SIGNAL,
            trade_allowed=False,
        )