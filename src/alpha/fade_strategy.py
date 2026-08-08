import logging

import pandas as pd

logger = logging.getLogger(__name__)

class FadeStrategy:
    """
    Implements a mean-reversion shorting strategy ("The Fade").
    Trigger condition:
    1. FinBERT sentiment is historically high (> 90th percentile, trailing 30-day window).
    2. Technical Confluence shows momentum breaking down.
    """

    def __init__(self, historical_90th_percentile: float = None):
        """
        Initialize with the pre-calculated 90th percentile of sentiment scores from the trailing 30 days.
        """
        self.threshold = historical_90th_percentile

    def is_sentiment_euphoric(self, current_score: float) -> bool:
        """
        Checks if the current sentiment is above the 90th percentile of the trailing 30-day baseline.
        """
        if self.threshold is None:
            # Need a minimum baseline to safely calculate percentiles
            return False

        logger.debug(f"Current Score: {current_score:.4f}, 90th Pct Threshold: {self.threshold:.4f}")
        return current_score > self.threshold

    def evaluate(self, current_score: float, technical_data: pd.Series) -> bool:
        """
        Evaluates if the conditions for the Fade Strategy are met.
        Technical criteria for momentum breaking down:
        - Heikin-Ashi turns red (Close < Open)
        - MACD crosses below MACD Signal
        Returns True if a SHORT signal should be generated.
        """
        euphoric = self.is_sentiment_euphoric(current_score)

        # Check technical breakdown
        try:
            ha_red = technical_data.get('HA_Close', 1) < technical_data.get('HA_Open', 0)
            macd_bearish = technical_data.get('MACD', 1) < technical_data.get('MACD_Signal', 0)
            momentum_breaking = ha_red and macd_bearish

            if euphoric and momentum_breaking:
                logger.info("FADE STRATEGY TRIGGERED! Sentiment is euphoric and momentum is breaking.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error evaluating Fade Strategy technicals: {e}")
            return False

    def generate_signal(self, ticker: str, current_score: float, technical_data: pd.Series, base_qty: int, cvar: float) -> dict:
        """
        Returns a formatted short signal if the strategy triggers, otherwise None.
        """
        if self.evaluate(current_score, technical_data):
            # We enforce a SELL (short) order for the Fade Strategy
            signal = {
                "ticker": ticker.upper(),
                "side": "SELL",
                "quantity": base_qty,
                "order_type": "MARKET",
                "target_cvar_allocation": cvar,
                "strategy": "FadeStrategy"
            }
            return signal
        return None
