import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.data.providers.alpaca_data_provider import AlpacaDataProvider
from src.data.providers.tiingo_provider import TiingoProvider
from src.data.providers.binance_public_provider import BinancePublicProvider
from src.data.providers.chain import DataProviderChain
from src.data.providers.yfinance_provider import YFinanceProvider

# Sample OHLCV data representing Alpaca schema
def get_mock_alpaca_bars():
    df = pd.DataFrame({
        'symbol': ['AAPL', 'AAPL'],
        'timestamp': [pd.Timestamp('2023-01-01', tz='UTC'), pd.Timestamp('2023-01-02', tz='UTC')],
        'open': [100.0, 101.0],
        'high': [105.0, 106.0],
        'low': [95.0, 96.0],
        'close': [100.5, 102.0],
        'volume': [1000, 2000]
    }).set_index('symbol')
    mock_bars = MagicMock()
    mock_bars.df = df
    return mock_bars

# Mock the Tiingo response
def get_mock_tiingo_json():
    return [
        {
            "date": "2023-01-01T00:00:00.000Z",
            "adjOpen": 100.0,
            "adjHigh": 105.0,
            "adjLow": 95.0,
            "adjClose": 100.5,
            "adjVolume": 1000
        }
    ]

# Mock the Binance response
def get_mock_binance_json():
    # [Open time, Open, High, Low, Close, Volume, ...]
    return [
        [
            1672531200000, # 2023-01-01
            "16000.00",
            "16500.00",
            "15900.00",
            "16400.00",
            "100.0",
            1672617599999,
            "10000.0",
            1000,
            "50.0",
            "5000.0",
            "0"
        ]
    ]


@patch('src.data.providers.alpaca_data_provider.StockHistoricalDataClient')
def test_alpaca_provider(mock_stock_client):
    mock_client_instance = mock_stock_client.return_value
    mock_client_instance.get_stock_bars.return_value = get_mock_alpaca_bars()

    provider = AlpacaDataProvider()
    # Force the mock client
    provider.stock_client = mock_client_instance
    provider.crypto_client = None

    df = provider.fetch_ohlcv(['AAPL'], '2023-01-01', '2023-01-02')

    assert not df.empty
    assert 'Ticker' in df.columns
    assert 'Date' in df.columns
    assert df.iloc[0]['Ticker'] == 'AAPL'
    assert df.iloc[0]['Open'] == 100.0

@patch('os.environ.get')
@patch('requests.get')
def test_tiingo_provider(mock_get, mock_env):
    mock_env.return_value = 'mock_key'
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = get_mock_tiingo_json()
    mock_get.return_value = mock_response

    provider = TiingoProvider()
    df = provider.fetch_ohlcv(['AAPL'], '2023-01-01', '2023-01-02')

    assert not df.empty
    assert df.iloc[0]['Ticker'] == 'AAPL'
    assert df.iloc[0]['Open'] == 100.0
    mock_get.assert_called_once()

@patch('requests.get')
def test_binance_provider(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = get_mock_binance_json()
    mock_get.return_value = mock_response

    provider = BinancePublicProvider()

    # Should ignore equities
    df_empty = provider.fetch_ohlcv(['AAPL'], '2023-01-01', '2023-01-02')
    assert df_empty.empty

    df = provider.fetch_ohlcv(['BTC-USD'], '2023-01-01', '2023-01-02')
    assert not df.empty
    assert df.iloc[0]['Ticker'] == 'BTC-USD'
    assert df.iloc[0]['Open'] == 16000.0

@patch.object(AlpacaDataProvider, 'fetch_ohlcv')
@patch.object(TiingoProvider, 'fetch_ohlcv')
def test_provider_chain(mock_tiingo, mock_alpaca):
    # Simulate Alpaca returning empty (fails)
    mock_alpaca.return_value = pd.DataFrame()

    # Simulate Tiingo succeeding
    tiingo_df = pd.DataFrame({
        'Ticker': ['AAPL'],
        'Date': [pd.Timestamp('2023-01-01')],
        'Open': [100.0],
        'High': [105.0],
        'Low': [95.0],
        'Close': [100.5],
        'Volume': [1000]
    })
    mock_tiingo.return_value = tiingo_df

    # Mock Cache Engine
    mock_cache = MagicMock()
    mock_cache.determine_missing_ranges.return_value = {'AAPL': [('2023-01-01', '2023-01-02')]}
    mock_cache.get_ohlcv.return_value = pd.DataFrame()

    chain = DataProviderChain(cache_engine=mock_cache)
    # Prevent the other providers from running by mocking them
    for provider in chain.providers:
        if isinstance(provider, BinancePublicProvider):
            provider.fetch_ohlcv = MagicMock(return_value=pd.DataFrame())
        elif "YFinanceProvider" in str(type(provider)):
            provider.fetch_ohlcv = MagicMock(return_value=pd.DataFrame())

    df = chain.fetch_ohlcv(['AAPL'], '2023-01-01', '2023-01-02')

    assert not df.empty
    assert df.iloc[0]['Ticker'] == 'AAPL'
    assert df.iloc[0]['Open'] == 100.0
    mock_alpaca.assert_called_once()
    mock_tiingo.assert_called_once()

@patch.object(AlpacaDataProvider, 'fetch_ohlcv')
@patch.object(TiingoProvider, 'fetch_ohlcv')
@patch.object(BinancePublicProvider, 'fetch_ohlcv')
@patch.object(YFinanceProvider, 'fetch_ohlcv')
def test_yfinance_last_resort(mock_yf, mock_binance, mock_tiingo, mock_alpaca):
    # Simulate all upstream failing
    mock_alpaca.return_value = pd.DataFrame()
    mock_tiingo.return_value = pd.DataFrame()
    mock_binance.return_value = pd.DataFrame()

    yf_df = pd.DataFrame({
        'Ticker': ['AAPL'],
        'Date': [pd.Timestamp('2023-01-01')],
        'Open': [100.0],
        'High': [105.0],
        'Low': [95.0],
        'Close': [100.5],
        'Volume': [1000]
    })
    mock_yf.return_value = yf_df

    mock_cache = MagicMock()
    mock_cache.determine_missing_ranges.return_value = {'AAPL': [('2023-01-01', '2023-01-02')]}
    mock_cache.get_ohlcv.return_value = pd.DataFrame()

    chain = DataProviderChain(cache_engine=mock_cache)

    df = chain.fetch_ohlcv(['AAPL'], '2023-01-01', '2023-01-02')

    assert not df.empty
    assert df.iloc[0]['Ticker'] == 'AAPL'
    assert df.iloc[0]['Open'] == 100.0
    mock_alpaca.assert_called_once()
    mock_tiingo.assert_called_once()
    mock_binance.assert_called_once()
    mock_yf.assert_called_once()