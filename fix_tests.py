with open("src/backtest/run_historic_backtest.py", "r") as f:
    content = f.read()

# I see it's asking for custom_posts_df, stock_dfs_preloaded, and spy_close_preloaded in tests/test_backtest_real.py, but the function signature in src/backtest/run_historic_backtest.py was modified in PR 110. Oh wait, my task doesn't state I should fix origin/main tests, they are broken on main anyway. Let me verify tests on main.
