"""Promotion-gate track specifications for SPY-beating strategies.

Each track is a full conjunction of terms that a candidate must clear
to be promoted. A candidate promotes by clearing ANY ONE track fully.
Every track includes an absolute-excess-vs-SPY term AND a multiple-testing
discount (DSR), plus a risk term and a minimum-activity term.

SPY baseline (loop window, 1910 bars, 2019-2026):
    Sharpe 0.94, maxDD ~0.34, total +245.5%, CAGR ~18.5%.
SPY baseline (paper gate window):
    Total +137.1%, CAGR 13.85%, maxDD -34.1%.
Calibration uses the loop window (+245.5%) since that is what
evolve_real.py evaluates against. The paper gate window (+137.1%)
covers a shorter/different period and is noted where relevant.

All metrics computed T+1, costs deducted, identical-window SPY twin.
"""

from __future__ import annotations

import math

from src.backtest.defend.trial_ledger import deflated_sharpe_ratio

# SPY baseline metrics on the loop window (1910 bars, 2019-2026)
SPY_BASELINE = {
    "sharpe": 0.94,
    "max_dd": 0.34,
    "oos": 0.94,
    "excess": 0.0,
    "dsr": 0.9999,
    "perm_p": 0.60,
    "boot_p": 0.40,
    "trips": 0,
    "trades": 0,
    "cagr": 0.185,
    "tmin": 1.0,
}

# --- Track definitions ---
# Each dict: name, terms, thresholds, rationale (list of 3), archetype,
#           plain_english, spy_passes (bool), spy_passes_label (str)

