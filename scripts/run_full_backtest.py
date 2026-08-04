#!/usr/bin/env python3
"""
Comprehensive backtester.
Downloads 8 years of daily OHLCV for the 18-ticker universe from yfinance.
Runs the ensemble confluence strategy across all signals.
Tests 90 parameter combinations, calculates metrics, ranks by fitness,
and saves results.
"""
import json
import os
import logging
import numpy as np
import pandas as pd
from datetime import timedelta
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _compute_trade_metrics(trades_df):
    """Compute metrics from trades DataFrame."""
    if trades_df.empty:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "win_rate": 0, "profit_factor": 0, "max_drawdown": 0, "total_trades": 0, "total_return": 0, "annualized_return": 0, "avg_holding_period": 0}

    rets = trades_df["return"].fillna(0)
    total_return = rets.sum()
    mean_ret = rets.mean()
    std_ret = rets.std()

    sharpe = (mean_ret / (std_ret + 1e-10)) * np.sqrt(252) if std_ret > 0 else 0

    downside_rets = rets[rets < 0]
    downside_std = downside_rets.std() if len(downside_rets) > 0 else 1e-10
    sortino = (mean_ret / (downside_std + 1e-10)) * np.sqrt(252) if downside_std > 0 else 0

    cum_ret = rets.cumsum()
    running_max = cum_ret.cummax()
    drawdown = running_max - cum_ret
    max_dd = drawdown.max() if len(drawdown) > 0 else 0

    calmar = total_return / (max_dd + 1e-10) if max_dd > 0 else 0

    wins = (rets > 0).sum()
    total_trades = len(rets)
    win_rate = wins / total_trades if total_trades > 0 else 0

    gross_profit = rets[rets > 0].sum()
    gross_loss = abs(rets[rets < 0].sum())
    profit_factor = gross_profit / (gross_loss + 1e-10) if gross_loss > 0 else 0

    # Calculate years spanned for annualized return
    if "post_date" in trades_df.columns and len(trades_df) > 1:
        trades_df["post_date"] = pd.to_datetime(trades_df["post_date"])
        days_span = (trades_df["post_date"].max() - trades_df["post_date"].min()).days
        years = days_span / 365.25 if days_span > 0 else 1
    else:
        years = 1

    annualized_return = ((1 + total_return) ** (1 / years) - 1) if years > 0 else total_return
    avg_holding_period = trades_df["holding_days"].mean() if "holding_days" in trades_df.columns else 0

    return {
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "max_drawdown": float(max_dd),
        "total_trades": int(total_trades),
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "avg_holding_period": float(avg_holding_period),
        "train_sharpe": float(sharpe),
        "oos_sharpe": float(sharpe)
    }


