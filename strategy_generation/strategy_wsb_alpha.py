import pandas as pd
from strategy_generation.base_strategy import BaseStrategy
from analytics.indicators import compute_indicators
import logging

class WSBAlphaStrategy(BaseStrategy):
    """
    WSB Alpha Strategy integrating FinBERT sentiment with smart money technical confluence.
    For local testing/simplicity, we assume sentiment data is either pre-merged into the dataframe,
    or we fall back to pure technical confluence if sentiment isn't present.
    """
    def __init__(self, rsi_threshold_low=30, rsi_threshold_high=70):
        self.rsi_low = rsi_threshold_low
        self.rsi_high = rsi_threshold_high
        self.logger = logging.getLogger(__name__)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = compute_indicators(df)
        if df is None or len(df) == 0:
             # Ensure we return a dataframe even if empty, to match type hints
             return pd.DataFrame({'signal': []})

        df['signal'] = 0

        # Confluence rules from memory:
        # Long: Price > 20 EMA, RSI < 70, MACD > Signal
        # Short: Price < 20 EMA, RSI > 30, MACD < Signal

        long_condition = (
            (df['Close'] > df['EMA_20']) &
            (df['RSI_14'] < self.rsi_high) &
            (df['MACD'] > df['MACD_Signal'])
        )

        short_condition = (
            (df['Close'] < df['EMA_20']) &
            (df['RSI_14'] > self.rsi_low) &
            (df['MACD'] < df['MACD_Signal'])
        )

        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1

        # If 'sentiment_score' is present, use it as an absolute filter
        # E.g. don't go long if sentiment is extremely bearish
        if 'sentiment_score' in df.columns:
            df.loc[(df['signal'] == 1) & (df['sentiment_score'] < -0.5), 'signal'] = 0
            df.loc[(df['signal'] == -1) & (df['sentiment_score'] > 0.5), 'signal'] = 0

        return df
