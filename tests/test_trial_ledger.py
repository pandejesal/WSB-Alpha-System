"""Tests for the persisted trial ledger + Deflated Sharpe Ratio guard.

Covers: content-hash deduplication, JSONL read/write/update semantics,
corrupt-line tolerance (FP checklist), the Bailey & Lopez de Prado DSR
math, and the ingest CLI end to end (without touching the real
docs/data/strategy_rankings.json).
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

from src.backtest.defend.trial_ledger import (
    STATUSES,
    TrialLedger,
    deflated_sharpe_ratio,
    deflated_sharpe_threshold,
    expected_max_std_normal,
    inverse_normal_cdf,
    normal_cdf,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VALID_STATUSES = ("PENDING", "INCUBATING", "PROMOTED", "REJECTED")

_PARAMS = {"atr_trailing_mult": 1.5, "rsi_bounds": [30, 70], "min_confluence": 3}
_METRICS = {"sharpe": 0.8, "profit_factor": 1.4, "max_drawdown_pct": 0.12}


class StatsHelpersTest(unittest.TestCase):
    """Deflated Sharpe Ratio math (Bailey & Lopez de Prado 2014)."""

    def test_normal_cdf_known_values(self):
        self.assertAlmostEqual(normal_cdf(0.0), 0.5, places=9)
        self.assertAlmostEqual(normal_cdf(1.6448536269514722), 0.95, places=9)
        self.assertAlmostEqual(normal_cdf(-3.0), 0.0013498980, places=6)

    def test_inverse_normal_cdf_known_quantiles(self):
        cases = [
            (0.5, 0.0),
            (0.95, 1.6448536269514722),
            (0.975, 1.959963984540054),
            (0.99, 2.3263478740408408),
            (0.01, -2.3263478740408408),
            (0.001, -3.090232306167813),
        ]
        for p, expected in cases:
            self.assertAlmostEqual(inverse_normal_cdf(p), expected, places=5)

    def test_inverse_normal_cdf_rejects_bad_probs(self):
        for p in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                inverse_normal_cdf(p)

    def test_expected_max_std_normal(self):
        self.assertEqual(expected_max_std_normal(1), 0.0)
        self.assertAlmostEqual(expected_max_std_normal(100), 2.5076, delta=0.1)
        self.assertLess(expected_max_std_normal(10), expected_max_std_normal(100))
        self.assertLess(expected_max_std_normal(100), expected_max_std_normal(1000))

    def test_dsr_n_one_is_psr(self):
        t, sr = 2500, 0.8
        psr = normal_cdf(sr * (t - 1) ** 0.5 / (1 + 0.5 * sr * sr) ** 0.5)
        self.assertAlmostEqual(deflated_sharpe_ratio(t, sr, 1), psr, places=9)

    def test_dsr_monotonicity(self):
        # At SR=1.0 every variant saturates to 1.0 in double precision, so use a
        # mid-range SR (0.05) where the deflation ordering is observable.
        self.assertGreater(deflated_sharpe_ratio(2500, 0.05, 1), deflated_sharpe_ratio(2500, 0.05, 50))
        self.assertGreater(deflated_sharpe_ratio(5000, 0.05, 50), deflated_sharpe_ratio(1000, 0.05, 50))
        self.assertGreater(deflated_sharpe_ratio(2500, 0.05, 36), deflated_sharpe_ratio(2500, 0.02, 36))
        self.assertTrue(0.0 < deflated_sharpe_ratio(2500, 0.05, 36) < 1.0)

    def test_dsr_rejects_bad_arguments(self):
        with self.assertRaises(ValueError):
            deflated_sharpe_ratio(1, 0.5, 10)   # T must be > 1
        with self.assertRaises(ValueError):
            deflated_sharpe_ratio(2500, 0.5, 0)  # N must be >= 1

    def test_threshold_inverts_dsr(self):
        for n in (1, 5, 36, 100):
            break_even = deflated_sharpe_threshold(2500, n, confidence=0.95)
            self.assertTrue(break_even > 0.0)
            self.assertAlmostEqual(
                deflated_sharpe_ratio(2500, break_even, n), 0.95, places=6
            )

    def test_threshold_grows_with_trials(self):
        self.assertLess(
            deflated_sharpe_threshold(2500, 1),
            deflated_sharpe_threshold(2500, 100),
        )

    def test_threshold_impossible_at_tiny_t(self):
        self.assertTrue(math.isinf(deflated_sharpe_threshold(2, 10 ** 6)))


class TrialLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger_path = os.path.join(self.tmp.name, "trials.jsonl")
        self.ledger = TrialLedger(path=self.ledger_path)

    def test_append_creates_file_and_full_row(self):
        sha = self.ledger.append_experiment(
            "strat_a", _PARAMS, "2021-01-01/2024-12-31", _METRICS, "test"
        )
        self.assertTrue(os.path.exists(self.ledger_path))
        self.assertEqual(len(sha), 64)
        int(sha, 16)  # valid hex

        trial = self.ledger.load_trials()[0]
        self.assertEqual(trial.status, "PENDING")
        self.assertEqual(trial.strategy_id, "strat_a")
        self.assertEqual(trial.provider, "test")
        self.assertEqual(trial.params["rsi_bounds"], [30, 70])
        self.assertEqual(trial.metrics["sharpe"], 0.8)
        self.assertEqual(trial.metrics["max_dd"], 0.12)
        self.assertTrue(
            {"sharpe", "profit_factor", "max_dd"} <= set(trial.metrics.keys())
        )

    def test_append_creates_missing_parent_folder(self):
        nested = os.path.join(self.tmp.name, "a", "b", "c", "trials.jsonl")
        ledger = TrialLedger(path=nested)
        ledger.append_experiment("strat_a", {}, "r", _METRICS, "test")
        self.assertTrue(os.path.exists(nested))

    def test_dedupe_skips_identical_trial(self):
        with self.assertLogs("src.backtest.defend.trial_ledger", level="WARNING"):
            first = self.ledger.append_experiment("strat_a", _PARAMS, "range", _METRICS, "t")
            second = self.ledger.append_experiment("strat_a", _PARAMS, "range", _METRICS, "t")
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        trials = self.ledger.load_trials()
        self.assertEqual(len(trials), 1)

    def test_hash_changes_with_params_and_is_order_stable(self):
        base = self.ledger.append_experiment("s", {"a": 1, "b": 2}, "r", _METRICS, "t")
        different = self.ledger.append_experiment("s", {"a": 1, "b": 3}, "r", _METRICS, "t")
        self.assertNotEqual(base, different)
        # same params in a different dict order canonicalize to the same hash,
        # so the reordered append is deduplicated (returns None)
        with self.assertLogs("src.backtest.defend.trial_ledger", level="WARNING"):
            reordered = self.ledger.append_experiment(
                "s", {"b": 2, "a": 1}, "r", _METRICS, "t"
            )
        self.assertIsNone(reordered)

    def test_load_trials_missing_file_returns_empty(self):
        self.assertEqual(self.ledger.load_trials(), [])

    def test_load_trials_roundtrip_preserves_order(self):
        self.ledger.append_experiment("first", {}, "r", _METRICS, "t")
        self.ledger.append_experiment("second", {}, "r", _METRICS, "t")
        names = [t.strategy_id for t in self.ledger.load_trials()]
        self.assertEqual(names, ["first", "second"])

    def test_corrupt_lines_are_logged_and_skipped(self):
        self.ledger.append_experiment("ok", {}, "r", _METRICS, "t")
        with open(self.ledger.path, "a", encoding="utf-8") as fh:
            fh.write("{not-json-at-all\n")
            fh.write('{"sha256":"deadbeef"}\n')
        with self.assertLogs("src.backtest.defend.trial_ledger", level="WARNING"):
            trials = self.ledger.load_trials()
        self.assertEqual(len(trials), 2)
        self.assertEqual(self.ledger.corrupt_lines, 1)

    def test_metrics_normalization_guards_non_finite(self):
        ledger = TrialLedger(path=os.path.join(self.tmp.name, "g.jsonl"))
        ledger.append_experiment(
            "s", {},
            "r",
            {"sharpe": float("nan"), "profit_factor": "junk", "max_dd": None},
            "t",
        )
        metrics = ledger.load_trials()[0].metrics
        self.assertIsNone(metrics["sharpe"])
        self.assertIsNone(metrics["profit_factor"])
        self.assertIsNone(metrics["max_dd"])

    def test_update_status_rewrites_row_in_place(self):
        sha = self.ledger.append_experiment("strat_a", _PARAMS, "r", _METRICS, "t")
        self.assertTrue(self.ledger.update_status(sha, "PROMOTED"))
        trial = self.ledger.load_trials()[0]
        self.assertEqual(trial.status, "PROMOTED")
        self.assertEqual(trial.strategy_id, "strat_a")
        self.assertEqual(trial.metrics["sharpe"], 0.8)

    def test_update_status_leaves_other_rows_untouched(self):
        first = self.ledger.append_experiment("a", {}, "r", _METRICS, "t")
        second = self.ledger.append_experiment("b", {}, "r", _METRICS, "t")
        self.ledger.update_status(second, "REJECTED")
        statuses = [t.status for t in self.ledger.load_trials()]
        self.assertEqual(statuses, ["PENDING", "REJECTED"])
        self.assertEqual(first, self.ledger.load_trials()[0].sha256)

    def test_update_status_preserves_corrupt_lines(self):
        self.ledger.append_experiment("a", {}, "r", _METRICS, "t")
        with open(self.ledger.path, "a", encoding="utf-8") as fh:
            fh.write("{corrupt\n")
        sha = self.ledger.load_trials()[0].sha256
        self.assertTrue(self.ledger.update_status(sha, "INCUBATING"))
        with open(self.ledger.path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        self.assertIn("{corrupt", raw)
        self.assertEqual(self.ledger.load_trials()[0].status, "INCUBATING")

    def test_update_status_unknown_hash_returns_false(self):
        self.ledger.append_experiment("a", {}, "r", _METRICS, "t")
        self.assertFalse(self.ledger.update_status("0" * 64, "PROMOTED"))

    def test_update_status_validates_inputs(self):
        with self.assertRaises(ValueError):
            self.ledger.update_status("0" * 64, "NOT_A_STATUS")
        with self.assertRaises(ValueError):
            self.ledger.update_status("short", "PROMOTED")

    def test_append_validates_inputs(self):
        with self.assertRaises(ValueError):
            self.ledger.append_experiment("  ", {}, "r", _METRICS, "t")
        with self.assertRaises(TypeError):
            self.ledger.append_experiment("s", {"x": object()}, "r", _METRICS, "t")

    def test_status_constants(self):
        self.assertEqual(set(STATUSES), set(VALID_STATUSES))


_CLI_ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


class CliIngestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.rankings = os.path.join(self.tmp.name, "rankings.json")
        self.ledger = os.path.join(self.tmp.name, "run-logs", "trials.jsonl")
        self.entries = [
            {
                "id": "strat_0000",
                "name": "alpha",
                "parameters": {"x": 1},
                "metrics": {"sharpe": -0.5, "profit_factor": 0.8, "max_drawdown_pct": 0.1},
            },
            {
                "id": "strat_0001",
                "name": "beta",
                "parameters": {"x": 2},
                "metrics": {"sharpe": 1.6, "profit_factor": 1.4, "max_drawdown_pct": 0.2},
            },
        ]
        with open(self.rankings, "w", encoding="utf-8") as fh:
            json.dump(self.entries, fh)

    def _run(self, *extra):
        cmd = [
            sys.executable, "-m", "src.backtest.defend.trial_ledger",
            "--ingest", self.rankings,
            "--ledger", self.ledger,
        ] + list(extra)
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=_CLI_ENV
        )

    def test_ingest_reports_table_and_creates_ledger(self):
        result = self._run("--max-deflate", "10", "--obs", "2500", "--top", "5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Multiple-comparison guard", result.stdout)
        self.assertIn("Best trial", result.stdout)
        self.assertIn("raw Sharpe", result.stdout)
        with open(self.ledger, "r", encoding="utf-8") as fh:
            self.assertEqual(len(fh.readlines()), 2)

    def test_ingest_does_not_modify_rankings(self):
        before = open(self.rankings, "rb").read()
        self._run("--max-deflate", "10")
        after = open(self.rankings, "rb").read()
        self.assertEqual(before, after)

    def test_second_run_deduplicates(self):
        self._run("--max-deflate", "10")
        second = self._run("--max-deflate", "10")
        self.assertEqual(second.returncode, 0)
        self.assertIn("duplicates skipped: 2", second.stdout)
        with open(self.ledger, "r", encoding="utf-8") as fh:
            self.assertEqual(len(fh.readlines()), 2)

    def test_missing_ingest_file_fails_cleanly(self):
        cmd = [
            sys.executable, "-m", "src.backtest.defend.trial_ledger",
            "--ingest", os.path.join(self.tmp.name, "nope.json"),
            "--ledger", self.ledger,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=REPO_ROOT, env=_CLI_ENV
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("ingest failed", result.stderr)


if __name__ == "__main__":
    unittest.main()