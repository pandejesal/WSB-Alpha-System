import unittest
import pandas as pd
import numpy as np
import os

# Lazy-load reporting (from private repo)
try:
    from src.alpha.reporting import PerformanceReporter
    HAS_PRIVATE = True
except ImportError:
    HAS_PRIVATE = False

class TestReporting(unittest.TestCase):
    def test_plot_trajectories(self):
        if not HAS_PRIVATE:
            self.skipTest("Private strategies repo not available")
        reporter = PerformanceReporter(output_dir="tests/mock_reports")
        dates = pd.date_range("2023-01-01", periods=100)
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        filepath = reporter.plot_trajectories({"Strat A": returns}, "Test Plot")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
