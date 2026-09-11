"""
AgentQuant Harness Evolution — Grid-Based Strategy Optimization
===============================================================

Ported from AgentQuant's src/agent/harness_evolution_algo.py.
Evolves strategy parameters via grid sampling + walk-forward validation.
No LLM dependency; no network calls. All local CSV data only.

Key components:
  - HarnessGenome: candidate solution encoding strategy parameters
  - HarnessEvolution: orchestrates grid search, crossover, mutation
  - Walk-forward evaluation with T+1 enforcement
"""

import copy
import logging
import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# R-C3 reference-only: canonical commission lives in config/risk_config.py
# (single source; numeric value unchanged at 1.0bp).
try:
    from config.risk_config import CANONICAL_COMMISSION_BPS as _CANONICAL_COMMISSION_BPS
except Exception:
    _CANONICAL_COMMISSION_BPS = 1.0


# ---------------------------------------------------------------------------
# Strategy parameter grids (ported from AgentQuant parameter_grid.py)
# ---------------------------------------------------------------------------

DEFAULT_GRIDS: dict[str, dict[str, list]] = {
    "momentum": {
        "lookback": [10, 20, 30, 50, 60, 80, 100],
        "forward_return_days": [5, 10, 15, 20, 30],
        "entry_threshold": [0.01, 0.02, 0.03, 0.05],
        "exit_threshold": [-0.01, -0.02, -0.03],
    },
    "mean_reversion": {
        "lookback": [10, 15, 20, 30, 50],
        "z_entry": [1.0, 1.5, 2.0, 2.5],
        "z_exit": [0.0, 0.5],
        "stop_loss_z": [3.0, 3.5, 4.0],
    },
    "volatility": {
        "vol_lookback": [10, 15, 20, 30, 60],
        "target_vol": [0.10, 0.15, 0.20, 0.25],
        "max_leverage": [1.0, 1.5, 2.0],
        "vol_scale_factor": [0.5, 1.0, 1.5],
    },
    "trend_following": {
        "short_window": [5, 10, 15, 20],
        "medium_window": [30, 40, 50, 60],
        "long_window": [100, 150, 200],
        "adx_threshold": [20, 25, 30],
    },
    "breakout": {
        "lookback": [10, 20, 30, 50],
        "entry_std_mult": [1.5, 2.0, 2.5, 3.0],
        "exit_std_mult": [0.5, 1.0, 1.5],
        "volume_confirm": [True, False],
    },
}


# ---------------------------------------------------------------------------
# HarnessGenome — candidate solution
# ---------------------------------------------------------------------------

@dataclass
class HarnessGenome:
    """
    Encodes a single strategy candidate's parameters.
    Ported from AgentQuant's HarnessGenome.
    """
    strategy_family: str = "momentum"
    params: dict[str, Any] = field(default_factory=dict)
    fitness: float = 0.0
    sharpe_train: float = 0.0
    sharpe_test: float = 0.0
    sortino: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    trade_count: int = 0
    walk_forward_efficiency: float = 0.0
    regime_label: str = "Unknown"

    def to_dict(self) -> dict:
        return {
            "strategy_family": self.strategy_family,
            "params": self.params,
            "fitness": self.fitness,
            "sharpe_train": self.sharpe_train,
            "sharpe_test": self.sharpe_test,
            "sortino": self.sortino,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "trade_count": self.trade_count,
            "walk_forward_efficiency": self.walk_forward_efficiency,
            "regime_label": self.regime_label,
        }


# ---------------------------------------------------------------------------
# Grid sampler
# ---------------------------------------------------------------------------

def sample_grid(family: str, grid: dict[str, list] | None = None) -> dict[str, Any]:
    """
    Randomly sample one parameter combination from the grid for a given family.

    Args:
        family: Strategy family name (e.g. "momentum", "mean_reversion").
        grid: Override grid dict. If None, uses DEFAULT_GRIDS.

    Returns:
        Dict of sampled parameter values.
    """
    if grid is None:
        grid = DEFAULT_GRIDS
    if family not in grid:
        raise ValueError(f"Unknown strategy family: {family}. Available: {list(grid.keys())}")
    return {k: random.choice(v) for k, v in grid[family].items()}


