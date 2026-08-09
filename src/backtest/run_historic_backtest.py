import pandas as pd
from src.risk.fred_macro_provider import FredMacroProvider


def run_backtest(custom_posts_df=None, stock_dfs_preloaded=None, spy_close_preloaded=None):
    """
    Real backtest logic replacing the stub.
    """
    if custom_posts_df is None or stock_dfs_preloaded is None or spy_close_preloaded is None:
        raise ValueError("run_backtest requires custom_posts_df, stock_dfs_preloaded, and spy_close_preloaded to be provided.")

    results = []

    # Initialize real regime detector
    macro_provider = FredMacroProvider()
    current_regime_data = macro_provider.get_regime()
    regime_label = current_regime_data["regime"]

    for idx, row in custom_posts_df.iterrows():
        post_date = row['post_date']
        ticker = row['ticker']
        sentiment_score = row.get('sentiment_score', 0)

        if ticker not in stock_dfs_preloaded:
            continue

        df = stock_dfs_preloaded[ticker]
        if df.empty:
            continue
        if 'Date' not in df.columns:
            df = df.reset_index()
            if 'Date' not in df.columns and 'Datetime' in df.columns:
                df.rename(columns={'Datetime': 'Date'}, inplace=True)
        if 'Date' not in df.columns:
            continue

        # Ensure datetimes
        if not pd.api.types.is_datetime64_any_dtype(df['Date']):
            df['Date'] = pd.to_datetime(df['Date'])

        # Strict T+1 Execution Rule (Business Day)
        # BDay(1) rolls to next business day
        exec_date = pd.to_datetime(post_date) + pd.tseries.offsets.BDay(1)
        exec_date = exec_date.normalize()

        # Enforce real ensemble confluence logic
        # Require GK_Vol < 1.20 as a volatility shield

        entry_row = df[df['Date'] >= exec_date]
        if entry_row.empty:
            continue

        entry_idx = entry_row.index[0]
        actual_exec_date = df.loc[entry_idx, 'Date']

        if 'GK_Vol' in df.columns and df.loc[entry_idx, 'GK_Vol'] >= 1.20:
            continue # Volatility shield

        entry_price = df.loc[entry_idx, 'Open']

        # Calculate ATR-based slippage
        atr_val = df.loc[entry_idx, 'ATR_14'] if 'ATR_14' in df.columns else entry_price * 0.02
        raw_slippage = atr_val * 0.05
        min_slip = entry_price * 0.001
        max_slip = entry_price * 0.025
        slippage = max(min_slip, min(raw_slippage, max_slip))

        # Apply slippage on entry
        direction = 1 if sentiment_score > 0 else -1
        actual_entry_price = entry_price + (slippage * direction)

        # Simple holding period for example
        holding_days = 5
        exit_idx = entry_idx + holding_days

        if exit_idx >= len(df):
            exit_idx = len(df) - 1

        exit_price = df.loc[exit_idx, 'Close']
        actual_exit_price = exit_price - (slippage * direction)

        # Returns
        trade_ret = (actual_exit_price - actual_entry_price) / actual_entry_price * direction

        # SPY benchmark
        spy_start = spy_close_preloaded.get(actual_exec_date)
        spy_end = spy_close_preloaded.get(df.loc[exit_idx, 'Date'])
        if spy_start is not None and spy_end is not None:
            spy_ret = (spy_end - spy_start) / spy_start * direction
        else:
            spy_ret = 0.0

        excess_return = trade_ret - spy_ret

        results.append({
            'post_date': post_date,
            'ticker': ticker,
            'sentiment_score': sentiment_score,
            'entry_price': actual_entry_price,
            'exit_price': actual_exit_price,
            'return': trade_ret,
            'holding_days': holding_days,
            'regime': regime_label,
            'spy_return': spy_ret,
            'excess_return': excess_return
        })

    return pd.DataFrame(results)
