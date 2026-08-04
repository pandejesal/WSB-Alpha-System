import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Modify main() to calculate SPY EMA 200 and generate benchmark equity curve
main_replacement = """def main():
    logger.info("Starting Comprehensive Backtest Report Generation")
    tickers = load_universe()
    if not tickers:
        logger.error("No tickers found in universe.")
        return

    start_date = "2019-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    raw_data, spy_data = download_data(tickers, start_date, end_date)

    # Process SPY
    if isinstance(spy_data.columns, pd.MultiIndex):
        if 'Ticker' in spy_data.columns.names:
            spy_df = spy_data.xs('SPY', level='Ticker', axis=1)
        else:
            spy_df = spy_data.copy()
            spy_df.columns = spy_df.columns.get_level_values(0)
    else:
        spy_df = spy_data

    spy_df = spy_df.copy()
    spy_df['EMA_200'] = spy_df['Close'].ewm(span=200, adjust=False).mean()
    spy_df = spy_df[spy_df.index >= pd.to_datetime(start_date)]
"""

content = re.sub(
    r"def main\(\):.*?spy_df = spy_data\n",
    main_replacement,
    content,
    flags=re.DOTALL
)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
