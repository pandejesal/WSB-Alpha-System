"""Leakage guard for LLM-augmented strategies.

Enforces temporal train/test splits and blocks future-data access during
evaluation. This is the validation step referenced by the Pipeline Registry
for LLM-augmented strategies (arXiv 2608.27734): no future data in training,
future data blocked in evaluation, and LLM-augmented strategies must declare
proper data boundaries.

The guard is fail-closed: any violation raises ``LeakageViolation`` rather
than silently proceeding with contaminated data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


class LeakageViolation(Exception):
    """Raised when a strategy's data access violates temporal boundaries."""


@dataclass
class LeakageReport:
    """Result of a leakage guard check on a single strategy entry."""

    strategy_id: str
    family: str
    passed: bool
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "family": self.family,
            "passed": self.passed,
            "violations": list(self.violations),
            "warnings": list(self.warnings),
        }


def _extract_timestamps(data: pd.DataFrame) -> pd.Series:
    """Return a monotonic datetime Series from a DataFrame index or Date column.

    Supports both a DatetimeIndex and a ``Date``/``datetime`` column. Returns
    an empty Series when no usable timestamps exist so callers can decide how
    to treat missing time information.
    """
    if data is None or data.empty:
        return pd.Series(dtype="datetime64[ns]")

    if isinstance(data.index, pd.DatetimeIndex):
        return pd.Series(data.index)

    for col in ("Date", "datetime", "timestamp", "time"):
        if col in data.columns:
            try:
                return pd.to_datetime(data[col], errors="coerce").dropna()
            except (TypeError, ValueError):
                continue

    return pd.Series(dtype="datetime64[ns]")


def detect_future_data(data: pd.DataFrame, as_of: pd.Timestamp) -> list[pd.Timestamp]:
    """Return timestamps in ``data`` that occur strictly after ``as_of``.

    Used to block future data during evaluation: any row whose timestamp is
    after the evaluation cutoff is a leakage violation.
    """
    ts = _extract_timestamps(data)
    if ts.empty:
        return []
    future = ts[ts > as_of]
    return list(future)


def validate_temporal_split(
    data: pd.DataFrame,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    *,
    strategy_id: str = "unknown",
) -> LeakageReport:
    """Enforce a strict temporal train/test split with no overlap.

    ``train_end`` must be strictly before ``test_start``. Any row in the
    training region that falls at or after ``test_start``, or any row in the
    test region that falls at or before ``train_end``, is a violation.

    Returns a :class:`LeakageReport`; raises nothing (callers decide whether
    to raise based on ``passed``).
    """
    report = LeakageReport(strategy_id=strategy_id, family="", passed=True)

    if train_end >= test_start:
        report.passed = False
        report.violations.append(
            f"train_end ({train_end}) must be strictly before test_start ({test_start})"
        )
        return report

    ts = _extract_timestamps(data)
    if ts.empty:
        report.warnings.append("no usable timestamps found; split not verifiable")
        return report

    # Rows that belong to the test region but appear in training data
    leaked_into_train = ts[(ts >= test_start) & (ts <= train_end)]  # noqa: SIM114
    # Rows that belong to the training region but appear in test data
    leaked_into_test = ts[(ts <= train_end) & (ts >= test_start)]

    if not leaked_into_train.empty:
        report.passed = False
        report.violations.append(
            f"{len(leaked_into_train)} row(s) in training region fall at/after test_start"
        )
    if not leaked_into_test.empty:
        report.passed = False
        report.violations.append(
            f"{len(leaked_into_test)} row(s) in test region fall at/before train_end"
        )

    return report


def validate_llm_data_boundaries(
    spec: dict[str, Any],
    data: pd.DataFrame,
    *,
    as_of: pd.Timestamp | None = None,
) -> LeakageReport:
    """Validate that an LLM-augmented strategy declares proper data boundaries.

    An LLM-augmented strategy is one whose spec carries an ``llm`` section
    (e.g. ``llm: {enabled: true}``) or whose family is in the known LLM
    families (``xgboost_exits``, ``sentiment_overlay``, ``ta_rules``).

    Checks:
      * If ``as_of`` is provided, no row may be strictly after it (future data
        blocked during evaluation).
      * If the spec declares ``train_end``/``test_start``, the temporal split
        must be valid and non-overlapping.
      * If the spec declares an ``llm`` section, it must declare a
        ``data_boundary`` (``train``/``test``/``live``) so downstream consumers
        know which region the LLM may read.
    """
    strategy_id = str(spec.get("id", "unknown"))
    family = str(spec.get("family", ""))
    report = LeakageReport(strategy_id=strategy_id, family=family, passed=True)

    llm_section = spec.get("llm") if isinstance(spec.get("llm"), dict) else {}
    is_llm_augmented = bool(llm_section) or family in {
        "xgboost_exits",
        "sentiment_overlay",
        "ta_rules",
    }

    # Future-data block during evaluation
    if as_of is not None:
        future = detect_future_data(data, as_of)
        if future:
            report.passed = False
            report.violations.append(
                f"{len(future)} row(s) after evaluation cutoff {as_of} (future data blocked)"
            )

    # Temporal split enforcement when declared
    train_end = spec.get("train_end")
    test_start = spec.get("test_start")
    if train_end is not None and test_start is not None:
        try:
            train_end_ts = pd.Timestamp(train_end)
            test_start_ts = pd.Timestamp(test_start)
        except (TypeError, ValueError):
            report.passed = False
            report.violations.append("train_end/test_start are not valid timestamps")
        else:
            split = validate_temporal_split(
                data, train_end_ts, test_start_ts, strategy_id=strategy_id
            )
            report.passed = report.passed and split.passed
            report.violations.extend(split.violations)
            report.warnings.extend(split.warnings)

    # LLM-augmented strategies must declare a data boundary
    if is_llm_augmented and "data_boundary" not in llm_section:
        report.passed = False
        report.violations.append(
            "LLM-augmented strategy must declare llm.data_boundary (train/test/live)"
        )

    return report


def guard_signals(
    data: pd.DataFrame,
    registry_entries: list[dict],
    *,
    as_of: pd.Timestamp | None = None,
    raise_on_violation: bool = True,
) -> list[LeakageReport]:
    """Run the leakage guard over registry entries before signal generation.

    For each entry that is active (status in ``active``/``ported``/
    ``PASS_ALL_GATES``) and carries a spec, validate its data boundaries.
    Returns one :class:`LeakageReport` per checked entry.

    When ``raise_on_violation`` is True (default), the first violation raises
    :class:`LeakageViolation` with the offending strategy id. Otherwise the
    reports are returned and callers decide how to proceed.
    """
    reports: list[LeakageReport] = []
    active_statuses = {"active", "ported", "PASS_ALL_GATES"}

    for entry in registry_entries:
        if entry.get("status") not in active_statuses:
            continue
        spec = entry.get("spec", {})
        if not spec:
            continue

        report = validate_llm_data_boundaries(spec, data, as_of=as_of)
        reports.append(report)

        if raise_on_violation and not report.passed:
            raise LeakageViolation(
                f"Leakage violation for strategy '{report.strategy_id}': "
                + "; ".join(report.violations)
            )

    return reports
