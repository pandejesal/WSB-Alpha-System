#!/usr/bin/env python3
"""
Generate strategy data for the dashboard by running the full evolution pipeline.
Downloads pricing data, generates synthetic signals, runs backtests,
evaluates the population through the Darwinian engine, and writes
docs/data/strategies.json + strategy_population.json + thompson_state.json.
"""
import json
import os
import sys
import logging
import numpy as np
import pandas as pd
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        import yfinance as yf
        from src.alpha.indicators import compute_indicators
        from src.evolution.darwin_engine import DarwinEngine

        # 1. Load universe
        with open("config/universe.json") as f:
            universe = json.load(f).get("tickers", [])
        # Deduplicate
        universe = list(dict.fromkeys(universe))

        # 2. Download 2 years of pricing data
        logger.info("Downloading pricing data...")
        end_date = pd.Timestamp.now()
        start_date = end_date - timedelta(days=730)
        px_data = yf.download(universe, start=start_date, end=end_date, progress=False, auto_adjust=True)

        if px_data.empty:
            logger.warning("No pricing data available. Writing empty strategies.")
            _write_empty_strategies()
            return

        # 3. Generate synthetic signals from technical indicators
        synthetic_signals = []
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
                    continue
                ind_df = compute_indicators(t_px)
                if ind_df is None:
                    continue

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
            except Exception:
                continue

        if not synthetic_signals:
            logger.warning("No signals generated. Writing empty strategies.")
            _write_empty_strategies()
            return

        posts_df = pd.DataFrame(synthetic_signals)
        logger.info(f"Generated {len(posts_df)} synthetic signals for {len(posts_df['ticker'].unique())} tickers")

        # 4. Build stock_dfs with indicators
        stock_dfs = {}
        for ticker in posts_df["ticker"].unique():
            try:
                if isinstance(px_data.columns, pd.MultiIndex):
                    t_px = px_data.loc[:, (slice(None), ticker)].copy()
                    t_px.columns = t_px.columns.get_level_values(0)
                else:
                    t_px = px_data.copy()
                t_px = t_px.dropna(subset=["Close", "Open", "High", "Low"])
                if len(t_px) >= 20:
                    stock_dfs[ticker] = compute_indicators(t_px)
            except Exception:
                continue

        # 5. Run backtests with multiple parameter combos
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

        # 6. Evaluate population through Darwinian engine
        darwin = DarwinEngine()
        population = darwin.evaluate_population(population)

        # 7. Save strategy_population.json
        with open("strategy_population.json", "w") as f:
            json.dump(population, f, indent=2)
        logger.info("Saved strategy_population.json")

        # 8. Initialize or load thompson_state.json
        thompson_path = "thompson_state.json"
        if os.path.exists(thompson_path):
            with open(thompson_path) as f:
                thompson = json.load(f)
        else:
            thompson = {}

        for s in population:
            sid = s["id"]
            if sid not in thompson:
                thompson[sid] = {"alpha": 1, "beta": 1}

        with open(thompson_path, "w") as f:
            json.dump(thompson, f, indent=2)

        # 9. Write docs/data/strategies.json for dashboard
        strategies = []
        for s in population:
            metrics = s.get("metrics", {})
            sid = s["id"]
            alpha = thompson.get(sid, {}).get("alpha", 1)
            beta = thompson.get(sid, {}).get("beta", 1)
            strategies.append({
                "id": sid,
                "name": s.get("strategy_name", sid),
                "fitness": s.get("fitness", 0),
                "sharpe": metrics.get("sharpe", 0),
                "sortino": metrics.get("sortino", 0),
                "calmar": metrics.get("calmar", 0),
                "max_drawdown": metrics.get("max_drawdown", 0),
                "win_rate": metrics.get("win_rate", 0),
                "profit_factor": metrics.get("profit_factor", 0),
                "total_trades": metrics.get("total_trades", 0),
                "oos_sharpe": metrics.get("oos_sharpe", 0),
                "thompson_alpha": alpha,
                "thompson_beta": beta,
                "thompson_ev": alpha / (alpha + beta) if (alpha + beta) > 0 else 0.5,
                "status": s.get("status", "unknown"),
                "parameters": s.get("parameters", {})
            })

        strategies.sort(key=lambda x: x["fitness"], reverse=True)

        output = {
            "strategies": strategies,
            "generated_at": pd.Timestamp.now().isoformat()
        }

        os.makedirs("docs/data", exist_ok=True)
        with open("docs/data/strategies.json", "w") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Generated strategies.json with {len(strategies)} strategies")

        # 10. Print top 5
        print("\n=== TOP 5 STRATEGIES ===")
        for i, s in enumerate(strategies[:5]):
            print(f"#{i+1} {s['name']}: fitness={s['fitness']:.4f}, sharpe={s['sharpe']:.2f}, return={s.get('total_return', 0)*100:.1f}%, max_dd={s['max_drawdown']*100:.1f}%")

    except Exception as e:
        logger.error(f"Strategy generation failed: {e}", exc_info=True)
        _write_empty_strategies()


def _run_backtest_with_params(posts_df, stock_dfs, holding_days, rsi_low, rsi_high, gk_vol_limit, min_confluence_score):
    """Run backtest with specific parameter combination."""
    import src.backtest.run_historic_backtest as rb

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


def _compute_trade_metrics(trades_df):
    """Compute metrics from trades DataFrame."""
    if trades_df.empty:
        return {"sharpe": 0, "sortino": 0, "calmar": 0, "win_rate": 0, "profit_factor": 0, "max_drawdown": 0, "total_trades": 0, "total_return": 0}

    rets = trades_df["return"].fillna(0)
    total_return = rets.sum()
    mean_ret = rets.mean()
    std_ret = rets.std()

    sharpe = (mean_ret / (std_ret + 1e-10)) * np.sqrt(252) if std_ret > 0 else 0

    # Sortino: use only negative returns for downside deviation
    downside_rets = rets[rets < 0]
    downside_std = downside_rets.std() if len(downside_rets) > 0 else 1e-10
    sortino = (mean_ret / (downside_std + 1e-10)) * np.sqrt(252) if downside_std > 0 else 0

    # Max drawdown
    cum_ret = rets.cumsum()
    running_max = cum_ret.cummax()
    drawdown = running_max - cum_ret
    max_dd = drawdown.max() if len(drawdown) > 0 else 0

    # Calmar
    calmar = total_return / (max_dd + 1e-10) if max_dd > 0 else 0

    # Win rate
    wins = (rets > 0).sum()
    total_trades = len(rets)
    win_rate = wins / total_trades if total_trades > 0 else 0

    # Profit factor
    gross_profit = rets[rets > 0].sum()
    gross_loss = abs(rets[rets < 0].sum())
    profit_factor = gross_profit / (gross_loss + 1e-10) if gross_loss > 0 else 0

    return {
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "calmar": float(calmar),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor),
        "max_drawdown": float(max_dd),
        "total_trades": int(total_trades),
        "total_return": float(total_return),
        "train_sharpe": float(sharpe),
        "oos_sharpe": float(sharpe)
    }


def _write_empty_strategies():
    """Write empty strategies.json on failure."""
    os.makedirs("docs/data", exist_ok=True)
    output = {
        "strategies": [],
        "generated_at": pd.Timestamp.now().isoformat(),
        "error": "No data available or generation failed"
    }
    with open("docs/data/strategies.json", "w") as f:
        json.dump(output, f, indent=2)
    logger.warning("Wrote empty strategies.json")


if __name__ == "__main__":
    main()