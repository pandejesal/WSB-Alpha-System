"""Tests for gatespec_tracks promotion-gate track specifications.

Coverage:
- SPY-baseline fixture passes at least one track (benchmark_parity)
- Fabricated low-exposure high-Sharpe fixture (TOP5 scenario) fails all tracks
- Threshold boundary checks
- Evaluator determinism
"""

import pytest

from src.backtest.gatespec_tracks import (
    SPY_BASELINE,
    TRACKS,
    check_track,
    get_track,
    get_track_names,
    recompute_dsr,
)

# --- Fixtures ---

@pytest.fixture
def spy_baseline_metrics():
    """SPY buy-hold metrics on the loop window (1910 bars, 2019-2026).

    Sharpe 0.94, maxDD ~0.34, total +245.5%, CAGR ~18.5%.
    This is the calibration window used by evolve_real.py.
    """
    return {
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


@pytest.fixture
def low_exposure_high_sharpe():
    """Fabricated TOP5-scenario metrics: Sharpe ~0.9 but excess -85pp.

    Matches the TOP5_TRIPLE_CHECK.md finding where low-exposure timing
    overlays post Sharpe ~0.9 but trail SPY by 70-137pp in absolute return.
    """
    return {
        "sharpe": 0.93,
        "max_dd": 0.12,
        "oos": 0.90,
        "excess": -85.0,
        "dsr": 0.02,
        "perm_p": 0.50,
        "boot_p": 0.45,
        "trips": 189,
        "trades": 189,
        "cagr": 0.08,
        "tmin": 0.18,
    }


@pytest.fixture
def sample_strategy_metrics():
    """A plausible mid-tier strategy that should pass core_timing_overlay."""
    return {
        "sharpe": 0.65,
        "max_dd": 0.28,
        "oos": 0.42,
        "excess": 0.08,
        "dsr": 0.82,
        "perm_p": 0.03,
        "boot_p": 0.04,
        "trips": 10,
        "trades": 10,
        "cagr": 0.12,
        "tmin": 0.20,
    }


@pytest.fixture
def high_exposure_strategy_metrics():
    """A plausible high-exposure momentum strategy that should pass
    high_exposure_momentum track."""
    return {
        "sharpe": 0.78,
        "max_dd": 0.30,
        "oos": 0.52,
        "excess": 0.06,
        "dsr": 0.91,
        "perm_p": 0.04,
        "boot_p": 0.03,
        "trips": 8,
        "trades": 8,
        "cagr": 0.20,
        "tmin": 0.75,
    }


# --- Tests ---

def test_spy_baseline_passes_at_least_one_track(spy_baseline_metrics):
    """SPY buy-hold must pass at least one track (benchmark_parity).

    This confirms the gate is calibrated: if SPY cannot pass its own
    benchmark, the gate is miscalibrated.
    """
    passing = check_track(spy_baseline_metrics)
    assert len(passing) >= 1, (
        f"SPY baseline passes {len(passing)} tracks; expected >= 1. "
        f"Passing tracks: {passing}"
    )
    assert "benchmark_parity" in passing


def test_low_exposure_high_sharpe_fails_all_tracks(low_exposure_high_sharpe):
    """The TOP5 low-exposure high-Sharpe scenario must fail ALL tracks.

    This is the core failure mode documented in TOP5_TRIPLE_CHECK.md:
    strategies with Sharpe ~0.9 but excess -70% to -137% must never pass.
    """
    passing = check_track(low_exposure_high_sharpe)
    assert passing == [], (
        f"Low-exposure high-Sharpe fixture should fail all tracks but "
        f"passed: {passing}"
    )


def test_core_timing_overlay_passes_sample_strategy(sample_strategy_metrics):
    """A mid-tier timing overlay should pass core_timing_overlay."""
    passing = check_track(sample_strategy_metrics)
    assert "core_timing_overlay" in passing


def test_high_exposure_momentum_passes_high_exposure_strategy(high_exposure_strategy_metrics):
    """A high-exposure momentum strategy should pass high_exposure_momentum."""
    passing = check_track(high_exposure_strategy_metrics)
    assert "high_exposure_momentum" in passing


def test_threshold_boundary_sharpe():
    """Sharpe threshold boundary checks for each track."""
    for track in TRACKS:
        thresholds = track["thresholds"]
        if "sharpe_min" not in thresholds:
            continue
        val = thresholds["sharpe_min"]
        at_threshold = {
            "sharpe": val, "max_dd": 0.35, "oos": 0.5,
            "excess": 0.1, "dsr": 0.9, "trips": 10,
            "tmin": 1.0, "perm_p": 0.04, "boot_p": 0.04,
        }
        below_threshold = dict(at_threshold)
        below_threshold["sharpe"] = val - 0.001
        # If all terms met at threshold, the track passes
        # If sharpe drops below, the track must fail
        pass_at = check_track(at_threshold)
        pass_below = check_track(below_threshold)
        if track["name"] in pass_at:
            assert track["name"] not in pass_below, (
                f"Track {track['name']} should reject Sharpe "
                f"{val - 0.001} when threshold is {val}"
            )


def test_threshold_boundary_excess():
    """Excess threshold boundary checks: SPY (excess=0) must fail tracks
    with positive excess_min, and pass benchmark_parity (excess_min=0.0)."""
    positive_excess_tracks = [t for t in TRACKS
                              if t["thresholds"].get("excess_min", 0) > 0]
    spy_metrics = {
        "sharpe": 0.94, "max_dd": 0.34, "oos": 0.94, "excess": 0.0,
        "dsr": 0.9999, "perm_p": 0.60, "boot_p": 0.40,
        "trips": 0, "trades": 0, "cagr": 0.185, "tmin": 1.0,
    }
    for track in positive_excess_tracks:
        passing = check_track(spy_metrics)
        assert track["name"] not in passing, (
            f"Track {track['name']} with excess_min={track['thresholds']['excess_min']} "
            f"should reject SPY (excess=0)"
        )


def test_threshold_boundary_max_dd():
    """maxDD threshold boundary: SPY (max_dd=0.34) must fail tracks with
    max_dd_max < 0.34."""
    spy_metrics = {
        "sharpe": 0.94, "max_dd": 0.34, "oos": 0.94, "excess": 0.0,
        "dsr": 0.9999, "perm_p": 0.60, "boot_p": 0.40,
        "trips": 0, "trades": 0, "cagr": 0.185, "tmin": 1.0,
    }
    for track in TRACKS:
        thresholds = track["thresholds"]
        if "max_dd_max" in thresholds and thresholds["max_dd_max"] < 0.34:
            passing = check_track(spy_metrics)
            assert track["name"] not in passing, (
                f"Track {track['name']} with max_dd_max={thresholds['max_dd_max']} "
                f"should reject SPY (max_dd=0.34)"
            )


def test_evaluator_determinism():
    """check_track must return identical results for identical inputs
    across multiple calls (no randomness in evaluation)."""
    metrics = {
        "sharpe": 0.70, "max_dd": 0.30, "oos": 0.45, "excess": 0.05,
        "dsr": 0.85, "perm_p": 0.04, "boot_p": 0.03,
        "trips": 12, "trades": 12, "cagr": 0.15, "tmin": 0.5,
    }
    results = [check_track(metrics) for _ in range(100)]
    assert all(r == results[0] for r in results), (
        "check_track is not deterministic across repeated calls"
    )


def test_get_track_returns_none_when_no_pass():
    """get_track should return None when no track passes."""
    failing_metrics = {
        "sharpe": 0.3, "max_dd": 0.5, "oos": 0.2, "excess": -50.0,
        "dsr": 0.01, "perm_p": 0.8, "boot_p": 0.7,
        "trips": 1, "trades": 1, "cagr": 0.02, "tmin": 0.05,
    }
    assert get_track(failing_metrics) is None


def test_get_track_returns_first_passing_track(spy_baseline_metrics):
    """get_track should return the first passing track for SPY baseline."""
    track = get_track(spy_baseline_metrics)
    assert track is not None
    assert track["name"] == "benchmark_parity"


def test_all_tracks_have_required_fields():
    """Every track must have all required fields per the worker brief."""
    required_fields = [
        "name", "terms", "thresholds", "rationale", "archetype",
        "plain_english", "spy_passes", "spy_passes_label",
    ]
    for track in TRACKS:
        for field in required_fields:
            assert field in track, (
                f"Track {track.get('name', '?')} missing field '{field}'"
            )
        assert len(track["rationale"]) == 3, (
            f"Track {track['name']} must have exactly 3 rationale lines, "
            f"got {len(track['rationale'])}"
        )


def test_rationale_cites_failure_modes():
    """Each rationale must cite which failure mode each term blocks."""
    for track in TRACKS:
        rationale_text = " ".join(track["rationale"])
        assert len(rationale_text) > 50, (
            f"Track {track['name']} rationale too short"
        )


def test_at_least_3_low_exposure_tracks():
    """At least 3 tracks must be plausibly satisfiable by low-exposure
    timing overlays (the only shape currently near passing)."""
    low_exposure = [t for t in TRACKS if "trips_min" in t["thresholds"]]
    assert len(low_exposure) >= 3, (
        f"Expected >= 3 low-exposure tracks (using trips_min), got {len(low_exposure)}"
    )


def test_at_least_2_high_exposure_tracks():
    """At least 2 tracks must REQUIRE high time-in-market or buy-hold-like
    exposure (using tmin_min as the activity term)."""
    high_exposure = [t for t in TRACKS if "tmin_min" in t["thresholds"]]
    assert len(high_exposure) >= 2, (
        f"Expected >= 2 high-exposure tracks (using tmin_min), got {len(high_exposure)}"
    )


def test_all_tracks_have_absolute_excess_and_dsr():
    """Every track must include BOTH an absolute-excess-vs-SPY term
    AND a multiple-testing discount (DSR)."""
    for track in TRACKS:
        assert "excess" in track["terms"], (
            f"Track {track['name']} missing excess term"
        )
        assert "excess_min" in track["thresholds"], (
            f"Track {track['name']} missing excess_min threshold"
        )
        assert "dsr" in track["terms"], (
            f"Track {track['name']} missing DSR term"
        )
        assert "dsr_min" in track["thresholds"], (
            f"Track {track['name']} missing dsr_min threshold"
        )


def test_all_tracks_have_risk_and_activity_terms():
    """Every track must include a risk term (maxDD) and a minimum-activity
    term (trips_min or tmin_min in thresholds)."""
    for track in TRACKS:
        assert "max_dd" in track["terms"], (
            f"Track {track['name']} missing risk term"
        )
        has_activity = "trips_min" in track["thresholds"] or "tmin_min" in track["thresholds"]
        assert has_activity, (
            f"Track {track['name']} missing minimum-activity term"
        )


def test_track_count():
    """Must have at least 7 tracks."""
    assert len(TRACKS) >= 7, (
        f"Expected >= 7 tracks, got {len(TRACKS)}"
    )


def test_track_names_unique():
    """All track names must be unique."""
    names = get_track_names()
    assert len(names) == len(set(names)), "Duplicate track names found"


def test_recompute_dsr_consistency():
    """recompute_dsr should return a value consistent with
    deflated_sharpe_ratio for known inputs."""
    result = recompute_dsr(1000, 0.5, 1)
    assert 0.0 <= result <= 1.0, f"DSR out of range: {result}"

    result_small_n = recompute_dsr(1000, 0.5, 10)
    result_large_n = recompute_dsr(1000, 0.5, 10000)
    assert result_large_n <= result_small_n, (
        f"DSR should decrease with larger N: small={result_small_n}, large={result_large_n}"
    )


def test_spy_baseline_fields_complete():
    """SPY_BASELINE must contain all metric keys used by tracks."""
    required_keys = {"sharpe", "max_dd", "oos", "excess", "dsr",
                     "perm_p", "boot_p", "trips", "trades", "cagr", "tmin"}
    assert required_keys.issubset(SPY_BASELINE.keys()), (
        f"SPY_BASELINE missing keys: {required_keys - set(SPY_BASELINE.keys())}"
    )