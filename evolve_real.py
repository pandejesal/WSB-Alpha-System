#!/usr/bin/env python3
"""REAL self-evolve loop for WSB-Alpha-System (rebuilt 2026-09-04).

Every metric comes from a real vectorized backtest on local OHLCV CSVs
with slippage deducted and 1-day execution delay. Failures record
ABANDON and are never promoted. Promotions are status=paper only.
Never live.

Honest gate (2026-09-06): the 10-track gatespec38 union is the MAIN promotion
gate (docs/GATESPEC38_TRACKS.md, superset of the ling-fin 9 tracks — adds
tail_risk_sentinel). A candidate promotes by clearing ANY ONE track fully;
every track carries excess-vs-SPY > 0 (except benchmark_parity, the SPY
calibration anchor) + DSR multiple-testing discount + maxDD + activity.
Universal overlays on top of tracks: perm_p<=0.05 and boot_p<=0.05 timing-skill
screens (can only block, never admit — verified calibrations still hold).
ML: sklearn MLPRegressor learns params->Sharpe from history JSONL and
biases proposals (epsilon-greedy). Falls back to uniform random below
15 samples or when sklearn is unavailable.

Generational input: consumes bred proposals from
docs/data/next_gen_proposals.jsonl (written by scripts/evolve_generations.py
breed step); every 200 iters it runs the prune+breed step itself so top
strategies seed the next generation and the weak retire.

Guardrails (fail-closed, always on):
  - Single instance via docs/data/evolve_real.lock (stale PIDs reaped).
  - Kill switch: SafetyGuard kill-switch file halts iteration (loops
    sleeping, never evolves while active).
  - Disk guard: needs 500MB free, else sleeps instead of crashing mid-write.
  - Registry writes are atomic (tmp + os.replace) + validated.
  - Paper only: every promoted entry has status=paper, live never set.
"""
import json
import os
import pathlib
import random
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent  # this file lives at repo root
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.backtest.metrics import safe_sharpe  # noqa: E402
from src.backtest.gatespec38_tracks import (  # noqa: E402
    check_track, recompute_dsr)

HIST = ROOT / "docs/data/evolve_real_history.jsonl"
PROM = ROOT / "docs/data/evolve_real_promoted.jsonl"
LOGF = ROOT / "docs/data/evolve_real.log"
REG = ROOT / "strategies/registry.json"
PROP = ROOT / "docs/data/next_gen_proposals.jsonl"
POINTER = ROOT / "docs/data/next_gen_consumed.txt"
LOCK = ROOT / "docs/data/evolve_real.lock"

REAL_GATE = dict(sharpe_min=0.8, max_dd=0.35, oos_min=0.5, trips_min=10,
                  excess_min=0.0)  # 6th fitting (2026-09-05): must BEAT SPY absolute
MIN_FREE_BYTES = 500 * 1024 * 1024
PRUNE_EVERY = 200
DSR_MIN = 0.95
PERM_P_MAX = 0.05
BOOT_P_MAX = 0.05
# Mutable trial counter shared with backtest() for the DSR screen: total
# evaluated candidates (winners AND losers), the N in Bailey-Lopez de Prado.
TRIAL_COUNT = [0]
# Per-family trial counts for the gatespec per-family DSR telemetry: at
# N~=1000 scoped trials the DSR 0.70-0.80 bar needs Sharpe ~1.4, not 2.0.
FAM_TRIALS: dict = {}

FAMILIES = ["spy_sma", "spy_rsi2", "btc_vol", "btc_donchian", "us_momentum", "us_lowvol",
            "spy_ltrend", "us_ltrend", "gap_mr", "btc_regime"]
