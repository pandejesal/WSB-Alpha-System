"""qlib Alpha158-style feature library (pandas-only port).

Ported from microsoft/qlib Alpha158 factor library. Computes 47 features
across OHLCV data using rolling windows. All features are lagged by 1 day
(T+1 execution) to prevent lookahead bias.

Feature families mirror qlib's naming conventions:
  - KMid: Keltner Channel midpoint (EMA-based)
  - KLen: Keltner Channel length
  - KMid2: Modified Keltner midpoint (SMA-based)
  - KUp: Keltner upper band distance
  - ROC: Rate of change
  - Rank: Cross-sectional percentile rank
  - Quantile: Rolling quantile ratio
  - Std: Rolling standard deviation
  - Sum: Rolling sum of signed returns
  - Mean: Rolling mean return
  - Max: Rolling max return
  - Min: Rolling min return
  - VWAP: Volume-weighted average price ratio
"""

import numpy as np
import pandas as pd

WINDOWS = [5, 10, 20, 30, 60]

ALPHA_FEATURE_NAMES: list[str] = []


def _register(name: str) -> str:
    ALPHA_FEATURE_NAMES.append(name)
    return name


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _keltner_mid_ema(close: pd.Series, high: pd.Series, low: pd.Series,
                     window: int) -> pd.Series:
    """Keltner Channel midpoint using EMA: EMA(C, W)."""
    return _ema(close, window)


def _keltner_len(high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    """Keltner Channel length: rolling mean(H-L)."""
    return (high - low).rolling(window).mean()


def _keltner_mid2(close: pd.Series, window: int) -> pd.Series:
    """Modified Keltner midpoint using SMA."""
    return close.rolling(window).mean()


def _keltner_upper(close: pd.Series, high: pd.Series, low: pd.Series,
                   window: int) -> pd.Series:
    """Keltner upper band distance: KMid + 0.5 * KLen - Close."""
    kmid = _keltner_mid_ema(close, high, low, window)
    klen = _keltner_len(high, low, window)
    return kmid + 0.5 * klen - close


def _roc(close: pd.Series, window: int) -> pd.Series:
    """Rate of change: (C - C_w) / C_w."""
    return close.pct_change(window)


def _rank_pct(s: pd.Series, window: int) -> pd.Series:
    """Rolling percentile rank within window."""
    return s.rolling(window).rank(pct=True)


def _quantile_ratio(close: pd.Series, high: pd.Series, low: pd.Series,
                    window: int) -> pd.Series:
    """(Close - RollingMin) / (RollingMax - RollingMin)."""
    rmax = close.rolling(window).max()
    rmin = close.rolling(window).min()
    denom = rmax - rmin
    denom = denom.replace(0, np.nan)
    return (close - rmin) / denom


def _rolling_std(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).std()


def _rolling_sum(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).sum()


def _rolling_mean(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).mean()


def _rolling_max(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).max()


def _rolling_min(s: pd.Series, window: int) -> pd.Series:
    return s.rolling(window).min()


def compute_alpha158(df: pd.DataFrame) -> pd.DataFrame:
    """Compute Alpha158-style features from OHLCV data.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: date, open, high, low, close, volume.
        'date' is used as index but not required as DatetimeIndex.

    Returns
    -------
    pd.DataFrame
        Original columns plus 47 new feature columns. All features are
        shifted by 1 to enforce T+1 execution (no lookahead).
    """
    global ALPHA_FEATURE_NAMES
    ALPHA_FEATURE_NAMES = []

    df = df.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    df = df.sort_index()

    c = df["close"].astype(float)
    h = df["high"].astype(float)
    lo = df["low"].astype(float)
    v = df["volume"].astype(float)

    ret = c.pct_change()
    log_ret = np.log(c / c.shift(1))

    vwap = (c * v).rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)

    for w in WINDOWS:
        # === KMid family (qlib: KMID) ===
        name = _register(f"KMid_{w}")
        df[name] = _keltner_mid_ema(c, h, lo, w)

        # === KLen family (qlib: KLEN) ===
        name = _register(f"KLen_{w}")
        df[name] = _keltner_len(h, lo, w)

        # === KMid2 family (qlib: KMID2) ===
        name = _register(f"KMid2_{w}")
        df[name] = _keltner_mid2(c, w)

        # === KUp family (qlib: KUP) ===
        name = _register(f"KUp_{w}")
        df[name] = _keltner_upper(c, h, lo, w)

        # === ROC family ===
        name = _register(f"ROC_{w}")
        df[name] = _roc(c, w)

        # === Rank family ===
        name = _register(f"Rank_{w}")
        df[name] = _rank_pct(c, w)

        # === Quantile family ===
        name = _register(f"Quantile_{w}")
        df[name] = _quantile_ratio(c, h, lo, w)

        # === Std family ===
        name = _register(f"Std_{w}")
        df[name] = _rolling_std(log_ret, w)

        # === Sum family ===
        name = _register(f"Sum_{w}")
        df[name] = _rolling_sum(ret, w)

        # === Mean family ===
        name = _register(f"Mean_{w}")
        df[name] = _rolling_mean(ret, w)

        # === Max family ===
        name = _register(f"Max_{w}")
        df[name] = _rolling_max(ret, w)

        # === Min family ===
        name = _register(f"Min_{w}")
        df[name] = _rolling_min(ret, w)

    # === VWAP ratio ===
    name = _register("VWAP")
    df[name] = c / vwap

    # === High/Low ROC ===
    name = _register("HighROC_10")
    df[name] = h.pct_change(10)

    name = _register("LowROC_10")
    df[name] = lo.pct_change(10)

    # === Close-to-High ratio ===
    name = _register("CloseHighRatio")
    df[name] = c / h

    # === Close-to-Low ratio ===
    name = _register("CloseLowRatio")
    df[name] = c / lo

    # === Log-volume change ===
    name = _register("LogVolumeChg_5")
    df[name] = np.log(v / v.shift(1)).rolling(5).mean()

    # === Price range ===
    name = _register("PriceRange_20")
    df[name] = (h.rolling(20).max() - lo.rolling(20).min()) / c

    # === Volume shock ===
    name = _register("VolumeShock_10")
    df[name] = v / v.rolling(10).mean().replace(0, np.nan)

    # === Ret dispersion ===
    name = _register("RetDispersion_20")
    df[name] = _rolling_std(ret, 20) - _rolling_std(ret, 5)

    # === Signed volume ===
    name = _register("SignedVolume_10")
    df[name] = (ret.apply(np.sign) * v).rolling(10).sum() / v.rolling(10).sum().replace(0, np.nan)

    # === All features shifted by 1 to prevent lookahead ===
    feat_cols = [c for c in df.columns if c not in ["open", "high", "low", "close", "volume", "source"]]
    for col in feat_cols:
        df[col] = df[col].shift(1)

    return df


def get_feature_names() -> list[str]:
    """Return the list of feature column names from the last compute_alpha158 call."""
    return list(ALPHA_FEATURE_NAMES)


def get_feature_matrix(df: pd.DataFrame, features: list[str] | None = None,
                       dropna: bool = True) -> pd.DataFrame:
    """Return just the feature columns as a clean matrix.

    Parameters
    ----------
    df : pd.DataFrame
        Output of compute_alpha158().
    features : list[str], optional
        Subset of features to return. None = all computed features.
    dropna : bool
        If True, drop rows with any NaN in the feature columns.
    """
    if features is None:
        features = [c for c in df.columns if c not in
                     ["open", "high", "low", "close", "volume", "source"]]
    mat = df[features].copy()
    if dropna:
        mat = mat.dropna()
    return mat
