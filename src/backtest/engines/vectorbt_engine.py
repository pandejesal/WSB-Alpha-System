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

# 3b. Add volume-weighted slippage and ADV filter
        if 'Volume' in df.columns:
            avg_volume = df['Volume'].rolling(20).mean()
            avg_dollar_volume = avg_volume * df['Close']
            min_adv_threshold = 1_000_000
            illiquid_mask = avg_dollar_volume < min_adv_threshold
            entries = entries & ~illiquid_mask
            exits = exits & ~illiquid_mask

        # T+1 Execution Rule Implementation in VectorBT:
        entries_t1 = entries.shift(1).fillna(False)
        exits_t1 = exits.shift(1).fillna(False)

        portfolio = vbt.Portfolio.from_signals(
            close,
            entries=entries_t1,
            exits=exits_t1,
            freq='1D',
            init_cash=100.0,
            fees=strategy_spec.get('fees', 0.001),
            slippage=strategy_spec.get('slippage', 0.001)
        )

        trades_df = portfolio.trades.records_readable
        return trades_df
