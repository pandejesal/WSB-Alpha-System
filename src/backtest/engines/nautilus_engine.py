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
            logger.info("NautilusTrader not installed or incompatible.")

    def run_sim(self, strategy_spec: dict, historical_data: pd.DataFrame) -> pd.DataFrame:
        if not self.use_nautilus:
            logger.warning("NautilusTrader is missing. Failing fast and returning empty trades DataFrame.")
            return pd.DataFrame()

        df = historical_data.copy()

        if df.empty:
            return pd.DataFrame()

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])

        # Returning empty DataFrame if NautilusTrader is installed but run_sim is called
        # (the real integration logic goes here)
        return pd.DataFrame()
