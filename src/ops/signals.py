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
import io
import time
import random
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from yfinance.exceptions import YFRateLimitError

_orig_download = yf.download

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

def _retry_wrapper(func, *args, **kwargs):
    retries = int(os.environ.get("OPS_FETCH_RETRIES", "4"))
    backoff_base = float(os.environ.get("OPS_FETCH_BACKOFF_BASE", "30.0"))

    attempt = 1
    while attempt <= retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_name = type(e).__name__
            is_transient = err_name in ["YFRateLimitError", "ConnectionError", "ReadTimeout", "HTTPError"]
            if not is_transient or attempt == retries:
                raise e

            delay = backoff_base * (2 ** (attempt - 1))
            jitter = delay * 0.2
            delay += random.uniform(-jitter, jitter)

            print(f"Fetch failed (attempt {attempt}), waited {delay:.2f}s, error class: {err_name}")

            time.sleep(max(0, delay))
            attempt += 1


def _fetch_single_yahoo_v8(ticker: str):
    session = _get_shared_session()
    # Upper case ticker as-is
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}?range=2y&interval=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
        "Accept": "application/json"
    }
    resp = session.get(url, headers=headers, timeout=10)

    # Transient errors should raise so _retry_wrapper can catch them
    if resp.status_code in [429, 500, 502, 503, 504]:
        resp.raise_for_status()

    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    try:
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None

        timestamps = result[0].get("timestamp", [])
        if not timestamps:
            return None

        quote = result[0].get("indicators", {}).get("quote", [{}])[0]

        df = pd.DataFrame({
            "Date": pd.to_datetime(timestamps, unit="s", utc=True),
            "Open": quote.get("open", []),
            "High": quote.get("high", []),
            "Low": quote.get("low", []),
            "Close": quote.get("close", []),
            "Volume": quote.get("volume", [])
        })

        # Drop rows where Close is NaN
        df = df.dropna(subset=["Close"])
        if df.empty:
            return None

        df.set_index("Date", inplace=True)
        # Convert timezone to naive
        df.index = df.index.tz_localize(None)
        # Sort index
        df = df.sort_index()

        return df
    except Exception:
        return None

def fetch_daily_yahoo_v8(tickers: list[str]) -> dict:
    results = {}
    for t in tickers:
        try:
            res = _retry_wrapper(_fetch_single_yahoo_v8, t)
            results[t] = res
        except Exception as e:
            print(f"Yahoo v8 fetch failed for {t}: {e}")
            results[t] = None
    return results

def _fetch_single_stooq(ticker: str):
    session = _get_shared_session()
    if ticker == 'BTC-USD':
        stooq_sym = 'btcusd'
    else:
        stooq_sym = ticker.lower().replace('.', '-') + '.us'
    url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = session.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    if 'Date,Open,High,Low,Close,Volume' not in resp.text:
        raise ValueError(f"Invalid Stooq data or No data for {ticker}")
    df = pd.read_csv(io.StringIO(resp.text), parse_dates=['Date'])
    df.set_index('Date', inplace=True)
    df = df.sort_index()
    return df

def fetch_daily_stooq(tickers: list[str]) -> dict:
    results = {}
    for t in tickers:
        try:
            results[t] = _retry_wrapper(_fetch_single_stooq, t)
        except Exception as e:
            print(f"Stooq fetch failed for {t}: {e}")
            results[t] = None
    return results

def _hybrid_download(tickers, *args, **kwargs):
    if isinstance(tickers, str):
        tickers_list = [tickers]
        is_string = True
    else:
        tickers_list = list(tickers)
        is_string = False

    if not tickers_list:
        return pd.DataFrame()

    # Priority 1: Yahoo v8 chart API
    v8_data = fetch_daily_yahoo_v8(tickers_list)
    failed_v8_tickers = [t for t, df in v8_data.items() if df is None or df.empty]

    # Priority 2: Stooq fallback
    stooq_data = {}
    failed_stooq_tickers = failed_v8_tickers.copy()
    if failed_v8_tickers:
        stooq_data = fetch_daily_stooq(failed_v8_tickers)
        failed_stooq_tickers = [t for t, df in stooq_data.items() if df is None or df.empty]

    # Priority 3: YF fallback
    yf_data = {}
    if failed_stooq_tickers:
        kwargs["session"] = _get_shared_session()
        try:
            yf_df = _retry_wrapper(_orig_download, failed_stooq_tickers, *args, **kwargs)
            if yf_df is not None and not yf_df.empty:
                for t in failed_stooq_tickers:
                    if isinstance(yf_df.columns, pd.MultiIndex):
                        if ('Close', t) in yf_df.columns:
                            try:
                                df_t = yf_df.xs(t, level=1, axis=1)
                                yf_data[t] = df_t
                            except KeyError:
                                pass
                    else:
                        if len(failed_stooq_tickers) == 1:
                            yf_data[t] = yf_df
        except Exception as e:
            print(f"Fallback YF failed for {failed_stooq_tickers}: {e}")

    frames = []
    for t in tickers_list:
        df = v8_data.get(t)
        if df is None or df.empty:
            df = stooq_data.get(t)
        if df is None or df.empty:
            df = yf_data.get(t)

        if df is not None and not df.empty:
            cols = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
            df = df[cols]
            df.columns = pd.MultiIndex.from_product([df.columns, [t]])
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, axis=1)
    combined = combined.sort_index()
    combined.columns.names = ['Price', 'Ticker']

    if is_string:
        combined.columns = combined.columns.get_level_values(0)

    return combined

yf.download = _hybrid_download
