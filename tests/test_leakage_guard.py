"""Tests for src.alpha.leakage_guard — temporal train/test split enforcement,
future-data blocking, and LLM-augmented strategy data boundary validation."""

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# LeakageReport
# ---------------------------------------------------------------------------

def test_leakage_report_to_dict():
    from src.alpha.leakage_guard import LeakageReport

    report = LeakageReport(
        strategy_id="s1",
        family="ta_rules",
        passed=True,
        violations=[],
        warnings=["no timestamps"],
    )
    d = report.to_dict()
    assert d["strategy_id"] == "s1"
    assert d["family"] == "ta_rules"
    assert d["passed"] is True
    assert d["violations"] == []
    assert d["warnings"] == ["no timestamps"]


def test_leakage_report_defaults():
    from src.alpha.leakage_guard import LeakageReport

    report = LeakageReport(strategy_id="s2", family="xgboost_exits", passed=False)
    d = report.to_dict()
    assert d["violations"] == []
    assert d["warnings"] == []
    assert d["passed"] is False


# ---------------------------------------------------------------------------
# _extract_timestamps
# ---------------------------------------------------------------------------

def test_extract_timestamps_none_input():
    from src.alpha.leakage_guard import _extract_timestamps

    result = _extract_timestamps(None)
    assert result.empty
    assert pd.api.types.is_datetime64_any_dtype(result)


def test_extract_timestamps_empty_dataframe():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame()
    result = _extract_timestamps(df)
    assert result.empty


def test_extract_timestamps_datetime_index():
    from src.alpha.leakage_guard import _extract_timestamps

    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    result = _extract_timestamps(df)
    assert len(result) == 3
    assert result.iloc[0] == dates[0]


def test_extract_timestamps_date_column():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame({
        "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "val": [10, 20],
    })
    result = _extract_timestamps(df)
    assert len(result) == 2


def test_extract_timestamps_lowercase_datetime_column():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame({
        "datetime": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"]),
        "x": [1, 2, 3],
    })
    result = _extract_timestamps(df)
    assert len(result) == 3


def test_extract_timestamps_timestamp_column():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame({
        "timestamp": ["2024-03-10", "2024-03-11"],
        "val": [5, 6],
    })
    result = _extract_timestamps(df)
    assert len(result) == 2
    assert pd.api.types.is_datetime64_any_dtype(result)


def test_extract_timestamps_time_column():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame({
        "time": ["2024-07-01T10:00", "2024-07-01T11:00"],
        "v": [1, 2],
    })
    result = _extract_timestamps(df)
    assert len(result) == 2


def test_extract_timestamps_no_time_column():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame({"price": [100, 200], "vol": [1000, 2000]})
    result = _extract_timestamps(df)
    assert result.empty


def test_extract_timestamps_coerce_errors():
    from src.alpha.leakage_guard import _extract_timestamps

    df = pd.DataFrame({
        "Date": ["2024-01-01", "not-a-date", "2024-01-03"],
    })
    result = _extract_timestamps(df)
    # bad row is dropped by errors="coerce" + dropna
    assert len(result) == 2


# ---------------------------------------------------------------------------
# detect_future_data
# ---------------------------------------------------------------------------

def test_detect_future_data_with_future_rows():
    from src.alpha.leakage_guard import detect_future_data

    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame({"val": range(5)}, index=dates)
    as_of = pd.Timestamp("2024-01-03")
    future = detect_future_data(df, as_of)
    assert len(future) == 2  # Jan 4 and Jan 5
    assert all(t > as_of for t in future)


def test_detect_future_data_no_future_rows():
    from src.alpha.leakage_guard import detect_future_data

    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    as_of = pd.Timestamp("2024-01-10")
    future = detect_future_data(df, as_of)
    assert future == []


def test_detect_future_data_empty_data():
    from src.alpha.leakage_guard import detect_future_data

    df = pd.DataFrame()
    future = detect_future_data(df, pd.Timestamp("2024-01-01"))
    assert future == []


