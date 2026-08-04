import json
import pandas as pd

with open('docs/data/backtest_report.json') as f:
    report = json.load(f)

with open('README.md', 'r') as f:
    readme = f.read()

section = f'''## Historical Backtest Results (2019-2026)

### Summary Table
| Metric | Value |
|--------|-------|
| Backtest Period | Jan 2019 – Aug 2026 |
| Initial Capital | $100 |
| Quarterly Deposit | $50 |
| Total Deposits | ${report["total_deposited"]} ({report["total_deposits"]} deposits) |
| Final Portfolio Value | ${report["portfolio_summary"]["final_equity"]:.2f} |
| Total Return | {report["portfolio_summary"]["total_return_pct"]:.2f}% |
| CAGR | {report["portfolio_summary"]["cagr"]:.2f}% |
| Max Drawdown | {report["portfolio_summary"]["max_drawdown_pct"]:.2f}% (on {report["portfolio_summary"]["max_drawdown_date"]}) |
| Sharpe Ratio | {report["portfolio_summary"]["sharpe_ratio"]:.2f} |
| Sortino Ratio | {report["portfolio_summary"]["sortino_ratio"]:.2f} |
| Win Rate | {report["portfolio_summary"]["win_rate"]:.1f}% |
| Total Trades | {report["portfolio_summary"]["total_trades"]} |
| Profit Factor | {report["portfolio_summary"]["profit_factor"]:.2f} |

### Best Strategy: {report["best_strategy"]["name"]}
- Parameters: holding_days={report["best_strategy"]["parameters"]["holding_days"]}, RSI=({report["best_strategy"]["parameters"]["rsi_bounds"][0]},{report["best_strategy"]["parameters"]["rsi_bounds"][1]}), GK_Vol={report["best_strategy"]["parameters"]["gk_limit"]}, min_confluence={report["best_strategy"]["parameters"]["min_confluence"]}
- Total Return: {report["portfolio_summary"]["total_return_pct"]:.2f}%
- Sharpe: {report["portfolio_summary"]["sharpe_ratio"]:.2f} | Sortino: {report["portfolio_summary"]["sortino_ratio"]:.2f} | Calmar: {report["portfolio_summary"]["calmar_ratio"]:.2f}
- Max Drawdown: {report["portfolio_summary"]["max_drawdown_pct"]:.2f}%
- Win Rate: {report["portfolio_summary"]["win_rate"]:.1f}% | Profit Factor: {report["portfolio_summary"]["profit_factor"]:.2f}
- Total Trades: {report["portfolio_summary"]["total_trades"]}
- Walk-Forward Efficiency: {report["best_strategy"]["overfitting"]["avg_wf_efficiency"]:.2f} (OOS Sharpe / IS Sharpe)
- Overfitting Risk: {'High' if report['best_strategy']['overfitting']['likely_overfit'] else 'Low'}

### Performance by Year
| Year | Return | Sharpe | Max DD | Trades | Win Rate |
|------|--------|--------|--------|--------|----------|
'''

hist = pd.DataFrame(report['equity_curve'])
hist['date'] = pd.to_datetime(hist['date'])
hist.set_index('date', inplace=True)

trades = pd.DataFrame(report['trade_log'])
if not trades.empty:
    trades['exit_date'] = pd.to_datetime(trades['exit_date'])

for year in range(2019, 2027):
    mask = hist.index.year == year
    if not mask.any(): continue

    year_data = hist.loc[mask].copy()
    start_eq = year_data['equity'].iloc[0]
    end_eq = year_data['equity'].iloc[-1]
    deposits_year = year_data['deposits'].iloc[-1] - year_data['deposits'].iloc[0]
    ret = (end_eq - (start_eq + deposits_year)) / (start_eq + deposits_year) * 100 if start_eq > 0 else 0

    year_data['ret'] = year_data['equity'].pct_change().fillna(0)
    year_data['dep_diff'] = year_data['deposits'].diff().fillna(0)
    dep_mask = year_data['dep_diff'] > 0
    if dep_mask.any():
        prev_eq = year_data['equity'].shift(1)
        year_data.loc[dep_mask, 'ret'] = (year_data.loc[dep_mask, 'equity'] - year_data.loc[dep_mask, 'dep_diff'] - prev_eq.loc[dep_mask]) / prev_eq.loc[dep_mask]

    rf_daily = 0.029/252
    excess = year_data['ret'] - rf_daily
    std = excess.std()
    sharpe = (excess.mean() / std * (252**0.5)) if std > 0 else 0

    cum = (1 + year_data['ret']).cumprod()
    rmax = cum.cummax()
    dd = (cum - rmax) / rmax
    max_dd = abs(dd.min()) * 100

    if not trades.empty:
        yr_trades = trades[trades['exit_date'].dt.year == year]
        num_trades = len(yr_trades)
        win_rate = (len(yr_trades[yr_trades['pnl']>0]) / num_trades * 100) if num_trades > 0 else 0
    else:
        num_trades = 0
        win_rate = 0

    section += f'| {year} | {ret:.1f}% | {sharpe:.2f} | {max_dd:.1f}% | {num_trades} | {win_rate:.1f}% |\n'

section += '''
### Performance by Regime
| Regime | Trades | Avg Return | Win Rate | Best Strategy |
|--------|--------|------------|----------|---------------|
'''
regimes = report['regime_breakdown']
for name, m in regimes.items():
    section += f'| {name.replace("_", " ").title()} | {m["trades"]} | {m["avg_return"]:.2f}% | {m["win_rate"]:.1f}% | {report["best_strategy"]["name"]} |\n'

overfit_count = sum(1 for s in report['all_strategies'] if s['metrics'].get('likely_overfit', True))
robust_count = sum(1 for s in report['all_strategies'] if s['metrics'].get('wf_efficiency', 0) >= 0.7)
avg_wf = sum(s['metrics'].get('wf_efficiency', 0) for s in report['all_strategies']) / len(report['all_strategies'])

section += f'''
### Overfitting Analysis
- Strategies tested: {report['strategies_tested']}
- Likely overfit (WF efficiency < 0.5): {overfit_count}
- Robust strategies (WF efficiency >= 0.7): {robust_count}
- Average walk-forward efficiency: {avg_wf:.2f}

### Assumptions
- Slippage: ATR(14) * 0.05, clamped 0.1%-2.5% of price per side
- Fees: $0 commission (Alpaca), SEC fee $0.000008 per $ sell-side, TAF $0.000166/share sell-side
- Spread: 0.05% liquid large-cap, 0.15% mid-cap
- Market impact: negligible at <$25 position sizes
- Risk-free rate: 2.0% (2019-2023), 4.5% (2024-2026)

### Limitations
- Survivorship bias: current ticker list used, delisted tickers excluded
- No intraday data, daily OHLCV only
- Spread modeled as fixed percentage, not actual bid-ask
- Slippage modeled as ATR-based, not actual fills
- Regulatory fees approximated
'''

new_readme = readme.replace('## Setup Instructions', section + '\n## Setup Instructions')

with open('README.md', 'w') as f:
    f.write(new_readme)

print('README updated')