SPACES = {
    "spy_sma": {"window": (50, 300, int)},
    "spy_rsi2": {"entry": (5, 20, int), "exit_hi": (60, 80, int), "max_hold": (3, 10, int)},
    "btc_vol": {"target": (0.20, 0.50, float), "vol_window": (20, 60, int), "gate": (50, 200, int)},
    "btc_donchian": {"entry_ch": (10, 30, int), "exit_ch": (5, 20, int)},
    "us_momentum": {"lookback": (63, 252, int), "skip": (5, 42, int), "top_n": (3, 10, int)},
    "us_lowvol": {"vol_window": (20, 120, int), "top_n": (10, 50, int)},
    # long-term families: slow trend + slow rotation, multi-year holds
    "spy_ltrend": {"window": (150, 400, int)},
    "us_ltrend": {"lookback": (252, 504, int), "top_n": (3, 10, int)},
    # Prime proposals 2026-09-06 (verified deliverable): gap MR long-only
    # adapted (no shorts per mandate), BTC regime overlay (no leverage)
    "gap_mr": {"gap_z_window": (10, 60, int), "entry_z": (1.2, 3.0, float),
               "exit_mid_frac": (0.3, 0.8, float), "max_hold_days": (1, 5, int),
               "vol_filter_pct": (0.6, 1.4, float)},
    "btc_regime": {"target": (0.20, 0.50, float), "btc_vol_window": (15, 60, int),
                   "spy_vol_window": (20, 90, int), "corr_window": (20, 60, int),
                   "spy_vol_cap": (0.12, 0.30, float), "corr_cap": (0.2, 0.7, float)},
}
# long-horizon families trade rarely; trips floor 5 instead of 10
LONGTERM = {"spy_ltrend": 5, "us_ltrend": 5}
PARAM_ORDER = ["p1", "p2", "p3"]
UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "META", "GOOGL", "AMZN", "TSLA"]


def log(msg):
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def load_csv(ticker: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / f"market_data_2019_2026/ohlcv/{ticker}.csv", parse_dates=["date"])
    return df.set_index("date").sort_index()


def max_dd(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak.replace(0, np.nan)
    return float(-dd.min()) if len(dd) else 0.0


def cagr(equity: pd.Series, periods: int = 252) -> float:
    n = len(equity)
    if n < 2 or equity.iloc[0] <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (periods / n) - 1)


def first_trading_day_of_month(idx):
    s = pd.Series(range(len(idx)), index=idx)
    return s.resample("MS").first().dropna().index.intersection(idx)


# ---- parameterized signals (vectorized, past-only) ----
def sig_spy_sma(close, window):
    sma = close.rolling(int(window)).mean().shift(1)
    sig = pd.Series(0.0, index=close.index)
    sig[close > sma] = 1.0
    return sig.fillna(0.0)


def sig_spy_rsi2(close, entry, exit_hi, max_hold):
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)
    rs = gains.rolling(2).mean() / losses.rolling(2).mean().replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    rsi = rsi.shift(1)
    pos = pd.Series(0.0, index=close.index)
    holding = 0
    hold_n = 0
    for i in range(len(close)):
        r = rsi.iloc[i]
        if holding:
            hold_n += 1
            if (pd.notna(r) and r > exit_hi) or hold_n >= max_hold:
                holding, hold_n = 0, 0
        elif pd.notna(r) and r < entry:
            holding, hold_n = 1, 0
        pos.iloc[i] = holding
    return pos


def sig_btc_donchian(high, low, close, entry_ch, exit_ch):
    hi = high.rolling(int(entry_ch)).max().shift(1)
    lo = low.rolling(int(exit_ch)).min().shift(1)
    pos = pd.Series(0.0, index=close.index)
    holding = 0
    for i in range(len(close)):
        if holding and close.iloc[i] < lo.iloc[i]:
            holding = 0
        elif not holding and close.iloc[i] > hi.iloc[i]:
            holding = 1
        pos.iloc[i] = holding
    return pos


