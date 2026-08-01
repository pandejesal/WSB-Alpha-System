import pandas as pd
import numpy as np
from strategy_generation.base_strategy import BaseStrategy
from analytics.indicators import compute_indicators
import logging

class ManAHLStrategy(BaseStrategy):
    """
    Man AHL Multi-Horizon Momentum Strategy.
    Uses 4 distinct lookback windows (5, 10, 21, 42 days) with volatility normalization.
    """
    def __init__(self, windows=[5, 10, 21, 42], vol_window=63):
        self.windows = windows
        self.vol_window = vol_window
        self.logger = logging.getLogger(__name__)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        if len(df) < max(self.windows) + self.vol_window:
            self.logger.warning("Not enough data to compute Man AHL signals.")
            df['signal'] = 0
            return df

        # Calculate daily returns
        df['returns'] = df['Close'].pct_change()

        # Calculate annualized volatility for normalization
        df['volatility'] = df['returns'].rolling(window=self.vol_window).std() * np.sqrt(252)
        df['volatility'] = df['volatility'].replace(0, np.nan).bfill() # Prevent div by zero

        # Calculate momentum across multiple horizons
        signals_components = []
        for w in self.windows:
            momentum = df['Close'] / df['Close'].shift(w) - 1
            # Normalize by volatility
            normalized_momentum = momentum / df['volatility']
            signals_components.append(normalized_momentum)

        # Combine horizon signals (Equal weight)
        combined_signal_raw = sum(signals_components) / len(self.windows)

        # Cross-sectional scaling or simple thresholding for the final signal.
        # For simplicity in this iteration, we map positive momentum to 1, negative to -1
        # In a real portfolio, this raw signal would dictate size.
        df['raw_signal'] = combined_signal_raw

        df['signal'] = 0
        df.loc[df['raw_signal'] > 0.1, 'signal'] = 1
        df.loc[df['raw_signal'] < -0.1, 'signal'] = -1

        # Optional: EWM smoothing (14-day) to prevent whipsaws (mentioned in project memory)
        df['signal'] = df['signal'].ewm(span=14).mean()
        df['signal'] = np.sign(df['signal']).fillna(0).astype(int)

        return df
