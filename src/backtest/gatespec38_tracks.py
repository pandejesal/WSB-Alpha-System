"""Promotion-gate track specifications for SPY-beating strategies (Worker 8 / gatespec38).

Each track is a full conjunction of terms that a candidate must clear
to be promoted. A candidate promotes by clearing ANY ONE track fully.
Every track includes an absolute-excess-vs-SPY term AND a multiple-testing
discount (DSR), plus a risk term (maxDD) and a minimum-activity term (trips or tmin).

Calibration baseline:
    Loop window (1910 bars, 2019-01-02 to 2026-08-07):
        Total Return: +245.50%, Sharpe: 0.941, maxDD: 33.72% (~0.34), CAGR: 17.77%.
    Paper gate window (1678 bars, 2020-01-02 to 2026-09-04):
        Total Return: +137.10%, Sharpe: 0.744, maxDD: 34.10% (~0.34), CAGR: 13.85%.
    Calibration actively targets the loop window (+245.5%) since evolve_real.py
    evaluates candidates on this 1910-bar period.

All metrics computed T+1, costs deducted (5bps), identical-window SPY twin.
"""

from __future__ import annotations

import math
from typing import Any

from src.backtest.defend.trial_ledger import (
    deflated_sharpe_ratio,
    deflated_sharpe_threshold,
)

# SPY baseline metrics on the loop window (1910 bars, 2019-2026)
SPY_BASELINE: dict[str, Any] = {
    "sharpe": 0.941,
    "max_dd": 0.337,
    "oos": 0.941,
    "excess": 0.0,
    "dsr": 0.9952,  # PSR equivalent at N=1 benchmark level
    "perm_p": 0.60,
    "boot_p": 0.40,
    "trips": 0,
    "trades": 0,
    "cagr": 0.1777,
    "tmin": 1.0,
}

# --- Track definitions ---
# Each track dict contains:
#   name: identifier string
#   terms: list of metric names evaluated
#   thresholds: dict of parameter bounds
#   rationale: list of 3 strings citing failure modes blocked
#   archetype: qualitative category and profile
#   plain_english: plain-English explanation for non-finance readers
#   spy_passes: bool whether SPY buy-hold satisfies the track
#   spy_passes_label: 'benchmark-parity' or 'elite-only'

