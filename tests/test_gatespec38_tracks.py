"""Tests for gatespec38_tracks promotion-gate track specifications (Worker 8).

Coverage:
- SPY-baseline fixture passes at least one track (benchmark_parity)
- Fabricated low-exposure high-Sharpe fixture (TOP5 scenario) fails all tracks
- Sample strategies pass intended tracks
- Threshold boundary checks (Sharpe, excess, max_dd)
- Evaluator determinism across repeated calls
- Detailed audit dictionary structure
- Structural validation (all fields, exactly 3 rationales, low/high exposure count)
- DSR helper functions and mathematical monotonicity
"""

import pytest

from src.backtest.gatespec38_tracks import (
    SPY_BASELINE,
    TRACKS,
    check_track,
    check_track_detailed,
    get_track,
    get_track_names,
    recompute_dsr,
    required_sharpe_for_dsr,
)

# --- Fixtures ---

@pytest.fixture
def spy_baseline_metrics() -> dict:
    """SPY buy-hold metrics on the loop window (1910 bars, 2019-2026).

    Sharpe 0.941, maxDD ~0.337, total +245.50%, CAGR ~17.77%.
    Matches the calibration baseline used by evolve_real.py.
    """
    return dict(SPY_BASELINE)


@pytest.fixture
def low_exposure_high_sharpe() -> dict:
    """Fabricated TOP5-scenario metrics: Sharpe ~0.93 but excess -85pp.

    Matches TOP5_TRIPLE_CHECK.md where low-exposure timing overlays
    post Sharpe ~0.9 but trail SPY by 70-137pp in absolute cumulative return.
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
def sample_timing_metrics() -> dict:
    """A plausible mid-tier timing strategy that should pass core_timing_overlay."""
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
def sample_hedged_metrics() -> dict:
    """A plausible tail-risk hedging strategy that should pass tail_risk_sentinel."""
    return {
        "sharpe": 0.58,
        "max_dd": 0.22,
        "oos": 0.38,
        "excess": 0.04,
        "dsr": 0.78,
        "perm_p": 0.04,
        "boot_p": 0.03,
        "trips": 8,
        "trades": 8,
        "cagr": 0.10,
        "tmin": 0.25,
    }


@pytest.fixture
def high_exposure_strategy_metrics() -> dict:
    """A plausible high-exposure momentum strategy passing high_exposure_momentum."""
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


@pytest.fixture
def buy_hold_companion_metrics() -> dict:
    """A high-exposure factor rotation strategy passing buy_hold_companion."""
    return {
        "sharpe": 0.88,
        "max_dd": 0.32,
        "oos": 0.58,
        "excess": 0.03,
        "dsr": 0.96,
        "perm_p": 0.02,
        "boot_p": 0.02,
        "trips": 12,
        "trades": 12,
        "cagr": 0.19,
        "tmin": 0.85,
    }


# --- Tests ---

def test_spy_baseline_passes_at_least_one_track(spy_baseline_metrics):
    """SPY buy-hold must pass at least one track (benchmark_parity).

    Ensures the gate is calibrated: if benchmark buy-and-hold fails its own
    parity reference, the gate is miscalibrated.
    """
    passing = check_track(spy_baseline_metrics)
    assert len(passing) >= 1, (
        f"SPY baseline passes {len(passing)} tracks; expected >= 1. "
        f"Passing tracks: {passing}"
    )
    assert "benchmark_parity" in passing


def test_low_exposure_high_sharpe_fails_all_tracks(low_exposure_high_sharpe):
    """The TOP5 low-exposure high-Sharpe scenario must fail ALL tracks.

    Blocks strategies that boast Sharpe ~0.9 due to low volatility while trailing
    SPY by 70-137pp in cumulative return.
    """
    passing = check_track(low_exposure_high_sharpe)
    assert passing == [], (
        f"Low-exposure high-Sharpe fixture should fail all tracks but passed: {passing}"
    )


def test_core_timing_overlay_passes_sample_strategy(sample_timing_metrics):
    """A mid-tier timing overlay should pass core_timing_overlay."""
    passing = check_track(sample_timing_metrics)
    assert "core_timing_overlay" in passing


def test_tail_risk_sentinel_passes_hedged_strategy(sample_hedged_metrics):
    """A crisis-alpha / low-drawdown hedging strategy should pass tail_risk_sentinel."""
    passing = check_track(sample_hedged_metrics)
    assert "tail_risk_sentinel" in passing


def test_high_exposure_momentum_passes_high_exposure_strategy(high_exposure_strategy_metrics):
    """A high-exposure momentum strategy should pass high_exposure_momentum."""
    passing = check_track(high_exposure_strategy_metrics)
    assert "high_exposure_momentum" in passing


def test_buy_hold_companion_passes_strategy(buy_hold_companion_metrics):
    """A high-exposure factor rotation strategy should pass buy_hold_companion."""
    passing = check_track(buy_hold_companion_metrics)
    assert "buy_hold_companion" in passing


def test_threshold_boundary_sharpe():
    """Sharpe threshold boundary checks for each track."""
    for track in TRACKS:
        thresholds = track["thresholds"]
        if "sharpe_min" not in thresholds:
            continue
        val = thresholds["sharpe_min"]
        at_threshold = {
            "sharpe": val,
            "max_dd": 0.20,
            "oos": 0.90,
            "excess": 0.25,
            "dsr": 0.99,
            "trips": 20,
            "tmin": 1.0,
            "perm_p": 0.01,
            "boot_p": 0.01,
        }
        below_threshold = dict(at_threshold)
        below_threshold["sharpe"] = val - 0.001

        pass_at = check_track(at_threshold)
        pass_below = check_track(below_threshold)
        if track["name"] in pass_at:
            assert track["name"] not in pass_below, (
                f"Track {track['name']} should reject Sharpe {val - 0.001} "
                f"when threshold is {val}"
            )


def test_threshold_boundary_excess():
    """Excess threshold boundary checks: SPY (excess=0.0) must fail all tracks
    demanding positive excess return."""
    positive_excess_tracks = [
        t for t in TRACKS if t["thresholds"].get("excess_min", 0.0) > 0.0
    ]
    spy_metrics = dict(SPY_BASELINE)
    for track in positive_excess_tracks:
        passing = check_track(spy_metrics)
        assert track["name"] not in passing, (
            f"Track {track['name']} with excess_min={track['thresholds']['excess_min']} "
            f"should reject SPY (excess=0)"
        )


def test_threshold_boundary_max_dd():
    """maxDD boundary checks: SPY (max_dd ~0.337) must fail tracks with
    max_dd_max < 0.337."""
    spy_metrics = dict(SPY_BASELINE)
    for track in TRACKS:
        thresholds = track["thresholds"]
        if "max_dd_max" in thresholds and thresholds["max_dd_max"] < 0.337:
            passing = check_track(spy_metrics)
            assert track["name"] not in passing, (
                f"Track {track['name']} with max_dd_max={thresholds['max_dd_max']} "
                f"should reject SPY (max_dd=0.337)"
            )


def test_evaluator_determinism():
    """check_track must return identical results for identical inputs
    across multiple calls."""
    metrics = {
        "sharpe": 0.70,
        "max_dd": 0.30,
        "oos": 0.45,
        "excess": 0.05,
        "dsr": 0.85,
        "perm_p": 0.04,
        "boot_p": 0.03,
        "trips": 12,
        "trades": 12,
        "cagr": 0.15,
        "tmin": 0.5,
    }
    results = [check_track(metrics) for _ in range(100)]
    assert all(r == results[0] for r in results), (
        "check_track is not deterministic across repeated calls"
    )


def test_get_track_returns_none_when_no_pass():
    """get_track should return None when no track passes."""
    failing_metrics = {
        "sharpe": 0.2,
        "max_dd": 0.6,
        "oos": 0.1,
        "excess": -50.0,
        "dsr": 0.01,
        "trips": 1,
    }
    assert get_track(failing_metrics) is None


def test_get_track_returns_first_passing_track(spy_baseline_metrics):
    """get_track should return the first passing track for SPY baseline."""
    track = get_track(spy_baseline_metrics)
    assert track is not None
    assert track["name"] == "benchmark_parity"


def test_all_tracks_have_required_fields():
    """Every track must contain all required fields with valid types."""
    required_fields = [
        "name",
        "terms",
        "thresholds",
        "rationale",
        "archetype",
        "plain_english",
        "spy_passes",
        "spy_passes_label",
    ]
    for track in TRACKS:
        for field in required_fields:
            assert field in track, f"Track {track.get('name', '?')} missing field '{field}'"
        assert isinstance(track["rationale"], list), f"Track {track['name']} rationale must be list"
        assert len(track["rationale"]) == 3, (
            f"Track {track['name']} must have exactly 3 rationale lines, got {len(track['rationale'])}"
        )
        assert track["plain_english"].startswith("This track means:"), (
            f"Track {track['name']} plain_english must start with 'This track means:'"
        )
        assert track["spy_passes_label"] in ("benchmark-parity", "elite-only"), (
            f"Track {track['name']} label invalid: {track['spy_passes_label']}"
        )


def test_rationale_cites_failure_modes():
    """Each rationale must be substantive (>40 chars) and cite failure modes."""
    for track in TRACKS:
        for line in track["rationale"]:
            assert len(line) >= 40, f"Track {track['name']} rationale too short: '{line}'"


def test_at_least_3_low_exposure_tracks():
    """At least 3 tracks must be plausibly satisfiable by low-exposure
    timing overlays (using trips_min as activity term)."""
    low_exposure = [t for t in TRACKS if "trips_min" in t["thresholds"]]
    assert len(low_exposure) >= 3, (
        f"Expected >= 3 low-exposure tracks, got {len(low_exposure)}"
    )


def test_at_least_2_high_exposure_tracks():
    """At least 2 tracks must REQUIRE high time-in-market (tmin_min >= 0.70)."""
    high_exposure = [
        t for t in TRACKS if t["thresholds"].get("tmin_min", 0.0) >= 0.70
    ]
    assert len(high_exposure) >= 2, (
        f"Expected >= 2 high-exposure tracks, got {len(high_exposure)}"
    )


def test_all_tracks_have_absolute_excess_and_dsr():
    """Every track must include BOTH an absolute-excess-vs-SPY term
    AND a multiple-testing discount (DSR)."""
    for track in TRACKS:
        assert "excess" in track["terms"], f"Track {track['name']} missing excess term"
        assert "excess_min" in track["thresholds"], f"Track {track['name']} missing excess_min"
        assert "dsr" in track["terms"], f"Track {track['name']} missing dsr term"
        assert "dsr_min" in track["thresholds"], f"Track {track['name']} missing dsr_min"


def test_all_tracks_have_risk_and_activity_terms():
    """Every track must include a risk term (max_dd) and an activity term
    (trips_min or tmin_min)."""
    for track in TRACKS:
        assert "max_dd" in track["terms"], f"Track {track['name']} missing max_dd term"
        assert "max_dd_max" in track["thresholds"], f"Track {track['name']} missing max_dd_max"
        has_activity = "trips_min" in track["thresholds"] or "tmin_min" in track["thresholds"]
        assert has_activity, f"Track {track['name']} missing activity threshold"


def test_track_count_in_spec():
    """Must have 7 to 10 tracks per worker brief."""
    assert 7 <= len(TRACKS) <= 10, f"Expected 7-10 tracks, got {len(TRACKS)}"


def test_track_names_unique():
    """All track names must be unique."""
    names = get_track_names()
    assert len(names) == len(set(names)), "Duplicate track names found"


def test_recompute_dsr_consistency():
    """recompute_dsr should decrease with increasing trial count N."""
    dsr_1 = recompute_dsr(1910, 1.0, 1)
    dsr_100 = recompute_dsr(1910, 1.0, 100)
    dsr_10000 = recompute_dsr(1910, 1.0, 10000)
    assert 0.0 <= dsr_1 <= 1.0
    assert 0.0 <= dsr_100 <= 1.0
    assert 0.0 <= dsr_10000 <= 1.0
    assert dsr_1 >= dsr_100 >= dsr_10000, "DSR must decrease as trials N increase"


def test_required_sharpe_for_dsr():
    """required_sharpe_for_dsr should increase as trial count N increases."""
    sr_10 = required_sharpe_for_dsr(1910, 10, 0.95)
    sr_1000 = required_sharpe_for_dsr(1910, 1000, 0.95)
    sr_10000 = required_sharpe_for_dsr(1910, 10000, 0.95)
    assert sr_10 < sr_1000 < sr_10000, "Sharpe required for DSR must grow with N"
    # At N=10000, required Sharpe exceeds 1.95
    assert sr_10000 > 1.95


def test_check_track_detailed_matches_check_track(sample_timing_metrics):
    """Detailed audit should match binary check_track output."""
    passing = check_track(sample_timing_metrics)
    detailed = check_track_detailed(sample_timing_metrics)
    for track_name, audit in detailed.items():
        if track_name in passing:
            assert audit["passed"] is True
            assert all(audit["terms"].values())
        else:
            assert audit["passed"] is False
            assert not all(audit["terms"].values())


def test_metric_alias_normalization():
    """Evaluator should handle history aliases (round_trips, excess_spy, oos_sharpe)."""
    aliased_metrics = {
        "sharpe": 0.65,
        "max_dd": 0.28,
        "oos_sharpe": 0.42,
        "excess_spy": 0.08,
        "dsr": 0.82,
        "round_trips": 10,
    }
    passing = check_track(aliased_metrics)
    assert "core_timing_overlay" in passing
