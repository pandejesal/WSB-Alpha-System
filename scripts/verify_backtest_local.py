"""Verification run: full backtest on REAL local historical data (2019-2026)
using the exact same engine + signal logic as scripts/run_full_backtest.py,
bypassing only the (broken) network fetch path. SPY benchmark included."""
import json
import logging
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING)

DATA_DIR = "market_data_2019_2026/ohlcv"
UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ", "WMT", "MA", "UNH", "XOM", "DIS"]


def load_local_data():
    stock_dfs, spy_close = {}, {}
    for ticker in UNIVERSE + ["SPY"]:
        path = os.path.join(DATA_DIR, f"{ticker}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index.name = "Date"
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"])
        rename_map = {c: c.capitalize() for c in df.columns if c.lower() in ["open", "high", "low", "close", "volume"]}
        df.rename(columns=rename_map, inplace=True)
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if ticker == "SPY":
            spy_close = dict(zip(df["Date"], df["Close"]))
        else:
            stock_dfs[ticker] = df
    return stock_dfs, spy_close


def compute_signals(stock_dfs, from_alpha=True):
    from src.alpha.indicators import compute_indicators

    enhanced, synthetic_signals = {}, []
    for ticker, df in stock_dfs.items():
        px = df.set_index("Date")
        if len(px) < 50:
            continue
        ind = compute_indicators(px)
        if ind is None or ind.empty:
            continue
        ind = ind.reset_index()
        ind["Date"] = pd.to_datetime(ind["Date"])
        enhanced[ticker] = ind
        ind_idx = ind.set_index("Date")
        for idx, row in ind_idx.iterrows():
            rsi = row.get("RSI_14", 50)
            macd_hist = row.get("MACD_Hist", 0)
            close = row["Close"]
            bb_lower = row.get("BB_Lower", close * 0.95)
            bb_upper = row.get("BB_Upper", close * 1.05)
            ha_close = row.get("HA_Close", close)
            ha_open = row.get("HA_Open", close)
            gk_vol = row.get("GK_Vol", 0.50)
            ema_20 = row.get("EMA_20", close)
            vol_passed = gk_vol < 1.20
            bull_score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi < 70) + int(close > bb_lower)
            bear_score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi < 70) + int(close < bb_upper)
            if vol_passed:
                if bull_score >= 3:
                    synthetic_signals.append({"ticker": ticker, "post_date": idx, "sentiment_score": 1.0})
                elif bear_score >= 3:
                    synthetic_signals.append({"ticker": ticker, "post_date": idx, "sentiment_score": -1.0})
    return enhanced, pd.DataFrame(synthetic_signals)


def trade_metrics(trades_df):
    from src.backtest.metrics import safe_sharpe, safe_sortino

    if trades_df.empty:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "win_rate": 0, "profit_factor": 0,
                "max_drawdown": 0, "total_trades": 0, "total_return": 0, "annualized_return": 0,
                "avg_excess_return": 0, "spy_total_return": 0, "avg_holding_period": 0}
    rets = trades_df["return"].fillna(0)
    total_return = rets.sum()
    sharpe = safe_sharpe(rets, periods=252)
    sortino = safe_sortino(rets, periods=252)
    cum_ret = rets.cumsum()
    running_max = cum_ret.cummax()
    drawdown = running_max - cum_ret
    max_dd = drawdown.max() if len(drawdown) > 0 else 0
    calmar = total_return / (max_dd + 1e-10) if max_dd > 0 else 0
    wins = (rets > 0).sum()
    win_rate = wins / len(rets)
    gross_profit = rets[rets > 0].sum()
    gross_loss = abs(rets[rets < 0].sum())
    profit_factor = gross_profit / (gross_loss + 1e-10) if gross_loss > 0 else 0
    days_span = (pd.to_datetime(trades_df["post_date"]).max() - pd.to_datetime(trades_df["post_date"]).min()).days
    years = days_span / 365.25 if days_span > 0 else 1
    annualized_return = ((1 + total_return) ** (1 / years) - 1) if years > 0 else total_return
    return {"sharpe": float(sharpe), "sortino": float(sortino), "calmar": float(calmar),
            "win_rate": float(win_rate), "profit_factor": float(profit_factor),
            "max_drawdown": float(max_dd), "total_trades": int(len(rets)),
            "total_return": float(total_return), "annualized_return": float(annualized_return),
            "avg_excess_return": float(trades_df["excess_return"].fillna(0).mean()),
            "spy_total_return": float(trades_df["spy_return"].fillna(0).sum()),
            "avg_holding_period": float(trades_df["holding_days"].mean())}


