import pandas as pd
import numpy as np
from datetime import timedelta

class WalkForwardOptimizer:
    def __init__(self, train_days=90, test_days=30, step_days=30):
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days

    def generate_windows(self, start_date, end_date):
        windows = []
        current = start_date
        while current + timedelta(days=self.train_days + self.test_days) <= end_date:
            train_start = current
            train_end = current + timedelta(days=self.train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)
            windows.append((train_start, train_end, test_start, test_end))
            current += timedelta(days=self.step_days)
        return windows

    def optimize(self, strategy_class, param_grid, data, windows):
        results = []
        for train_start, train_end, test_start, test_end in windows:
            train_data = data[(data.index >= train_start) & (data.index < train_end)]
            test_data = data[(data.index >= test_start) & (data.index < test_end)]

            best_params = None
            best_sharpe = -np.inf
            for params in param_grid:
                strat = strategy_class(**params)
                metrics = strat.backtest(train_data)
                if metrics.get('sharpe', -np.inf) > best_sharpe:
                    best_sharpe = metrics['sharpe']
                    best_params = params

            if best_params:
                best_strat = strategy_class(**best_params)
                oos_metrics = best_strat.backtest(test_data)
                results.append({
                    'window': (train_start, test_end),
                    'best_params': best_params,
                    'train_sharpe': best_sharpe,
                    'oos_sharpe': oos_metrics.get('sharpe', 0),
                    'oos_return': oos_metrics.get('return', 0),
                    'oos_max_dd': oos_metrics.get('max_drawdown', 1.0)
                })
        return pd.DataFrame(results)
