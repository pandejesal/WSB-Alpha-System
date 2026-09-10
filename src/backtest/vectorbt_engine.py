# CH-14 candidate: duplicate backtest engine — candidate for consolidation into src/backtest/engines/canonical.py (no merge in this phase; canonical is engines/canonical.py)
import logging
from typing import Any

import pandas as pd

try:
    import vectorbt as vbt  # type: ignore

    _VBT2_AVAILABLE = True
except (ImportError, ValueError) as _e2:
    vbt = None  # type: ignore
    _VBT2_AVAILABLE = False
    _VBT2_IMPORT_ERROR = str(_e2)

from src.backtest.base_engine import BacktestEngine


class VectorBTEngine(BacktestEngine):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def run_backtest(self, data: pd.DataFrame, strategy: Any, **kwargs) -> dict[str, Any]:
        """
        Runs the generated strategy instance using vectorbt.
        Assumes 'strategy' has a 'generate_signals' method returning a DataFrame with a 'signal' column.
        """
        if not _VBT2_AVAILABLE or vbt is None:
            return {"status": "error", "message": f"vectorbt not available: {_VBT2_IMPORT_ERROR if '_VBT2_IMPORT_ERROR' in globals() else 'not installed'}", "metrics": {}}
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
