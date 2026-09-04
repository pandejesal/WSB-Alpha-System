"""
Multi-Agent Orchestrator — TradingGroup role-based composition.

Defines specialist agent roles (researcher, risk, execution) and a routing
function that composes them into a pipeline for each strategy family.
Following TradingGroup agent composition patterns: each family is processed
by a chain of specialist agents whose outputs feed the next.

Fail-closed: unknown families raise ``UnsupportedRuleShape`` — never silent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from src.ops.signals import UnsupportedRuleShape


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentRole:
    """A specialist agent role in the multi-agent pipeline."""
    name: str
    description: str
    allowed_families: frozenset[str]
    processor: Callable[..., dict[str, Any]]


def _researcher_process(
    signal: dict[str, Any],
    *,
    data: pd.DataFrame | None = None,
    tickers: list[str] | None = None,
    **_params: Any,
) -> dict[str, Any]:
    """Researcher agent: validates that the raw signal contains actionable
    targets. Flags empty or unavailable signals for downstream veto."""
    out = dict(signal)
    if signal.get("signal") == "FLAT" or signal.get("data_unavailable"):
        out["researcher_verdict"] = "NO_BID"
        out["researcher_reason"] = signal.get("warning", "no_signal")
    else:
        out["researcher_verdict"] = "PROCEED"
        out["researcher_reason"] = "targets_present"
    return out


def _risk_process(
    signal: dict[str, Any],
    *,
    max_targets: int = 10,
    max_single_weight: float = 0.50,
    **_params: Any,
) -> dict[str, Any]:
    """Risk agent: enforces concentration limits and vetoes oversized positions.
    Veto flips the signal to FLAT — never allows a risk-breach through."""
    out = dict(signal)
    if out.get("researcher_verdict") == "NO_BID":
        out["risk_verdict"] = "VETO"
        out["risk_reason"] = "upstream_no_bid"
        out["signal"] = "FLAT"
        return out

    targets = out.get("targets", [])
    if not targets:
        out["risk_verdict"] = "VETO"
        out["risk_reason"] = "no_targets"
        out["signal"] = "FLAT"
        return out

    # Enforce max targets
    if len(targets) > max_targets:
        out["risk_verdict"] = "VETO"
        out["risk_reason"] = f"too_many_targets:{len(targets)}>{max_targets}"
        out["signal"] = "FLAT"
        return out

    # Enforce single-position weight cap
    for t in targets:
        w = t.get("weight", 0)
        if w > max_single_weight:
            out["risk_verdict"] = "VETO"
            out["risk_reason"] = f"weight_breach:{w}>{max_single_weight}"
            out["signal"] = "FLAT"
            return out

    out["risk_verdict"] = "PASS"
    out["risk_reason"] = "within_limits"
    return out


def _execution_process(
    signal: dict[str, Any],
    *,
    min_weight: float = 0.01,
    normalize: bool = True,
    **_params: Any,
) -> dict[str, Any]:
    """Execution agent: normalises weights, clips micro-positions, and
    stamps the final output with an execution receipt."""
    out = dict(signal)
    if out.get("risk_verdict") == "VETO" or out.get("signal") == "FLAT":
        out["execution_verdict"] = "SKIP"
        out["execution_reason"] = "vetoed_or_flat"
        return out

    targets = out.get("targets", [])
    if not targets:
        out["execution_verdict"] = "SKIP"
        out["execution_reason"] = "no_targets"
        out["signal"] = "FLAT"
        return out

    # Clip micro-positions below min_weight
    targets = [t for t in targets if t.get("weight", 0) >= min_weight]

    if not targets:
        out["execution_verdict"] = "SKIP"
        out["execution_reason"] = "all_targets_below_min_weight"
        out["signal"] = "FLAT"
        return out

    # Normalise weights to sum to 1.0
    if normalize:
        total = sum(t.get("weight", 0) for t in targets)
        if total > 0:
            targets = [{**t, "weight": t["weight"] / total} for t in targets]

    out["targets"] = targets
    out["execution_verdict"] = "EXECUTE"
    out["execution_reason"] = "ready"
    return out


# ---------------------------------------------------------------------------
# Built-in role instances
# ---------------------------------------------------------------------------

RESEARCHER = AgentRole(
    name="researcher",
    description="Gathers data, scores opportunities, flags no-signal states.",
    allowed_families=frozenset({
        "momentum", "trend", "mean_reversion", "breakout_burst",
        "low_vol", "event_driven", "vol_targeting", "ta_rules",
        "sentiment_overlay", "xgboost_exits",
    }),
    processor=_researcher_process,
)

RISK = AgentRole(
    name="risk",
    description="Applies concentration limits, weight caps, and veto authority.",
    allowed_families=frozenset({
        "momentum", "trend", "mean_reversion", "breakout_burst",
        "low_vol", "event_driven", "vol_targeting", "ta_rules",
        "sentiment_overlay", "xgboost_exits",
    }),
    processor=_risk_process,
)

EXECUTION = AgentRole(
    name="execution",
    description="Normalises weights, clips micro-positions, stamps receipts.",
    allowed_families=frozenset({
        "momentum", "trend", "mean_reversion", "breakout_burst",
        "low_vol", "event_driven", "vol_targeting", "ta_rules",
        "sentiment_overlay", "xgboost_exits",
    }),
    processor=_execution_process,
)

# Canonical pipeline order
DEFAULT_PIPELINE: list[AgentRole] = [RESEARCHER, RISK, EXECUTION]

# Registry: family -> custom pipeline override (None means default)
_FAMILY_PIPELINE_OVERRIDES: dict[str, list[AgentRole] | None] = {
    # Example: sentiment families skip researcher (it's an overlay, not a primary signal)
    # "sentiment_overlay": [RISK, EXECUTION],
}


# ---------------------------------------------------------------------------
# Role-based routing
# ---------------------------------------------------------------------------

def get_pipeline_for_family(family: str) -> list[AgentRole]:
    """Return the agent pipeline for a strategy family.

    Raises ``UnsupportedRuleShape`` for unknown families (fail-closed).
    """
    if family in _FAMILY_PIPELINE_OVERRIDES:
        override = _FAMILY_PIPELINE_OVERRIDES[family]
        if override is None:
            return list(DEFAULT_PIPELINE)
        return list(override)

    # Validate family exists in at least one role's allowed set
    any_known = any(family in r.allowed_families for r in DEFAULT_PIPELINE)
    if not any_known:
        raise UnsupportedRuleShape(
            f"Unknown strategy family '{family}' — cannot route to agent pipeline"
        )

    return list(DEFAULT_PIPELINE)


def route_signal_through_agents(
    signal: dict[str, Any],
    family: str,
    *,
    data: pd.DataFrame | None = None,
    tickers: list[str] | None = None,
    risk_params: dict[str, Any] | None = None,
    execution_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Route a raw signal through the specialist agent pipeline.

    Each agent in the pipeline processes the signal in order, and its
    output becomes the input for the next agent. If any agent vetoes,
    the pipeline short-circuits (fail-closed).

    Parameters
    ----------
    signal : dict
        Raw signal output from the signal generator.
    family : str
        Strategy family name for pipeline selection.
    data : DataFrame, optional
        Market data (passed through to researcher role).
    tickers : list[str], optional
        Ticker list (passed through to researcher role).
    risk_params : dict, optional
        Override parameters for the risk agent.
    execution_params : dict, optional
        Override parameters for the execution agent.

    Returns
    -------
    dict
        Final signal after processing through all agents.
    """
    pipeline = get_pipeline_for_family(family)

    result = dict(signal)
    for role in pipeline:
        extra_kwargs: dict[str, Any] = {}
        if role.name == "researcher":
            extra_kwargs["data"] = data
            extra_kwargs["tickers"] = tickers
        elif role.name == "risk" and risk_params:
            extra_kwargs.update(risk_params)
        elif role.name == "execution" and execution_params:
            extra_kwargs.update(execution_params)

        result = role.processor(result, **extra_kwargs)

        # Short-circuit on veto or no-bid — fail-closed
        verdict = result.get(f"{role.name}_verdict")
        if verdict == "VETO" or verdict == "NO_BID":
            result["signal"] = "FLAT"
            result["pipeline_vetoed_by"] = role.name
            break

    return result
