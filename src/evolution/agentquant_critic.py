"""
AgentQuant Critic — Proposal Validation & Deduplication
=======================================================

Ported from AgentQuant's src/agent/swarm/critic_agent.py.
Screens strategy proposals via:
  1. Deduplication against existing proposals
  2. Trend-following window ordering enforcement
  3. Parameter range sanity checks
  4. Walk-forward efficiency gate

No LLM dependency. All local.
"""

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CriticVerdict:
    """Result of critiquing a single proposal."""
    approved: bool
    reason: str
    genome_id: str = ""
    fitness: float = 0.0
    issues: list[str] = field(default_factory=list)


class CriticAgent:
    """
    Validates strategy proposals before they enter the evolution pool.
    Ported from AgentQuant's CriticAgent.

    Checks:
      - Deduplication: no two proposals with identical params
      - Window ordering: short < medium < long for trend_following
      - Parameter sanity: values within valid bounds
      - Walk-forward efficiency: must exceed minimum threshold
      - Minimum trade count: too few trades = overfit
    """

    def __init__(
        self,
        min_wfe: float = 0.3,
        min_trades: int = 10,
        max_duplicate_distance: float = 0.001,
    ):
        self.min_wfe = min_wfe
        self.min_trades = min_trades
        self.max_duplicate_distance = max_duplicate_distance
        self.approved_genomes: list[dict] = []
        self.rejection_history: list[dict] = []

    def _check_trend_following_windows(self, params: dict) -> list[str]:
        """
        Enforce trend_following window ordering: short < medium < long.
        Returns list of issues (empty if valid).
        """
        issues = []
        sw = params.get("short_window")
        mw = params.get("medium_window")
        lw = params.get("long_window")

        if sw is None or mw is None or lw is None:
            return issues  # not a trend_following strategy

        if not (isinstance(sw, (int, float)) and isinstance(mw, (int, float)) and isinstance(lw, (int, float))):
            return issues

        if sw >= mw:
            issues.append(f"short_window ({sw}) must be < medium_window ({mw})")
        if mw >= lw:
            issues.append(f"medium_window ({mw}) must be < long_window ({lw})")

        return issues

    def _check_param_sanity(self, params: dict, family: str) -> list[str]:
        """
        Validate parameter values are within reasonable bounds.
        Returns list of issues.
        """
        issues = []

        # Universal checks
        for k, v in params.items():
            if isinstance(v, (int, float)):
                if v > 10000:
                    issues.append(f"{k}={v} exceeds maximum allowed value")

        # Family-specific checks
        if family == "momentum":
            lb = params.get("lookback", 20)
            if isinstance(lb, (int, float)) and (lb < 2 or lb > 500):
                issues.append(f"lookback={lb} outside valid range [2, 500]")

        elif family == "mean_reversion":
            z_entry = params.get("z_entry", 2.0)
            if isinstance(z_entry, (int, float)) and (z_entry < 0.1 or z_entry > 10.0):
                issues.append(f"z_entry={z_entry} outside valid range [0.1, 10.0]")

        elif family == "volatility":
            target_vol = params.get("target_vol", 0.15)
            if isinstance(target_vol, (int, float)) and (target_vol < 0.01 or target_vol > 2.0):
                issues.append(f"target_vol={target_vol} outside valid range [0.01, 2.0]")

        return issues

    def _check_duplicate(self, params: dict, family: str) -> list[str]:
        """
        Check if this proposal is a near-duplicate of an already-approved one.
        Uses normalized Hamming distance on parameter values.
        """
        issues = []

        for approved in self.approved_genomes:
            if approved.get("strategy_family") != family:
                continue

            approved_params = approved.get("params", {})
            if set(params.keys()) != set(approved_params.keys()):
                continue

            # Compute normalized distance
            distances = []
            for k in params:
                v1 = params[k]
                v2 = approved_params.get(k)
                if type(v1) is not type(v2):
                    distances.append(1.0)
                    continue
                if isinstance(v1, bool):
                    distances.append(0.0 if v1 == v2 else 1.0)
                elif isinstance(v1, (int, float)):
                    # Normalize by typical range
                    max_val = max(abs(v1), abs(v2), 1.0)
                    distances.append(abs(v1 - v2) / max_val)
                else:
                    distances.append(0.0 if v1 == v2 else 1.0)

            avg_dist = float(np.mean(distances)) if distances else 0.0
            if avg_dist < self.max_duplicate_distance:
                issues.append(
                    f"Near-duplicate of existing proposal (distance={avg_dist:.4f})"
                )
                break

        return issues

    def critique(
        self,
        genome_id: str,
        params: dict,
        family: str,
        fitness: float = 0.0,
        sharpe_test: float = 0.0,
        walk_forward_efficiency: float = 0.0,
        trade_count: int = 0,
    ) -> CriticVerdict:
        """
        Critique a single proposal and return a verdict.

        Args:
            genome_id: Unique identifier for the genome.
            params: Strategy parameters.
            family: Strategy family name.
            fitness: Computed fitness score.
            sharpe_test: Out-of-sample Sharpe ratio.
            walk_forward_efficiency: Walk-forward efficiency ratio.
            trade_count: Number of trades in backtest.

        Returns:
            CriticVerdict with approved=True/False and reason.
        """
        all_issues = []

        # 1. Trend-following window ordering
        window_issues = self._check_trend_following_windows(params)
        all_issues.extend(window_issues)

        # 2. Parameter sanity
        sanity_issues = self._check_param_sanity(params, family)
        all_issues.extend(sanity_issues)

        # 3. Deduplication
        dup_issues = self._check_duplicate(params, family)
        all_issues.extend(dup_issues)

        # 4. Walk-forward efficiency gate
        if walk_forward_efficiency < self.min_wfe:
            all_issues.append(
                f"WFE={walk_forward_efficiency:.3f} below minimum {self.min_wfe}"
            )

        # 5. Minimum trade count
        if trade_count < self.min_trades:
            all_issues.append(
                f"Trade count {trade_count} below minimum {self.min_trades}"
            )

        approved = len(all_issues) == 0

        verdict = CriticVerdict(
            approved=approved,
            reason="; ".join(all_issues) if all_issues else "All checks passed",
            genome_id=genome_id,
            fitness=fitness,
            issues=all_issues,
        )

        if approved:
            self.approved_genomes.append({
                "genome_id": genome_id,
                "strategy_family": family,
                "params": params.copy(),
                "fitness": fitness,
            })
            logger.info("APPROVED: %s (fitness=%.4f)", genome_id, fitness)
        else:
            self.rejection_history.append({
                "genome_id": genome_id,
                "reason": verdict.reason,
                "fitness": fitness,
            })
            logger.info("REJECTED: %s — %s", genome_id, verdict.reason)

        return verdict

    def critique_batch(
        self,
        proposals: list[dict],
    ) -> list[CriticVerdict]:
        """
        Critique a batch of proposals. Each proposal dict should have keys:
            genome_id, params, family, fitness, sharpe_test,
            walk_forward_efficiency, trade_count.

        Returns:
            List of CriticVerdict, one per proposal.
        """
        verdicts = []
        for p in proposals:
            v = self.critique(
                genome_id=p.get("genome_id", "unknown"),
                params=p.get("params", {}),
                family=p.get("family", "unknown"),
                fitness=p.get("fitness", 0.0),
                sharpe_test=p.get("sharpe_test", 0.0),
                walk_forward_efficiency=p.get("walk_forward_efficiency", 0.0),
                trade_count=p.get("trade_count", 0),
            )
            verdicts.append(v)
        return verdicts

    def summary(self) -> dict:
        """Return a summary of critic activity."""
        return {
            "approved_count": len(self.approved_genomes),
            "rejected_count": len(self.rejection_history),
            "approval_rate": (
                len(self.approved_genomes)
                / max(1, len(self.approved_genomes) + len(self.rejection_history))
            ),
            "top_approved": sorted(
                self.approved_genomes,
                key=lambda g: g.get("fitness", 0),
                reverse=True,
            )[:5],
        }
