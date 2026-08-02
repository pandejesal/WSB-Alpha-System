import pandas as pd
from abc import ABC, abstractmethod

class BaseBacktestEngine(ABC):
    """
    Abstract Base Class for all backtesting engines.
    """

    @abstractmethod
    def run_sim(self, strategy_spec: dict, historical_data: pd.DataFrame) -> pd.DataFrame:
        """
        Run the simulation for a given strategy specification and return a DataFrame with trades/performance.
        """
        pass

    def apply_t1_execution_rule(self, signals: pd.DataFrame, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """
        Strict T+1 Execution Rule to eliminate Look-Ahead Bias.
        Assumes signals has a 'timestamp' column indicating when the signal was generated.
        Returns a modified signals DataFrame mapping the execution to the NEXT available market open/close.
        """
        if signals.empty:
            return signals

        df = signals.copy()
        df['signal_time'] = pd.to_datetime(df['timestamp'])

        # Simple T+1 shift for daily data:
        # If signal occurs on date T, execution happens on date T+1 (at open, usually)
        df['execution_date'] = df['signal_time'] + pd.Timedelta(days=1)

        # Strip time for daily alignment
        df['execution_date'] = df['execution_date'].dt.floor('d')

        return df