def mutate_grid_params(
    params: dict[str, Any],
    family: str,
    grid: dict[str, list] | None = None,
    mutation_rate: float = 0.3,
) -> dict[str, Any]:
    """
    Mutate a parameter dict by randomly replacing values from the grid.

    Args:
        params: Current parameter dict.
        family: Strategy family name.
        grid: Override grid dict.
        mutation_rate: Probability of mutating each parameter.

    Returns:
        New parameter dict with mutations applied.
    """
    if grid is None:
        grid = DEFAULT_GRIDS
    if family not in grid:
        return params.copy()

    mutated = params.copy()
    for k, v in grid[family].items():
        if random.random() < mutation_rate:
            mutated[k] = random.choice(v)
    return mutated


def crossover_grid_params(
    params_a: dict[str, Any],
    params_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Uniform crossover between two parameter dicts.
    Each parameter is randomly inherited from one parent.
    """
    child = {}
    all_keys = set(params_a.keys()) | set(params_b.keys())
    for k in all_keys:
        if k in params_a and k in params_b:
            child[k] = random.choice([params_a[k], params_b[k]])
        elif k in params_a:
            child[k] = params_a[k]
        else:
            child[k] = params_b[k]
    return child


# ---------------------------------------------------------------------------
# Backtesting core
# ---------------------------------------------------------------------------

def _compute_returns(prices: pd.Series) -> pd.Series:
    """Simple daily returns."""
    return prices.pct_change().dropna()


def _apply_t1_signals(signals: pd.Series) -> pd.Series:
    """
    Enforce T+1 execution: shift signals forward by 1 day.
    Signal on day t determines position held on day t+1.
    """
    return signals.shift(1).fillna(0.0)


def backtest_strategy(
    df: pd.DataFrame,
    params: dict[str, Any],
    family: str,
    initial_cash: float = 100_000.0,
    slippage_bps: float = 5.0,
    commission_bps: float = _CANONICAL_COMMISSION_BPS,
) -> dict[str, Any]:
    """
    Simple vectorized backtest for a given strategy family and parameters.

    Args:
        df: DataFrame with at least 'Close' column and optional derived columns.
        params: Strategy parameters.
        family: Strategy family name.
        initial_cash: Starting capital.
        slippage_bps: Slippage in basis points (default 5 bps per brief).
        commission_bps: Commission in basis points.

    Returns:
        Dict with keys: equity_curve, returns, sharpe, sortino, max_drawdown,
        win_rate, profit_factor, trade_count.
    """
    close = df["Close"].copy()
    signals = _generate_signals(df, params, family)
    signals = _apply_t1_signals(signals)

    # Compute daily returns
    daily_ret = close.pct_change().fillna(0.0)

    # Position returns (signal * next-day return, already shifted)
    strategy_ret = signals * daily_ret

    # Slippage and commission on signal changes
    signal_changes = signals.diff().fillna(0.0).abs()
    cost = signal_changes * (slippage_bps + commission_bps) / 10_000.0
    strategy_ret = strategy_ret - cost

    # Equity curve
    equity = initial_cash * (1 + strategy_ret).cumprod()

    # Metrics
    sharpe = _compute_sharpe(strategy_ret)
    sortino = _compute_sortino(strategy_ret)
    max_dd = _compute_max_drawdown(equity)
    win_rate = float((strategy_ret[strategy_ret != 0] > 0).mean()) if (strategy_ret != 0).any() else 0.0
    profit_factor = _compute_profit_factor(strategy_ret)
    trade_count = int(signal_changes.sum() / 2)  # round-trips

    return {
        "equity_curve": equity,
        "returns": strategy_ret,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "trade_count": trade_count,
    }


def _generate_signals(
    df: pd.DataFrame,
    params: dict[str, Any],
    family: str,
) -> pd.Series:
    """
    Generate position signals (1 = long, 0 = flat) for a given strategy family.
    All logic uses .shift() where needed to prevent lookahead bias.
    """
    close = df["Close"]
    signals = pd.Series(0.0, index=df.index)

    if family == "momentum":
        lookback = int(params.get("lookback", 20))
        entry_thresh = float(params.get("entry_threshold", 0.02))
        exit_thresh = float(params.get("exit_threshold", -0.01))

        mom = close.pct_change(lookback).shift(1)  # shift to prevent lookahead
        signals = pd.Series(0.0, index=df.index)
        in_position = False
        for i in range(lookback + 1, len(df)):
            m = mom.iloc[i]
            if pd.isna(m):
                continue
            if not in_position and m > entry_thresh:
                in_position = True
            elif in_position and m < exit_thresh:
                in_position = False
            signals.iloc[i] = 1.0 if in_position else 0.0

    elif family == "mean_reversion":
        lookback = int(params.get("lookback", 20))
        z_entry = float(params.get("z_entry", 2.0))
        z_exit = float(params.get("z_exit", 0.0))

        roll_mean = close.rolling(lookback).mean()
        roll_std = close.rolling(lookback).std()
        z = ((close - roll_mean) / (roll_std + 1e-12)).shift(1)
        signals = pd.Series(0.0, index=df.index)
        in_position = False
        for i in range(lookback + 1, len(df)):
            z_val = z.iloc[i]
            if pd.isna(z_val):
                continue
            if not in_position and z_val < -z_entry:
                in_position = True
            elif in_position and z_val > -z_exit:
                in_position = False
            signals.iloc[i] = 1.0 if in_position else 0.0

    elif family == "trend_following":
        sw = int(params.get("short_window", 10))
        mw = int(params.get("medium_window", 50))
        lw = int(params.get("long_window", 200))

        sma_short = close.rolling(sw).mean()
        sma_med = close.rolling(mw).mean()
        sma_long = close.rolling(lw).mean()

        # Enforce sw < mw < lw
        if not (sw < mw < lw):
            sw, mw, lw = sorted([sw, mw, lw])

        # Trend = short > medium > long (all above long)
        trend = ((sma_short > sma_med) & (sma_med > sma_long)).astype(float)
        signals = trend.shift(1).fillna(0.0)

    elif family == "volatility":
        vol_lookback = int(params.get("vol_lookback", 20))
        target_vol = float(params.get("target_vol", 0.15))
        max_lev = float(params.get("max_leverage", 1.0))

        daily_ret = close.pct_change()
        realized_vol = daily_ret.rolling(vol_lookback).std() * np.sqrt(252)
        vol_scale = target_vol / (realized_vol + 1e-12)
        vol_scale = vol_scale.clip(upper=max_lev).shift(1).fillna(0.0)
        signals = (vol_scale > 0.3).astype(float)  # only long when vol budget allows

    elif family == "breakout":
        lookback = int(params.get("lookback", 20))
        entry_mult = float(params.get("entry_std_mult", 2.0))
        exit_mult = float(params.get("exit_std_mult", 1.0))

        roll_mean = close.rolling(lookback).mean()
        roll_std = close.rolling(lookback).std()
        upper = roll_mean + entry_mult * roll_std
        lower = roll_mean - exit_mult * roll_std

        signals = pd.Series(0.0, index=df.index)
        in_position = False
        for i in range(lookback + 1, len(df)):
            c = close.iloc[i]
            u = upper.iloc[i]
            lo = lower.iloc[i]
            if pd.isna(u) or pd.isna(lo):
                continue
            if not in_position and c > u:
                in_position = True
            elif in_position and c < lo:
                in_position = False
            signals.iloc[i] = 1.0 if in_position else 0.0
    else:
        logger.warning("Unknown family %s, returning flat signals", family)

    return signals


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def _compute_sharpe(returns: pd.Series, rf: float = 0.0, annualize: bool = True) -> float:
    """Annualized Sharpe ratio."""
    if returns.empty or returns.std() == 0:
        return 0.0
    excess = returns - rf / 252
    sharpe = excess.mean() / excess.std()
    return float(sharpe * np.sqrt(252)) if annualize else float(sharpe)


def _compute_sortino(returns: pd.Series, rf: float = 0.0) -> float:
    """Annualized Sortino ratio (penalizes downside only)."""
    if returns.empty:
        return 0.0
    excess = returns - rf / 252
    downside = excess[excess < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    sortino = excess.mean() / downside.std()
    return float(sortino * np.sqrt(252))


def _compute_max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown as a positive fraction (0.0 = no drawdown)."""
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(abs(dd.min()))


def _compute_profit_factor(returns: pd.Series) -> float:
    """Gross profit / gross loss."""
    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


# ---------------------------------------------------------------------------
# Walk-forward evaluation
# ---------------------------------------------------------------------------

def walk_forward_eval(
    df: pd.DataFrame,
    params: dict[str, Any],
    family: str,
    n_splits: int = 5,
    train_ratio: float = 0.7,
    initial_cash: float = 100_000.0,
    slippage_bps: float = 5.0,
) -> dict[str, Any]:
    """
    Walk-forward evaluation with train/test split per window.

    Args:
        df: Full DataFrame with OHLCV data.
        params: Strategy parameters.
        family: Strategy family name.
        n_splits: Number of walk-forward windows.
        train_ratio: Fraction of each window used for training.
        initial_cash: Starting capital.
        slippage_bps: Slippage in basis points.

    Returns:
        Dict with train_sharpe, test_sharpe, walk_forward_efficiency,
        per-window results.
    """
    total_len = len(df)
    window_size = total_len // n_splits

    if window_size < 50:
        logger.warning("Window too small (%d rows). Falling back to single split.", window_size)
        n_splits = 1
        window_size = total_len

    train_sharpes = []
    test_sharpes = []
    window_results = []

    for i in range(n_splits):
        start = i * window_size
        end = min(start + window_size, total_len)
        window_df = df.iloc[start:end].copy()

        if len(window_df) < 30:
            continue

        split_idx = int(len(window_df) * train_ratio)
        train_df = window_df.iloc[:split_idx]
        test_df = window_df.iloc[split_idx:]

        if len(train_df) < 20 or len(test_df) < 10:
            continue

        train_res = backtest_strategy(train_df, params, family, initial_cash, slippage_bps)
        test_res = backtest_strategy(test_df, params, family, initial_cash, slippage_bps)

        train_sharpes.append(train_res["sharpe"])
        test_sharpes.append(test_res["sharpe"])

        window_results.append({
            "window": i,
            "train_sharpe": train_res["sharpe"],
            "test_sharpe": test_res["sharpe"],
            "train_len": len(train_df),
            "test_len": len(test_df),
        })

    avg_train = float(np.mean(train_sharpes)) if train_sharpes else 0.0
    avg_test = float(np.mean(test_sharpes)) if test_sharpes else 0.0
    wfe = avg_test / avg_train if avg_train > 0 else 0.0

    return {
        "train_sharpe": avg_train,
        "test_sharpe": avg_test,
        "walk_forward_efficiency": wfe,
        "n_windows": len(window_results),
        "windows": window_results,
    }


# ---------------------------------------------------------------------------
# Fitness scoring (no LLM)
# ---------------------------------------------------------------------------

def compute_fitness(genome: HarnessGenome) -> float:
    """
    Compute fitness score for a genome. No LLM involved.

    Fitness = weighted combination of:
      - OOS Sharpe (40%)
      - Sortino (15%)
      - Calmar proxy via 1-max_dd (10%)
      - Win rate (10%)
      - Profit factor (10%)
      - Walk-forward efficiency (15%)
    """
    oos = max(0.0, min(genome.sharpe_test, 3.0)) / 3.0
    sortino = max(0.0, min(genome.sortino, 5.0)) / 5.0
    dd_consistency = max(0.0, 1.0 - genome.max_drawdown)
    win = max(0.0, min(genome.win_rate, 1.0))
    pf = max(0.0, min(genome.profit_factor, 3.0)) / 3.0
    wfe = max(0.0, min(genome.walk_forward_efficiency, 1.0))

    fitness = (
        oos * 0.40
        + sortino * 0.15
        + dd_consistency * 0.10
        + win * 0.10
        + pf * 0.10
        + wfe * 0.15
    )
    return float(fitness)


# ---------------------------------------------------------------------------
# Evolution orchestrator
# ---------------------------------------------------------------------------

class HarnessEvolution:
    """
    Orchestrates grid-based evolution of strategy parameters.
    No LLM dependency. Uses grid sampling, crossover, and mutation.

    Ported from AgentQuant's harness_evolution_algo.
    """

    def __init__(
        self,
        families: list[str] | None = None,
        population_size: int = 20,
        generations: int = 5,
        n_splits: int = 5,
        train_ratio: float = 0.7,
        initial_cash: float = 100_000.0,
        slippage_bps: float = 5.0,
        mutation_rate: float = 0.3,
        crossover_rate: float = 0.5,
        elite_fraction: float = 0.2,
        random_seed: int | None = None,
    ):
        if families is None:
            families = list(DEFAULT_GRIDS.keys())

        self.families = families
        self.population_size = population_size
        self.generations = generations
        self.n_splits = n_splits
        self.train_ratio = train_ratio
        self.initial_cash = initial_cash
        self.slippage_bps = slippage_bps
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_fraction = elite_fraction
        self.rng = random.Random(random_seed)

        self.history: list[dict] = []
        self.best_genome: HarnessGenome | None = None

    def _init_population(self) -> list[HarnessGenome]:
        """Create initial population by random grid sampling."""
        pop = []
        for _ in range(self.population_size):
            family = self.rng.choice(self.families)
            params = sample_grid(family)
            pop.append(HarnessGenome(strategy_family=family, params=params))
        return pop

    def _evaluate(
        self,
        population: list[HarnessGenome],
        df: pd.DataFrame,
    ) -> list[HarnessGenome]:
        """Evaluate all genomes in the population via walk-forward."""
        for genome in population:
            wf = walk_forward_eval(
                df,
                genome.params,
                genome.strategy_family,
                n_splits=self.n_splits,
                train_ratio=self.train_ratio,
                initial_cash=self.initial_cash,
                slippage_bps=self.slippage_bps,
            )
            # Full-sample metrics for reference
            full = backtest_strategy(
                df,
                genome.params,
                genome.strategy_family,
                self.initial_cash,
                self.slippage_bps,
            )

            genome.sharpe_train = wf["train_sharpe"]
            genome.sharpe_test = wf["test_sharpe"]
            genome.walk_forward_efficiency = wf["walk_forward_efficiency"]
            genome.sortino = full["sortino"]
            genome.max_drawdown = full["max_drawdown"]
            genome.win_rate = full["win_rate"]
            genome.profit_factor = full["profit_factor"]
            genome.trade_count = full["trade_count"]
            genome.fitness = compute_fitness(genome)

        population.sort(key=lambda g: g.fitness, reverse=True)
        return population

    def _select_elites(self, population: list[HarnessGenome]) -> list[HarnessGenome]:
        """Select top-performing elites to survive to next generation."""
        n_elites = max(1, int(len(population) * self.elite_fraction))
        return [copy.deepcopy(g) for g in population[:n_elites]]

    def _breed_next_gen(
        self,
        elites: list[HarnessGenome],
        target_size: int,
    ) -> list[HarnessGenome]:
        """Create next generation via crossover and mutation of elites."""
        next_gen = list(elites)  # elites survive

        while len(next_gen) < target_size:
            if len(elites) >= 2 and self.rng.random() < self.crossover_rate:
                # Crossover
                parent_a = self.rng.choice(elites)
                parent_b = self.rng.choice(elites)
                child_params = crossover_grid_params(parent_a.params, parent_b.params)
                child_family = parent_a.strategy_family  # same family
                child = HarnessGenome(strategy_family=child_family, params=child_params)
            else:
                # Clone + mutate
                parent = self.rng.choice(elites)
                child_params = mutate_grid_params(
                    parent.params,
                    parent.strategy_family,
                    mutation_rate=self.mutation_rate,
                )
                child = HarnessGenome(
                    strategy_family=parent.strategy_family,
                    params=child_params,
                )

            next_gen.append(child)

        return next_gen[:target_size]

    def evolve(self, df: pd.DataFrame) -> HarnessGenome:
        """
        Run the full evolution loop.

        Args:
            df: DataFrame with OHLCV data for SPY.

        Returns:
            Best HarnessGenome found.
        """
        logger.info(
            "Starting harness evolution: pop=%d, gen=%d, families=%s",
            self.population_size,
            self.generations,
            self.families,
        )

        population = self._init_population()

        for gen in range(self.generations):
            population = self._evaluate(population, df)

            best = population[0]
            self.history.append({
                "generation": gen,
                "best_fitness": best.fitness,
                "best_sharpe_test": best.sharpe_test,
                "best_family": best.strategy_family,
                "avg_fitness": float(np.mean([g.fitness for g in population])),
                "population_size": len(population),
            })

            logger.info(
                "Gen %d: best=%.4f (sharpe_test=%.3f, family=%s, avg=%.4f)",
                gen,
                best.fitness,
                best.sharpe_test,
                best.strategy_family,
                self.history[-1]["avg_fitness"],
            )

            if gen < self.generations - 1:
                elites = self._select_elites(population)
                population = self._breed_next_gen(elites, self.population_size)

        # Final evaluation
        population = self._evaluate(population, df)
        self.best_genome = population[0]

        logger.info(
            "Evolution complete. Best: fitness=%.4f, sharpe_test=%.3f, family=%s",
            self.best_genome.fitness,
            self.best_genome.sharpe_test,
            self.best_genome.strategy_family,
        )

        return self.best_genome