def main():
    from src.backtest.metrics import safe_sharpe
    from src.backtest import run_historic_backtest as rb
    from src.risk.fred_macro_provider import FredMacroProvider

    _cache = {}
    _orig_get_historical_regimes = FredMacroProvider.get_historical_regimes
    def cached_regimes(self):
        if "regimes" not in _cache:
            _cache["regimes"] = _orig_get_historical_regimes(self)
            print(f"FRED regimes fetched once: {len(_cache['regimes'])} days")
        return _cache["regimes"]
    FredMacroProvider.get_historical_regimes = cached_regimes

    print("=" * 80)
    print("STEP 2: BACKTEST CORRECTNESS ON REAL HISTORICAL DATA (2019-2026)")
    print("=" * 80)
    stock_dfs, spy_close = load_local_data()
    print(f"Loaded {len(stock_dfs)}/{len(UNIVERSE)} universe tickers + SPY benchmark from local CSVs")

    enhanced, posts_df = compute_signals(stock_dfs)
    posts_df = posts_df.iloc[::3].reset_index(drop=True)
    print(f"Synthetic signals generated: {len(posts_df)} (subsampled /3; long={int((posts_df['sentiment_score']>0).sum())}, short={int((posts_df['sentiment_score']<0).sum())})")
    if posts_df.empty:
        print("NO SIGNALS - backtest cannot run")
        return

    holding_periods = [3, 7, 15]
    rsi_thresholds = [(30, 70), (40, 60)]
    gk_vol_limits = [1.0, 1.2]
    min_confluence_scores = [3, 4]

    population = []
    combo = 0
    for hp in holding_periods:
        for rsi_low, rsi_high in rsi_thresholds:
            for gk_limit in gk_vol_limits:
                for min_score in min_confluence_scores:
                    combo += 1
                    trades = rb.run_backtest_with_params(
                        posts_df, enhanced, hp, rsi_low, rsi_high, gk_limit, min_score,
                        spy_close_preloaded=spy_close, stop_loss_pct=0.0)
                    m = trade_metrics(trades)
                    m["oos_sharpe"] = 0.0
                    if len(trades) >= 10:
                        split = int(len(trades) * 0.8)
                        m["oos_sharpe"] = float(safe_sharpe(trades.iloc[split:]["return"].fillna(0), periods=252))
                    population.append({
                        "id": f"strat_{len(population):04d}",
                        "strategy_name": f"HA_MACD_RSI_BB_hp{hp}_rsi{rsi_low}{rsi_high}_gk{gk_limit}_min{min_score}",
                        "metrics": m})
                    print(f"  hp={hp:>2} rsi={rsi_low}-{rsi_high} gk={gk_limit} min={min_score} | trades={m['total_trades']:>4} ret={m['total_return']*100:>7.2f}% sharpe={m['sharpe']:>6.2f} oos_sharpe={m['oos_sharpe']:>6.2f} spy_sum={m['spy_total_return']*100:>7.2f}% excess_avg={m['avg_excess_return']*100:>7.2f}%")

    population.sort(key=lambda x: x.get("metrics", {}).get("sharpe", 0), reverse=True)
    print()
    print("=" * 80)
    print("TOP 5 BY SHARPE")
    print("=" * 80)
    for i, s in enumerate(population[:5]):
        m = s["metrics"]
        print(f"#{i+1} {s['strategy_name']:<40} ret={m['total_return']*100:>7.2f}% ann={m['annualized_return']*100:>6.2f}% sharpe={m['sharpe']:>6.2f} oos={m['oos_sharpe']:>6.2f} dd={m['max_drawdown']*100:>6.2f}% wr={m['win_rate']*100:>5.1f}% pf={m['profit_factor']:>5.2f} spy={m['spy_total_return']*100:>7.2f}% excess_avg={m['avg_excess_return']*100:>6.2f}%")

    print()
    print("=" * 80)
    print("SPY BUY & HOLD 2019-2026 (full-period reference)")
    print("=" * 80)
    spy_series = pd.Series(spy_close).sort_index()
    spy_ret = spy_series.iloc[-1] / spy_series.iloc[0] - 1
    years = (spy_series.index.max() - spy_series.index.min()).days / 365.25
    print(f"SPY {spy_series.index.min().date()} -> {spy_series.index.max().date()}: total={spy_ret*100:.2f}% ann={(1+spy_ret)**(1/years)-1:.2%}")

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/backtest_verification_2026.json", "w") as f:
        json.dump(population, f, indent=2)
    print("\nSaved docs/data/backtest_verification_2026.json")


if __name__ == "__main__":
    main()