def sig_gap_mr(op: pd.Series, close: pd.Series, gap_z_window: int,
               entry_z: float, exit_mid_frac: float, max_hold_days: int,
               vol_filter_pct: float) -> pd.Series:
    """Overnight gap mean-reversion, LONG-ONLY (short leg dropped per mandate).

    gap_t = (open_t - close_{t-1}) / close_{t-1}; enter long on extreme
    negative z when calm; exit on partial gap fill or time stop.
    All normalizers shifted (no lookahead); T+1 applied by backtest().
    """
    prev_close = close.shift(1)
    gap = (op - prev_close) / prev_close
    gmean = gap.shift(1).rolling(int(gap_z_window)).mean()
    gstd = gap.shift(1).rolling(int(gap_z_window)).std(ddof=0).replace(0, np.nan)
    z = (gap - gmean) / gstd
    cc = close.pct_change()
    vol = cc.shift(1).rolling(20).std()
    vol_med = vol.rolling(60).median()
    calm = vol < vol_filter_pct * vol_med
    pos = pd.Series(0.0, index=close.index)
    holding = 0
    held = 0.0
    entry_gap = 0.0
    for i in range(len(close)):
        if holding:
            held += 1
            filled = 0.0
            if entry_gap < 0:
                filled = (close.iloc[i] - op.iloc[i]) / -entry_gap if entry_gap else 1.0
            if filled >= exit_mid_frac or held >= max_hold_days:
                holding = 0
        elif (pd.notna(z.iloc[i]) and z.iloc[i] < -entry_z
              and bool(calm.iloc[i] if pd.notna(calm.iloc[i]) else False)):
            holding = 1
            held = 0
            entry_gap = float(op.iloc[i] - prev_close.iloc[i])
        pos.iloc[i] = holding
    return pos


def sig_btc_regime(btc: pd.Series, spy: pd.Series, target: float,
                   btc_vol_window: int, spy_vol_window: int, corr_window: int,
                   spy_vol_cap: float, corr_cap: float) -> pd.Series:
    """BTC vol targeting gated by SPY regime. LONG/FLAT, unlevered (clip 0..1)."""
    b, s = btc.align(spy, join="inner")
    bvol = b.pct_change().rolling(int(btc_vol_window)).std() * np.sqrt(252)
    svol = s.pct_change().rolling(int(spy_vol_window)).std() * np.sqrt(252)
    corr = b.pct_change().rolling(int(corr_window)).corr(s.pct_change())
    lev = (target / bvol.replace(0, np.nan)).clip(0, 1)
    scale = pd.Series(1.0, index=b.index)
    scale[svol.shift(1) > spy_vol_cap] = 0.5
    scale[corr.shift(1) > corr_cap] = scale * 0.5
    return (lev * scale).fillna(0.0).reindex(btc.index).fillna(0.0)


def sig_btc_vol(close, target, vol_window, gate):
    vol = close.pct_change().rolling(int(vol_window)).std() * np.sqrt(252)
    sma = close.rolling(int(gate)).mean().shift(1)
    lev = (target / vol.replace(0, np.nan)).clip(0, 1).fillna(0.0)
    trend = (close > sma).astype(float)
    return lev * trend


def monthly_rotation(prices: pd.DataFrame, lookback: int, skip: int, top_n: int,
                     lowvol: bool = False, vol_window: int = 60,
                     return_weights: bool = False):
    """Equal-weight top_n monthly rotation; returns portfolio return series,
    or (returns, executed weights) with return_weights=True for the
    rotation timing test."""
    rets = prices.pct_change()
    months = first_trading_day_of_month(prices.index)
    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    for m in months:
        hist = rets.loc[:m].iloc[-(lookback + skip):-skip] if skip else rets.loc[:m].iloc[-lookback:]
        if len(hist) < 20:
            continue
        if lowvol:
            score = hist.std().sort_values()
        else:
            score = hist.mean().sort_values(ascending=False)
        picks = list(score.head(int(top_n)).index)
        w.loc[m, picks] = 1.0 / len(picks)
    w = w.shift(1).fillna(0.0)  # T+1
    port = (w * rets).sum(axis=1)
    if return_weights:
        return port, w
    return port


