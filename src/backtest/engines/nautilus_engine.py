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
            logger.info("NautilusTrader not installed or incompatible. Using internal simulation engine on provided real data.")

    def run_sim(self, strategy_spec: dict, historical_data: pd.DataFrame) -> pd.DataFrame:
        df = historical_data.copy()

        if df.empty:
            return pd.DataFrame()

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])

        # Fallback missing real signal logic; returning empty trades to avoid fabricated data.
        logger.warning("NautilusTrader fallback missing real signal logic; returning empty trades to avoid fabricated data.")
        return pd.DataFrame()
