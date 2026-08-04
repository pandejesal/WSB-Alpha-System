import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Add benchmark logic in main() right after spy_df processing
benchmark_logic = """    # Calculate SPY Benchmark Equity Curve
    spy_benchmark_portfolio = Portfolio(initial_capital=100)

    # We need to compute SPY shares properly based on deposits
    benchmark_history = []

    deposit_schedule = get_deposit_schedule(start_date, end_date, 50, 'quarterly')

    spy_trading_days = spy_df.index
    spy_qty = 0
    cash = 100

    for i, date in enumerate(spy_trading_days):
        date_str = date.strftime('%Y-%m-%d')

        # Add deposits
        if date_str in deposit_schedule:
            cash += deposit_schedule[date_str]
            spy_benchmark_portfolio.total_deposits += deposit_schedule[date_str]
            spy_benchmark_portfolio.deposits_count += 1

        current_price = spy_df.loc[date, 'Close']

        # If we have cash, buy SPY (fractional shares allowed for benchmark simplicity)
        if cash > 0:
            spy_qty += cash / current_price
            cash = 0

        equity = cash + spy_qty * current_price

        benchmark_history.append({
            'date': date_str,
            'equity': equity,
            'cash': cash,
            'deposits': spy_benchmark_portfolio.initial_capital + spy_benchmark_portfolio.total_deposits
        })

    spy_benchmark_portfolio.history = benchmark_history
    spy_metrics = calculate_metrics(spy_benchmark_portfolio, spy_df)
"""

content = re.sub(
    r"    spy_df = spy_df\[spy_df\.index >= pd\.to_datetime\(start_date\)\]\n",
    r"    spy_df = spy_df[spy_df.index >= pd.to_datetime(start_date)]\n\n" + benchmark_logic,
    content
)

# Pass spy_metrics to report JSON
report_logic = """    report = {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "period": {"start": start_date, "end": end_date},
        "initial_capital": 100,
        "quarterly_deposit": 50,
        "total_deposits": best_portfolio.deposits_count,
        "total_deposited": best_portfolio.total_deposits,
        "strategies_tested": 90,"""

content = re.sub(
    r"    report = \{\n\s*\"report_date\".*?\"strategies_tested\": 90,",
    report_logic,
    content,
    flags=re.DOTALL
)

bench_compare_logic = """        "best_strategy": {
            "name": best_name,
            "parameters": best_params,
            "overfitting": best_overfitting
        },
        "benchmark_comparison": {
            "strategy_return_pct": best_metrics["total_return_pct"],
            "spy_return_pct": spy_metrics["total_return_pct"],
            "alpha_return_pct": best_metrics["total_return_pct"] - spy_metrics["total_return_pct"],
            "strategy_cagr": best_metrics["cagr"],
            "spy_cagr": spy_metrics["cagr"],
            "strategy_sharpe": best_metrics["sharpe"],
            "spy_sharpe": spy_metrics["sharpe"],
            "strategy_max_dd_pct": best_metrics["max_drawdown_pct"],
            "spy_max_dd_pct": spy_metrics["max_drawdown_pct"]
        },
        "portfolio_summary": {"""

content = re.sub(
    r"        \"best_strategy\": \{\n.*?\},\n\s*\"portfolio_summary\": \{",
    bench_compare_logic,
    content,
    flags=re.DOTALL
)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
