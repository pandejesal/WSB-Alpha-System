import json

with open("docs/data/backtest_report.json", "r") as f:
    data = json.load(f)
    print("Strategy sharpe:", data["portfolio_summary"]["sharpe_ratio"])
    print("SPY benchmark sharpe:", data["benchmark_comparison"]["spy_sharpe"])
