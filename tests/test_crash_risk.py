"""Regression tests for the compute-only crash-risk signal module.

Covers scoring, classification, the strict evaluation path, the fail-closed
gate, and the no-execution-surface guarantee (numpy + stdlib only).
"""

from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from src.risk.crash_risk import (
    DEFAULT_GATE_THRESHOLD,
    DEFAULT_HIGH_THRESHOLD,
    DEFAULT_IV_SKEW_HIGH,
    DEFAULT_IV_SKEW_LOW,
    DEFAULT_LOW_THRESHOLD,
    DEFAULT_MODERATE_THRESHOLD,
    DEFAULT_PUT_CALL_HIGH,
    DEFAULT_PUT_CALL_LOW,
    DEFAULT_TERM_SLOPE_HIGH,
    DEFAULT_TERM_SLOPE_LOW,
    DEFAULT_WEIGHTS,
    LEVEL_ELEVATED,
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MODERATE,
    LEVEL_NO_SIGNAL,
    CrashRiskVerdict,
    classify_crash_risk,
    compute_iv_skew,
    compute_put_call_skew,
    compute_term_structure_slope,
    crash_risk_gate,
    crash_risk_score,
    evaluate_crash_risk,
    iv_skew_score,
    put_call_skew_score,
    term_slope_score,
)


