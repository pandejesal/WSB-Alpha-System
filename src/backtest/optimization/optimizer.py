import itertools
import pandas as pd
from typing import Dict, List
from scipy.optimize import minimize
import numpy as np

class GridSearchOptimizer:
    def __init__(self, param_grid: Dict[str, List]):
        self.param_grid = param_grid

    def generate_combinations(self):
        keys = self.param_grid.keys()
        values = self.param_grid.values()
        return [dict(zip(keys, combo)) for combo in itertools.product(*values)]

    def optimize(self, strategy_class, data):
        results = []
        for params in self.generate_combinations():
            strat = strategy_class(**params)
            metrics = strat.backtest(data)
            results.append({**params, **metrics})

        if not results:
            return pd.DataFrame()

        return pd.DataFrame(results).sort_values('sharpe', ascending=False)

class BayesianOptimizer:
    def __init__(self, strategy_class, bounds: Dict[str, tuple]):
        self.strategy_class = strategy_class
        self.bounds = bounds
        self.data = None

    def objective(self, param_values):
        params_dict = dict(zip(self.bounds.keys(), param_values))
        strat = self.strategy_class(**params_dict)
        metrics = strat.backtest(self.data)
        return -metrics.get('sharpe', 0)

    def optimize(self, data, n_iterations=50):
        self.data = data
        x0 = [(b[0] + b[1]) / 2.0 for b in self.bounds.values()]

        # We need bounded minimization. Nelder-Mead with bounds via wrapper or just L-BFGS-B
        # L-BFGS-B supports bounds directly
        result = minimize(
            self.objective,
            x0=x0,
            method='L-BFGS-B',
            bounds=list(self.bounds.values()),
            options={'maxiter': n_iterations}
        )
        return dict(zip(self.bounds.keys(), result.x))
