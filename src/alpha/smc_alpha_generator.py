import pandas as pd

from src.alpha.smc import SmartMoneyConcepts


class SMCAlphaGenerator:
    """
    Combines FinBERT sentiment velocity with Smart Money Concepts (FVGs, OBs)
    and momentum filters to generate robust trading signals.
    """

    @staticmethod
    def generate_signals(
        price_df: pd.DataFrame,
        sentiment_score: float,
        sentiment_velocity: float,
        regime: str
    ) -> pd.DataFrame:
        """
        Generates combined signals.
        Requires BOTH a confirmed sentiment-velocity regime AND an institutional structure
        alignment (FVG/OB/Sweep), OR a momentum backstop.
        """
        df = price_df.copy()

        # 1. Identify SMC features
        df = SmartMoneyConcepts.identify_fvgs(df)
        df = SmartMoneyConcepts.identify_order_blocks(df)
        df = SmartMoneyConcepts.identify_liquidity_sweeps(df)

        # 2. Momentum Backstop (e.g., RSI and EMA crossover)
        # Simplified momentum for demonstration
        df['ema_short'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_long'] = df['close'].ewm(span=21, adjust=False).mean()
        df['momentum_bullish'] = df['ema_short'] > df['ema_long']
        df['momentum_bearish'] = df['ema_short'] < df['ema_long']

        # 3. Sentiment Velocity Threshold
        velocity_threshold = 0.1 # Example threshold
        sentiment_bullish = sentiment_velocity > velocity_threshold
        sentiment_bearish = sentiment_velocity < -velocity_threshold

        df['signal'] = 0
        df['confidence'] = 0.0

        # 4. Combine Signals (Logic from blueprint)
        for i in range(len(df)):
            smc_bullish = df['fvg_bullish'].iloc[i] or df['ob_bullish'].iloc[i] or df['sweep_bullish'].iloc[i]
            smc_bearish = df['fvg_bearish'].iloc[i] or df['ob_bearish'].iloc[i] or df['sweep_bearish'].iloc[i]
            mom_bullish = df['momentum_bullish'].iloc[i]
            mom_bearish = df['momentum_bearish'].iloc[i]

            # Require (Sentiment + SMC) OR Momentum
            if (sentiment_bullish and smc_bullish) or mom_bullish:
                # Regime Gating: Only take longs in BULLISH or NORMAL regimes
                if regime in ['BULLISH', 'NORMAL']:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'confidence'] = 0.8 if (sentiment_bullish and smc_bullish) else 0.6

            elif (sentiment_bearish and smc_bearish) or mom_bearish:  # noqa: SIM102 - Nested if is more readable here
                 # Regime Gating: Only take shorts in BEARISH or HIGH_VOL regimes
                 if regime in ['BEARISH', 'HIGH_VOL']:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'confidence'] = 0.8 if (sentiment_bearish and smc_bearish) else 0.6

        return df
