"""FinGPT Sentiment Eval — run lexicon evaluation + optional overlay backtest.

Usage:
    python scripts/fingpt_eval.py                 # eval only
    python scripts/fingpt_eval.py --backtest      # eval + SPY overlay backtest

No API keys or network access required. All data is local or synthetic.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys

# Ensure repo root is on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.signals.fingpt_sentiment import (  # noqa: E402
    generate_synthetic_sentiment,
    map_sentiment_to_signal,
    run_evaluation,
)


def run_backtest(spy_csv: str, lookback: int = 5, noise_std: float = 0.1) -> dict:
    """Run sentiment overlay backtest on SPY data.

    WARNING: Uses SYNTHETIC sentiment derived from returns.
    Any backtest results are FRAUDULENT for alpha claims.
    This demonstrates overlay mechanics only.

    Args:
        spy_csv: Path to SPY OHLCV CSV.
        lookback: Lookback window for synthetic sentiment.
        noise_std: Noise std for synthetic sentiment.

    Returns:
        Dictionary with backtest results.
    """
    # Load SPY data
    dates = []
    closes = []
    with open(spy_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dates.append(row["Date"])
            closes.append(float(row["Close"]))

    if len(closes) < 2:
        return {"error": "Not enough data"}

    # Calculate returns
    returns = []
    for i in range(1, len(closes)):
        ret = (closes[i] - closes[i - 1]) / closes[i - 1]
        returns.append(ret)

    # Generate synthetic sentiment
    sentiments = generate_synthetic_sentiment(returns, lookback=lookback, noise_std=noise_std)

    # Run overlay backtest
    # Buy-and-hold baseline
    bh_value = 1.0
    bh_values = [bh_value]
    for ret in returns:
        bh_value *= (1 + ret)
        bh_values.append(bh_value)

    # Sentiment overlay: LONG when sentiment > 0.2, else FLAT
    overlay_value = 1.0
    overlay_values = [overlay_value]
    position = 0  # 0 = flat, 1 = long
    trades = 0

    for i, ret in enumerate(returns):
        sentiment = sentiments[i] if i < len(sentiments) else 0.0
        signal = map_sentiment_to_signal(sentiment)

        if signal["signal"] == "LONG" and position == 0:
            position = 1
            trades += 1
        elif signal["signal"] == "FLAT" and position == 1:
            position = 0
            trades += 1

        if position == 1:
            overlay_value *= (1 + ret)
        overlay_values.append(overlay_value)

    # Calculate metrics
    bh_total_return = (bh_values[-1] - 1.0) * 100
    overlay_total_return = (overlay_values[-1] - 1.0) * 100

    # Sharpe ratio (annualized, assuming 252 trading days)
    bh_returns = [(bh_values[i] - bh_values[i - 1]) / bh_values[i - 1]
                  for i in range(1, len(bh_values))]
    overlay_returns = [(overlay_values[i] - overlay_values[i - 1]) / overlay_values[i - 1]
                       for i in range(1, len(overlay_values))]

    def sharpe(rets: list) -> float:
        if len(rets) < 2:
            return 0.0
        mean_r = sum(rets) / len(rets)
        var_r = sum((r - mean_r) ** 2 for r in rets) / len(rets)
        std_r = math.sqrt(var_r) if var_r > 0 else 1e-10
        return (mean_r / std_r) * math.sqrt(252)

    # Max drawdown
    def max_drawdown(values: list) -> float:
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        return max_dd * 100

    bh_sharpe = sharpe(bh_returns)
    overlay_sharpe = sharpe(overlay_returns)
    bh_mdd = max_drawdown(bh_values)
    overlay_mdd = max_drawdown(overlay_values)

    return {
        "period": f"{dates[0]} to {dates[-1]}",
        "trading_days": len(returns),
        "buy_and_hold": {
            "total_return_pct": round(bh_total_return, 2),
            "sharpe": round(bh_sharpe, 3),
            "max_drawdown_pct": round(bh_mdd, 2),
        },
        "sentiment_overlay": {
            "total_return_pct": round(overlay_total_return, 2),
            "sharpe": round(overlay_sharpe, 3),
            "max_drawdown_pct": round(overlay_mdd, 2),
            "trades": trades,
            "lookback": lookback,
            "noise_std": noise_std,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FinGPT Sentiment Eval — lexicon evaluation + optional overlay backtest"
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run SPY overlay backtest after evaluation",
    )
    parser.add_argument(
        "--spy-csv",
        default=os.path.join(REPO_ROOT, "data", "spy_ohlcv_2019_2026.csv"),
        help="Path to SPY OHLCV CSV (default: data/spy_ohlcv_2019_2026.csv)",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=5,
        help="Lookback window for synthetic sentiment (default: 5)",
    )
    parser.add_argument(
        "--noise-std",
        type=float,
        default=0.1,
        help="Noise std for synthetic sentiment (default: 0.1)",
    )
    args = parser.parse_args()

    # === Evaluation ===
    print("=" * 60)
    print("FinGPT Sentiment Factor — Evaluation Report")
    print("=" * 60)
    print()

    result = run_evaluation()

    print(f"Total samples:  {result['total']}")
    print(f"Accuracy:       {result['accuracy']:.2%}")
    print(f"Macro F1:       {result['macro_f1']:.4f}")
    print()

    print("Per-label metrics:")
    print(f"  {'Label':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}")
    print(f"  {'-'*52}")
    for label, metrics in result["per_label"].items():
        print(
            f"  {label:<12} {metrics['precision']:>10.4f} {metrics['recall']:>10.4f} "
            f"{metrics['f1']:>10.4f} {metrics['support']:>10}"
        )
    print()

    cm = result["confusion"]
    print("Confusion matrix:")
    print(f"  True positives:  {cm['true_pos']}")
    print(f"  True negatives:  {cm['true_neg']}")
    print(f"  False positives: {cm['false_pos']}")
    print(f"  False negatives: {cm['false_neg']}")
    print()

    # === Backtest ===
    if args.backtest:
        print("=" * 60)
        print("SPY Sentiment Overlay Backtest (SYNTHETIC SENTIMENT)")
        print("WARNING: Results are FRAUDULENT for alpha claims.")
        print("=" * 60)
        print()

        if not os.path.exists(args.spy_csv):
            print(f"ERROR: SPY CSV not found at {args.spy_csv}")
            sys.exit(1)

        bt = run_backtest(args.spy_csv, lookback=args.lookback, noise_std=args.noise_std)

        print(f"Period:           {bt['period']}")
        print(f"Trading days:     {bt['trading_days']}")
        print()

        bh = bt["buy_and_hold"]
        ov = bt["sentiment_overlay"]

        print(f"{'Metric':<25} {'Buy & Hold':>15} {'Sentiment Overlay':>18}")
        print(f"{'-'*58}")
        print(f"{'Total Return':<25} {bh['total_return_pct']:>14.2f}% {ov['total_return_pct']:>17.2f}%")
        print(f"{'Sharpe Ratio':<25} {bh['sharpe']:>15.3f} {ov['sharpe']:>18.3f}")
        print(f"{'Max Drawdown':<25} {bh['max_drawdown_pct']:>14.2f}% {ov['max_drawdown_pct']:>17.2f}%")
        print(f"{'Trades':<25} {'N/A':>15} {ov['trades']:>18}")
        print(f"{'Lookback':<25} {'N/A':>15} {ov['lookback']:>18}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