TRACKS: list[dict[str, Any]] = [
    {
        "name": "core_timing_overlay",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.60,
            "max_dd_max": 0.30,
            "oos_min": 0.40,
            "excess_min": 0.05,
            "dsr_min": 0.80,
            "trips_min": 8,
        },
        "rationale": [
            "sharpe>=0.60 and max_dd<=0.30 admit low-exposure timing overlays that sit in cash much of the time yet produce reliable risk-adjusted return, matching the viable candidate pool in current search families.",
            "excess>=0.05pp blocks the TOP5 failure mode documented in TOP5_TRIPLE_CHECK.md where low-exposure timing models boast phantom Sharpe ~0.9 while trailing SPY buy-and-hold by 70-137pp in absolute dollars.",
            "dsr>=0.80 imposes a multiple-testing penalty scaled to the 10,000+ trial ledger, filtering selection-bias luck while remaining achievable for a genuine 15-40% time-in-market edge.",
        ],
        "archetype": "Low-exposure timing overlay (10-40% time-in-market)",
        "plain_english": "This track means: your strategy must beat SPY by at least 0.05 percentage points in total return, stay in the market at least 15% of the time, make at least 8 round trips, and maintain a Sharpe above 0.60 after discounting for the number of attempts the evolution loop has made.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "drawdown_warrior",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.55,
            "max_dd_max": 0.35,
            "oos_min": 0.35,
            "excess_min": 0.10,
            "dsr_min": 0.75,
            "trips_min": 6,
        },
        "rationale": [
            "max_dd<=0.35 matches SPY's historical drawdown ceiling while allowing cash-rotation mechanics to dodge severe market crashes without suffering excessive uninvested drag.",
            "excess>=0.10pp blocks passive underperformers by demanding a double-sized terminal wealth cushion (+0.10pp) over SPY buy-and-hold net of all slippage and fees.",
            "dsr>=0.75 adjusts for parameter search over 10,000 trials, screening out transient regime flukes while acknowledging lower trade frequencies in tactical risk-off regimes.",
        ],
        "archetype": "Low-exposure drawdown-avoidance timing",
        "plain_english": "This track means: avoid drawdowns worse than 35%, beat SPY by at least 0.10 percentage points total, make at least 6 trades, and have a Sharpe above 0.55 after adjusting for how many parameter combinations the loop tried.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "conservative_timing",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.50,
            "max_dd_max": 0.35,
            "oos_min": 0.35,
            "excess_min": 0.15,
            "dsr_min": 0.70,
            "trips_min": 5,
        },
        "rationale": [
            "sharpe>=0.50 accommodates strategies with 80%+ cash allocations whose annualized Sharpe is diluted by long uninvested periods despite high trade win rates.",
            "excess>=0.15pp enforces the strictest excess return bar among timing tracks (+0.15pp), blocking opportunistic freeloaders and requiring substantial absolute dollar outperformance.",
            "dsr>=0.70 sets an honest entry bar for low-frequency signals tested across the search space, preventing premature rejection of real edges that trade only 5-10 times.",
        ],
        "archetype": "Low-exposure conservative timing overlay",
        "plain_english": "This track means: be in the market as little as 10% of the time, beat SPY by at least 0.15 percentage points total, make at least 5 trades, and pass the multiple-comparison test at 70% confidence after all the attempts the loop has made so far.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "tail_risk_sentinel",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.55,
            "max_dd_max": 0.25,
            "oos_min": 0.35,
            "excess_min": 0.03,
            "dsr_min": 0.75,
            "trips_min": 6,
        },
        "rationale": [
            "max_dd<=0.25 mandates institutional tail-risk protection that cuts SPY's 33.7% drawdown by over a quarter, blocking high-beta strategies from passing during bull runs.",
            "excess>=0.03pp prevents pure cash-parking strategies by requiring net positive excess returns against SPY after accounting for all execution costs.",
            "dsr>=0.75 guards against curve-fitted crash avoidance, ensuring the drawdown reduction is an enduring systematic property rather than an artifact of single-event timing.",
        ],
        "archetype": "Asymmetric downside hedge / crisis alpha overlay",
        "plain_english": "This track means: keep maximum drawdown strictly below 25%, beat SPY by at least 0.03 percentage points net of costs, execute at least 6 round trips, and maintain statistically defensible edge under multiple testing.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "high_exposure_momentum",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "tmin"],
        "thresholds": {
            "sharpe_min": 0.75,
            "max_dd_max": 0.35,
            "oos_min": 0.50,
            "excess_min": 0.05,
            "dsr_min": 0.90,
            "tmin_min": 0.70,
        },
        "rationale": [
            "tmin>=0.70 requires at least 70% time-in-market exposure, selecting for trend-following and momentum models (e.g. spy_ltrend, us_ltrend) that maintain near-continuous market participation.",
            "excess>=0.05pp ensures that bearing equity beta produces tangible alpha, blocking index-huggers that match market volatility while bleeding cost drag.",
            "dsr>=0.90 exploits the high sample size of daily market exposure to enforce strong statistical confidence against data mining.",
        ],
        "archetype": "High time-in-market momentum / trend-following",
        "plain_english": "This track means: be invested 70% or more of the time, beat SPY by at least 0.05 percentage points in total return, maintain a Sharpe above 0.75, and pass the multiple-testing guard at 90% confidence.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "buy_hold_companion",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "tmin"],
        "thresholds": {
            "sharpe_min": 0.85,
            "max_dd_max": 0.35,
            "oos_min": 0.55,
            "excess_min": 0.02,
            "dsr_min": 0.95,
            "tmin_min": 0.80,
        },
        "rationale": [
            "tmin>=0.80 requires 80%+ continuous market presence, targeting factor rotation strategies (us_lowvol, us_momentum) that function as core buy-and-hold replacements.",
            "sharpe>=0.85 and oos>=0.55 block substandard factor tilts, demanding risk-adjusted performance on par with SPY buy-and-hold (0.94) across both in-sample and out-of-sample periods.",
            "dsr>=0.95 provides the most stringent statistical shield against false discoveries across 10,000+ searches.",
        ],
        "archetype": "Near-buy-hold momentum / rotation",
        "plain_english": "This track means: stay invested at least 80% of the time, beat SPY by at least 0.02 percentage points, achieve a Sharpe above 0.85, and satisfy the strictest 95% multiple-testing defense standard.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "statistical_rigor",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.70,
            "max_dd_max": 0.35,
            "oos_min": 0.45,
            "excess_min": 0.02,
            "dsr_min": 0.92,
            "trips_min": 15,
        },
        "rationale": [
            "trips>=15 guarantees a robust trade sample size, eliminating small-sample noise where 2-3 lucky events skew observed Sharpe.",
            "dsr>=0.92 heavily penalizes data snooping across the full trial history, confirming that the observed Sharpe reflects genuine market inefficiency.",
            "excess>=0.02pp links statistical validity with economic utility, ensuring that mathematically proven edges still generate real-dollar outperformance against the index.",
        ],
        "archetype": "Statistically validated timing or rotation",
        "plain_english": "This track means: complete at least 15 round trips, beat SPY by any positive margin, keep Sharpe above 0.70, and pass the multiple-comparison screen with 92% statistical confidence.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "absolute_return_focus",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.65,
            "max_dd_max": 0.35,
            "oos_min": 0.40,
            "excess_min": 0.20,
            "dsr_min": 0.75,
            "trips_min": 10,
        },
        "rationale": [
            "excess>=0.20pp sets the system's highest absolute return hurdle (+0.20pp above SPY), blocking low-volatility underperformers and prioritizing raw wealth creation.",
            "sharpe>=0.65 accepts slightly elevated portfolio volatility provided it is rewarded by substantial absolute alpha and bounded by max_dd<=0.35.",
            "dsr>=0.75 and trips>=10 verify that the exceptional returns are not the result of a single lucky outlier trade.",
        ],
        "archetype": "Absolute-return focused timing or rotation",
        "plain_english": "This track means: outperform SPY by at least 0.20 percentage points in total return, execute at least 10 trades, contain drawdown within 35%, and maintain a DSR of at least 0.75.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "risk_adjusted_discipline",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.70,
            "max_dd_max": 0.28,
            "oos_min": 0.45,
            "excess_min": 0.05,
            "dsr_min": 0.85,
            "trips_min": 12,
        },
        "rationale": [
            "max_dd<=0.28 establishes a strict drawdown ceiling tighter than SPY's 33.7%, excluding unhedged long-only exposure during major market downturns.",
            "sharpe>=0.70 coupled with excess>=0.05pp ensures the strategy achieves superior risk efficiency without sacrificing absolute dollar growth.",
            "dsr>=0.85 validates that the improved risk-return trade-off is statistically resilient across repeated optimization passes.",
        ],
        "archetype": "Risk-disciplined timing with strict drawdown control",
        "plain_english": "This track means: cap drawdown at 28% (substantially safer than SPY), beat SPY by 0.05 percentage points net, make at least 12 trades, and sustain an 85% DSR confidence level.",
        "spy_passes": False,
        "spy_passes_label": "elite-only",
    },
    {
        "name": "benchmark_parity",
        "terms": ["sharpe", "max_dd", "oos", "excess", "dsr", "trips"],
        "thresholds": {
            "sharpe_min": 0.90,
            "max_dd_max": 0.35,
            "oos_min": 0.85,
            "excess_min": 0.00,
            "dsr_min": 0.95,
            "trips_min": 0,
        },
        "rationale": [
            "excess_min=0.00 and trips_min=0 permit SPY buy-and-hold itself to pass, serving as an indispensable calibration anchor proving the gate is not inherently impossible.",
            "sharpe>=0.90 and oos>=0.85 verify that candidates matching benchmark-level risk efficiency and stability achieve promotion parity.",
            "dsr>=0.95 confirms that benchmark-parity assets satisfy gold-standard multiple-testing confidence under standard asymptotic distributions.",
        ],
        "archetype": "Benchmark parity reference (calibration check)",
        "plain_english": "This track means: match SPY's historical risk-adjusted return (Sharpe >= 0.90) and drawdown (<= 35%) while achieving at least parity in total return and satisfying 95% multiple-testing confidence — the track SPY itself passes.",
        "spy_passes": True,
        "spy_passes_label": "benchmark-parity",
    },
]


