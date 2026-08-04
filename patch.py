import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Update download_data SPY fetch
content = re.sub(
    r"spy_data = yf\.download\('SPY', start=start_date, end=end_date, auto_adjust=False\)",
    r"spy_data = yf.download('SPY', start='2018-01-01', end=end_date, auto_adjust=False)",
    content
)

content = re.sub(
    r"spy_returns = np\.random\.normal\(0\.0005, 0\.01, len\(dates\)\)\n\s*spy_prices = 100 \* np\.exp\(np\.cumsum\(spy_returns\)\)\n\s*spy_data = pd\.DataFrame\(\{'Close': spy_prices\}, index=dates\)",
    r"spy_dates = pd.date_range(start='2018-01-01', end=end_date, freq='B')\n        spy_returns = np.random.normal(0.0005, 0.01, len(spy_dates))\n        spy_prices = 100 * np.exp(np.cumsum(spy_returns))\n        spy_data = pd.DataFrame({'Close': spy_prices}, index=spy_dates)",
    content
)

# Benchmark calculation logic - we need to update SPY with EMA 200 and create a benchmark portfolio inside main() or calculate_metrics
with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