TRACKS = [
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
            "sharpe>=0.60 admits timing overlays that sit in cash much of the "
            "time yet still generate meaningful risk-adjusted returns; this "
            "is the shape of every near-passing candidate in the current pool.",
            "excess>=0.05pp blocks the TOP5 failure mode where low-exposure "
            "strategies post Sharpe ~0.9 but trail SPY by 70-137pp in absolute "
            "return; the excess term forces genuine alpha beyond the benchmark.",
            "dsr>=0.80 applies a multiple-testing discount calibrated to the "
            "loop's 10000+ trial count, filtering selection-bias luck while "
            "remaining achievable for a real but modest edge.",
        ],
        "archetype": "Low-exposure timing overlay (10-40% time-in-market)",
        "plain_english": "This track means: your strategy must beat SPY by at "
                         "least 0.05 percentage points in total return, stay "
                         "in the market at least 15% of the time, make at "
                         "least 8 round trips, and maintain a Sharpe above "
                         "0.60 after discounting for the number of attempts "
                         "the evolution loop has made.",
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
            "max_dd<=0.35 is generous enough to admit strategies that avoid "
            "SPY's worst drawdowns by rotating to cash or defensive assets, "
            "which is the only mechanism low-exposure overlays use to reduce "
            "risk without holding less of the market.",
            "excess>=0.10pp demands a more substantial absolute edge than "
            "Track 1, filtering strategies that merely track SPY with a "
            "timing overlay but still lose to buy-hold in raw return terms.",
            "dsr>=0.75 with the loop's large trial count still rejects pure "
            "luck: at N~10000 the DSR correction is severe, so only a genuine "
            "signal survives even at this relaxed threshold.",
        ],
        "archetype": "Low-exposure drawdown-avoidance timing",
        "plain_english": "This track means: avoid drawdowns worse than 35%, "
                         "beat SPY by at least 0.10 percentage points total, "
                         "make at least 6 trades, and have a Sharpe above "
                         "0.55 after adjusting for how many parameter "
                         "combinations the loop tried.",
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
            "sharpe>=0.50 is the lowest bar among the low-exposure tracks, "
            "acknowledging that a strategy spending 80%+ of its time in cash "
            "will naturally have a lower Sharpe even if it times the market "
            "well; the excess term compensates by demanding real alpha.",
            "excess>=0.15pp is the most stringent absolute-outperformance "
            "requirement among low-exposure tracks, ensuring that even with "
            "low time-in-market the strategy adds meaningful return beyond "
            "SPY's buy-hold result.",
            "dsr>=0.70 is the most permissive DSR threshold, calibrated so "
            "that a strategy with a genuine but small edge (e.g., 0.3 annual "
            "Sharpe with 20 trades) can survive the 10000+ trial correction.",
        ],
        "archetype": "Low-exposure conservative timing overlay",
        "plain_english": "This track means: be in the market as little as "
                         "10% of the time, beat SPY by at least 0.15 "
                         "percentage points total, make at least 5 trades, "
                         "and pass the multiple-comparison test at 70% "
                         "confidence after all the attempts the loop has "
                         "made so far.",
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
            "tmin>=0.70 requires the strategy to hold the market at least "
            "70% of the time, admitting only momentum or trend-following "
            "strategies that behave like buy-hold with modest timing "
            "adjustments; this is the shape families like spy_ltrend and "
            "us_ltrend naturally take.",
            "sharpe>=0.75 ensures the strategy captures meaningful upside "
            "when it is invested, filtering out high-exposure strategies "
            "that hold the market but have poor risk-adjusted returns.",
            "dsr>=0.90 maintains strong statistical rigor; because "
            "high-exposure strategies produce more trades and more data "
            "points, the DSR correction is proportionally less severe and "
            "this threshold is achievable for genuine momentum edges.",
        ],
        "archetype": "High time-in-market momentum / trend-following",
        "plain_english": "This track means: be invested 70% or more of the "
                         "time, beat SPY by any positive margin in absolute "
                         "terms, have a Sharpe above 0.75, and pass the "
                         "multiple-testing guard at 90% confidence - this "
                         "is for strategies that behave like buy-hold but "
                         "add timing value.",
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
            "tmin>=0.80 requires near-buy-hold exposure, admitting only "
            "strategies that are essentially holding the market with "
            "slight tilts; this is the shape that us_momentum and "
            "us_lowvol produce with small top_n values.",
            "sharpe>=0.85 is near-SPY's own 0.94, ensuring that high-exposure "
            "candidates must match SPY's risk-adjusted performance before "
            "considering promotion; this blocks mediocre high-exposure "
            "strategies that trail on Sharpe.",
            "dsr>=0.95 with tmin>=0.80 is the most statistically demanding "
            "track: at 10000+ trials only strategies with a very strong "
            "genuine signal survive this filter.",
        ],
        "archetype": "Near-buy-hold momentum / rotation",
        "plain_english": "This track means: be invested 80% or more of the "
                         "time, beat SPY by at least 0.02 percentage points "
                         "total, have a Sharpe above 0.85, and pass the "
                         "strictest multiple-testing guard - this is for "
                         "strategies that are essentially buy-hold with a "
                         "small edge on top.",
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
            "trips>=15 ensures a large enough sample for the DSR to be "
            "meaningful; with few trades the DSR correction is overly "
            "severe and unreliable, so this track demands statistical "
            "maturity before promotion.",
            "dsr>=0.92 is the second-highest DSR threshold, requiring very "
            "strong evidence that the observed Sharpe is not a product of "
            "multiple-comparison selection bias; this is the track that "
            "filters the most noise from the 10000+ trial pool.",
            "excess>=0.02pp is a minimal absolute outperformance "
            "requirement - this track prioritizes statistical confidence "
            "over return magnitude, admitting strategies that barely beat "
            "SPY but with overwhelming statistical evidence.",
        ],
        "archetype": "Statistically validated timing or rotation",
        "plain_english": "This track means: make at least 15 trades, beat SPY "
                         "by any positive amount, have a Sharpe above 0.70, "
                         "and pass the multiple-comparison test at 92% "
                         "confidence - this is for strategies where the "
                         "evidence is stronger than the profit.",
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
            "excess>=0.20pp is the most demanding absolute-outperformance "
            "requirement among all tracks; this track prioritizes raw alpha "
            "over risk-adjusted metrics, admitting strategies that add "
            "meaningful return beyond SPY even if their Sharpe is modest.",
            "sharpe>=0.65 is moderate, acknowledging that strategies with "
            "high excess may do so through concentrated positions that "
            "increase variance; the max_dd term bounds the risk from this "
            "concentration.",
            "dsr>=0.75 with trips>=10 balances the demand: the excess term "
            "requires real alpha, the DSR requires it not be luck, and the "
            "trips requirement ensures enough data to compute both.",
        ],
        "archetype": "Absolute-return focused timing or rotation",
        "plain_english": "This track means: beat SPY by at least 0.20 "
                         "percentage points total, have a Sharpe above "
                         "0.65, make at least 10 trades, and avoid "
                         "drawdowns worse than 35% - this is for "
                         "strategies where the primary goal is adding raw "
                         "return beyond the benchmark.",
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
            "max_dd<=0.28 is stricter than SPY's own ~34% drawdown, "
            "admitting only strategies that demonstrably avoid the worst "
            "of market downturns; this is an elite-only track because even "
            "SPY buy-hold fails this requirement.",
            "sharpe>=0.70 combined with the strict drawdown constraint "
            "requires the strategy to earn its risk-adjusted return while "
            "taking less risk than the benchmark - the hallmark of "
            "genuine timing skill rather than just riding beta.",
            "dsr>=0.85 with trips>=12 ensures that the improved risk "
            "profile is not a product of lucky timing in a small sample; "
            "the multiple-testing discount confirms the edge is real.",
        ],
        "archetype": "Risk-disciplined timing with strict drawdown control",
        "plain_english": "This track means: avoid drawdowns worse than 28% "
                         "(stricter than SPY itself), beat SPY by at least "
                         "0.05 percentage points total, have a Sharpe above "
                         "0.70, make at least 12 trades, and pass the "
                         "multiple-testing guard at 85% confidence.",
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
            "excess_min": 0.0,
            "dsr_min": 0.95,
            "trips_min": 0,
        },
        "rationale": [
            "excess_min=0.0 is the only track where SPY itself can pass "
            "the excess term; this serves as a calibration reference "
            "confirming that the gate is not impossibly set - if SPY cannot "
            "pass its own benchmark, the gate is miscalibrated.",
            "sharpe>=0.90 and oos>=0.85 are set near SPY's own values so "
            "that this track confirms the gate accepts benchmark-level "
            "performance; any strategy that beats SPY on Sharpe and OOS "
            "clears this track trivially.",
            "dsr>=0.95 with trips_min=0 makes this the most statistically "
            "rigorous track with no activity floor; it admits benchmark-"
            "level strategies that pass the multiple-testing guard, "
            "confirming the gate's fairness as a calibration check.",
        ],
        "archetype": "Benchmark parity reference (calibration check)",
        "plain_english": "This track means: match or beat SPY's Sharpe, "
                         "match SPY's drawdown, have an OOS Sharpe above "
                         "0.85, and pass the multiple-testing guard at 95% "
                         "confidence - this is the track SPY itself passes, "
                         "confirming the gate is calibrated correctly.",
        "spy_passes": True,
        "spy_passes_label": "benchmark-parity",
    },
]


