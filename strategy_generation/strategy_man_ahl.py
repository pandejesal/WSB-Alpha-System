import pandas as pd
import numpy as np
from strategy_generation.base_strategy import BaseStrategy
from analytics.indicators import compute_indicators
import logging

class ManAHLStrategy(BaseStrategy):
    def __init__(self, windows=[5, 10, 21, 42], vol_window=63):
        self.windows = windows
        self.vol_window = vol_window
        self.logger = logging.getLogger(__name__)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < max(self.windows) + self.vol_window:
            self.logger.warning("Not enough data to compute Man AHL signals.")
            df['signal'] = 0
            return df

        df['returns'] = df['Close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=self.vol_window).std() * np.sqrt(252)
        df['volatility'] = df['volatility'].replace(0, np.nan).bfill()

        signals_components = []
        for w in self.windows:
            momentum = df['Close'] / df['Close'].shift(w) - 1
            normalized_momentum = momentum / df['volatility']
            signals_components.append(normalized_momentum)

        combined_signal_raw = sum(signals_components) / len(self.windows)
        df['raw_signal'] = combined_signal_raw

        df['signal'] = 0
        df.loc[df['raw_signal'] > 0.1, 'signal'] = 1
        df.loc[df['raw_signal'] < -0.1, 'signal'] = -1

        df['signal'] = df['signal'].ewm(span=14).mean()
        df['signal'] = np.sign(df['signal']).fillna(0).astype(int)
        return df