def test_detect_future_data_exact_boundary_not_future():
    from src.alpha.leakage_guard import detect_future_data

    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    as_of = pd.Timestamp("2024-01-03")  # exact match on last row
    future = detect_future_data(df, as_of)
    assert future == []  # strictly after only


# ---------------------------------------------------------------------------
# validate_temporal_split
# ---------------------------------------------------------------------------

def test_validate_temporal_split_valid():
    from src.alpha.leakage_guard import validate_temporal_split

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({"val": range(10)}, index=dates)
    report = validate_temporal_split(
        df,
        train_end=pd.Timestamp("2024-01-05"),
        test_start=pd.Timestamp("2024-01-06"),
        strategy_id="good_split",
    )
    assert report.passed is True
    assert report.violations == []


def test_validate_temporal_split_train_end_overlaps_test():
    from src.alpha.leakage_guard import validate_temporal_split

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({"val": range(10)}, index=dates)
    report = validate_temporal_split(
        df,
        train_end=pd.Timestamp("2024-01-07"),
        test_start=pd.Timestamp("2024-01-05"),
        strategy_id="bad_split",
    )
    assert report.passed is False
    assert len(report.violations) >= 1
    assert "train_end" in report.violations[0]


def test_validate_temporal_split_equal_boundaries():
    from src.alpha.leakage_guard import validate_temporal_split

    report = validate_temporal_split(
        pd.DataFrame(),
        train_end=pd.Timestamp("2024-01-05"),
        test_start=pd.Timestamp("2024-01-05"),
        strategy_id="equal",
    )
    assert report.passed is False


def test_validate_temporal_split_no_timestamps():
    from src.alpha.leakage_guard import validate_temporal_split

    df = pd.DataFrame({"price": [1, 2, 3]})
    report = validate_temporal_split(
        df,
        train_end=pd.Timestamp("2024-01-05"),
        test_start=pd.Timestamp("2024-01-10"),
        strategy_id="no_ts",
    )
    assert report.passed is True
    assert any("no usable timestamps" in w for w in report.warnings)


# ---------------------------------------------------------------------------
# validate_llm_data_boundaries
# ---------------------------------------------------------------------------

def test_llm_boundary_future_data_blocked():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame({"val": range(5)}, index=dates)
    spec = {"id": "strat1", "family": "sentiment_overlay"}
    report = validate_llm_data_boundaries(
        spec, df, as_of=pd.Timestamp("2024-01-03")
    )
    assert report.passed is False
    assert any("future data blocked" in v for v in report.violations)


def test_llm_boundary_no_future_data():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    spec = {"id": "strat2", "family": "momentum_breakout"}
    report = validate_llm_data_boundaries(
        spec, df, as_of=pd.Timestamp("2024-01-10")
    )
    assert report.passed is True


def test_llm_boundary_missing_data_boundary_declaration():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    spec = {"id": "strat3", "family": "sentiment_overlay", "llm": {"enabled": True}}
    df = pd.DataFrame()
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is False
    assert any("data_boundary" in v for v in report.violations)


def test_llm_boundary_has_data_boundary_declaration():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    spec = {
        "id": "strat4",
        "family": "xgboost_exits",
        "llm": {"enabled": True, "data_boundary": "train"},
    }
    df = pd.DataFrame()
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is True


def test_llm_boundary_temporal_split_valid():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({"val": range(10)}, index=dates)
    spec = {
        "id": "strat5",
        "family": "sentiment_overlay",
        "llm": {"data_boundary": "train"},
        "train_end": "2024-01-05",
        "test_start": "2024-01-06",
    }
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is True


def test_llm_boundary_temporal_split_invalid():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({"val": range(10)}, index=dates)
    spec = {
        "id": "strat6",
        "family": "ta_rules",
        "train_end": "2024-01-08",
        "test_start": "2024-01-03",
    }
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is False
    assert len(report.violations) >= 1


def test_llm_boundary_bad_timestamp_strings():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    spec = {
        "id": "strat7",
        "family": "ta_rules",
        "train_end": "not-a-date",
        "test_start": "also-not-a-date",
    }
    df = pd.DataFrame()
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is False
    assert any("not valid timestamps" in v for v in report.violations)


