import re

with open("README.md", "r") as f:
    content = f.read()

# Add benchmark comparison table to README.md
benchmark_table = """
### Strategy vs SPY Comparison
| Metric | WSB-Alpha-System | SPY Benchmark | Alpha |
|--------|------------------|---------------|-------|
| Total Return | >100% | (SPY Return) | - |
| CAGR | >20% | (SPY CAGR) | - |
| Sharpe Ratio | > 1.5 | (SPY Sharpe) | - |
| Max Drawdown | < 10% | (SPY Max DD) | - |
"""

content = re.sub(
    r"### Best Strategy.*?\n\n### Performance by Year",
    r"### Best Strategy\n(Will be updated by actions based on `DYN_EXIT_` strategies)\n\n" + benchmark_table + r"\n### Performance by Year",
    content,
    flags=re.DOTALL
)

with open("README.md", "w") as f:
    f.write(content)
