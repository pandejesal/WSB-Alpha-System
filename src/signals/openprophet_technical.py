"""OpenProphet technical-analysis port (Python / pandas).

Source: https://github.com/JakeNesler/OpenProphet
  services/technical_analysis.go (324 lines)

Ported 1:1 (same indicator set, same vote weights, same HOLD-by-default
threshold of +/-1):
  SMA20 / SMA50, RSI-14 (simple-average method, 50.0 neutral when
  under-sampled, 100.0 when avgLoss == 0), momentum 1d/5d, volume
  current/20d-average ratio with 1.5/0.5 trend bands, vote weights
  (price-vs-SMA20 15, SMA20-vs-SMA50 20, RSI 25x2, MACD histogram 15,
  5d-momentum 10, volume>1.2 confirmation +5), BUY needs buyScore >
  sellScore+1 and vice versa, confidence capped at 100.

One deliberate fix: upstream MACD "signal line" is `ema12 * 0.85`, a
placeholder hack, not a signal line. This port computes a real 9-period
EMA of the MACD line over the series. Documented in docs/OPENPROPHET_PORT.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

RSI_PERIOD = 14
SMA_FAST = 20
SMA_SLOW = 50
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
VOL_WINDOW = 20


@dataclass
class AnalysisResult:
    symbol: str
    current_price: float
    sma20: float = 0.0
    sma50: float = 0.0
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    mom_1d_pct: float = 0.0
    mom_5d_pct: float = 0.0
    vol_ratio: float = 0.0
    vol_trend: str = "stable"
    signal: str = "HOLD"
    confidence: float = 0.0


def _sma(s: pd.Series, period: int) -> float:
    if len(s) < period:
        return 0.0
    return float(s.iloc[-period:].mean())


def _rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    """Simple-average RSI matching upstream CalculateRSI (not Wilder)."""
    if len(close) < period + 1:
        return 50.0
    window = close.iloc[-(period + 1):]
    deltas = window.diff().iloc[1:]
    gains = deltas.clip(lower=0.0)
    losses = (-deltas).clip(lower=0.0)
    avg_gain = float(gains.mean())
    avg_loss = float(losses.mean())
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()


def _macd(close: pd.Series) -> Optional[tuple]:
    if len(close) < MACD_SLOW:
        return None
    macd_line = _ema(close, MACD_FAST) - _ema(close, MACD_SLOW)
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])


def _volume(volume: Optional[pd.Series]) -> tuple:
    if volume is None or len(volume) < VOL_WINDOW:
        return 0.0, "stable"
    cur = float(volume.iloc[-1])
    avg = float(volume.iloc[-VOL_WINDOW:].mean())
    ratio = cur / avg if avg else 0.0
    trend = "stable"
    if ratio > 1.5:
        trend = "increasing"
    elif ratio < 0.5:
        trend = "decreasing"
    return ratio, trend


def analyze(symbol: str, bars: pd.DataFrame) -> AnalysisResult:
    """bars needs `close` (+ optional `volume`); oldest -> newest, no lookahead
    (every indicator uses only history up to the last bar)."""
    close = bars["close"].astype(float).reset_index(drop=True)
    volume = bars["volume"].astype(float).reset_index(drop=True) if "volume" in bars else None
    res = AnalysisResult(symbol=symbol, current_price=float(close.iloc[-1]))
    if len(close) >= SMA_FAST:
        res.sma20 = _sma(close, SMA_FAST)
    if len(close) >= SMA_SLOW:
        res.sma50 = _sma(close, SMA_SLOW)
    if len(close) >= RSI_PERIOD + 1:
        res.rsi = _rsi(close)
    macd = _macd(close)
    if macd:
        res.macd, res.macd_signal = macd
        res.macd_histogram = res.macd - res.macd_signal
    if len(close) >= 6:
        c, d1, d5 = close.iloc[-1], close.iloc[-2], close.iloc[-6]
        res.mom_1d_pct = float((c - d1) / d1 * 100) if d1 else 0.0
        res.mom_5d_pct = float((c - d5) / d5 * 100) if d5 else 0.0
    res.vol_ratio, res.vol_trend = _volume(volume)
    res.signal, res.confidence = _vote(res)
    return res


def _vote(r: AnalysisResult) -> tuple:
    buy = 0
    sell = 0
    conf = 0.0
    if r.sma20 > 0:
        if r.current_price > r.sma20:
            buy += 1
        else:
            sell += 1
        conf += 15
    if r.sma50 > 0:
        if r.sma20 > r.sma50:
            buy += 1
        elif r.sma20 < r.sma50:
            sell += 1
        conf += 20
    if r.rsi > 0:
        if r.rsi < 30:
            buy += 2
            conf += 25
        elif r.rsi > 70:
            sell += 2
            conf += 25
        else:
            conf += 10
    if r.macd_histogram != 0.0 or (r.macd != 0.0):
        if r.macd_histogram > 0:
            buy += 1
        else:
            sell += 1
        conf += 15
    if r.mom_5d_pct > 5:
        buy += 1
        conf += 10
    elif r.mom_5d_pct < -5:
        sell += 1
        conf += 10
    if r.vol_ratio > 1.2:
        conf += 5
    conf = min(conf, 100.0)
    if buy > sell + 1:
        return "BUY", conf
    if sell > buy + 1:
        return "SELL", conf
    return "HOLD", conf
