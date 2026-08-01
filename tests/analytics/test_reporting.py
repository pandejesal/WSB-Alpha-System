import unittest
import pandas as pd
import numpy as np
import os
from src.alpha.reporting import PerformanceReporter

class TestReporting(unittest.TestCase):
    def test_plot_trajectories(self):
        reporter = PerformanceReporter(output_dir="tests/mock_reports")
        dates = pd.date_range("2023-01-01", periods=100)
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        filepath = reporter.plot_trajectories({"Strat A": returns}, "Test Plot")
        self.assertIsNotNone(filepath)
        self.assertTrue(os.path.exists(filepath))
