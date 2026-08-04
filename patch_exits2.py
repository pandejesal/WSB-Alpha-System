import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Replace run_backtest_for_params signature and params handling
run_bt_orig = """def run_backtest_for_params(df_dict, spy_df, params, deposit_schedule):
    holding_days = params['holding_days']
    rsi_bounds = params['rsi_bounds']
    gk_limit = params['gk_limit']
    min_confluence = params['min_confluence']"""

run_bt_new = """def run_backtest_for_params(df_dict, spy_df, params, deposit_schedule):
    holding_days = 30 # Fixed max holding guardrail
    atr_trailing_mult = params['atr_trailing_mult']
    atr_profit_mult = params['atr_profit_mult']
    rsi_bounds = params['rsi_bounds']
    gk_limit = params.get('gk_limit', 1.0) # Keep for compatibility, or fix to 1.0/0.8
    min_confluence = params['min_confluence']"""
content = content.replace(run_bt_orig, run_bt_new)

# Update prices building to include Highs
prices_orig = """        # Current prices for MTM and closing
        current_prices = {}
        for ticker, df in df_dict.items():
            if date in df.index:
                current_prices[ticker] = df.loc[date, "Close"]

        def get_slippage(ticker):"""

prices_new = """        # Current prices for MTM and closing
        current_prices = {}
        current_highs = {}
        current_lows = {}
        for ticker, df in df_dict.items():
            if date in df.index:
                current_prices[ticker] = df.loc[date, "Close"]
                current_highs[ticker] = df.loc[date, "High"]
                current_lows[ticker] = df.loc[date, "Low"]

        def get_slippage(ticker):"""
content = content.replace(prices_orig, prices_new)

# Update daily_dd call
daily_dd_orig = "daily_dd = portfolio.update_daily(date_str, current_prices)"
daily_dd_new = "daily_dd = portfolio.update_daily(date_str, current_prices, current_highs)"
content = content.replace(daily_dd_orig, daily_dd_new)

# Modify closing logic
close_logic_orig = """        # 2. Close positions that have reached holding period
        for pos in list(portfolio.open_positions):
            if pos['days_held'] >= holding_days:
                ticker = pos['ticker']
                if ticker in current_prices:
                    exit_price_raw = current_prices[ticker]"""

close_logic_new = """        # 2. Dynamic Exit System (Trailing Stop, Hard Stop, Profit Target, Max Holding)
        for pos in list(portfolio.open_positions):
            ticker = pos['ticker']
            if ticker in current_prices:
                low = current_lows[ticker]
                high = current_highs[ticker]
                close = current_prices[ticker]

                # Check stops and targets
                # Initial Hard Stop: Entry - (Trailing_Mult * ATR_14)
                hard_stop = pos['entry_price'] - (atr_trailing_mult * pos['atr_14'])
                # Trailing Stop: Highest High - (Trailing_Mult * ATR_14)
                trailing_stop = pos['highest_high'] - (atr_trailing_mult * pos['atr_14'])

                actual_stop = max(hard_stop, trailing_stop)

                # Profit Target: Entry + (Profit_Mult * ATR_14)
                profit_target = pos['entry_price'] + (atr_profit_mult * pos['atr_14'])

                exit_price_raw = None

                # We check if Low hit the stop
                if low <= actual_stop:
                    # Execute at stop price (or open if it gapped down, simplified to stop price)
                    exit_price_raw = actual_stop
                # We check if High hit the profit target
                elif high >= profit_target:
                    exit_price_raw = profit_target
                # Guardrail: max holding days (30)
                elif pos['days_held'] >= 30:
                    exit_price_raw = close

                if exit_price_raw is not None:"""
content = content.replace(close_logic_orig, close_logic_new)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
