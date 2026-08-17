import yfinance as yf
import pandas as pd
import numpy as np

def get_us_momentum_top5_signal(data: pd.DataFrame, tickers: list[str]) -> dict:
    signal_data = {}

    if data is None or data.empty:
         signal_data["data_unavailable"] = True
         return signal_data

    closes = data['Close'] if 'Close' in data else data
    if len(closes) > 147:
         current_idx = -1
         skip_idx = current_idx - 21
         lookback_idx = skip_idx - 126

         momenta = {}
         for t in tickers:
             if t in closes and pd.notna(closes[t].iloc[skip_idx]) and pd.notna(closes[t].iloc[lookback_idx]):
                 p_skip = closes[t].iloc[skip_idx]
                 p_lookback = closes[t].iloc[lookback_idx]
                 if p_lookback > 0:
                     momenta[t] = float((p_skip / p_lookback) - 1)

         sorted_mom = sorted(momenta.items(), key=lambda x: x[1], reverse=True)
         signal_data["top_5"] = [t for t, _ in sorted_mom[:5]]
         signal_data["momenta"] = {t: round(m, 4) for t, m in sorted_mom}
    else:
         signal_data["data_unavailable"] = True

    return signal_data


def get_spy_sma200_signal(data: pd.DataFrame) -> dict:
    signal_data = {}

    if data is None or data.empty or len(data) < 200:
        signal_data["data_unavailable"] = True
        return signal_data

    close = data['Close'] if 'Close' in data else data
    if isinstance(close, pd.DataFrame): close = close.squeeze()

    sma200 = close.rolling(window=200).mean().iloc[-1]
    last_close = close.iloc[-1]

    signal_data["sma200"] = float(sma200)
    signal_data["last_close"] = float(last_close)
    signal_data["signal"] = "BUY" if last_close > sma200 else "CASH"

    return signal_data


def get_spy_rsi2_signal(data: pd.DataFrame) -> dict:
    signal_data = {}

    if data is None or data.empty or len(data) < 5:
        signal_data["data_unavailable"] = True
        return signal_data

    close = data['Close'] if 'Close' in data else data
    if isinstance(close, pd.DataFrame): close = close.squeeze()

    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=2).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    last_rsi = rsi.iloc[-1]
    sma5 = close.rolling(window=5).mean().iloc[-1]
    last_close = close.iloc[-1]

    signal_data["rsi2"] = float(last_rsi) if pd.notna(last_rsi) else None
    signal_data["sma5"] = float(sma5) if pd.notna(sma5) else None
    signal_data["last_close"] = float(last_close)

    return signal_data


def get_btc_vol_target_sma100_signal(data: pd.DataFrame) -> dict:
    signal_data = {}

    if data is None or data.empty or len(data) < 100:
        signal_data["data_unavailable"] = True
        return signal_data

    close = data['Close'] if 'Close' in data else data
    if isinstance(close, pd.DataFrame): close = close.squeeze()

    returns = close.pct_change()
    realized_vol = returns.rolling(window=30).std() * np.sqrt(365)
    last_vol = realized_vol.iloc[-1]
    sma100 = close.rolling(window=100).mean().iloc[-1]
    last_close = close.iloc[-1]

    signal_data["realized_vol"] = float(last_vol) if pd.notna(last_vol) else None
    signal_data["sma100"] = float(sma100) if pd.notna(sma100) else None
    signal_data["last_close"] = float(last_close)

    exposure = min(0.30 / last_vol, 1.0) if pd.notna(last_vol) and last_vol > 0 else 0
    signal_data["target_exposure"] = float(exposure) if last_close > sma100 else 0.0

    return signal_data


def get_dual_momentum_signal(data: pd.DataFrame, tickers: list[str] = None) -> dict:
    signal_data = {}

    if tickers is None:
        tickers = ["SPY", "QQQ"]

    if data is None or data.empty or len(data) < 42:
        signal_data["data_unavailable"] = True
        return signal_data

    closes = data['Close'] if 'Close' in data else data

    current_idx = -1
    skip_idx = current_idx - 21
    lookback_idx = skip_idx - 21

    momenta = {}
    for t in tickers:
        if t in closes and pd.notna(closes[t].iloc[skip_idx]) and pd.notna(closes[t].iloc[lookback_idx]):
            p_skip = closes[t].iloc[skip_idx]
            p_lookback = closes[t].iloc[lookback_idx]
            if p_lookback > 0:
                momenta[t] = float((p_skip / p_lookback) - 1)

    signal_data["momenta"] = {t: round(m, 4) for t, m in momenta.items()}
    spy_mom = momenta.get("SPY", -1)
    qqq_mom = momenta.get("QQQ", -1)

    if spy_mom > 0 or qqq_mom > 0:
        signal_data["signal"] = "SPY" if spy_mom > qqq_mom else "QQQ"
    else:
        signal_data["signal"] = "AGG"

    return signal_data


import os
import time
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from yfinance.exceptions import YFRateLimitError

_orig_download = yf.download

# Use a single persistent Session across calls
_shared_session = None

def _get_shared_session():
    global _shared_session
    if _shared_session is None:
        _shared_session = requests.Session()
        adapter_retries = int(os.environ.get("OPS_FETCH_ADAPTER_RETRIES", "3"))
        adapter_backoff = float(os.environ.get("OPS_FETCH_ADAPTER_BACKOFF", "2.0"))

        retry_strategy = Retry(
            total=adapter_retries,
            connect=adapter_retries,
            read=adapter_retries,
            backoff_factor=adapter_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _shared_session.mount("https://", adapter)
        _shared_session.mount("http://", adapter)
    return _shared_session

def _fetch_with_retry(*args, **kwargs):
    retries = int(os.environ.get("OPS_FETCH_RETRIES", "4"))
    backoff_base = float(os.environ.get("OPS_FETCH_BACKOFF_BASE", "30.0"))

    kwargs["session"] = _get_shared_session()

    attempt = 1
    while attempt <= retries:
        try:
            return _orig_download(*args, **kwargs)
        except Exception as e:
            err_name = type(e).__name__
            is_transient = err_name in ["YFRateLimitError", "ConnectionError", "ReadTimeout"]
            if not is_transient or attempt == retries:
                raise e

            delay = backoff_base * (2 ** (attempt - 1))
            jitter = delay * 0.2
            delay += random.uniform(-jitter, jitter)

            print(f"Fetch failed (attempt {attempt}), waited {delay:.2f}s, error class: {err_name}")

            time.sleep(max(0, delay))
            attempt += 1

yf.download = _fetch_with_retry
