with open("scripts/comprehensive_backtest_report.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "final_date_str =" in line:
        lines[i] = "    " + line.lstrip()
    elif "portfolio.liquidate_all(" in line and i > 400 and i < 500:
        lines[i] = "    " + line.lstrip()
    elif "portfolio.update_daily(final_date_str" in line:
        lines[i] = "    " + line.lstrip()

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.writelines(lines)
