"""Example SMA crossover algorithm using the Lean engine port.

Demonstrates the Algorithm base class with a simple long-only
SMA crossover strategy on SPY.
"""

from __future__ import annotations

from src.backtest.lean_engine import Algorithm, Slice


class SMACrossAlgorithm(Algorithm):
    """Simple moving average crossover: buy when fast SMA > slow SMA."""

    def __init__(self, fast: int = 50, slow: int = 200) -> None:
        super().__init__()
        self.fast_period = fast
        self.slow_period = slow
        self._prices: list[float] = []

    def Initialize(self) -> None:  # noqa: N802
        self.SetCash(100_000)
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2025, 12, 31)
        self.SetBenchmark("SPY")
        self.AddEquity("SPY")

    def OnData(self, slice: Slice) -> None:  # noqa: N802
        if "SPY" not in slice:
            return
        price = slice["SPY"].close
        self._prices.append(price)
        if len(self._prices) < self.slow_period:
            return
        fast_sma = sum(self._prices[-self.fast_period:]) / self.fast_period
        slow_sma = sum(self._prices[-self.slow_period:]) / self.slow_period
        if fast_sma > slow_sma:
            self.SetHoldings("SPY", 1.0)
        else:
            self.Liquidate("SPY")


def run_example() -> dict:
    """Run the SMA crossover and return results."""
    algo = SMACrossAlgorithm(fast=50, slow=200)
    return algo.run()


if __name__ == "__main__":
    results = run_example()
    print(f"Strategy return: {results['strategy_return']:.2%}")
    print(f"Benchmark return: {results['benchmark_return']:.2%}")
    print(f"Total orders: {results['total_orders']}")
    print(f"Total fees: ${results['total_fees']:.2f}")
