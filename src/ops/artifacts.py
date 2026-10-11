"""Canonical schema + validation for docs/data/ops artifacts (audit finding F3).

Producers (PaperExecutor, scripts/reconcile.py) and consumers (GateEvaluator,
scripts/baseline_paper_track.py) MUST go through these helpers so the artifact
contract lives in exactly one place. The executor/gate schema mismatch
(executor wrote {"run_id", "fills": [{"sleeve": ...}]}, gate expected a bare
list of {"sleeve_id": ...} dicts) was a Critical audit finding: G1 counted
top-level dict keys and G2 raised AttributeError on string keys.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Order lifecycle (audit finding F4): a submission is NOT a fill.
# ---------------------------------------------------------------------------
ORDER_STATUS_SUBMITTING = "SUBMITTING"  # intent persisted locally, broker call not yet made
ORDER_STATUS_SUBMITTED = "SUBMITTED"  # broker acknowledged receipt; no fill price yet
ORDER_STATUS_ACCEPTED = "ACCEPTED"
ORDER_STATUS_PARTIAL = "PARTIAL"
ORDER_STATUS_FILLED = "FILLED"  # broker-confirmed complete fill
ORDER_STATUS_CANCELLED = "CANCELLED"
ORDER_STATUS_REJECTED = "REJECTED"
ORDER_STATUS_FAILED = "FAILED"  # local failure at/before submission; broker outcome unknown
ORDER_STATUS_UNKNOWN = "UNKNOWN"  # ambiguous outcome (timeout/crash mid-call): never auto-retry

KNOWN_ORDER_STATUSES = {
    ORDER_STATUS_SUBMITTING,
    ORDER_STATUS_SUBMITTED,
    ORDER_STATUS_ACCEPTED,
    ORDER_STATUS_PARTIAL,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_CANCELLED,
    ORDER_STATUS_REJECTED,
    ORDER_STATUS_FAILED,
    ORDER_STATUS_UNKNOWN,
}

# Only broker-confirmed fills count toward completed-trade gates.
CONFIRMED_FILL_STATUSES = {ORDER_STATUS_FILLED, ORDER_STATUS_PARTIAL}

# Ambiguous terminal states: the order may exist at the broker, so a retry
# must NOT be sent without querying the broker by client_order_id first.
AMBIGUOUS_ORDER_STATUSES = {
    ORDER_STATUS_SUBMITTING,
    ORDER_STATUS_SUBMITTED,
    ORDER_STATUS_ACCEPTED,
    ORDER_STATUS_UNKNOWN,
}

# Canonical fills.json wrapper: {"run_id": ..., "fills": [ ... ]}
# Required for a fill to be schema-valid: identity, sleeve attribution, status.
# (ticker/side/qty/avg_px are validated for type when present.)
REQUIRED_FILL_FIELDS = ("client_order_id", "sleeve_id", "status")

# Reconciliation status values (audit finding F4): a fetch failure must never
# produce "clean".
RECON_STATUS_CLEAN = "clean"
RECON_STATUS_MISMATCH = "mismatch"
RECON_STATUS_UNKNOWN = "unknown"


def extract_fills(doc: Any) -> list[dict]:
    """Return the fills list from a fills artifact.

    Accepts either the canonical wrapper ``{"run_id": ..., "fills": [...]}``
    (written by PaperExecutor) or a bare list (historical artifacts).
    Raises ValueError on anything structurally malformed so callers can
    fail closed.
    """
    if doc is None:
        raise ValueError("fills artifact is missing")
    if isinstance(doc, dict):
        fills = doc.get("fills")
        if fills is None:
            raise ValueError("fills artifact dict has no 'fills' key")
    elif isinstance(doc, list):
        fills = doc
    else:
        raise ValueError(f"fills artifact has invalid type {type(doc).__name__}")  # noqa: TRY004 - callers contract on ValueError

    if not isinstance(fills, list):
        raise ValueError(f"'fills' must be a list, got {type(fills).__name__}")  # noqa: TRY004 - callers contract on ValueError

    for fill in fills:
        if not isinstance(fill, dict):
            raise ValueError("each fill must be an object")  # noqa: TRY004 - callers contract on ValueError
        missing = [f for f in REQUIRED_FILL_FIELDS if f not in fill]
        if missing:
            raise ValueError(f"fill missing required fields: {missing}")
        status = str(fill.get("status", "")).upper()
        if status not in KNOWN_ORDER_STATUSES:
            raise ValueError(f"fill has unknown status: {fill.get('status')!r}")
        for numeric_field in ("qty", "avg_px", "fee"):
            if fill.get(numeric_field) is not None and not isinstance(fill[numeric_field], (int, float)):
                raise ValueError(f"fill field {numeric_field} must be numeric")
    return fills


def is_confirmed_fill(fill: dict) -> bool:
    """True only for broker-confirmed fills (FILLED/PARTIAL with a fill price)."""
    if not isinstance(fill, dict):
        return False
    if str(fill.get("status", "")).upper() not in CONFIRMED_FILL_STATUSES:
        return False
    return fill.get("avg_px") is not None


def sleeve_of(fill: dict) -> str | None:
    """Sleeve identifier; canonical key is sleeve_id, legacy key sleeve is read
    as a fallback so historical artifacts keep working."""
    return fill.get("sleeve_id") if fill.get("sleeve_id") is not None else fill.get("sleeve")


def make_fill_record(
    client_order_id: str,
    sleeve_id: str,
    ticker: str,
    side: str,
    qty: float,
    status: str,
    avg_px: float | None = None,
    venue_order_id: str | None = None,
    fee: float = 0.0,
    ts: str = "",
) -> dict:
    """Build a canonical fill/order-event record. Executor-side constructor so
    the published schema cannot drift."""
    return {
        "client_order_id": client_order_id,
        "venue_order_id": venue_order_id,
        "sleeve_id": sleeve_id,
        "ticker": ticker,
        "side": side,
        "qty": qty,
        "fee": fee,
        "avg_px": avg_px,
        "status": status,
        "ts": ts,
    }