def test_llm_boundary_non_llm_family_no_declaration_required():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    spec = {"id": "strat8", "family": "momentum_breakout"}
    df = pd.DataFrame()
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is True


def test_llm_boundary_empty_spec():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    report = validate_llm_data_boundaries({}, pd.DataFrame())
    assert report.strategy_id == "unknown"
    assert report.passed is True


def test_llm_boundary_unknown_family_not_llm_augmented():
    from src.alpha.leakage_guard import validate_llm_data_boundaries

    spec = {"id": "strat9", "family": "unknown_family_xyz", "llm": "not-a-dict"}
    df = pd.DataFrame()
    report = validate_llm_data_boundaries(spec, df)
    assert report.passed is True


# ---------------------------------------------------------------------------
# guard_signals
# ---------------------------------------------------------------------------

def test_guard_signals_skips_inactive_entries():
    from src.alpha.leakage_guard import guard_signals

    entries = [
        {"status": "inactive", "spec": {"id": "s1", "family": "ta_rules"}},
        {"status": "draft", "spec": {"id": "s2", "family": "ta_rules"}},
        {"status": "needs_paper", "spec": {"id": "s3", "family": "ta_rules"}},
    ]
    reports = guard_signals(pd.DataFrame(), entries)
    assert reports == []


def test_guard_signals_skips_entries_without_spec():
    from src.alpha.leakage_guard import guard_signals

    entries = [{"status": "active", "spec": {}}]
    reports = guard_signals(pd.DataFrame(), entries)
    assert reports == []


def test_guard_signals_active_entry_passes():
    from src.alpha.leakage_guard import guard_signals

    entries = [
        {
            "status": "active",
            "spec": {"id": "s_ok", "family": "momentum"},
        }
    ]
    reports = guard_signals(pd.DataFrame(), entries)
    assert len(reports) == 1
    assert reports[0].passed is True


def test_guard_signals_raises_on_violation():
    from src.alpha.leakage_guard import LeakageViolation, guard_signals

    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame({"val": range(5)}, index=dates)
    entries = [
        {
            "status": "PASS_ALL_GATES",
            "spec": {"id": "bad_s", "family": "sentiment_overlay"},
        }
    ]
    with pytest.raises(LeakageViolation, match="bad_s"):
        guard_signals(df, entries, as_of=pd.Timestamp("2024-01-02"))


def test_guard_signals_no_raise_returns_reports():
    from src.alpha.leakage_guard import guard_signals

    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df = pd.DataFrame({"val": range(5)}, index=dates)
    entries = [
        {
            "status": "active",
            "spec": {"id": "s_warn", "family": "sentiment_overlay"},
        }
    ]
    reports = guard_signals(
        df, entries, as_of=pd.Timestamp("2024-01-02"), raise_on_violation=False
    )
    assert len(reports) == 1
    assert reports[0].passed is False


def test_guard_signals_ported_status_checked():
    from src.alpha.leakage_guard import guard_signals

    entries = [
        {"status": "ported", "spec": {"id": "s_ported", "family": "xgboost_exits", "llm": {"data_boundary": "train"}}}
    ]
    reports = guard_signals(pd.DataFrame(), entries)
    assert len(reports) == 1


def test_guard_signals_multiple_entries_mixed():
    from src.alpha.leakage_guard import guard_signals

    dates = pd.date_range("2024-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    entries = [
        {"status": "active", "spec": {"id": "good", "family": "momentum"}},
        {"status": "inactive", "spec": {"id": "skip", "family": "ta_rules"}},
        {"status": "ported", "spec": {"id": "also_good", "family": "ta_rules", "llm": {"data_boundary": "train"}}},
    ]
    reports = guard_signals(
        df, entries, as_of=pd.Timestamp("2024-12-31")
    )
    # only active + ported checked, both pass
    assert len(reports) == 2
    assert all(r.passed for r in reports)


def test_guard_signals_empty_registry():
    from src.alpha.leakage_guard import guard_signals

    reports = guard_signals(pd.DataFrame(), [])
    assert reports == []
