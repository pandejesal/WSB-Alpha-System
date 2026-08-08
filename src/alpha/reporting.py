import logging
import os

import matplotlib.pyplot as plt
import pandas as pd
import quantstats as qs


class PerformanceReporter:
    def __init__(self, output_dir: str = "experiments/reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def generate_tearsheet(self, strategy_returns: pd.Series, benchmark_returns: pd.Series = None, title: str = "Strategy"):
        output_file = os.path.join(self.output_dir, f"{title.replace(' ', '_').lower()}_tearsheet.html")
        try:
            qs.reports.html(strategy_returns, benchmark=benchmark_returns, title=title, output=output_file)
            return output_file
        except Exception:
            return None

    def plot_trajectories(self, returns_dict: dict, title: str = "Strategy Trajectories"):
        plt.figure(figsize=(12, 6))
        for name, returns in returns_dict.items():
            cumulative = (1 + returns).cumprod()
            plt.plot(cumulative.index, cumulative.values, label=name)
        plt.title(title)
        plt.ylabel("Cumulative Return")
        plt.xlabel("Date")
        plt.legend()
        plt.grid(True)
        output_file = os.path.join(self.output_dir, f"{title.replace(' ', '_').lower()}_trajectories.png")
        plt.savefig(output_file)
        plt.close()
        return output_file
