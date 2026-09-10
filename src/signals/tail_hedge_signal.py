"""Tail-hedge sleeve signal adapter (B4c, P2 item S8).

Wraps compute-only ``src.risk.crash_risk.evaluate_crash_risk`` into a
LONG/FLAT sleeve signal for the tail_risk_sentinel hunt family.

Status: INACTIVE — registered for autonomous consumption but never traded
until the hunt clears gatespec38 Track 4 + prereg. See
hunts/tail_risk_sentinel/BRIEF.yaml.

Fail-closed: any invalid input yields FLAT with reason (never raises).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SLEEVE_NAME = "tail_hedge"
SLEEVE_STATUS = "INACTIVE"  # never active until gates pass
HEDGE_SCORE_THRESHOLD = 60.0  # per BRIEF.yaml edge_gate_params


@dataclass(frozen=True)
class TailHedgeSignal:
    """Sleeve signal for the tail-hedge overlay."""

    sleeve: str
    signal: str  # LONG (hedge on) | FLAT (hedge off)
    score: float | None
    level: str
    reason: str
    status: str = SLEEVE_STATUS


def tail_hedge_signal(
    iv_skew: object = None,
    put_call_skew: object = None,
    term_slope: object = None,
    threshold: float = HEDGE_SCORE_THRESHOLD,
) -> TailHedgeSignal:
    """Map crash-risk score to a LONG/FLAT hedge signal. Fail-closed."""
    try:
        from src.risk.crash_risk import evaluate_crash_risk

        verdict = evaluate_crash_risk(
            iv_skew,
            put_call_skew,
            term_slope,
            gate_threshold=threshold,
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed by design
        logger.warning("tail_hedge fail-closed: %s", exc)
        return TailHedgeSignal(
            sleeve=SLEEVE_NAME,
            signal="FLAT",
            score=None,
            level="UNKNOWN",
            reason=f"fail-closed: {exc}",
        )
    try:
        score = float(verdict.score) if verdict.score is not None else None
    except (TypeError, ValueError):
        return TailHedgeSignal(
            sleeve=SLEEVE_NAME,
            signal="FLAT",
            score=None,
            level=str(verdict.level),
            reason="fail-closed: non-numeric score",
        )
    if score is not None and score > threshold:
        return TailHedgeSignal(
            sleeve=SLEEVE_NAME,
            signal="LONG",
            score=score,
            level=str(verdict.level),
            reason=f"hedge on: score {score:.1f} > {threshold}",
        )
    return TailHedgeSignal(
        sleeve=SLEEVE_NAME,
        signal="FLAT",
        score=score,
        level=str(verdict.level),
        reason=f"hedge off: score {score} <= {threshold}" if score is not None else "hedge off: no score",
    )
