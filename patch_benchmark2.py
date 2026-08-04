import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Make sure spy_benchmark_portfolio.history gets appended to a separate file or passed as well
report_logic = """        "all_strategies": all_strategies,
        "benchmark_equity_curve": benchmark_history,
        "equity_curve": [{"date": r['date'], "equity": r['equity'], "deposits": r['deposits']} for r in best_portfolio.history],"""

content = re.sub(
    r"        \"all_strategies\": all_strategies,\n\s*\"equity_curve\": \[\{\"date\": r\['date'\], \"equity\": r\['equity'\], \"deposits\": r\['deposits'\]\} for r in best_portfolio.history\],",
    report_logic,
    content
)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
