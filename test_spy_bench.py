import yfinance as yf
import pandas as pd
import numpy as np

dates = pd.date_range(start='2018-01-01', end='2019-02-01', freq='B')
spy_returns = np.random.normal(0.0005, 0.01, len(dates))
spy_prices = 100 * np.exp(np.cumsum(spy_returns))
spy_data = pd.DataFrame({'Close': spy_prices}, index=dates)

spy_df = spy_data.copy()
spy_df['EMA_200'] = spy_df['Close'].ewm(span=200, adjust=False).mean()
spy_df = spy_df[spy_df.index >= pd.to_datetime('2019-01-01')]
print(len(spy_df), "rows for 2019 onwards")
print("First row EMA_200:", spy_df['EMA_200'].iloc[0])
