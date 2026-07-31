import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class MacroRegimeFilter:
    """
    Fetches $SPY daily data to determine the macro market regime.
    If SPY is below its 200-day Simple Moving Average (SMA), the regime is "BEAR".
    """

    def __init__(self, ticker: str = "SPY"):
        self.ticker = ticker
        self.regime = "BULL"
        self.sma_200 = None
        self.current_price = None

    def fetch_regime(self) -> str:
        """Fetches SPY data, calculates 200-day SMA, and returns the regime."""
        try:
            logger.info(f"Fetching macro data for {self.ticker}")
            # Fetch 1 year of data to comfortably get 200 trading days
            data = yf.download(self.ticker, period="1y", interval="1d", progress=False)

            if len(data) < 200:
                logger.warning("Not enough data to calculate 200-day SMA. Defaulting to BULL.")
                return self.regime

            # 'Close' column can be a Series or DataFrame depending on yfinance version/call
            close_prices = data['Close']
            if isinstance(close_prices, pd.DataFrame):
                 close_prices = close_prices[self.ticker]

            self.sma_200 = close_prices.rolling(window=200).mean().iloc[-1]
            self.current_price = close_prices.iloc[-1]

            # Float conversion in case it's a pandas scalar type
            self.sma_200 = float(self.sma_200)
            self.current_price = float(self.current_price)

            if self.current_price < self.sma_200:
                self.regime = "BEAR"
            else:
                self.regime = "BULL"

            logger.info(f"Macro Regime: {self.regime} (SPY Price: {self.current_price:.2f}, 200 SMA: {self.sma_200:.2f})")
            return self.regime

        except Exception as e:
            logger.error(f"Error fetching macro regime: {e}")
            return "BULL" # Default to bull on failure

    def apply_filter(self, trade_signal: dict) -> dict:
        """
        Applies the macro regime rules to a trade signal.
        - If BEAR:
          - Reject if only 2-out-of-3 confluence (weak).
          - Slash allocation by 50% if 3-out-of-3 (strong).
        """
        if self.regime == "BULL":
            return trade_signal # No penalty

        # BEAR Regime logic
        confluence_score = trade_signal.get('confluence_score', 0)

        if confluence_score == 2:
            logger.info(f"BEAR Regime: Rejecting borderline trade for {trade_signal.get('ticker')} (Score: 2)")
            trade_signal['status'] = 'REJECTED'
            trade_signal['reject_reason'] = 'BEAR_REGIME_WEAK_CONFLUENCE'
        elif confluence_score >= 3:
            logger.info(f"BEAR Regime: Slashing allocation by 50% for {trade_signal.get('ticker')} (Score: {confluence_score})")
            trade_signal['quantity'] = max(1, int(trade_signal.get('quantity', 0) * 0.5))
            if 'target_cvar_allocation' in trade_signal:
                trade_signal['target_cvar_allocation'] *= 0.5

        return trade_signal