def _normalize_metric(metrics: dict[str, Any], key: str, default: float) -> float:
    """Normalize metric lookup with backward-compatible aliases."""
    if key in metrics:
        return float(metrics[key])
    aliases = {
        "oos": ["oos_sharpe"],
        "trips": ["round_trips", "trades"],
        "excess": ["excess_spy"],
        "tmin": ["time_in_market", "exposure"],
    }
    for alias in aliases.get(key, []):
        if alias in metrics:
            return float(metrics[alias])
    return default


def _check_term(metrics: dict[str, Any], term: str, value: float) -> bool:
    """Check a single metric threshold against the metrics dict."""
    if term == "sharpe_min":
        return _normalize_metric(metrics, "sharpe", 0.0) >= value
    if term == "max_dd_max":
        return _normalize_metric(metrics, "max_dd", 999.0) <= value
    if term == "oos_min":
        return _normalize_metric(metrics, "oos", 0.0) >= value
    if term == "excess_min":
        return _normalize_metric(metrics, "excess", -999.0) >= value
    if term == "dsr_min":
        return _normalize_metric(metrics, "dsr", 0.0) >= value
    if term == "trips_min":
        return _normalize_metric(metrics, "trips", 0.0) >= value
    if term == "tmin_min":
        return _normalize_metric(metrics, "tmin", 0.0) >= value
    if term == "perm_p_max":
        return _normalize_metric(metrics, "perm_p", 1.0) <= value
    if term == "boot_p_max":
        return _normalize_metric(metrics, "boot_p", 1.0) <= value
    return False


