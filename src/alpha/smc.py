import pandas as pd
import numpy as np

class SmartMoneyConcepts:
    """
    Mathematical implementations of Smart Money Concepts (SMC) for quantitative trading.
    """

    @staticmethod
    def identify_fvgs(df: pd.DataFrame, atr_threshold_multiplier: float = 0.5) -> pd.DataFrame:
        """
        Identifies Fair Value Gaps (FVGs) based on a 3-candle pattern.
        Bullish FVG: Candle 1 High < Candle 3 Low, gap >= threshold
        Bearish FVG: Candle 1 Low > Candle 3 High, gap >= threshold
        """
        df = df.copy()

        # Calculate ATR for dynamic thresholding
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean()

        df['fvg_bullish'] = False
        df['fvg_bearish'] = False
        df['fvg_size'] = 0.0

        # Shifted series for 3-candle pattern
        high_1 = df['high'].shift(2)
        low_1 = df['low'].shift(2)
        low_3 = df['low']
        high_3 = df['high']

        # Bullish FVG
        bullish_mask = (high_1 < low_3) & ((low_3 - high_1) >= atr_threshold_multiplier * atr)
        df.loc[bullish_mask, 'fvg_bullish'] = True
        df.loc[bullish_mask, 'fvg_size'] = df['low'] - df['high'].shift(2)

        # Bearish FVG
        bearish_mask = (low_1 > high_3) & ((low_1 - high_3) >= atr_threshold_multiplier * atr)
        df.loc[bearish_mask, 'fvg_bearish'] = True
        df.loc[bearish_mask, 'fvg_size'] = df['low'].shift(2) - df['high']

        return df

    @staticmethod
    def identify_order_blocks(df: pd.DataFrame, displacement_multiplier: float = 1.5, lookback: int = 20) -> pd.DataFrame:
        """
        Identifies Order Blocks (OB).
        Last opposite-color consolidation candle before a significant displacement impulse move.
        Displacement is defined as a move >= displacement_multiplier * median_ATR.
        """
        df = df.copy()

        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean()
        median_atr = atr.rolling(lookback).median()

        df['ob_bullish'] = False
        df['ob_bearish'] = False

        df['body_size'] = np.abs(df['close'] - df['open'])
        df['is_bullish_candle'] = df['close'] > df['open']
        df['is_bearish_candle'] = df['close'] < df['open']

        # Displacement detection
        displacement_bullish = (df['close'] - df['open']) >= (displacement_multiplier * median_atr)
        displacement_bearish = (df['open'] - df['close']) >= (displacement_multiplier * median_atr)

        # OB Bullish: Last bearish candle before bullish displacement
        for i in range(1, len(df)):
            if displacement_bullish.iloc[i]:
                # Look back for the last bearish candle
                for j in range(i-1, max(-1, i-6), -1):
                    if df['is_bearish_candle'].iloc[j]:
                        df.loc[df.index[j], 'ob_bullish'] = True
                        break

        # OB Bearish: Last bullish candle before bearish displacement
        for i in range(1, len(df)):
            if displacement_bearish.iloc[i]:
                # Look back for the last bullish candle
                for j in range(i-1, max(-1, i-6), -1):
                    if df['is_bullish_candle'].iloc[j]:
                        df.loc[df.index[j], 'ob_bearish'] = True
                        break

        return df

    @staticmethod
    def identify_liquidity_sweeps(df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        """
        Identifies Liquidity Sweeps.
        A wick that pierces a recent swing high or low then closes back within the range.
        """
        df = df.copy()

        df['swing_high'] = df['high'].rolling(window, center=False).max().shift(1)
        df['swing_low'] = df['low'].rolling(window, center=False).min().shift(1)

        df['sweep_bullish'] = False
        df['sweep_bearish'] = False

        # Bullish Sweep: Price sweeps below swing low but closes above it
        bullish_sweep = (df['low'] < df['swing_low']) & (df['close'] > df['swing_low'])
        df.loc[bullish_sweep, 'sweep_bullish'] = True

        # Bearish Sweep: Price sweeps above swing high but closes below it
        bearish_sweep = (df['high'] > df['swing_high']) & (df['close'] < df['swing_high'])
        df.loc[bearish_sweep, 'sweep_bearish'] = True

        return df
