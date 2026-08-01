from typing import Dict, Any
import pandas as pd
from backtesting.base_engine import BacktestEngine
import vectorbt as vbt
import logging

class VectorBTEngine(BacktestEngine):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run_backtest(self, data: pd.DataFrame, strategy: Any, **kwargs) -> Dict[str, Any]:
        """
        Runs the generated strategy instance using vectorbt.
        Assumes 'strategy' has a 'generate_signals' method returning a DataFrame with a 'signal' column.
        """
        self.logger.info(f"Running VectorBT simulation for {strategy.__class__.__name__}")

        try:
            # 1. Compute signals using the generated strategy instance
            df_with_signals = strategy.generate_signals(data)

            # 2. Extract boolean arrays for entries and exits
            # 1 = Long, -1 = Short (Shorting support can be added by passing short_entries)
            entries = df_with_signals['signal'] == 1
            exits = df_with_signals['signal'] == -1

            # 3. Run vectorbt simulation
            # Using defaults for now (100% allocation on entry, exit on signal)
            portfolio = vbt.Portfolio.from_signals(
                df_with_signals['Close'],
                entries,
                exits,
                init_cash=100.0,
                fees=0.001, # 10 bps default slippage/commission
                freq='1D'
            )

            # 4. Extract metrics
            metrics = {
                "total_return": portfolio.total_return(),
                "sharpe_ratio": portfolio.sharpe_ratio(),
                "max_drawdown": portfolio.max_drawdown(),
                "win_rate": portfolio.trades.win_rate(),
                "trades": portfolio.trades.count()
            }
            return {"status": "success", "metrics": metrics, "portfolio": portfolio}

        except Exception as e:
            self.logger.error(f"VectorBT simulation failed: {e}")
            return {"status": "error", "message": str(e), "metrics": {}}
