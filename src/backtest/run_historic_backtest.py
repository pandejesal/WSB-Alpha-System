import pandas as pd

def run_backtest_with_params(posts_df, stock_dfs, holding_days, rsi_low, rsi_high, gk_vol_limit, min_confluence_score, spy_close_preloaded=None):
    """Run backtest with specific parameter combination, with honest entry/exit rules."""
    if posts_df is None or posts_df.empty:
        return pd.DataFrame(columns=['post_date', 'ticker', 'sentiment_score', 'entry_price', 'exit_price', 'return', 'holding_days', 'regime', 'spy_return', 'excess_return'])

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
        entry_iloc = df.index.get_loc(entry_idx)

        # Lookahead Fix: compute decision indicators using the last closed bar
        # before the entry bar
        decision_iloc = entry_iloc - 1
        if decision_iloc < 0:
            continue

        decision_idx = df.index[decision_iloc]

        # GK Vol shield (evaluated on t-1)
        if "GK_Vol" in df.columns and df.loc[decision_idx, "GK_Vol"] >= gk_vol_limit:
            continue

        # RSI filter (evaluated on t-1)
        rsi_val = df.loc[decision_idx, "RSI_14"] if "RSI_14" in df.columns else 50
        if not (rsi_low < rsi_val < rsi_high):
            continue

        # Confluence check (evaluated on t-1)
        ha_close = df.loc[decision_idx, "HA_Close"] if "HA_Close" in df.columns else df.loc[decision_idx, "Close"]
        ha_open = df.loc[decision_idx, "HA_Open"] if "HA_Open" in df.columns else df.loc[decision_idx, "Close"]
        macd_hist = df.loc[decision_idx, "MACD_Hist"] if "MACD_Hist" in df.columns else 0
        close = df.loc[decision_idx, "Close"]
        bb_lower = df.loc[decision_idx, "BB_Lower"] if "BB_Lower" in df.columns else close * 0.95
        bb_upper = df.loc[decision_idx, "BB_Upper"] if "BB_Upper" in df.columns else close * 1.05
        ema_20 = df.loc[decision_idx, "EMA_20"] if "EMA_20" in df.columns else close

        if sentiment_score > 0:
            score = int(ha_close > ha_open) + int((close > ema_20) and (macd_hist > 0)) + int(30 < rsi_val < 70) + int(close > bb_lower)
        else:
            score = int(ha_close < ha_open) + int((close < ema_20) and (macd_hist < 0)) + int(30 < rsi_val < 70) + int(close < bb_upper)

        if score < min_confluence_score:
            continue

        # Fill at Open of entry_idx
        entry_price = df.loc[entry_idx, "Open"]

        # ATR slippage (evaluated on t-1 for the entry)
        atr_val = df.loc[decision_idx, "ATR_14"] if "ATR_14" in df.columns else entry_price * 0.02
        raw_slippage = atr_val * 0.05
        min_slip = entry_price * 0.001
        max_slip = entry_price * 0.025
        slippage = max(min_slip, min(raw_slippage, max_slip))

        direction = 1 if sentiment_score > 0 else -1
        actual_entry = entry_price + (slippage * direction)

        exit_iloc = entry_iloc + holding_days
        if exit_iloc >= len(df):
            exit_iloc = len(df) - 1

        exit_idx = df.index[exit_iloc]

        # Exit at Close of the exit bar
        exit_price = df.loc[exit_idx, "Close"]
        actual_exit = exit_price - (slippage * direction)
        trade_ret = (actual_exit - actual_entry) / actual_entry * direction

        actual_exec_date = df.loc[entry_idx, "Date"]

        # SPY benchmark
        spy_ret = 0.0
        if spy_close_preloaded is not None:
            spy_start = spy_close_preloaded.get(actual_exec_date)
            spy_end = spy_close_preloaded.get(df.loc[exit_idx, 'Date'])
            if spy_start is not None and spy_end is not None:
                spy_ret = (spy_end - spy_start) / spy_start * direction

        excess_return = trade_ret - spy_ret

        results.append({
            "post_date": post_date,
            "ticker": ticker,
            "sentiment_score": sentiment_score,
            "entry_price": actual_entry,
            "exit_price": actual_exit,
            "return": trade_ret,
            "holding_days": holding_days,
            "regime": "normal",
            "spy_return": spy_ret,
            "excess_return": excess_return
        })

    return pd.DataFrame(results)

def run_backtest(custom_posts_df=None, stock_dfs_preloaded=None, spy_close_preloaded=None):
    """
    Wrapper for the real backtest logic to match the validation.py interface.
    """
    if custom_posts_df is None or stock_dfs_preloaded is None or spy_close_preloaded is None:
        return pd.DataFrame(columns=['post_date', 'ticker', 'sentiment_score', 'entry_price', 'exit_price', 'return', 'holding_days', 'regime', 'spy_return', 'excess_return'])

    return run_backtest_with_params(
        custom_posts_df,
        stock_dfs_preloaded,
        holding_days=5,
        rsi_low=30,
        rsi_high=70,
        gk_vol_limit=1.20,
        min_confluence_score=3,
        spy_close_preloaded=spy_close_preloaded
    )
