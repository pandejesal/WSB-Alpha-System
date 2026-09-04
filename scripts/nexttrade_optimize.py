#!/usr/bin/env python3
"""Genetic optimizer port of NextTrade optimization/index.ts.

NextTrade original: population of condition-parameter vectors, fitness in
{percent gain, sortino, sharpe, maxDrawdown}, train/validation split via
trainValidationRatio (default 0.8) + trainingWindowLength, mutation with
mutationProbability/mutationIntensity, crossover, eliteSpontaneousRatio,
validationFrequency. Workers run backtests in parallel.

This port: same search semantics, single-process, pandas, Alpaca-only data
(local CSVs, never network), chronological train/val split, fitness choice
identical, emits paper-only strategy YAML (never live).

Search space (MovingAverageCondition + allocation):
  window: int, standard_deviation: float (negative = below mean),
  statistic: {mean, low}, comparator fixed LTE, allocation: float

Usage:
  python scripts/nexttrade_optimize.py --symbol SPY --generations 5 --population 12 --seed 7
  python scripts/nexttrade_optimize.py --symbol SPY --emit-yaml strategies/nexttrade_ma_opt.yaml
"""
import argparse
import json
import random
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.backtest.nexttrade_backtest import (  # noqa: E402
    BacktestConfig,
    load_prices,
    run_composable_backtest,
)
from src.signals.nexttrade_conditions import MovingAverageCondition  # noqa: E402

SPACE = {
    "window": (3, 30),
    "standard_deviation": (-3.0, -0.25),
    "allocation": (1000.0, 10000.0),
}
STATISTICS = ("mean", "low")


def random_gene(rng: random.Random) -> dict:
    return {
        "window": rng.randint(*SPACE["window"]),
        "standard_deviation": round(rng.uniform(*SPACE["standard_deviation"]), 2),
        "allocation": round(rng.uniform(*SPACE["allocation"]), 0),
        "statistic": rng.choice(STATISTICS),
    }


def mutate(g: dict, rng: random.Random, prob: float, intensity: float) -> dict:
    g = dict(g)
    if rng.random() < prob:
        lo, hi = SPACE["window"]
        step = max(1, int((hi - lo) * intensity))
        g["window"] = int(min(hi, max(lo, g["window"] + rng.randint(-step, step))))
    if rng.random() < prob:
        lo, hi = SPACE["standard_deviation"]
        step = (hi - lo) * intensity
        g["standard_deviation"] = round(min(hi, max(lo, g["standard_deviation"] + rng.uniform(-step, step))), 2)
    if rng.random() < prob:
        lo, hi = SPACE["allocation"]
        step = (hi - lo) * intensity
        g["allocation"] = round(min(hi, max(lo, g["allocation"] + rng.uniform(-step, step))), 0)
    if rng.random() < prob * 0.5:
        g["statistic"] = rng.choice(STATISTICS)
    return g


def crossover(a: dict, b: dict, rng: random.Random) -> dict:
    return {k: rng.choice([a[k], b[k]]) for k in a}


FITNESS_KEY = {"sharpe": "sharpe", "sortino": "sortino", "return": "percent_change",
               "maxdd": "max_drawdown"}


def fitness_of(stats: dict, fitness: str) -> float:
    if fitness == "maxdd":
        return -stats["max_drawdown"]  # maximize negative drawdown
    return float(stats[FITNESS_KEY[fitness]])


