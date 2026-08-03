import unittest
import pandas as pd
from datetime import datetime
from src.backtest.optimization.walk_forward import WalkForwardOptimizer
from src.backtest.optimization.optimizer import GridSearchOptimizer
from src.evolution.strategy_selector import ThompsonSampler

class TestOptimization(unittest.TestCase):
    def test_walk_forward_windows(self):
        opt = WalkForwardOptimizer(train_days=90, test_days=30, step_days=30)
        start = datetime(2023, 1, 1)
        end = datetime(2024, 1, 1) # 365 days
        windows = opt.generate_windows(start, end)

        self.assertTrue(len(windows) > 0)
        # Check first window
        t_start, t_end, test_s, test_e = windows[0]
        self.assertEqual(t_start, start)
        self.assertEqual((t_end - t_start).days, 90)
        self.assertEqual(test_s, t_end)
        self.assertEqual((test_e - test_s).days, 30)

    def test_grid_search_returns_results(self):
        param_grid = {'a': [1, 2], 'b': [3, 4]}
        opt = GridSearchOptimizer(param_grid)

        class DummyStrat:
            def __init__(self, **kwargs):
                self.p = kwargs
            def backtest(self, data):
                return {'sharpe': self.p['a'] + self.p['b']}

        res = opt.optimize(DummyStrat, None)
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('sharpe', res.columns)
        self.assertEqual(res.iloc[0]['sharpe'], 6) # max is 2+4=6

    def test_thompson_sampling_converges(self):
        strategies = [
            {'id': 'A'}, # P(success) ~ 0.5
            {'id': 'B'}, # P(success) ~ 0.8
        ]
        sampler = ThompsonSampler(strategies)

        # Simulate 1000 rounds
        import random
        for _ in range(1000):
            sid = sampler.select()
            if sid == 'A':
                sampler.update('A', random.random() < 0.5)
            else:
                sampler.update('B', random.random() < 0.8)

        # B should have a much higher expected value and higher alpha
        evs = sampler.get_expected_values()
        self.assertGreater(evs['B'], evs['A'])

if __name__ == '__main__':
    unittest.main()