class TestComputeIndicators:
    def test_iv_skew_scalar(self) -> None:
        assert compute_iv_skew(20.0, 25.0) == pytest.approx(5.0)

    def test_iv_skew_array(self) -> None:
        result = compute_iv_skew([20.0, 30.0], [25.0, 40.0])
        np.testing.assert_allclose(result, [5.0, 10.0])

    def test_put_call_skew_scalar(self) -> None:
        assert compute_put_call_skew(25.0, 20.0) == pytest.approx(1.25)

    def test_put_call_skew_array(self) -> None:
        result = compute_put_call_skew([25.0, 40.0], [20.0, 20.0])
        np.testing.assert_allclose(result, [1.25, 2.0])

    def test_term_slope_scalar(self) -> None:
        assert compute_term_structure_slope(20.0, 18.0) == pytest.approx(-2.0)

    def test_term_slope_array(self) -> None:
        result = compute_term_structure_slope([20.0, 20.0], [18.0, 22.0])
        np.testing.assert_allclose(result, [-2.0, 2.0])

    def test_zero_call_iv_raises(self) -> None:
        with pytest.raises(ValueError, match="strictly positive"):
            compute_put_call_skew(25.0, 0.0)

    def test_negative_iv_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            compute_iv_skew(-1.0, 25.0)

    def test_nan_raises(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            compute_iv_skew(np.nan, 25.0)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            compute_iv_skew([], 25.0)

    def test_bool_raises(self) -> None:
        with pytest.raises(ValueError, match="numeric"):
            compute_iv_skew(True, 25.0)

    def test_incompatible_shapes_raise(self) -> None:
        with pytest.raises(ValueError, match="incompatible"):
            compute_iv_skew([20.0, 21.0], [25.0, 26.0, 27.0])


class TestScoring:
    def test_iv_skew_bounds(self) -> None:
        assert iv_skew_score(DEFAULT_IV_SKEW_LOW) == pytest.approx(0.0)
        assert iv_skew_score(DEFAULT_IV_SKEW_HIGH) == pytest.approx(100.0)
        assert iv_skew_score(5.0) == pytest.approx(50.0)

    def test_iv_skew_clipping(self) -> None:
        assert iv_skew_score(0.0) == pytest.approx(0.0)
        assert iv_skew_score(10.0) == pytest.approx(100.0)

    def test_put_call_bounds(self) -> None:
        assert put_call_skew_score(DEFAULT_PUT_CALL_LOW) == pytest.approx(0.0)
        assert put_call_skew_score(DEFAULT_PUT_CALL_HIGH) == pytest.approx(100.0)
        assert put_call_skew_score(1.25) == pytest.approx(50.0)

    def test_put_call_clipping(self) -> None:
        assert put_call_skew_score(0.5) == pytest.approx(0.0)
        assert put_call_skew_score(2.0) == pytest.approx(100.0)

    def test_put_call_non_positive_raises(self) -> None:
        with pytest.raises(ValueError, match="strictly positive"):
            put_call_skew_score(0.0)
        with pytest.raises(ValueError, match="strictly positive"):
            put_call_skew_score(-1.0)

    def test_term_slope_bounds(self) -> None:
        assert term_slope_score(DEFAULT_TERM_SLOPE_HIGH) == pytest.approx(0.0)
        assert term_slope_score(DEFAULT_TERM_SLOPE_LOW) == pytest.approx(100.0)
        assert term_slope_score(0.0) == pytest.approx(50.0)

    def test_term_slope_clipping(self) -> None:
        assert term_slope_score(4.0) == pytest.approx(0.0)
        assert term_slope_score(-4.0) == pytest.approx(100.0)

    def test_bad_calibration_bounds_raise(self) -> None:
        with pytest.raises(ValueError, match="strictly below"):
            iv_skew_score(5.0, low=8.0, high=2.0)
        with pytest.raises(ValueError, match="finite"):
            iv_skew_score(5.0, low=np.nan, high=8.0)

    def test_composite_all_normal(self) -> None:
        assert crash_risk_score(0, 0, 0) == pytest.approx(0.0)

    def test_composite_all_extreme(self) -> None:
        assert crash_risk_score(100, 100, 100) == pytest.approx(100.0)

    def test_composite_midpoint(self) -> None:
        assert crash_risk_score(50, 50, 50) == pytest.approx(50.0)

    def test_composite_array(self) -> None:
        result = crash_risk_score([0, 100], [0, 100], [0, 100])
        np.testing.assert_allclose(result, [0.0, 100.0])

    def test_composite_single_weight(self) -> None:
        assert crash_risk_score(50, 100, 100, weights=(1, 0, 0)) == pytest.approx(50.0)

    def test_composite_default_weights(self) -> None:
        assert DEFAULT_WEIGHTS == (0.4, 0.3, 0.3)

    def test_bad_weights_raise(self) -> None:
        with pytest.raises(ValueError, match="all be zero"):
            crash_risk_score(50, 50, 50, weights=(0, 0, 0))
        with pytest.raises(ValueError, match="exactly three"):
            crash_risk_score(50, 50, 50, weights=(1, 2))
        with pytest.raises(ValueError, match="exactly three"):
            crash_risk_score(50, 50, 50, weights=(1, 0, 0, 0))
        with pytest.raises(ValueError, match="non-negative"):
            crash_risk_score(50, 50, 50, weights=(-1, 0, 0))

    def test_composite_incompatible_shapes_raise(self) -> None:
        with pytest.raises(ValueError, match="incompatible"):
            crash_risk_score([0, 0, 0], [0, 0], [0, 0, 0])


class TestClassification:
    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (30.0, LEVEL_LOW),
            (50.0, LEVEL_MODERATE),
            (70.0, LEVEL_ELEVATED),
            (90.0, LEVEL_HIGH),
        ],
    )
    def test_levels(self, score: float, expected: str) -> None:
        assert classify_crash_risk(score) == expected

    @pytest.mark.parametrize(
        ("score", "expected"),
        [
            (DEFAULT_LOW_THRESHOLD, LEVEL_MODERATE),
            (DEFAULT_MODERATE_THRESHOLD, LEVEL_ELEVATED),
            (DEFAULT_HIGH_THRESHOLD, LEVEL_HIGH),
        ],
    )
    def test_boundaries(self, score: float, expected: str) -> None:
        assert classify_crash_risk(score) == expected

    def test_bad_thresholds_raise(self) -> None:
        with pytest.raises(ValueError, match="thresholds"):
            classify_crash_risk(50.0, low=60.0, moderate=40.0)
        with pytest.raises(ValueError, match="thresholds"):
            classify_crash_risk(50.0, low=-1.0)
        with pytest.raises(ValueError, match="thresholds"):
            classify_crash_risk(50.0, high=101.0)
        with pytest.raises(ValueError, match="thresholds"):
            classify_crash_risk(50.0, low=50.0, moderate=50.0)

    def test_array_score_raises(self) -> None:
        with pytest.raises(ValueError, match="single value"):
            classify_crash_risk([30.0, 50.0])