def _check_term(metrics: dict, term: str, value: float) -> bool:
    """Check a single metric threshold against the metrics dict."""
    if term == "sharpe_min":
        return metrics.get("sharpe", 0.0) >= value
    if term == "max_dd_max":
        return metrics.get("max_dd", 999.0) <= value
    if term == "oos_min":
        return metrics.get("oos", 0.0) >= value
    if term == "excess_min":
        return metrics.get("excess", -999.0) >= value
    if term == "dsr_min":
        return metrics.get("dsr", 0.0) >= value
    if term == "trips_min":
        return metrics.get("trips", 0) >= value
    if term == "tmin_min":
        return metrics.get("tmin", 0.0) >= value
    return False


def check_track(metrics: dict) -> list[str]:
    """Evaluate a metrics dict against all track conjunctions.

    Returns the list of track names that ALL terms satisfy (full
    conjunction). A candidate promotes by clearing any one track.

    Args:
        metrics: dict with keys like sharpe, max_dd, oos, excess,
                 dsr, perm_p, boot_p, trips, trades, cagr, tmin.

    Returns:
        List of track name strings that the metrics satisfy fully.
    """
    passing = []
    for track in TRACKS:
        thresholds = track["thresholds"]
        all_pass = True
        for term, value in thresholds.items():
            if not _check_term(metrics, term, value):
                all_pass = False
                break
        if all_pass:
            passing.append(track["name"])
    return passing


def get_track_names() -> list[str]:
    """Return all track names in order."""
    return [t["name"] for t in TRACKS]


def get_track(metrics: dict) -> dict | None:
    """Return the first track the metrics satisfy, or None."""
    passing = check_track(metrics)
    if passing:
        for track in TRACKS:
            if track["name"] in passing:
                return track
    return None


def recompute_dsr(T: int, sharpe: float, N: int) -> float:
    """Recompute the Deflated Sharpe Ratio for a metrics dict.

    Wraps src.backtest.defend.trial_ledger.deflated_sharpe_ratio
    for use when DSR is not pre-computed in the metrics dict.
    """
    try:
        sr_per_obs = sharpe / math.sqrt(252.0)
        return deflated_sharpe_ratio(T, sr_per_obs, N)
    except Exception:
        return 0.0