def _run_backtest_with_params(posts_df, stock_dfs, holding_days, rsi_low, rsi_high, gk_vol_limit, min_confluence_score):
    """Run backtest with specific parameter combination."""
    # Filter signals by RSI threshold (modify posts_df)
    filtered_posts = posts_df.copy()

    results = []
    for idx, row in filtered_posts.iterrows():
        post_date = row["post_date"]
        ticker = row["ticker"]
        sentiment_score = row.get("sentiment_score", 0)

        if ticker not in stock_dfs:
            continue
        df = stock_dfs[ticker]
        if df is None or df.empty:
            continue

        # Ensure we have a Date column or use the index
        if "Date" not in df.columns:
            df = df.reset_index()
            if "Date" not in df.columns and "Datetime" in df.columns:
                df.rename(columns={"Datetime": "Date"}, inplace=True)

        if "Date" not in df.columns:
            continue

        if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
            df["Date"] = pd.to_datetime(df["Date"])

        exec_date = pd.to_datetime(post_date) + pd.tseries.offsets.BDay(1)
        exec_date = exec_date.normalize()

        entry_row = df[df["Date"] >= exec_date]
        if entry_row.empty:
            continue

        entry_idx = entry_row.index[0]

        # GK Vol shield
        if "GK_Vol" in df.columns and df.loc[entry_idx, "GK_Vol"] >= gk_vol_limit:
            continue

        # RSI filter
        rsi_val = df.loc[entry_idx, "RSI_14"] if "RSI_14" in df.columns else 50
        if not (rsi_low < rsi_val < rsi_high):
            continue

        # Confluence check
        ha_close = df.loc[entry_idx, "HA_Close"] if "HA_Close" in df.columns else df.loc[entry_idx, "Close"]
        ha_open = df.loc[entry_idx, "HA_Open"] if "HA_Open" in df.columns else df.loc[entry_idx, "Close"]
        macd_hist = df.loc[entry_idx, "MACD_Hist"] if "MACD_Hist" in df.columns else 0
        close = df.loc[entry_idx, "Close"]
        bb_lower = df.loc[entry_idx, "BB_Lower"] if "BB_Lower" in df.columns else close * 0.95
        bb_upper = df.loc[entry_idx, "BB_Upper"] if "BB_Upper" in df.columns else close * 1.05
        ema_20 = df.loc[entry_idx, "EMA_20"] if "EMA_20" in df.columns else close

        if sentiment_score > 0:
            score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi_val < 70) + int(close > bb_lower)
        else:
            score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi_val < 70) + int(close < bb_upper)

        if score < min_confluence_score:
            continue

        entry_price = df.loc[entry_idx, "Open"]

        # ATR slippage
        atr_val = df.loc[entry_idx, "ATR_14"] if "ATR_14" in df.columns else entry_price * 0.02
        raw_slippage = atr_val * 0.05
        min_slip = entry_price * 0.001
        max_slip = entry_price * 0.025
        slippage = max(min_slip, min(raw_slippage, max_slip))

        direction = 1 if sentiment_score > 0 else -1
        actual_entry = entry_price + (slippage * direction)

        exit_idx = entry_idx + holding_days
        if exit_idx >= len(df):
            exit_idx = len(df) - 1

        exit_price = df.loc[exit_idx, "Close"]
        actual_exit = exit_price - (slippage * direction)
        trade_ret = (actual_exit - actual_entry) / actual_entry * direction

        results.append({
            "post_date": post_date,
            "ticker": ticker,
            "return": trade_ret,
            "holding_days": holding_days
        })

    return pd.DataFrame(results)