class TestEvaluate:
    def test_normal_input(self) -> None:
        verdict = evaluate_crash_risk(2.0, 1.0, 2.0)
        assert verdict.score == pytest.approx(0.0)
        assert verdict.level == LEVEL_LOW
        assert verdict.trade_allowed is True
        assert verdict.components == {
            "iv_skew_score": 0.0,
            "put_call_skew_score": 0.0,
            "term_slope_score": 0.0,
        }

    def test_extreme_input(self) -> None:
        verdict = evaluate_crash_risk(8.0, 1.5, -2.0)
        assert verdict.score == pytest.approx(100.0)
        assert verdict.level == LEVEL_HIGH
        assert verdict.trade_allowed is False

    def test_elevated_blocks(self) -> None:
        verdict = evaluate_crash_risk(6.2, 1.375, -1.0)
        assert verdict.score == pytest.approx(73.0)
        assert verdict.level == LEVEL_ELEVATED
        assert verdict.trade_allowed is False

    def test_gate_boundary_blocks(self) -> None:
        verdict = evaluate_crash_risk(5.6, 1.0, 2.0, weights=(1, 0, 0))
        assert verdict.score == pytest.approx(DEFAULT_GATE_THRESHOLD)
        assert verdict.trade_allowed is False

    def test_below_gate_allowed(self) -> None:
        verdict = evaluate_crash_risk(5.4, 1.0, 2.0, weights=(1, 0, 0))
        assert verdict.score == pytest.approx(170.0 / 3.0)
        assert verdict.trade_allowed is True

    def test_verdict_type(self) -> None:
        verdict = evaluate_crash_risk(2.0, 1.0, 2.0)
        assert isinstance(verdict, CrashRiskVerdict)

    def test_verdict_frozen(self) -> None:
        verdict = evaluate_crash_risk(2.0, 1.0, 2.0)
        with pytest.raises(FrozenInstanceError):
            verdict.score = 0.0  # type: ignore[misc]

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"iv_skew": None},
            {"iv_skew": ""},
            {"iv_skew": "abc"},
            {"iv_skew": []},
            {"iv_skew": np.array([])},
            {"iv_skew": np.nan},
            {"iv_skew": np.inf},
            {"iv_skew": True},
            {"iv_skew": [2, 8]},
            {"put_call_skew": 0},
            {"weights": (0, 0, 0)},
            {"gate_threshold": np.nan},
            {"low": 60.0, "moderate": 40.0},
        ],
    )
    def test_invalid_input_raises(self, kwargs: dict) -> None:
        args = {"iv_skew": 2.0, "put_call_skew": 1.0, "term_slope": 2.0}
        args.update(kwargs)
        with pytest.raises(ValueError):
            evaluate_crash_risk(**args)


class TestGateFailClosed:
    def test_valid_input_passes(self) -> None:
        verdict = crash_risk_gate(2.0, 1.0, 2.0)
        assert verdict.score == pytest.approx(0.0)
        assert verdict.level == LEVEL_LOW
        assert verdict.trade_allowed is True

    def test_all_missing_is_no_signal(self) -> None:
        verdict = crash_risk_gate()
        assert verdict.score is None
        assert verdict.level == LEVEL_NO_SIGNAL
        assert verdict.trade_allowed is False

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"iv_skew": 2.0, "put_call_skew": None, "term_slope": None},
            {"iv_skew": np.nan},
            {"iv_skew": np.inf},
            {"iv_skew": []},
            {"put_call_skew": 0},
            {"iv_skew": "abc"},
            {"iv_skew": True},
            {"weights": (0, 0, 0)},
        ],
    )
    def test_invalid_input_is_no_signal(self, kwargs: dict) -> None:
        args = {"iv_skew": 2.0, "put_call_skew": 1.0, "term_slope": 2.0}
        args.update(kwargs)
        verdict = crash_risk_gate(**args)
        assert verdict.score is None
        assert verdict.level == LEVEL_NO_SIGNAL
        assert verdict.trade_allowed is False

    def test_never_raises(self) -> None:
        battery = [
            {},
            {"iv_skew": None, "put_call_skew": None, "term_slope": None},
            {"iv_skew": np.nan, "put_call_skew": 1.0, "term_slope": 2.0},
            {"iv_skew": 2.0, "put_call_skew": 0, "term_slope": 2.0},
            {"iv_skew": "abc", "put_call_skew": 1.0, "term_slope": 2.0},
            {"iv_skew": 2.0, "put_call_skew": 1.0, "term_slope": 2.0, "weights": (0, 0, 0)},
            {"iv_skew": 2.0, "put_call_skew": 1.0, "term_slope": 2.0, "gate_threshold": np.nan},
        ]
        for kwargs in battery:
            crash_risk_gate(**kwargs)


class TestNoExecutionSurface:
    FORBIDDEN_ROOTS = {
        "requests",
        "alpaca",
        "ccxt",
        "websocket",
        "urllib",
        "http",
        "socket",
        "subprocess",
        "aiohttp",
        "yfinance",
        "pandas",
    }
    ALLOWED_ROOTS = {"numpy", "dataclasses", "typing", "__future__", "collections"}  # collections.abc.Sequence is stdlib, no execution surface

    @staticmethod
    def _module_source() -> str:
        import inspect

        import src.risk.crash_risk as crash_risk

        return inspect.getsource(crash_risk)

    @staticmethod
    def _import_roots(source: str) -> set[str]:
        roots: set[str] = set()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                roots.add(stripped.split()[1].split(".")[0])
        return roots

    def test_no_forbidden_imports(self) -> None:
        source = self._module_source()
        roots = self._import_roots(source)
        assert roots.isdisjoint(self.FORBIDDEN_ROOTS)

    def test_imports_are_numpy_and_stdlib_only(self) -> None:
        source = self._module_source()
        roots = self._import_roots(source)
        assert roots <= self.ALLOWED_ROOTS

    def test_no_execution_api_strings(self) -> None:
        source = self._module_source()
        for forbidden in ("os.system", "os.popen", "subprocess", "socket", "requests"):
            assert forbidden not in source