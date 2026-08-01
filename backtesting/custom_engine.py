from typing import Dict, Any
import pandas as pd
import numpy as np
from backtesting.base_engine import BacktestEngine
import logging

class CustomEngine(BacktestEngine):
    """
    Modularized sequential custom backtesting engine extracting the specific
    logics (like 'mixed_ret', custom slippage, and cumulative sum returns)
    from the original legacy monoliths.
    """
    def __init__(self, atr_period: int = 14, initial_capital: float = 100.0, commission: float = 0.0004):
        self.logger = logging.getLogger(__name__)
        self.atr_period = atr_period
        self.initial_capital = initial_capital
        self.commission = commission

    def run_backtest(self, data: pd.DataFrame, strategy: Any, **kwargs) -> Dict[str, Any]:
        self.logger.info(f"Running CustomEngine simulation for {strategy.__class__.__name__}")

        try:
            df = strategy.generate_signals(data.copy())
            if 'signal' not in df.columns or len(df) == 0:
                raise ValueError("Strategy failed to generate valid signals.")

            # Assume compute_indicators has been run if ATR is missing
            if 'ATR_14' not in df.columns:
                # Basic ATR approximation if missing
                df['tr0'] = abs(df['High'] - df['Low'])
                df['tr1'] = abs(df['High'] - df['Close'].shift())
                df['tr2'] = abs(df['Low'] - df['Close'].shift())
                df['TR'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
                df['ATR_14'] = df['TR'].rolling(self.atr_period).mean()

            df['Returns'] = df['Close'].pct_change()

            # Legacy custom slippage logic: 5% of 14-day ATR, bounded between 0.1% and 2.5%
            # Approximated here as a simple percentage hit per trade
            avg_price = df['Close'].mean()
            avg_atr = df['ATR_14'].mean()
            if pd.isna(avg_atr): avg_atr = 0
            slippage_pct = min(max(0.05 * avg_atr / avg_price, 0.001), 0.025) if avg_price > 0 else 0.001

            # Calculate strategy returns
            df['Strategy_Return'] = df['signal'].shift(1) * df['Returns']

            # Apply costs on trade entry/exit
            trade_mask = df['signal'].diff().fillna(0) != 0
            df.loc[trade_mask, 'Strategy_Return'] -= (self.commission + slippage_pct)

            # Cumulative sum logic instead of cumprod (Project Memory rule)
            df['Cumulative_Return'] = df['Strategy_Return'].fillna(0).cumsum()
            df['Equity'] = self.initial_capital * (1 + df['Cumulative_Return'])

            # Basic metrics
            total_return = df['Cumulative_Return'].iloc[-1]
            win_rate = (df['Strategy_Return'] > 0).mean() # Simplified
            max_dd = (df['Equity'] / df['Equity'].cummax() - 1).min()

            return {
                "status": "success",
                "metrics": {
                    "total_return": total_return,
                    "win_rate": win_rate,
                    "max_drawdown": max_dd,
                    "trades": trade_mask.sum()
                },
                "portfolio": df
            }

        except Exception as e:
            self.logger.error(f"CustomEngine simulation failed: {e}")
            return {"status": "error", "message": str(e), "metrics": {}}
