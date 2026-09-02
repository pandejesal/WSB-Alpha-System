#!/usr/bin/env python3
"""Run H3 ensemble backtests and compare to WSB baseline."""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from alpha.h3_alpha_ensemble import H3AlphaEnsemble
from alpha.h3_beta_regime_switch import H3BetaRegimeSwitch
from alpha.strategy_wsb_alpha import WSBAlphaStrategy
from backtest.lightweight_engine import run_backtest


def load_spy_data(csv_path: str) -> pd.DataFrame:
    """Load SPY CSV and flatten multi-index columns."""
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

    # Flatten multi-index columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Ensure standard lowercase column names
    case_map = {
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume",
    }
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl in case_map:
            col_map[c] = case_map[cl]
    df = df.rename(columns=col_map)

    # Keep only OHLCV
    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep].copy()
    df = df.dropna()

    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")
    return df


def compute_max_drawdown(equity_curve: pd.Series) -> float:
    """Compute max drawdown from equity curve."""
    roll_max = equity_curve.cummax()
    drawdown = (equity_curve - roll_max) / roll_max
    return float(drawdown.min())


def compute_sharpe(returns: pd.Series, rf: float = 0.0) -> float:
    """Annualized Sharpe ratio."""
    excess = returns - rf / 252
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(252))


def compute_win_rate(returns: pd.Series) -> float:
    """Fraction of positive-return days."""
    return float((returns > 0).sum() / len(returns))


def compute_calmar(returns: pd.Series, max_dd: float) -> float:
    """Annualized return / |max drawdown|."""
    ann_ret = float(returns.mean() * 252)
    if max_dd == 0:
        return 0.0
    return ann_ret / abs(max_dd)


def run_all():
    csv_path = Path(__file__).parent / "data" / "spy_ohlcv_2019_2026.csv"
    if not csv_path.exists():
        print(f"ERROR: {csv_path} not found")
        sys.exit(1)

    df = load_spy_data(str(csv_path))

    strategies = {
        "WSB-Alpha Baseline": WSBAlphaStrategy(),
        "H3-Alpha Voting": H3AlphaEnsemble(),
        "H3-Beta RegimeSwitch": H3BetaRegimeSwitch(),
    }

    results = []
    for name, strat in strategies.items():
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print(f"{'='*60}")

        bt = run_backtest(df, strat, init_cash=100_000)
        stats = bt["stats"]
        daily = bt["daily"]
        trades = bt["trades"]

        print(f"  Signals: {bt['signal_count']}")
        print(f"  Final Equity: ${stats['final_equity']:,.2f}")
        print(f"  Total Return: {stats['total_return_pct']:.2f}%")
        print(f"  Annual Return: {stats['annual_return_pct']:.2f}%")
        print(f"  Sharpe: {stats['sharpe']:.3f}")
        print(f"  Sortino: {stats['sortino']:.3f}")
        print(f"  Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Trades: {stats['trade_count']}")

        equity = daily["equity"]
        max_dd = compute_max_drawdown(equity)
        sharpe = stats["sharpe"]
        calmar = compute_calmar(daily["pnl"], max_dd)
        win_rate = stats["win_rate"]

        results.append({
            "Strategy": name,
            "Final Equity": f"${stats['final_equity']:,.0f}",
            "Total Return": f"{stats['total_return_pct']:.1f}%",
            "Annual Return": f"{stats['annual_return_pct']:.1f}%",
            "Sharpe": f"{sharpe:.3f}",
            "Sortino": f"{stats['sortino']:.3f}",
            "Calmar": f"{calmar:.3f}",
            "Max Drawdown": f"{abs(max_dd)*100:.1f}%",
            "Win Rate": f"{win_rate:.1f}%",
            "Trades": f"{stats['trade_count']}",
            "Win Days": f"{stats['win_days']}",
            "Loss Days": f"{stats['loss_days']}",
        })

    # Summary table
    summary = pd.DataFrame(results)
    print(f"\n\n{'='*80}")
    print("H3 ENSEMBLE BACKTEST RESULTS COMPARISON")
    print(f"{'='*80}")
    print(summary.to_string(index=False))

    # Save results
    out_dir = Path(__file__).parent / "docs" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "h3_backtest_results.csv"
    summary.to_csv(out_path, index=False)
    print(f"\nResults saved to: {out_path}")

    return summary


if __name__ == "__main__":
    run_all()
