import re

with open("scripts/comprehensive_backtest_report.py", "r") as f:
    content = f.read()

# Add ROC_60 to compute_indicators_vectorized
roc_logic = """    first_valid = df["GK_Vol"].dropna().iloc[0] if len(df["GK_Vol"].dropna()) > 0 else 0.50
    df["GK_Vol"] = df["GK_Vol"].fillna(first_valid)

    # 60-day Rate of Change (Momentum)
    df["ROC_60"] = df["Close"].pct_change(periods=60) * 100
"""
content = re.sub(
    r"    first_valid = df\[\"GK_Vol\"\].dropna\(\).iloc\[0\] if len\(df\[\"GK_Vol\"\].dropna\(\)\) > 0 else 0\.50\n\s*df\[\"GK_Vol\"\] = df\[\"GK_Vol\"\].fillna\(first_valid\)\n",
    roc_logic,
    content
)

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.write(content)