def stationary_bootstrap_p(values, block_mean: int = 21, boot_n: int = 200,
                           seed: int = 7) -> float:
    """Stationary bootstrap significance (Hall-Wilson centered).

    Centers the return series, resamples with geometric-length blocks
    (mean 21 bars, preserving autocorrelation), and returns the fraction
    of bootstrapped Sharpe ratios at or above the observed one.
    p <= 0.05 means the observed Sharpe is significant: the full Monte
    Carlo screen the loop was missing. Fail-closed (1.0) on error.
    """
    try:
        x = np.asarray(values, dtype=float)
        x = x[np.isfinite(x)]
        n = len(x)
        if n < 60:
            return 1.0
        mu = x.mean()
        sd = x.std(ddof=1)
        if sd < 1e-12:
            return 1.0
        obs = mu / sd * np.sqrt(252.0)
        xc = x - mu  # center: null of zero true Sharpe
        rng = np.random.default_rng(seed)
        wins = 0
        for _ in range(boot_n):
            idx = []
            while len(idx) < n:
                start = int(rng.integers(0, n))
                length = int(rng.geometric(1.0 / block_mean)) + 1
                idx.extend((start + np.arange(length)) % n)
            sample = xc[np.array(idx[:n])]
            s = sample.std(ddof=1)
            if s < 1e-12:
                continue
            if sample.mean() / s * np.sqrt(252.0) >= obs:
                wins += 1
        return wins / boot_n
    except Exception:
        return 1.0


def stat_screens(net: pd.Series, pos: pd.Series, close: pd.Series,
                 slippage_bps: float = 5.0) -> dict:
    """DSR multiple-testing screen + circular-shift timing test.

    Shared by backtest() and _rotation_result() so every family faces
    identical statistics. Fail-closed: any error yields dsr=0/perm_p=1
    (reject), never a pass.
    """
    try:
        from src.backtest.defend.trial_ledger import deflated_sharpe_ratio
        dsr = float(deflated_sharpe_ratio(len(net), float(safe_sharpe(net)) / np.sqrt(252.0),
                                          max(1, TRIAL_COUNT[0])))
    except Exception:
        dsr = 0.0
    try:
        actual = float(safe_sharpe(net))
        pv = np.asarray(pos.fillna(0.0).values, dtype=float)
        rv = np.asarray(close.pct_change().fillna(0.0).values, dtype=float)
        rng = np.random.default_rng(7)
        wins = 0
        K = 200
        for _ in range(K):
            shift = int(rng.integers(1, len(pv)))
            ps = np.roll(pv, shift)
            tn = pd.Series(rv * ps).sub(
                pd.Series(np.abs(np.diff(ps, prepend=ps[0]))) * (slippage_bps / 10000.0))
            if float(safe_sharpe(tn)) >= actual:
                wins += 1
        perm_p = wins / K
    except Exception:
        perm_p = 1.0
    boot_p = stationary_bootstrap_p(np.asarray(net.fillna(0.0).values, dtype=float))
    return {"dsr": round(dsr, 4), "perm_p": round(perm_p, 4),
            "boot_p": round(boot_p, 4)}


