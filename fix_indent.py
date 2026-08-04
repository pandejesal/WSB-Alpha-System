with open("scripts/comprehensive_backtest_report.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "gk = df.loc[prev_date" in line:
        print(f"Line {i+1}: {repr(line)}")
    if "if gk < 0.20:" in line:
        print(f"Line {i+1}: {repr(line)}")