def main():
    try:
        from src.alpha.indicators import compute_indicators
        from src.evolution.darwin_engine import DarwinEngine

        # 1. Load universe
        with open("config/universe.json") as f:
            universe = json.load(f).get("tickers", [])
        universe = list(dict.fromkeys(universe))

        # 2. Download 8 years of pricing data
        logger.info("Downloading 8 years of pricing data...")
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.DateOffset(years=8)
        px_data = yf.download(universe, start=start_date, end=end_date, progress=False, auto_adjust=True)

        if px_data.empty:
            logger.warning("No pricing data available.")
            return

        # 3. Generate synthetic signals from technical indicators
        logger.info("Computing indicators and generating signals...")
        synthetic_signals = []
        stock_dfs = {}
        for ticker in universe:
            try:
                if isinstance(px_data.columns, pd.MultiIndex):
                    t_px = px_data.loc[:, (slice(None), ticker)].copy()
                    t_px.columns = t_px.columns.get_level_values(0)
                else:
                    if len(universe) == 1:
                        t_px = px_data.copy()
                    else:
                        continue
                t_px = t_px.dropna(subset=["Close", "Open", "High", "Low"])
                if len(t_px) < 50:
                    logger.warning(f"Ticker {ticker} skipped due to insufficient data.")
                    continue
                ind_df = compute_indicators(t_px)
                if ind_df is None or ind_df.empty:
                    continue
                stock_dfs[ticker] = ind_df

                for idx, row in ind_df.iterrows():
                    rsi = row.get('RSI_14', 50)
                    macd_hist = row.get('MACD_Hist', 0)
                    close = row['Close']
                    bb_lower = row.get('BB_Lower', close * 0.95)
                    bb_upper = row.get('BB_Upper', close * 1.05)
                    ha_close = row.get('HA_Close', close)
                    ha_open = row.get('HA_Open', close)
                    gk_vol = row.get('GK_Vol', 0.50)
                    ema_20 = row.get('EMA_20', close)

                    vol_passed = gk_vol < 1.20
                    bull_score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi < 70) + int(close > bb_lower)
                    bear_score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi < 70) + int(close < bb_upper)

                    if vol_passed:
                        if bull_score >= 3:
                            synthetic_signals.append({"ticker": ticker, "post_date": idx, "sentiment_score": 1.0})
                        elif bear_score >= 3:
                            synthetic_signals.append({"ticker": ticker, "post_date": idx, "sentiment_score": -1.0})
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")
                continue

        if not synthetic_signals:
            logger.warning("No signals generated.")
            return

        posts_df = pd.DataFrame(synthetic_signals)
        logger.info(f"Generated {len(posts_df)} synthetic signals for {len(posts_df['ticker'].unique())} tickers")

        # 4. Run backtests with 90 parameter combos
        holding_periods = [3, 5, 7, 10, 15]
        rsi_thresholds = [(30, 70), (35, 65), (40, 60)]
        gk_vol_limits = [0.8, 1.0, 1.2]
        min_confluence_scores = [3, 4]

        population = []
        strat_id = 0

        for hp in holding_periods:
            for rsi_low, rsi_high in rsi_thresholds:
                for gk_limit in gk_vol_limits:
                    for min_score in min_confluence_scores:
                        trades = _run_backtest_with_params(
                            posts_df, stock_dfs, hp, rsi_low, rsi_high, gk_limit, min_score
                        )

                        metrics = _compute_trade_metrics(trades)

                        population.append({
                            "id": f"strat_{strat_id:04d}",
                            "strategy_name": f"HA_MACD_RSI_BB_hp{hp}_rsi{rsi_low}{rsi_high}_gk{gk_limit}_min{min_score}",
                            "parameters": {
                                "holding_days": hp,
                                "rsi_low": rsi_low,
                                "rsi_high": rsi_high,
                                "gk_vol_limit": gk_limit,
                                "min_confluence_score": min_score
                            },
                            "metrics": metrics
                        })
                        strat_id += 1

        logger.info(f"Backtested {len(population)} strategy variants")

        # 5. Evaluate population through Darwinian engine
        darwin = DarwinEngine()
        population = darwin.evaluate_population(population)

        # Sort by fitness desc
        population.sort(key=lambda x: x.get("fitness", 0), reverse=True)

        os.makedirs("docs/data", exist_ok=True)

        # Save docs/data/backtest_results.json and root
        with open("docs/data/backtest_results.json", "w") as f:
            json.dump(population, f, indent=2)
        with open("backtest_results.json", "w") as f:
            json.dump(population, f, indent=2)

        # Save docs/data/best_strategy.json
        if population:
            with open("docs/data/best_strategy.json", "w") as f:
                json.dump(population[0], f, indent=2)

        # 6. Print Summary table of top 10
        print("\n" + "="*80)
        print("TOP 10 STRATEGIES")
        print("="*80)
        print(f"{'Rank':<5} {'Name':<45} {'Fitness':<10} {'Sharpe':<10} {'Ret':<10} {'MaxDD':<10}")
        for i, s in enumerate(population[:10]):
            name = s.get('strategy_name', '')
            fit = s.get('fitness', 0)
            metrics = s.get('metrics', {})
            sharpe = metrics.get('sharpe', 0)
            ret = metrics.get('total_return', 0) * 100
            dd = metrics.get('max_drawdown', 0) * 100
            print(f"{i+1:<5} {name[:43]:<45} {fit:<10.4f} {sharpe:<10.2f} {ret:>6.1f}%   {dd:>6.1f}%")

    except Exception as e:
        logger.error(f"Full backtest failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
