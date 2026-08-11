import logging

import pandas as pd

from ..engine_base import BaseBacktestEngine

logger = logging.getLogger(__name__)

class NautilusEngine(BaseBacktestEngine):
    def __init__(self):
        self.use_nautilus = False
        try:
            import nautilus_trader  # noqa: F401 - unused import (intentionally exposed/exported)
            self.use_nautilus = True
        except ImportError:
            logger.info("NautilusTrader not installed or incompatible. Using mock simulation fallback.")

    def run_sim(self, strategy_spec: dict, historical_data: pd.DataFrame) -> pd.DataFrame:
        df = historical_data.copy()

        if df.empty:
            return pd.DataFrame()

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])

        signals = []
        for i in range(len(df) - 1):
            if i % 10 == 0:
                signals.append({
                    'timestamp': df.iloc[i]['Date'],
                    'price_at_signal': df.iloc[i]['Close'],
                    'direction': 'BUY'
                })

        signals_df = pd.DataFrame(signals)
        signals_df = self.apply_t1_execution_rule(signals_df, df)

        trades = []
        for _, row in signals_df.iterrows():
            exec_date = row['execution_date']
            exec_row = df[df['Date'] == exec_date]
            if not exec_row.empty:
                volume = exec_row.iloc[0]['Volume'] if 'Volume' in exec_row.columns else 1_000_000
                avg_volume = df['Volume'].rolling(20).mean().iloc[exec_row.index[0]] if 'Volume' in df.columns else 1_000_000
                volume_ratio = avg_volume / (volume + 1)
                slippage_bps = min(50, max(5, int(volume_ratio * 10)))
                exec_price = exec_row.iloc[0]['Open'] * (1 + slippage_bps / 10000)

                trades.append({
                    'signal_timestamp': row['timestamp'],
                    'execution_timestamp': exec_date,
                    'price_at_signal': row['price_at_signal'],
                    'execution_price': exec_price,
                    'direction': row['direction']
                })

        return pd.DataFrame(trades)
