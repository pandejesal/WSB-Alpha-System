from dataclasses import dataclass
from typing import Any


@dataclass
class StrategyConfig:
    name: str
    parameters: dict[str, Any]


class MetaStrategy:
    def __init__(self, custom_mapping: dict[str, dict[str, Any]] | None = None):
        self.default_mapping = {
            "trending_up": {"name": "momentum_breakout_v2", "parameters": {}},
            "trending_down": {"name": "cash/defensive", "parameters": {}},
            "mean_reverting": {"name": "mean_reversion_enhanced", "parameters": {}},
            "volatile": {"name": "volatile", "parameters": {"sizing": "reduced", "stops": "wider"}},
            "quiet": {"name": "trend_following_v3", "parameters": {}},
        }
        self.custom_mapping = custom_mapping or {}

    def select_strategy(self, regime_label: str) -> StrategyConfig:
        if regime_label in self.custom_mapping:
            config = self.custom_mapping[regime_label]
        elif regime_label in self.default_mapping:
            config = self.default_mapping[regime_label]
        else:
            raise ValueError(f"Unknown regime label: {regime_label}")
        return StrategyConfig(name=config["name"], parameters=config.get("parameters", {}))

    def run_meta_strategy(self, data, regime_series):
        """
        Simulate meta-strategy performance based on regime transitions.
        This is a simplified mock representation for integration testing.
        """
        import pandas as pd
        import vectorbt as vbt

        if data.empty or regime_series.empty:
            return None

        # Just to demonstrate the return of a BacktestResult object / portfolio object
        # In a real implementation this would iterate through regime series,
        # compute signals based on `select_strategy(regime)` and the underlying logic,
        # then combine signals into a single portfolio.

        # We will create a simple mock portfolio using vectorbt for now to satisfy the API signature.
        close = data["Close"] if "Close" in data.columns else data.iloc[:, 0]
        entries = pd.Series(False, index=close.index)
        exits = pd.Series(False, index=close.index)

        # Randomly enter and exit to simulate some activity, or use moving average crossover
        # just so it produces a valid vbt.Portfolio
        fast_ma = vbt.MA.run(close, window=10)
        slow_ma = vbt.MA.run(close, window=20)
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)

        portfolio = vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            freq="1D",
            init_cash=10000.0
        )
        return portfolio


class ParameterTuner:
    def __init__(self, grid_config_path: str):
        self.grid_config_path = grid_config_path

    def tune(self, strategies: list[str], data, output_csv: str):
        import csv
        import itertools
        import json

        import yaml

        import vectorbt as vbt

        with open(self.grid_config_path) as f:
            grids = yaml.safe_load(f)

        results = []
        close = data["Close"] if "Close" in data.columns else data.iloc[:, 0]

        for strategy in strategies:
            if strategy not in grids:
                continue

            param_grid = grids[strategy]
            keys, values = zip(*param_grid.items())
            permutations = [dict(zip(keys, v)) for v in itertools.product(*values)]

            for params in permutations:
                # Simulate strategy logic based on params. We'll use dummy indicators for now.
                window1 = params.get("lookback", params.get("rsi_period", params.get("ema_fast", params.get("sma_period", 10))))
                window2 = params.get("ema_slow", window1 * 2)

                fast_ma = vbt.MA.run(close, window=int(window1))
                slow_ma = vbt.MA.run(close, window=int(window2))

                entries = fast_ma.ma_crossed_above(slow_ma)
                exits = fast_ma.ma_crossed_below(slow_ma)

                portfolio = vbt.Portfolio.from_signals(
                    close,
                    entries=entries,
                    exits=exits,
                    freq="1D",
                    init_cash=10000.0
                )

                sharpe = portfolio.sharpe_ratio()
                max_dd = portfolio.max_drawdown()
                win_rate = portfolio.trades.win_rate()
                total_trades = portfolio.trades.count()

                results.append({
                    "strategy": strategy,
                    "params": json.dumps(params),
                    "sharpe": sharpe,
                    "max_dd": max_dd,
                    "win_rate": win_rate,
                    "total_trades": total_trades
                })

        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["strategy", "params", "sharpe", "max_dd", "win_rate", "total_trades"])
            writer.writeheader()
            writer.writerows(results)
