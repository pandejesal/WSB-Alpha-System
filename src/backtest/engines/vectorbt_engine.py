import pandas as pd
import vectorbt as vbt
from ..engine_base import BaseBacktestEngine

class VectorBTEngine(BaseBacktestEngine):
    def run_sim(self, strategy_spec: dict, historical_data: pd.DataFrame) -> pd.DataFrame:
        if historical_data.empty:
            return pd.DataFrame()

        df = historical_data.copy()

        # Example: VectorBT needs datetime index
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

        close = df['Close']

        # We need to simulate the signal generation.
        # For demonstration of T+1 rule, let's say the signal is randomly generated on day T
        # and executed on T+1.

        # Example basic strategy logic using vectorbt: Fast MA crossing Slow MA
        fast_window = strategy_spec.get('fast_window', 10)
        slow_window = strategy_spec.get('slow_window', 20)

        fast_ma = vbt.MA.run(close, window=fast_window)
        slow_ma = vbt.MA.run(close, window=slow_window)

        # Signal generated on day T
        entries = fast_ma.ma_crossed_above(slow_ma)
        exits = fast_ma.ma_crossed_below(slow_ma)

        # T+1 Execution Rule Implementation in VectorBT:
        # Shift the boolean signal array forward by 1 period so it actually triggers on the NEXT day
        entries_t1 = entries.shift(1).fillna(False)
        exits_t1 = exits.shift(1).fillna(False)

        portfolio = vbt.Portfolio.from_signals(
            close,
            entries=entries_t1,
            exits=exits_t1,
            freq='1D',
            init_cash=100.0,
            fees=strategy_spec.get('fees', 0.001)
        )

        # Return trades as a dataframe
        trades_df = portfolio.trades.records_readable

        # Add a check to confirm T+1 rule internally
        # (the shift above guarantees this, but we'll surface the timestamps)
        return trades_df
