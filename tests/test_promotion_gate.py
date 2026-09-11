"""Tests for promotion_gate.py — fail-closed gate logic."""
import json
import os
from pathlib import Path

import pytest

from scripts.promotion_gate import evaluate_gate, load_dashboard


class TestLoadDashboard:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_dashboard(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_unparseable_json_returns_empty(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{{")
        result = load_dashboard(str(bad_file))
        assert result == {}

    def test_valid_json_returns_dict(self, tmp_path):
        dash_file = tmp_path / "dash.json"
        dash_file.write_text(json.dumps({"verdict": "GO"}))
        result = load_dashboard(str(dash_file))
        assert result == {"verdict": "GO"}


class TestEvaluateGateFailClosed:
    def test_empty_dashboard_is_fail_closed(self):
        result = evaluate_gate({})
        assert result["gate"] == "FAIL_CLOSED"
        assert result["go"] is False

    def test_zero_months_is_fail_closed(self):
        dash = {
            "verdict": "GO",
            "months_tracked": 0,
            "min_months_required": 2,
            "all_months_green": True,
            "broken_executions": 0,
        }
        result = evaluate_gate(dash)
        assert result["gate"] == "FAIL_CLOSED"
        assert result["go"] is False


class TestEvaluateGateNoGo:
    def test_wrong_verdict(self):
        dash = {
            "verdict": "NEED_MORE_PAPER_TIME",
            "months_tracked": 3,
            "min_months_required": 2,
            "all_months_green": True,
            "broken_executions": 0,
        }
        result = evaluate_gate(dash)
        assert result["gate"] == "NO_GO"
        assert result["go"] is False

    def test_insufficient_months(self):
        dash = {
            "verdict": "GO",
            "months_tracked": 1,
            "min_months_required": 2,
            "all_months_green": True,
            "broken_executions": 0,
        }
        result = evaluate_gate(dash)
        assert result["gate"] == "NO_GO"
        assert result["go"] is False

    def test_not_all_months_green(self):
        dash = {
            "verdict": "GO",
            "months_tracked": 3,
            "min_months_required": 2,
            "all_months_green": False,
            "broken_executions": 0,
        }
        result = evaluate_gate(dash)
        assert result["gate"] == "NO_GO"
        assert result["go"] is False

    def test_broken_executions_positive(self):
        dash = {
            "verdict": "GO",
            "months_tracked": 3,
            "min_months_required": 2,
            "all_months_green": True,
            "broken_executions": 1,
        }
        result = evaluate_gate(dash)
        assert result["gate"] == "NO_GO"
        assert result["go"] is False


class TestEvaluateGateGo:
    def test_all_criteria_met(self):
        dash = {
            "verdict": "GO",
            "months_tracked": 3,
            "min_months_required": 2,
            "all_months_green": True,
            "broken_executions": 0,
        }
        result = evaluate_gate(dash)
        assert result["gate"] == "GO"
        assert result["go"] is True
