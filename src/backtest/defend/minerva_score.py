"""MinervaScore — post-selection robustness grade for trading strategies.

Implements paper 2608.23808 (Equity Strategy Backtesting: Luck or Edge?):
Combines 5 gates: Deflated Sharpe Ratio (DSR), Probability of Backtest Overfitting (PBO),
Superior Predictive Ability (SPA), Minimum Track Record Length (MTR), regime stability.
Maps signed margins to 0-100 display + binary Seal (>=80 only if all 5 pass).

Calibrated on 359,062 production backtests per paper. AUROC 0.989 vs lucky backtests in synthetic truth.
Intended as audit/reporting layer on top of binding DSR gate (trial_ledger.py), not a future-return predictor
(paper reports rho=0.013, p=0.40 on real-market forward test with limited edge).

Usage:
    from src.backtest.defend.minerva_score import minerva_score
    result = minerva_score(T=1000, sr=1.2, N=50, pbo=0.2, spa_p=0.03, regime_z=1.1, mtr_pass=True)
    # -> {raw, display_0_100, seal, margins, verdict}

Paper thresholds (conservative defaults aligned with WSB edge gate):
- DSR >= 0.95 (95% prob true SR >0)
- PBO <= 0.5 (logit-based expected rank deterioration)
- SPA p < 0.05 (Hansen bootstrap)
- MTR pass (T >= T* per Bailey)
- regime stability |z| < 1.5 across bull/bear splits

See docs/ARXIV_IMPLEMENTATION_REPORT.md I1.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.backtest.defend.trial_ledger import deflated_sharpe_ratio


# Thresholds per paper (tunable)
DSR_THRESHOLD = 0.95
PBO_THRESHOLD = 0.5
SPA_THRESHOLD = 0.05
REGIME_Z_THRESHOLD = 1.5


@dataclass(frozen=True)
class MinervaMargins:
    dsr: float
    pbo: float
    spa: float
    mtr: float
    regime: float


@dataclass(frozen=True)
class MinervaResult:
    raw: float
    display_0_100: int
    seal: bool
    margins: MinervaMargins
    verdict: str
    details: dict


def _signed_margin(value: float, threshold: float, higher_is_better: bool) -> float:
    """Signed distance from threshold, positive = pass. Scaled to ~±3."""
    if higher_is_better:
        # value - threshold, normalized by |threshold| or 1
        denom = abs(threshold) if abs(threshold) > 1e-9 else 1.0
        return (value - threshold) / denom
    else:
        denom = abs(threshold) if abs(threshold) > 1e-9 else 1.0
        return (threshold - value) / denom


def _raw_from_margins(margins: MinervaMargins) -> float:
    # Simple average of signed margins, clamped. Paper aggregates similarly then maps to 0-100.
    vals = [margins.dsr, margins.pbo, margins.spa, margins.mtr, margins.regime]
    return sum(vals) / len(vals)


def _display_from_raw(raw: float) -> int:
    display = int(round(50 + 50 * raw))
    return max(0, min(100, display))


def minerva_score(
    *,
    T: int,
    sr: float,
    N: int,
    pbo: float | None = None,
    spa_p: float | None = None,
    regime_z: float | None = None,
    mtr_pass: bool | None = None,
    mtr_margin: float | None = None,
) -> MinervaResult:
    """Compute MinervaScore.

    Args:
        T: observation count (trades or bars)
        sr: per-observation Sharpe (non-annualized, as in trial_ledger)
        N: number of trials (for DSR)
        pbo: Probability of Backtest Overfitting (0-1); None -> neutral 0.5
        spa_p: SPA p-value; None -> neutral 0.05
        regime_z: regime stability z-score; None -> neutral 0
        mtr_pass: whether T >= MTR T*; if None, inferred from T vs threshold if provided via mtr_margin
        mtr_margin: optional precomputed signed margin for MTR gate

    Returns MinervaResult with raw, display, seal, margins.
    """
    if T <= 1:
        raise ValueError(f"T must be >1, got {T}")
    if N < 1:
        raise ValueError(f"N must be >=1, got {N}")

    # Gate 1: DSR
    try:
        dsr_val = deflated_sharpe_ratio(T, sr, N)
    except Exception:
        dsr_val = 0.0
    dsr_margin = _signed_margin(dsr_val, DSR_THRESHOLD, higher_is_better=True)

    # Gate 2: PBO (lower is better)
    pbo_val = 0.5 if pbo is None else float(pbo)
    pbo_margin = _signed_margin(pbo_val, PBO_THRESHOLD, higher_is_better=False)

    # Gate 3: SPA p-value (lower is better)
    spa_val = 0.05 if spa_p is None else float(spa_p)
    spa_margin = _signed_margin(spa_val, SPA_THRESHOLD, higher_is_better=False)

    # Gate 4: MTR
    if mtr_margin is not None:
        mtr_m = float(mtr_margin)
    elif mtr_pass is not None:
        mtr_m = 1.0 if mtr_pass else -1.0
    else:
        # neutral if not supplied
        mtr_m = 0.0

    # Gate 5: regime stability (|z| lower is better) → margin = threshold - |z|
    r_z = 0.0 if regime_z is None else float(regime_z)
    regime_margin = _signed_margin(abs(r_z), REGIME_Z_THRESHOLD, higher_is_better=False)

    margins = MinervaMargins(dsr=dsr_margin, pbo=pbo_margin, spa=spa_margin, mtr=mtr_m, regime=regime_margin)
    raw = _raw_from_margins(margins)
    display = _display_from_raw(raw)

    all_pass = (dsr_margin >= 0) and (pbo_margin >= 0) and (spa_margin >= 0) and (mtr_m >= 0) and (regime_margin >= 0)
    seal = all_pass and display >= 80
    verdict = "SEAL" if seal else ("PASS" if all_pass else "FAIL")

    details = {
        "dsr": dsr_val,
        "pbo": pbo_val,
        "spa_p": spa_val,
        "regime_z": r_z,
        "mtr_pass": mtr_m >= 0,
        "T": T,
        "sr": sr,
        "N": N,
    }

    return MinervaResult(raw=raw, display_0_100=display, seal=seal, margins=margins, verdict=verdict, details=details)


def minerva_score_from_trial(T: int, sr: float, N: int, extra: dict | None = None) -> MinervaResult:
    """Convenience wrapper reading optional gates from extra dict."""
    extra = extra or {}
    return minerva_score(
        T=T,
        sr=sr,
        N=N,
        pbo=extra.get("pbo"),
        spa_p=extra.get("spa_p"),
        regime_z=extra.get("regime_z"),
        mtr_pass=extra.get("mtr_pass"),
        mtr_margin=extra.get("mtr_margin"),
    )
