from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Accepts an OHLCV dataframe, computes necessary indicators,
        and returns the dataframe augmented with a 'signal' column.
        Signal convention: 1 for Long, -1 for Short, 0 for Flat.
        """
        pass
