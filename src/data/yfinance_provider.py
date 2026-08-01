import pandas as pd
import yfinance as yf
from src.data.base_provider import MarketDataProvider

class YFinanceProvider(MarketDataProvider):
    def get_historical_data(self, ticker: str, start_date: str, end_date: str, timeframe: str = '1d') -> pd.DataFrame:
        df = yf.download(ticker, start=start_date, end=end_date, interval=timeframe, progress=False)
        return df
