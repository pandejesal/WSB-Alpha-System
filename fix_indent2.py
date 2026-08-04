with open("scripts/comprehensive_backtest_report.py", "r") as f:
    lines = f.readlines()

for i in range(460, 480):
    lines[i] = lines[i].lstrip()
    if lines[i].startswith("portfolio.") or lines[i].startswith("return portfolio"):
        lines[i] = "    " + lines[i]
    elif lines[i].startswith("def calculate_metrics"):
        lines[i] = lines[i]
    elif lines[i].startswith("if not portfolio.history"):
        lines[i] = "    " + lines[i]
    elif lines[i].startswith("return {}"):
        lines[i] = "        " + lines[i]
    elif lines[i].startswith("hist_df = "):
        lines[i] = "    " + lines[i]
    elif lines[i].startswith("hist_df["):
        lines[i] = "    " + lines[i]
    elif lines[i].startswith("hist_df."):
        lines[i] = "    " + lines[i]
    elif lines[i].startswith("# Daily"):
        lines[i] = "    " + lines[i]

with open("scripts/comprehensive_backtest_report.py", "w") as f:
    f.writelines(lines)
