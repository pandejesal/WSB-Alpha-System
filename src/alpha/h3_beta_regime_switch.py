import numpy as np
import pandas as pd
import ta

from src.alpha.base_strategy import BaseStrategy
from src.alpha.indicators import compute_indicators


class H3BetaRegimeSwitch(BaseStrategy):
    """
    H3-Beta: Volatility-Ratio Regime-Switching Ensemble

    Switches between momentum (EMA crossover) and mean-reversion (RSI extremes)
    sub-strategies based on the 20d/60d realized volatility ratio.

    Regimes:
      - vol_ratio < 0.8  → LOW volatility regime  → momentum sub-strategy
      - vol_ratio > 1.2  → HIGH volatility regime → mean-reversion sub-strategy
      - 0.8 <= ratio <= 1.2 → NEUTRAL regime → no position
    """

    def __init__(self, name="h3_beta_regime_switch", vol_short_window=20, vol_long_window=60,
                 low_threshold=0.8, high_threshold=1.2,
                 ema_fast=10, ema_slow=30, rsi_period=14, rsi_oversold=30, rsi_overbought=70):
        self.name = name
        self.vol_short_window = vol_short_window
        self.vol_long_window = vol_long_window
        self.low_threshold = low_threshold
        self.high_threshold = high_threshold
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'close' not in df.columns:
            return df

        # Compute base indicators
        df = compute_indicators(df)

        # Rolling realized volatility (annualized daily std)
        returns = df['close'].pct_change()
        vol_short = returns.rolling(window=self.vol_short_window, min_periods=self.vol_short_window).std()
        vol_long = returns.rolling(window=self.vol_long_window, min_periods=self.vol_long_window).std()

        # Volatility ratio
        vol_ratio = vol_short / vol_long

        # Add RSI if not already present
        if 'RSI_14' not in df.columns:
            rsi = ta.momentum.RSIIndicator(close=df['close'], window=self.rsi_period)
            df['RSI_14'] = rsi.rsi()

        # Momentum sub-strategy: EMA crossover
        ema_fast_series = ta.trend.EMAIndicator(close=df['close'], window=self.ema_fast).ema_indicator()
        ema_slow_series = ta.trend.EMAIndicator(close=df['close'], window=self.ema_slow).ema_indicator()

        # Mean-reversion sub-strategy: RSI extremes

        df['signal'] = 0  # Default: no position (NEUTRAL regime)

        for i in range(self.vol_long_window, len(df)):
            vr = vol_ratio.iloc[i]
            if pd.isna(vr):
                continue

            if vr < self.low_threshold:
                # LOW vol regime → momentum
                if ema_fast_series.iloc[i] > ema_slow_series.iloc[i]:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                elif ema_fast_series.iloc[i] < ema_slow_series.iloc[i]:
                    df.iloc[i, df.columns.get_loc('signal')] = -1

            elif vr > self.high_threshold:
                # HIGH vol regime → mean-reversion
                rsi_val = df['RSI_14'].iloc[i]
                if pd.isna(rsi_val):
                    continue
                if rsi_val < self.rsi_oversold:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                elif rsi_val > self.rsi_overbought:
                    df.iloc[i, df.columns.get_loc('signal')] = -1

            # else: NEUTRAL regime → signal stays 0

        return df
