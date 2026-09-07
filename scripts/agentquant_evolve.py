#!/usr/bin/env python3
"""
AgentQuant Evolution Runner
===========================

Entry point for the AgentQuant grid-based evolution pipeline.
Loads SPY data, runs regime detection, evolves strategy parameters,
and outputs results to console and JSON.

Usage:
    PYTHONPATH=. python scripts/agentquant_evolve.py
    PYTHONPATH=. python scripts/agentquant_evolve.py --family momentum --generations 10
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.signals.agentquant_regime import detect_regime_full, compute_regime_features
from src.evolution.agentquant_harness import HarnessEvolution
from src.evolution.agentquant_critic import CriticAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("agentquant_evolve")

DEFAULT_DATA_PATH = "data/spy_ohlcv_2019_2026.csv"
DEFAULT_OUTPUT_DIR = "output/agentquant"


def load_spy_data(path: str = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """
    Load SPY OHLCV data from CSV.
    Handles the quoted column format: "('Close', 'SPY')".
    """
    csv_path = Path(path)
    if not csv_path.exists():
        logger.error("Data file not found: %s", csv_path.absolute())
        sys.exit(1)

    df = pd.read_csv(csv_path)
    # Normalize column names: remove quotes and SPY suffix
    df.columns = [c.strip().strip("'\"") for c in df.columns]
    rename_map = {}
    for col in df.columns:
        if "Close" in col:
            rename_map[col] = "Close"
        elif "High" in col:
            rename_map[col] = "High"
        elif "Low" in col:
            rename_map[col] = "Low"
        elif "Open" in col:
            rename_map[col] = "Open"
        elif "Volume" in col:
            rename_map[col] = "Volume"
        elif "Date" in col:
            rename_map[col] = "Date"
    df = df.rename(columns=rename_map)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date")

    df = df.sort_index()
    logger.info("Loaded %d rows from %s", len(df), csv_path.name)
    return df


def run_evolution(
    df: pd.DataFrame,
    families: list[str],
    generations: int,
    population_size: int,
    random_seed: int | None,
) -> dict:
    """
    Run the full AgentQuant evolution pipeline:
      1. Compute regime features
      2. Detect current regime
      3. Evolve strategy parameters
      4. Critique best candidates
      5. Report results
    """
    # --- Regime detection ---
    logger.info("Computing regime features...")
    regime_features = compute_regime_features(df)
    regime = detect_regime_full(regime_features)
    logger.info("Current regime: %s (confidence=%.0f%%)", regime.regime_label, regime.regime_confidence * 100)

    # --- Evolution ---
    logger.info("Starting evolution...")
    evo = HarnessEvolution(
        families=families,
        population_size=population_size,
        generations=generations,
        n_splits=5,
        train_ratio=0.7,
        initial_cash=100_000.0,
        slippage_bps=5.0,
        random_seed=random_seed,
    )
    best = evo.evolve(df)

    # --- Critique ---
    logger.info("Running critic on top candidates...")
    critic = CriticAgent(min_wfe=0.3, min_trades=10)

    # Critique the final best
    verdict = critic.critique(
        genome_id=f"best_gen{generations-1}",
        params=best.params,
        family=best.strategy_family,
        fitness=best.fitness,
        sharpe_test=best.sharpe_test,
        walk_forward_efficiency=best.walk_forward_efficiency,
        trade_count=best.trade_count,
    )

    # --- SPY buy-hold baseline ---
    spy_returns = df["Close"].pct_change().fillna(0.0)
    spy_equity = 100_000.0 * (1 + spy_returns).cumprod()
    spy_sharpe = float(
        spy_returns.mean() / spy_returns.std() * (252 ** 0.5)
    ) if spy_returns.std() > 0 else 0.0
    spy_max_dd = float(
        abs(((spy_equity - spy_equity.cummax()) / spy_equity.cummax()).min())
    )

    # --- Results ---
    results = {
        "timestamp": datetime.now().isoformat(),
        "regime": {
            "label": regime.regime_label,
            "confidence": round(regime.regime_confidence, 3),
            "vol_percentile_252d": round(regime.vol_percentile_252d, 1),
            "momentum_63d": round(regime.momentum_63d, 4),
        },
        "best_genome": best.to_dict(),
        "critic_verdict": {
            "approved": verdict.approved,
            "reason": verdict.reason,
        },
        "spy_baseline": {
            "sharpe": round(spy_sharpe, 3),
            "max_drawdown": round(spy_max_dd, 4),
            "total_return_pct": round(float((spy_equity.iloc[-1] / 100_000 - 1) * 100), 2),
        },
        "evolution_history": evo.history,
        "families_evolved": families,
        "config": {
            "generations": generations,
            "population_size": population_size,
            "n_splits": 5,
            "slippage_bps": 5.0,
            "initial_cash": 100_000.0,
        },
    }

    return results


def print_results(results: dict) -> None:
    """Pretty-print key results to console."""
    print("\n" + "=" * 60)
    print("  AGENTQUANT EVOLUTION RESULTS")
    print("=" * 60)

    regime = results["regime"]
    print(f"\n  Regime:         {regime['label']} (confidence {regime['confidence']*100:.0f}%)")
    print(f"  Vol Percentile: {regime['vol_percentile_252d']:.0f}th")
    print(f"  63d Momentum:   {regime['momentum_63d']*100:.1f}%")

    best = results["best_genome"]
    print(f"\n  Best Strategy:  {best['strategy_family']}")
    print(f"  Parameters:     {json.dumps(best['params'], indent=4)}")
    print(f"  Fitness:        {best['fitness']:.4f}")
    print(f"  Sharpe (OOS):   {best['sharpe_test']:.3f}")
    print(f"  Sharpe (Train): {best['sharpe_train']:.3f}")
    print(f"  Sortino:        {best['sortino']:.3f}")
    print(f"  Max Drawdown:   {best['max_drawdown']:.4f}")
    print(f"  Win Rate:       {best['win_rate']:.1%}")
    print(f"  Profit Factor:  {best['profit_factor']:.2f}")
    print(f"  Trade Count:    {best['trade_count']}")
    print(f"  WFE:            {best['walk_forward_efficiency']:.3f}")

    spy = results["spy_baseline"]
    print("\n  SPY Baseline:")
    print(f"    Sharpe:       {spy['sharpe']:.3f}")
    print(f"    Max Drawdown: {spy['max_drawdown']:.4f}")
    print(f"    Total Return: {spy['total_return_pct']:.1f}%")

    verdict = results["critic_verdict"]
    status = "APPROVED" if verdict["approved"] else "REJECTED"
    print(f"\n  Critic Verdict: {status}")
    print(f"  Reason:         {verdict['reason']}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="AgentQuant Grid-Based Strategy Evolution"
    )
    parser.add_argument(
        "--data",
        default=DEFAULT_DATA_PATH,
        help="Path to SPY OHLCV CSV (default: data/spy_ohlcv_2019_2026.csv)",
    )
    parser.add_argument(
        "--family",
        nargs="+",
        default=None,
        help="Strategy family(ies) to evolve (default: all)",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=5,
        help="Number of evolution generations (default: 5)",
    )
    parser.add_argument(
        "--population",
        type=int,
        default=20,
        help="Population size per generation (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: output/agentquant/results_<timestamp>.json)",
    )
    args = parser.parse_args()

    df = load_spy_data(args.data)

    results = run_evolution(
        df=df,
        families=args.family,
        generations=args.generations,
        population_size=args.population,
        random_seed=args.seed,
    )

    print_results(results)

    # Save JSON
    output_dir = Path(DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"results_{ts}.json"

    # Convert non-serializable types
    def _serialize(obj):
        if hasattr(obj, "item"):
            return obj.item()
        if hasattr(obj, "tolist"):
            return obj.tolist()
        return str(obj)

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=_serialize)

    logger.info("Results saved to %s", out_path)


if __name__ == "__main__":
    main()