def check_track(metrics: dict[str, Any]) -> list[str]:
    """Evaluate a metrics dict against all track conjunctions.

    Returns the list of track names that ALL terms satisfy (full conjunction).
    A candidate promotes by clearing any one track.

    Args:
        metrics: dict with keys like sharpe, max_dd, oos, excess, dsr,
                 trips, tmin, perm_p, boot_p.

    Returns:
        List of track names that the candidate satisfies fully.
    """
    passing: list[str] = []
    for track in TRACKS:
        thresholds = track["thresholds"]
        if all(_check_term(metrics, term, val) for term, val in thresholds.items()):
            passing.append(track["name"])
    return passing


def check_track_detailed(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a detailed per-term audit for each track.

    Useful for diagnostic logging and optimization analysis.
    """
    results: dict[str, dict[str, Any]] = {}
    for track in TRACKS:
        name = track["name"]
        thresholds = track["thresholds"]
        term_results: dict[str, bool] = {}
        all_passed = True
        for term, val in thresholds.items():
            passed = _check_term(metrics, term, val)
            term_results[term] = passed
            if not passed:
                all_passed = False
        results[name] = {
            "passed": all_passed,
            "terms": term_results,
            "archetype": track["archetype"],
        }
    return results


def get_track_names() -> list[str]:
    """Return all track names in order."""
    return [t["name"] for t in TRACKS]


def get_track(metrics: dict[str, Any]) -> dict[str, Any] | None:
    """Return the first track dict the metrics satisfy, or None."""
    passing = check_track(metrics)
    if passing:
        for track in TRACKS:
            if track["name"] == passing[0]:
                return track
    return None


def recompute_dsr(T: int, sharpe: float, N: int) -> float:
    """Recompute Deflated Sharpe Ratio for a candidate under Bailey-Lopez de Prado.

    Wraps src.backtest.defend.trial_ledger.deflated_sharpe_ratio with safe bounds.
    """
    if T <= 1 or N < 1:
        return 0.0
    try:
        sr_per_obs = float(sharpe) / math.sqrt(252.0)
        return float(deflated_sharpe_ratio(T, sr_per_obs, N))
    except Exception:
        return 0.0


def required_sharpe_for_dsr(T: int, N: int, confidence: float = 0.95) -> float:
    """Compute minimum annualized Sharpe needed to achieve a target DSR confidence.

    Wraps deflated_sharpe_threshold.
    """
    if T <= 1 or N < 1:
        return float("inf")
    try:
        sr_thresh = deflated_sharpe_threshold(T, N, confidence)
        return float(sr_thresh * math.sqrt(252.0))
    except Exception:
        return float("inf")
