
import numpy as np
import pandas as pd
from numba import njit


@njit
def calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    atr = np.zeros(n)
    if n == 0:
        return atr
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = np.abs(high[i] - close[i-1])
        lc = np.abs(low[i] - close[i-1])
        tr[i] = max(hl, hc, lc)

    atr[0] = tr[0]
    for i in range(1, period):
        atr[i] = np.mean(tr[:i+1])

    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr

@njit
def find_swing_points(high: np.ndarray, low: np.ndarray) -> tuple:
    n = len(high)
    swing_highs = np.zeros(n, dtype=np.bool_)
    swing_lows = np.zeros(n, dtype=np.bool_)
    # Standard 5-bar fractal: k is max/min of k-2, k-1, k, k+1, k+2
    for k in range(2, n-2):
        if high[k] > high[k-1] and high[k] > high[k-2] and high[k] > high[k+1] and high[k] > high[k+2]:
            swing_highs[k] = True
        if low[k] < low[k-1] and low[k] < low[k-2] and low[k] < low[k+1] and low[k] < low[k+2]:
            swing_lows[k] = True
    return swing_highs, swing_lows

@njit
def detect_order_blocks_and_entries(
    open_p: np.ndarray, high: np.ndarray, low: np.ndarray, close: np.ndarray, atr: np.ndarray,
    swing_highs: np.ndarray, swing_lows: np.ndarray
):
    n = len(close)

    # States: 0 = Untouched, 1 = Touched, 2 = Mitigated/Invalidated
    ob_state = np.full(n, 2, dtype=np.int32)
    ob_type = np.zeros(n, dtype=np.int32) # 1 = Bullish, -1 = Bearish
    ob_high = np.zeros(n, dtype=np.float64)
    ob_low = np.zeros(n, dtype=np.float64)

    # Results Format: [Index, Type (1/-1), EntryPrice, StopLoss, TakeProfit]
    max_entries = n // 2
    out_entries = np.zeros((max_entries, 5), dtype=np.float64)
    entry_count = 0

    for i in range(2, n):
        # 1. Detect New Order Blocks
        # Bullish OB (Down-close candidate at i-2, Displacement at i-1, FVG at i)
        if close[i-2] < open_p[i-2]:
            disp_body = close[i-1] - open_p[i-1]
            if disp_body > atr[i-1]: # Momentum Threshold (Displacement body > 1.0 ATR)  # noqa: SIM102 - Nested if is more readable here
                if low[i] > high[i-2]: # FVG Creation
                    rng = high[i-2] - low[i-2]
                    if rng >= 0.1 * atr[i-2]: # Size Filter
                        ob_type[i-2] = 1
                        ob_high[i-2] = high[i-2]
                        ob_low[i-2] = low[i-2]
                        ob_state[i-2] = 0

        # Bearish OB (Up-close candidate at i-2, Displacement at i-1, FVG at i)
        if close[i-2] > open_p[i-2]:
            disp_body = open_p[i-1] - close[i-1]
            if disp_body > atr[i-1]: # Momentum Threshold  # noqa: SIM102 - Nested if is more readable here
                if high[i] < low[i-2]: # FVG Creation
                    rng = high[i-2] - low[i-2]
                    if rng >= 0.1 * atr[i-2]: # Size Filter
                        ob_type[i-2] = -1
                        ob_high[i-2] = high[i-2]
                        ob_low[i-2] = low[i-2]
                        ob_state[i-2] = 0

        # 2. Check active OBs for Mitigation, Invalidation, and Entry Triggers
        # We need to process from older to newer. j represents the OB creation index.
        for j in range(i-1):
            if ob_state[j] == 2:
                continue

            if ob_type[j] == 1: # Bullish OB
                if ob_state[j] == 0:  # noqa: SIM102 - Nested if is more readable here
                    if low[i] <= ob_high[j]: # Wick touches OB
                        if close[i] < ob_low[j]:
                            ob_state[j] = 2 # Invalidated due to structural break
                        else:
                            ob_state[j] = 1 # Marked as touched

                # Note: State could become 1 in the above block, so check again
                if ob_state[j] == 1:
                    if close[i] < ob_low[j]:
                        ob_state[j] = 2 # Momentum Invalidation
                    else:
                        # Require Rejection & Bullish Engulfing Confirmation
                        is_engulfing = (close[i-1] < open_p[i-1]) and (close[i] > open_p[i]) and (close[i] > open_p[i-1])

                        wick_i = min(open_p[i], close[i]) - low[i]
                        wick_prev = min(open_p[i-1], close[i-1]) - low[i-1]
                        body_i = close[i] - open_p[i]
                        body_prev = open_p[i-1] - close[i-1]

                        rejection = (wick_i > body_i * 0.5) or (wick_prev > body_prev * 0.5)

                        if is_engulfing and rejection:
                            tp = -1.0
                            # Search for most recent swing high looking backwards
                            for k in range(i-2, -1, -1):
                                if swing_highs[k]:
                                    tp = high[k]
                                    break

                            # Fallback if no swing high is found (unlikely in long data, but possible in start)
                            if tp == -1.0:
                                max_h = -1.0
                                for k in range(max(0, i-50), i):
                                    max_h = max(max_h, high[k])
                                tp = max_h

                            if tp > close[i]: # Only take valid RR
                                out_entries[entry_count, 0] = i
                                out_entries[entry_count, 1] = 1
                                out_entries[entry_count, 2] = close[i]
                                out_entries[entry_count, 3] = ob_low[j]
                                out_entries[entry_count, 4] = tp
                                entry_count += 1
                            ob_state[j] = 2 # Mitigated
                        elif low[i] > ob_high[j]:
                            # Bounced entirely out without triggering an engulfing (wicked in & bounced)
                            ob_state[j] = 2

            elif ob_type[j] == -1: # Bearish OB
                if ob_state[j] == 0 and high[i] >= ob_low[j]:
                    if close[i] > ob_high[j]:
                        ob_state[j] = 2
                    else:
                        ob_state[j] = 1

                if ob_state[j] == 1:
                    if close[i] > ob_high[j]:
                        ob_state[j] = 2
                    else:
                        is_engulfing = (close[i-1] > open_p[i-1]) and (close[i] < open_p[i]) and (close[i] < open_p[i-1])

                        wick_i = high[i] - max(open_p[i], close[i])
                        wick_prev = high[i-1] - max(open_p[i-1], close[i-1])
                        body_i = open_p[i] - close[i]
                        body_prev = close[i-1] - open_p[i-1]

                        rejection = (wick_i > body_i * 0.5) or (wick_prev > body_prev * 0.5)

                        if is_engulfing and rejection:
                            tp = -1.0
                            for k in range(i-2, -1, -1):
                                if swing_lows[k]:
                                    tp = low[k]
                                    break

                            if tp == -1.0:
                                min_l = 1e9
                                for k in range(max(0, i-50), i):
                                    min_l = min(min_l, low[k])
                                tp = min_l

                            if tp != -1.0 and tp < close[i]:
                                out_entries[entry_count, 0] = i
                                out_entries[entry_count, 1] = -1
                                out_entries[entry_count, 2] = close[i]
                                out_entries[entry_count, 3] = ob_high[j]
                                out_entries[entry_count, 4] = tp
                                entry_count += 1
                            ob_state[j] = 2 # Mitigated
                        elif high[i] < ob_low[j]:
                            # Bounced entirely out
                            ob_state[j] = 2

    return out_entries[:entry_count]

class OrderBlockDetector:
    """
    Institutional Order Block & Microstructure Module
    Detects unmitigated bullish/bearish order blocks with momentum FVG displacement.
    Triggers strictly on structure-confirmed rejections (Engulfing).
    Vectorized and optimized with Numba for production speed.
    """
    def __init__(self):
        pass

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        open_p = df['Open'].values
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values

        atr = calculate_atr(high, low, close, 14)
        swing_highs, swing_lows = find_swing_points(high, low)

        raw_entries = detect_order_blocks_and_entries(open_p, high, low, close, atr, swing_highs, swing_lows)

        entries = []
        for row in raw_entries:
            idx = int(row[0])
            entries.append({
                'Timestamp': df.index[idx] if isinstance(df.index, pd.DatetimeIndex) else idx,
                'Type': 'LONG' if row[1] == 1 else 'SHORT',
                'Entry_Price': row[2],
                'Stop_Loss': row[3],
                'Take_Profit': row[4]
            })

        return pd.DataFrame(entries)

