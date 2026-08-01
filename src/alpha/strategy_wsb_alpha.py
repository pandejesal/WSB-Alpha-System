import pandas as pd
from src.alpha.base_strategy import BaseStrategy
from src.alpha.indicators import compute_indicators
import logging

class WSBAlphaStrategy(BaseStrategy):
    def __init__(self, rsi_threshold_low=30, rsi_threshold_high=70):
        self.rsi_low = rsi_threshold_low
        self.rsi_high = rsi_threshold_high
        self.logger = logging.getLogger(__name__)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = compute_indicators(df)
        if df is None or len(df) == 0:
             return pd.DataFrame({'signal': []})

        df['signal'] = 0
        long_condition = (df['Close'] > df['EMA_20']) & (df['RSI_14'] < self.rsi_high) & (df['MACD'] > df['MACD_Signal'])
        short_condition = (df['Close'] < df['EMA_20']) & (df['RSI_14'] > self.rsi_low) & (df['MACD'] < df['MACD_Signal'])

        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1

        if 'sentiment_score' in df.columns:
            df.loc[(df['signal'] == 1) & (df['sentiment_score'] < -0.5), 'signal'] = 0
            df.loc[(df['signal'] == -1) & (df['sentiment_score'] > 0.5), 'signal'] = 0

        return df