def evaluate(gene: dict, prices, symbol: str, fitness: str):
    entry = MovingAverageCondition(window=gene["window"],
                                   standard_deviation=gene["standard_deviation"],
                                   statistic=gene["statistic"], comparator="LTE",
                                   symbol=symbol)
    cfg = BacktestConfig(symbol=symbol, allocation=gene["allocation"])
    res = run_composable_backtest(entry, prices, cfg)
    return fitness_of(res["stats"], fitness), res["stats"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="SPY")
    ap.add_argument("--generations", type=int, default=5)
    ap.add_argument("--population", type=int, default=12)
    ap.add_argument("--fitness", default="sharpe", choices=list(FITNESS_KEY))
    ap.add_argument("--train-ratio", type=float, default=0.8)
    ap.add_argument("--mutation-prob", type=float, default=0.15)
    ap.add_argument("--mutation-intensity", type=float, default=0.2)
    ap.add_argument("--elite-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--emit-yaml", default="")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    prices = load_prices(args.symbol, root=str(ROOT))
    n = len(prices)
    split = int(n * args.train_ratio)
    train, val = prices.iloc[:split], prices.iloc[split:]
    print(f"bars={n} train={len(train)} val={len(val)} symbol={args.symbol}")

    pop = [random_gene(rng) for _ in range(args.population)]
    best = None
    for gen in range(args.generations):
        scored = []
        for g in pop:
            f, _ = evaluate(g, train, args.symbol, args.fitness)
            scored.append((f, g))
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0]
        n_elite = max(1, int(args.population * args.elite_ratio))
        elites = [g for _, g in scored[:n_elite]]
        children = list(elites)
        while len(children) < args.population:
            a, b = rng.choice(elites), rng.choice(elites)
            child = mutate(crossover(a, b, rng), rng, args.mutation_prob,
                           args.mutation_intensity)
            children.append(child)
        pop = children
        ftr, _ = evaluate(best[1], train, args.symbol, args.fitness)
        fva, sva = evaluate(best[1], val, args.symbol, args.fitness)
        print(f"gen={gen} train_fit={ftr:.3f} val_fit={fva:.3f} "
              f"val_sharpe={sva['sharpe']:.3f} val_dd={sva['max_drawdown']:.3f} "
              f"gene={best[1]}")

    ftr, str_ = evaluate(best[1], train, args.symbol, args.fitness)
    fva, sva = evaluate(best[1], val, args.symbol, args.fitness)
    out = {"gene": best[1], "train_fitness": ftr, "val_fitness": fva,
           "train_stats": str_, "val_stats": sva, "fitness": args.fitness,
           "status": "paper", "venue": "alpaca", "live": False}
    print(json.dumps(out, indent=2))
    if args.emit_yaml:
        from datetime import date
        g = best[1]
        yaml_text = f"""# NextTrade-port optimized composable strategy (PAPER ONLY, Alpaca)
# Generated by scripts/nexttrade_optimize.py — never auto-promote to live.
id: nexttrade_ma_opt_{args.symbol.lower()}
name: NextTrade MA Opt {args.symbol}
family: mean_reversion
venue: alpaca
universe: "{args.symbol} daily OHLC (local CSV, Alpaca-compatible)"
pre_registration_ref: "docs/NEXTTRADE_PORT.md"
gates_passed: "0/5"
verdict: "UNVERIFIED_PAPER"
eval_records: "docs/data/nexttrade_opt_{args.symbol.lower()}.json"
signal:
  entry: "close LTE ({g['statistic']} {g['window']}d + {g['standard_deviation']} sd), T+1, long/flat"
  exit: "exit when entry false"
  sizing: "fixed ${g['allocation']:.0f} notional, buying-power capped, fail-closed"
  caps:
    max_concurrent_positions: 1
  rebalance: "daily"
parameters:
  window: {g['window']}
  standard_deviation: {g['standard_deviation']}
  statistic: "{g['statistic']}"
  allocation: {g['allocation']:.0f}
  train_ratio: {args.train_ratio}
  fitness: "{args.fitness}"
  seed: {args.seed}
indicators:
  - "rolling {g['statistic']} + sd band (shifted 1, no lookahead)"
fee_model:
  commission: "$0 (Alpaca)"
  slippage: "5 bps"
  settlement: "T+1"
benchmark_result:
  benchmark: "SPY"
  full: "val Sharpe {sva['sharpe']:.2f}, excess {sva['excess_percent']:.1f}% vs buy-hold (same window)"
robustness_notes:
  - "train/val split {args.train_ratio}; optimizer fitness only — still needs 5-gate validation"
  - "date: {date.today().isoformat()}"
risks:
  - "mean-reversion fails in trends; single-name concentration"
version: 1
status: "paper"
"""
        p = ROOT / args.emit_yaml
        p.write_text(yaml_text, encoding="utf-8")
        (ROOT / f"docs/data/nexttrade_opt_{args.symbol.lower()}.json").write_text(
            json.dumps(out, indent=2), encoding="utf-8")
        print(f"wrote {p} (paper only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