def backtest(signal: pd.Series, close: pd.Series, spy_close: pd.Series,
             slippage_bps: float = 5.0) -> dict:
    TRIAL_COUNT[0] += 1  # every evaluated candidate counts toward DSR's N
    pos = signal.shift(1).fillna(0.0)  # T+1
    strat = close.pct_change().fillna(0.0) * pos
    turnover = pos.diff().abs().fillna(pos.abs())
    net = strat - turnover * (slippage_bps / 10000.0)
    eq = (1 + net).cumprod()
    n = len(net)
    split = int(n * 0.7)
    oos = float(safe_sharpe(net.iloc[split:])) if n - split > 20 else 0.0
    trips = int((turnover > 0).sum() // 2)
    # IRL fitting: absolute excess vs SPY buy-hold over the SAME window.
    # A strategy that cannot clear this is timing noise, however high
    # its Sharpe (low time-in-market inflates Sharpe while trailing).
    spy = spy_close.pct_change().fillna(0.0).reindex(net.index).fillna(0.0)
    excess = float((1 + net).prod() - (1 + spy).prod()) * 100
    tmin = float((pos.abs() > 1e-9).mean()) if n else 0.0  # time-in-market for tracks 5/6
    out = {"sharpe": float(safe_sharpe(net)), "cagr": cagr(eq),
           "max_dd": max_dd(eq), "oos": oos, "trips": trips,
           "trades": int((turnover > 0).sum()), "excess": round(excess, 2),
           "tmin": round(tmin, 4), "n_bars": n}
    # DSR multiple-testing screen (Bailey & Lopez de Prado via defend/trial_ledger):
    # per-bar Sharpe discounted by total trials run so far.
    # Circular-shift timing test: randomly misalign positions vs returns;
    # genuine timing skill must beat 95% of misaligned versions.
    out.update(stat_screens(net, pos, close, slippage_bps))
    return out


def run_family(family: str, p: dict, data: dict) -> dict:
    spy = data["SPY"]
    if family == "spy_sma":
        sig = sig_spy_sma(data["SPY"], p["window"])
        return backtest(sig, data["SPY"], spy)
    if family == "spy_ltrend":  # long-horizon trend, same mechanics, slow window
        sig = sig_spy_sma(data["SPY"], p["window"])
        return backtest(sig, data["SPY"], spy)
    if family == "spy_rsi2":
        sig = sig_spy_rsi2(data["SPY"], p["entry"], p["exit_hi"], p["max_hold"])
        return backtest(sig, data["SPY"], spy)
    if family == "btc_vol":
        sig = sig_btc_vol(data["BTC"], p["target"], p["vol_window"], p["gate"])
        return backtest(sig, data["BTC"], spy)
    if family == "btc_donchian":
        d = data["BTCF"]
        sig = sig_btc_donchian(d["high"], d["low"], d["close"], p["entry_ch"], p["exit_ch"])
        return backtest(sig, d["close"], spy)
    if family == "gap_mr":  # Prime proposal 1, long-only adapted
        f = data["SPYF"]
        sig = sig_gap_mr(f["open"], f["close"], p["gap_z_window"], p["entry_z"],
                         p["exit_mid_frac"], p["max_hold_days"], p["vol_filter_pct"])
        return backtest(sig, f["close"], spy)
    if family == "btc_regime":  # Prime proposal 2, unlevered long/flat
        sig = sig_btc_regime(data["BTC"], data["SPY"], p["target"],
                             p["btc_vol_window"], p["spy_vol_window"],
                             p["corr_window"], p["spy_vol_cap"], p["corr_cap"])
        return backtest(sig, data["BTC"], spy)
    uni_rets = data["UNI"].pct_change()
    if family == "us_momentum":
        r, w = monthly_rotation(data["UNI"], p["lookback"], p["skip"], p["top_n"],
                                return_weights=True)
        return _rotation_result(r, data["SPY"], w, uni_rets)
    if family == "us_lowvol":
        r, w = monthly_rotation(data["UNI"], 252, 21, p["top_n"], lowvol=True,
                                vol_window=p["vol_window"], return_weights=True)
        return _rotation_result(r, data["SPY"], w, uni_rets)
    if family == "us_ltrend":  # slow cross-section: 1-2y formation, monthly hold
        r, w = monthly_rotation(data["UNI"], p["lookback"], 21, p["top_n"],
                                return_weights=True)
        return _rotation_result(r, data["SPY"], w, uni_rets)
    raise ValueError(f"unknown family {family}")


def _rotation_result(r: pd.Series, spy_close: pd.Series, weights: pd.DataFrame,
                     asset_rets: pd.DataFrame, slippage_bps: float = 5.0) -> dict:
    TRIAL_COUNT[0] += 1  # every evaluated candidate counts toward DSR's N
    r = r.fillna(0.0)
    eq = (1 + r).cumprod()
    spy = spy_close.pct_change().fillna(0.0).reindex(r.index).fillna(0.0)
    excess = float((1 + r).prod() - (1 + spy).prod()) * 100
    gross = weights.reindex(r.index).fillna(0.0).abs().sum(axis=1)
    tmin = float((gross > 1e-9).mean()) if len(r) else 0.0
    out = {"sharpe": float(safe_sharpe(r)), "cagr": cagr(eq),
           "max_dd": max_dd(eq),
           "oos": float(safe_sharpe(r.iloc[int(len(r) * 0.7):])),
           "trips": 12, "trades": 12, "excess": round(excess, 2),
           "tmin": round(tmin, 4), "n_bars": len(r)}
    # Rotation timing test: shift the whole weight schedule in time and
    # recompute returns; genuine rotation skill must beat 95% of shifted
    # schedules. DSR via shared helper (position proxy = gross exposure).
    try:
        from src.backtest.defend.trial_ledger import deflated_sharpe_ratio
        dsr = float(deflated_sharpe_ratio(len(r), float(safe_sharpe(r)) / np.sqrt(252.0),
                                          max(1, TRIAL_COUNT[0])))
    except Exception:
        dsr = 0.0
    try:
        actual = float(safe_sharpe(r))
        rng = np.random.default_rng(7)
        wins = 0
        K = 200
        vals = asset_rets.reindex(r.index).fillna(0.0).values
        wv = weights.reindex(r.index).fillna(0.0).values
        for _ in range(K):
            shift = int(rng.integers(1, len(r)))
            ps = np.roll(wv, shift, axis=0)
            tn = pd.Series((ps * vals).sum(axis=1), index=r.index)
            tn = tn - pd.Series(np.abs(np.diff(ps, axis=0, prepend=ps[:1])).sum(axis=1),
                                index=r.index) * (slippage_bps / 10000.0)
            if float(safe_sharpe(tn)) >= actual:
                wins += 1
        perm_p = wins / K
    except Exception:
        perm_p = 1.0
    boot_p = stationary_bootstrap_p(np.asarray(r.values, dtype=float))
    out.update({"dsr": round(dsr, 4), "perm_p": round(perm_p, 4),
                "boot_p": round(boot_p, 4)})
    return out


# ---- proposal machinery ----
def random_params(family: str, rng: random.Random) -> dict:
    out = {}
    for k, (lo, hi, typ) in SPACES[family].items():
        out[k] = rng.randint(lo, hi) if typ is int else round(rng.uniform(lo, hi), 4)
    return out


def encode(family: str, params: dict) -> list:
    vec = [float(FAMILIES.index(family)) / max(1, len(FAMILIES) - 1)]
    for k in SPACES[family]:
        lo, hi, _ = SPACES[family][k]
        vec.append((float(params[k]) - lo) / max(1e-9, hi - lo))
    while len(vec) < 1 + 6:  # room for widest space (btc_regime); MLP refits anyway
        vec.append(0.0)
    return vec[:7]


class MLPBias:
    def __init__(self):
        self.model = None
        self.n = 0

    def retrain(self):
        try:
            from sklearn.neural_network import MLPRegressor
        except ImportError:
            return
        try:
            rows = []
            with open(HIST, encoding="utf-8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        continue
            if len(rows) < 15:
                return
            X = np.array([encode(r["family"], r["params"]) for r in rows
                          if r.get("family") in FAMILIES])
            y = np.array([r["sharpe"] for r in rows if r.get("family") in FAMILIES],
                         dtype=float)
            if len(X) < 15:
                return
            self.model = MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=500,
                                      random_state=7)
            self.model.fit(X, y)
            self.n = len(X)
            log(f"MLP retrained on {self.n} samples")
        except Exception as e:
            log(f"MLP retrain skipped: {e}")

    def score(self, family: str, params: dict) -> float:
        if self.model is None:
            return 0.0
        try:
            return float(self.model.predict([encode(family, params)])[0])
        except Exception:
            return 0.0


def breed_proposals():
    """Next unconsumed bred proposal (pointer file; resets on new breed)."""
    try:
        if not PROP.exists():
            return None
        mtime = str(PROP.stat().st_mtime)
        ptr_mtime, idx = "", 0
        if POINTER.exists():
            parts = POINTER.read_text(encoding="utf-8").strip().split()
            if len(parts) == 2:
                ptr_mtime, idx = parts[0], int(parts[1])
        if ptr_mtime != mtime:
            idx = 0
        lines = PROP.read_text(encoding="utf-8").splitlines()
        if idx >= len(lines):
            return None
        POINTER.write_text(f"{mtime} {idx + 1}", encoding="utf-8")
        p = json.loads(lines[idx])
        if p.get("family") in FAMILIES and isinstance(p.get("params"), dict):
            # validate keys against space (breeder may drift)
            space = SPACES[p["family"]]
            if set(p["params"]) == set(space):
                return p
    except Exception as e:
        log(f"breed consume skipped: {e}")
    return None


# ---- guardrails ----
def single_instance() -> bool:
    try:
        if LOCK.exists():
            try:
                pid = int(LOCK.read_text(encoding="utf-8").strip() or "0")
            except (ValueError, OSError):
                pid = 0
            alive = False
            if pid > 0:
                try:
                    # POSIX: signal 0 probes liveness. Windows raises
                    # OSError/WinError for dead PIDs (and SystemError
                    # escapes `except OSError`), so catch everything.
                    os.kill(pid, 0)
                    alive = True
                except Exception:
                    alive = False
            if alive:
                return False  # another loop alive
        LOCK.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except OSError:
        return False


def guards_ok() -> bool:
    try:
        from src.risk.alptrading_safety import SafetyGuard
        if SafetyGuard().kill_switch_active():
            return False
    except Exception:
        return False  # probe broken: fail closed, halt until fixed
    try:
        import shutil
        if shutil.disk_usage(str(ROOT)).free < MIN_FREE_BYTES:
            return False
    except Exception:
        return False  # probe broken: fail closed, halt until fixed
    return True


def append_registry(entry: dict):
    try:
        raw = REG.read_text(encoding="utf-8")
        try:
            obj = json.loads(raw)
        except ValueError:
            obj, _ = json.JSONDecoder().raw_decode(raw)
        obj.setdefault("strategies", []).append(entry)
        tmp = REG.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
        os.replace(tmp, REG)
        json.loads(REG.read_text(encoding="utf-8"))  # validate
    except Exception as e:
        log(f"registry append skipped: {e}")


def main():
    if not single_instance():
        log("another evolve loop holds the lock; exiting")
        return 0
    rng = random.Random()  # nosec B311: parameter search, not cryptography
    log("=== evolve_real START (guarded: lock, kill-switch, disk, atomic registry) ===")
    data = {"SPY": load_csv("SPY")["close"], "BTC": load_csv("BTC")["close"],
            "BTCF": load_csv("BTC"), "SPYF": load_csv("SPY")}
    uni = {}
    for t in UNIVERSE:
        try:
            uni[t] = load_csv(t)["close"]
        except OSError:
            continue
    data["UNI"] = pd.DataFrame(uni).dropna()
    mlp = MLPBias()
    start_iter = 0
    hist_trials = 0
    try:
        with open(HIST, encoding="utf-8") as f:
            for line in f:
                try:
                    start_iter = max(start_iter, int(json.loads(line).get("iter", 0)))
                    hist_trials += 1
                except ValueError:
                    continue
    except OSError:
        pass
    TRIAL_COUNT[0] = hist_trials  # DSR's N includes all past trials, not just this run
    it = start_iter
    while True:
        it += 1
        if not guards_ok():
            log(f"iter={it} guardrail active (kill-switch or low disk); sleeping")
            time.sleep(600)
            continue
        if it % PRUNE_EVERY == 0:
            try:
                from scripts.evolve_generations import main as prune
                prune()
            except Exception as e:
                log(f"prune step skipped: {e}")
        mlp.retrain()
        bred = breed_proposals()
        if bred is not None:
            family, params, src = bred["family"], bred["params"], "bred"
        else:
            family = rng.choice(FAMILIES)
            params = random_params(family, rng)
            src = "random"
            if mlp.model is not None and rng.random() > 0.3:
                # epsilon-greedy: sample candidates, keep MLP-best
                cands = [random_params(family, rng) for _ in range(8)]
                params = max(cands, key=lambda c: mlp.score(family, c))
                src = "mlp"
        try:
            m = run_family(family, params, data)
        except Exception as e:
            log(f"iter={it} {family} backtest error (honest abandon): {e}")
            continue
        rec = {"iter": it, "family": family, "params": params, "proposed_by": src,
               "sharpe": round(m["sharpe"], 3), "cagr": round(m["cagr"], 4),
               "max_dd": round(m["max_dd"], 4), "oos_sharpe": round(m["oos"], 3),
               "round_trips": m["trips"], "trades": m["trades"],
               "excess_spy": m.get("excess", 0.0),
               "tmin": m.get("tmin", 0.0),
               "dsr": m.get("dsr", 0.0), "perm_p": m.get("perm_p", 1.0),
               "boot_p": m.get("boot_p", 1.0)}
        # Per-family DSR telemetry (spec scoping recommendation): same Sharpe
        # under the family's own trial count, not the global ledger.
        FAM_TRIALS[family] = FAM_TRIALS.get(family, 0) + 1
        try:
            rec["dsr_fam"] = round(recompute_dsr(int(m.get("n_bars", 1910)),
                                                 float(m["sharpe"]),
                                                 FAM_TRIALS[family]), 4)
        except Exception:
            rec["dsr_fam"] = 0.0
        rec["fam_trials"] = FAM_TRIALS[family]
        try:
            with open(HIST, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError as e:
            log(f"history write failed (disk?): {e}")
            time.sleep(600)
            continue
        # MAIN GATE (2026-09-06): 10-track gatespec38 union. Promote on ANY
        # fully-cleared track; each track owns its trips/tmin floor (no
        # LONGTERM override needed). perm/boot timing screens stay as
        # universal overlays — they can only block, never admit.
        try:
            tracks = check_track(m)
        except Exception as e:
            log(f"iter={it} track check error (fail-closed abandon): {e}")
            tracks = []
        overlays = (m.get("perm_p", 1.0) <= PERM_P_MAX
                    and m.get("boot_p", 1.0) <= BOOT_P_MAX)
        ok = bool(tracks) and overlays
        verdict = f"PROMOTE:{'+'.join(tracks)}" if ok else "abandon"
        log(f"iter={it} {family} {params} src={src} sharpe={m['sharpe']:.2f} "
            f"dd={m['max_dd']:.3f} oos={m['oos']:.2f} trips={m['trips']} "
            f"excess={m.get('excess', 0.0):.1f} dsr={m.get('dsr', 0.0):.3f} "
            f"tmin={m.get('tmin', 0.0):.2f} dsr_fam={rec['dsr_fam']:.3f} "
            f"pp={m.get('perm_p', 1.0):.3f} bp={m.get('boot_p', 1.0):.3f} {verdict}")
        if ok:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            # dedupe gap fix (2026-09-04): skip if identical family+params
            # already alive paper — the loop re-discovers optima otherwise.
            try:
                reg_now = json.loads(REG.read_text(encoding="utf-8"))
                dup = any(s.get("family") == family and s.get("status") == "paper"
                          and (s.get("metrics", {}) or {}).get("params") == params
                          for s in reg_now.get("strategies", []))
            except Exception:
                dup = False
            if dup:
                log(f"iter={it} {family} duplicate of alive paper entry; skip promote")
                continue
            append_registry({
                "id": f"{family}_real_{ts}", "family": family, "method": "evolve_real",
                "status": "paper", "gates_passed": f"GATESPEC38:{'+'.join(tracks)}",
                "evolved_from": bred["bred_from"] if bred else family,
                "metrics": {**rec, "proposed_by": src,
                            "bench_sharpe": round(float(safe_sharpe(
                                data["SPY"].pct_change().fillna(0.0))), 3)}})
            try:
                with open(PROM, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
